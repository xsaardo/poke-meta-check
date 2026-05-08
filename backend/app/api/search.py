"""Card search and meta relevance API."""

from datetime import date, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Card, DeckCard, Deck, Placement, Tournament

router = APIRouter()


class DeckAppearance(BaseModel):
    tournament_name: str
    tournament_date: date
    tournament_url: str
    placement: Optional[int]
    player_name: Optional[str]
    deck_archetype: Optional[str]
    deck_url: str
    card_supertype: str
    card_quantity: int
    format: Optional[str] = None


class SearchResult(BaseModel):
    card_name: str
    meta_relevant: bool
    total_appearances: int
    results: list[DeckAppearance]


@router.get("/search", response_model=SearchResult)
async def search_card(
    card: str = Query(
        ..., min_length=2, max_length=255, description="Card name to search for"
    ),
    months: int = Query(3, ge=1, le=12, description="Lookback window in months"),
    supertype: Optional[Literal["Pokémon", "Trainer", "Energy"]] = Query(
        None, description="Filter by supertype: Pokémon, Trainer, Energy"
    ),
    set_code: Optional[str] = Query(None, description="Limit to a specific set printing"),
    card_number: Optional[str] = Query(None, description="Limit to a specific card number"),
    db: AsyncSession = Depends(get_db),
):
    cutoff = date.today() - timedelta(days=months * 30)

    stmt = (
        select(
            DeckCard.card_name,
            DeckCard.supertype,
            DeckCard.quantity,
            Deck.archetype,
            Deck.deck_url,
            Deck.limitless_id.label("deck_limitless_id"),
            Placement.placement,
            Placement.player_name,
            Tournament.name.label("tournament_name"),
            Tournament.date.label("tournament_date"),
            Tournament.limitless_id.label("tournament_limitless_id"),
            Tournament.format.label("tournament_format"),
        )
        .join(Deck, DeckCard.deck_id == Deck.id)
        .join(Placement, Placement.deck_id == Deck.id)
        .join(Tournament, Placement.tournament_id == Tournament.id)
        .where(func.lower(DeckCard.card_name) == func.lower(card))
        .where(Tournament.date >= cutoff)
        .order_by(Tournament.date.desc())
    )

    if supertype:
        stmt = stmt.where(DeckCard.supertype == supertype)

    if set_code and card_number:
        card_id_val = f"{set_code.upper()}-{card_number}"
        # Subquery: all card IDs that share the same functional group as the requested card.
        # Falls back gracefully if the card isn't in our DB (group subquery returns null).
        group_sq = select(Card.card_group).where(Card.id == card_id_val).scalar_subquery()
        group_ids_sq = select(Card.id).where(
            Card.card_group.isnot(None),
            Card.card_group == group_sq,
        )
        stmt = stmt.where(
            or_(
                # DeckCards with a card_id: match precisely via card_group
                DeckCard.card_id.in_(group_ids_sq),
                # DeckCards without a card_id: fall back to name match
                and_(DeckCard.card_id.is_(None), func.lower(DeckCard.card_name) == func.lower(card)),
            )
        )

    rows = (await db.execute(stmt)).all()

    appearances = [
        DeckAppearance(
            tournament_name=r.tournament_name,
            tournament_date=r.tournament_date,
            tournament_url=f"https://play.limitlesstcg.com/tournament/{r.tournament_limitless_id}/standings",
            placement=r.placement,
            player_name=r.player_name,
            deck_archetype=r.archetype,
            deck_url=f"https://play.limitlesstcg.com/tournament/{r.tournament_limitless_id}/player/{r.player_name}/decklist",
            card_supertype=r.supertype,
            card_quantity=r.quantity,
            format=r.tournament_format,
        )
        for r in rows
    ]

    return SearchResult(
        card_name=card,
        meta_relevant=len(appearances) > 0,
        total_appearances=len(appearances),
        results=appearances,
    )
