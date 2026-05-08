"""Orchestrates the full scrape: tournaments → players/decklists → DB."""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Deck, DeckCard, Placement, Tournament
from app.scraper.client import make_client
from app.scraper.tournaments import (
    DeckData,
    TournamentRow,
    fetch_tournament_listing,
    fetch_tournament_players,
)

logger = logging.getLogger(__name__)


async def _upsert_tournament(session: AsyncSession, row: TournamentRow) -> Tournament:
    result = await session.execute(
        select(Tournament).where(Tournament.limitless_id == row.limitless_id)
    )
    tournament = result.scalar_one_or_none()
    if tournament is None:
        tournament = Tournament(
            limitless_id=row.limitless_id,
            name=row.name,
            date=row.date,
            country=row.country,
            player_count=row.player_count,
            format=row.format,
        )
        session.add(tournament)
    else:
        tournament.name = row.name
        tournament.country = row.country
        tournament.player_count = row.player_count
    await session.flush()
    return tournament


async def _upsert_deck(session: AsyncSession, deck_data: DeckData) -> Deck:
    result = await session.execute(
        select(Deck).where(Deck.limitless_id == deck_data.limitless_id)
    )
    deck = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if deck is None:
        deck = Deck(
            limitless_id=deck_data.limitless_id,
            archetype=deck_data.archetype,
            deck_url=deck_data.deck_url,
            scraped_at=now,
        )
        session.add(deck)
        await session.flush()

        for card in deck_data.cards:
            session.add(
                DeckCard(
                    deck_id=deck.id,
                    card_id=card.card_id,
                    card_name=card.card_name,
                    set_code=card.set_code,
                    card_number=card.card_number,
                    supertype=card.supertype,
                    quantity=card.quantity,
                )
            )
    await session.flush()
    return deck


async def _process_tournament(client, tournament_row: TournamentRow) -> None:
    """Fetch a single tournament's players/decklists and save to DB."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            tournament = await _upsert_tournament(session, tournament_row)

            existing = await session.execute(
                select(Placement)
                .where(Placement.tournament_id == tournament.id)
                .limit(1)
            )
            if existing.scalar_one_or_none():
                logger.debug(
                    "Tournament %s already has placements, skipping",
                    tournament_row.limitless_id,
                )
                return

            player_rows = await fetch_tournament_players(client, tournament_row.limitless_id)
            if not player_rows:
                tournament.scraped_at = datetime.now(timezone.utc)
                return

            for player_row in player_rows:
                deck: Deck | None = None
                if player_row.deck and player_row.deck.cards:
                    deck = await _upsert_deck(session, player_row.deck)

                session.add(
                    Placement(
                        tournament_id=tournament.id,
                        deck_id=deck.id if deck else None,
                        placement=player_row.placement,
                        player_name=player_row.player_name,
                    )
                )

            tournament.scraped_at = datetime.now(timezone.utc)

    logger.info("Saved tournament: %s", tournament_row.name)


async def run_scrape() -> dict:
    """Main entry point: scrape all recent PTCG tournaments."""
    logger.info("Starting scrape run")
    start = datetime.now(timezone.utc)

    async with make_client() as client:
        tournament_rows = await fetch_tournament_listing(client)
        logger.info(
            "Found %d tournaments in the last %d months",
            len(tournament_rows),
            settings.scraper_months_lookback,
        )

        sem = asyncio.Semaphore(settings.scraper_workers)

        async def process_with_sem(row):
            async with sem:
                try:
                    await _process_tournament(client, row)
                except Exception as e:
                    logger.error(
                        "Error processing tournament %s: %s", row.limitless_id, e
                    )

        await asyncio.gather(*[process_with_sem(row) for row in tournament_rows])

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info("Scrape complete in %.1fs", elapsed)
    return {
        "tournaments_found": len(tournament_rows),
        "elapsed_seconds": round(elapsed, 1),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
