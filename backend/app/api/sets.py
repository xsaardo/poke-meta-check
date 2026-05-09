"""Card set browsing API — list sets and their meta-relevant cards."""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.database import get_db
from app.models import (
    Card,
    CardSet,
    CardSetMembership,
    DeckCard,
    Deck,
    Placement,
    Tournament,
)

router = APIRouter()


class SetSummary(BaseModel):
    name: str
    card_count: int
    meta_relevant_count: int
    logo_url: Optional[str] = None


class SetsResponse(BaseModel):
    sets: list[SetSummary]
    months: int


class SetCard(BaseModel):
    id: str
    name: str
    supertype: str
    subtypes: Optional[str]
    image_path: Optional[str]
    deck_count: int
    tournament_count: int


class SetCardsResponse(BaseModel):
    set_name: str
    months: int
    cards: list[SetCard]


@router.get("/sets", response_model=SetsResponse)
async def list_sets(
    months: int = Query(3, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    cutoff = date.today() - timedelta(days=months * 30)

    card_count_sq = (
        select(
            CardSetMembership.set_id,
            func.count(CardSetMembership.card_id).label("card_count"),
        )
        .group_by(CardSetMembership.set_id)
        .subquery()
    )

    GroupCard = aliased(Card, flat=True)
    meta_sq = (
        select(
            CardSetMembership.set_id,
            func.count(func.distinct(CardSetMembership.card_id)).label("meta_count"),
        )
        .join(Card, Card.id == CardSetMembership.card_id)
        # Find all cards in the same functional group (covers reprints)
        .join(
            GroupCard,
            and_(GroupCard.card_group == Card.card_group, GroupCard.card_group.isnot(None)),
        )
        .join(
            DeckCard,
            or_(
                DeckCard.card_id == GroupCard.id,
                and_(DeckCard.card_id.is_(None), func.lower(DeckCard.card_name) == func.lower(Card.name)),
            ),
        )
        .join(Deck, Deck.id == DeckCard.deck_id)
        .join(Placement, Placement.deck_id == Deck.id)
        .join(Tournament, Tournament.id == Placement.tournament_id)
        .where(Tournament.date >= cutoff)
        .group_by(CardSetMembership.set_id)
        .subquery()
    )

    stmt = (
        select(
            CardSet.name,
            CardSet.logo_url,
            func.coalesce(card_count_sq.c.card_count, 0).label("card_count"),
            func.coalesce(meta_sq.c.meta_count, 0).label("meta_relevant_count"),
        )
        .outerjoin(card_count_sq, card_count_sq.c.set_id == CardSet.id)
        .outerjoin(meta_sq, meta_sq.c.set_id == CardSet.id)
        .where(func.coalesce(card_count_sq.c.card_count, 0) > 0)
        .order_by(CardSet.release_date.desc().nulls_last(), CardSet.name)
    )

    rows = (await db.execute(stmt)).all()
    return SetsResponse(
        sets=[
            SetSummary(
                name=r.name,
                card_count=r.card_count,
                meta_relevant_count=r.meta_relevant_count,
                logo_url=r.logo_url,
            )
            for r in rows
        ],
        months=months,
    )


@router.get("/sets/{set_name}/cards", response_model=SetCardsResponse)
async def get_set_cards(
    set_name: str,
    months: int = Query(3, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    cutoff = date.today() - timedelta(days=months * 30)

    set_row = (
        await db.execute(select(CardSet).where(CardSet.name == set_name))
    ).scalar_one_or_none()
    if set_row is None:
        raise HTTPException(status_code=404, detail="Card set not found")

    GroupCard2 = aliased(Card, flat=True)
    stmt = (
        select(
            Card.id,
            Card.name,
            Card.supertype,
            Card.subtypes,
            Card.image_path,
            func.count(func.distinct(DeckCard.deck_id)).label("deck_count"),
            func.count(func.distinct(Tournament.id)).label("tournament_count"),
        )
        .join(CardSetMembership, CardSetMembership.card_id == Card.id)
        .join(CardSet, CardSet.id == CardSetMembership.set_id)
        # Expand to all cards in the same functional group (reprints)
        .outerjoin(
            GroupCard2,
            and_(GroupCard2.card_group == Card.card_group, GroupCard2.card_group.isnot(None)),
        )
        .outerjoin(
            DeckCard,
            or_(
                DeckCard.card_id == GroupCard2.id,
                and_(DeckCard.card_id.is_(None), func.lower(DeckCard.card_name) == func.lower(Card.name)),
            ),
        )
        .outerjoin(Deck, Deck.id == DeckCard.deck_id)
        .outerjoin(Placement, Placement.deck_id == Deck.id)
        .outerjoin(
            Tournament,
            (Tournament.id == Placement.tournament_id) & (Tournament.date >= cutoff),
        )
        .where(CardSet.name == set_name)
        .group_by(Card.id, Card.name, Card.supertype, Card.subtypes, Card.image_path)
        .order_by(
            func.count(func.distinct(Tournament.id)).desc(),
            func.count(func.distinct(DeckCard.deck_id)).desc(),
            Card.name,
        )
    )

    rows = (await db.execute(stmt)).all()
    return SetCardsResponse(
        set_name=set_name,
        months=months,
        cards=[
            SetCard(
                id=r.id,
                name=r.name,
                supertype=r.supertype,
                subtypes=r.subtypes,
                image_path=r.image_path,
                deck_count=r.deck_count,
                tournament_count=r.tournament_count,
            )
            for r in rows
        ],
    )
