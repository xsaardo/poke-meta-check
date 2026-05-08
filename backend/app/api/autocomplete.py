"""Card autocomplete backed by the local cards table (with pokemontcg.io fallback)."""

from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Card

router = APIRouter()

CARD_API = "https://api.pokemontcg.io/v2/cards"


class CardSuggestion(BaseModel):
    id: str
    name: str
    supertype: str
    subtypes: Optional[str] = None
    set_code: Optional[str] = None
    card_number: Optional[str] = None
    image_url_small: str


async def _local_autocomplete(q: str, db: AsyncSession) -> list[CardSuggestion]:
    stmt = (
        select(Card)
        .where(Card.name.ilike(f"%{q}%"))
        .order_by(
            func.lower(Card.name).startswith(func.lower(q)).desc(),
            Card.name,
        )
        .limit(10)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        CardSuggestion(
            id=c.id,
            name=c.name,
            supertype=c.supertype,
            subtypes=c.subtypes,
            set_code=c.set_code,
            card_number=c.number,
            image_url_small=c.image_path or "",
        )
        for c in rows
    ]


async def _remote_autocomplete(q: str) -> list[CardSuggestion]:
    """Fallback: query pokemontcg.io when local card table is empty."""
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.get(
                CARD_API,
                params={"q": f'name:"{q}*"', "pageSize": 10, "orderBy": "name"},
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, KeyError, ValueError):
            return []

    suggestions = []
    for card in data.get("data", [])[:10]:
        images = card.get("images", {})
        image_url = images.get("small", "")
        set_code = card.get("set", {}).get("ptcgoCode") or card.get("set", {}).get("id", "").upper()
        suggestions.append(
            CardSuggestion(
                id=f"{set_code}-{card.get('number', '')}",
                name=card["name"],
                supertype=card.get("supertype", ""),
                subtypes=",".join(card.get("subtypes", [])) or None,
                set_code=set_code or None,
                card_number=card.get("number") or None,
                image_url_small=image_url,
            )
        )
    return suggestions


@router.get("/cards/{set_code}/{card_number}", response_model=CardSuggestion)
async def get_card(
    set_code: str,
    card_number: str,
    db: AsyncSession = Depends(get_db),
):
    card_id = f"{set_code.upper()}-{card_number}"
    row = (await db.execute(select(Card).where(Card.id == card_id))).scalar_one_or_none()
    if row is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Card not found")
    return CardSuggestion(
        id=row.id,
        name=row.name,
        supertype=row.supertype,
        subtypes=row.subtypes,
        set_code=row.set_code,
        card_number=row.number,
        image_url_small=row.image_path or "",
    )


@router.get("/autocomplete", response_model=list[CardSuggestion])
async def autocomplete(
    q: str = Query(..., min_length=2, max_length=255, description="Partial card name"),
    db: AsyncSession = Depends(get_db),
):
    try:
        count = (await db.execute(select(func.count()).select_from(Card))).scalar_one()
    except Exception:
        await db.rollback()
        return await _remote_autocomplete(q)

    if count > 0:
        return await _local_autocomplete(q, db)
    return await _remote_autocomplete(q)
