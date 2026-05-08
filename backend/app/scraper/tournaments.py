"""Fetch tournament listings and player standings from the Limitless TCG API."""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

import httpx

from app.config import settings
from app.scraper.client import LIMITLESS_API, HEADERS, fetch_json

logger = logging.getLogger(__name__)


@dataclass
class TournamentRow:
    limitless_id: str
    name: str
    date: date
    format: Optional[str]
    country: Optional[str]
    player_count: Optional[int]


@dataclass
class CardEntry:
    card_name: str
    set_code: Optional[str]
    card_number: Optional[str]
    card_id: Optional[str]  # "{SET_CODE}-{NUMBER}" if both available
    supertype: str
    quantity: int


@dataclass
class DeckData:
    limitless_id: str
    archetype: Optional[str]
    deck_url: str
    cards: list[CardEntry] = field(default_factory=list)


@dataclass
class PlacementRow:
    placement: Optional[int]
    player_name: Optional[str]
    deck: Optional[DeckData]


def _parse_date(raw: str) -> Optional[date]:
    # Handle ISO 8601 with optional time/timezone: "2026-05-07T02:00:00.000Z"
    # Grab just the date portion before any 'T'
    date_part = raw.split("T")[0].strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_part, fmt).date()
        except ValueError:
            continue
    logger.debug("Could not parse date %r", raw)
    return None


def _parse_card_entry(raw: dict) -> Optional[CardEntry]:
    """Parse a single card entry from the Limitless API decklist."""
    name = raw.get("name") or raw.get("card") or raw.get("cardName")
    if not name:
        return None

    quantity = raw.get("count") or raw.get("quantity") or raw.get("qty") or 1
    try:
        quantity = int(quantity)
    except (ValueError, TypeError):
        quantity = 1

    set_code = raw.get("set") or raw.get("setCode") or raw.get("setAbbr")
    number = raw.get("number") or raw.get("cardNumber") or raw.get("num")

    # Normalize set_code to uppercase
    if set_code:
        set_code = str(set_code).upper()
    if number:
        number = str(number)

    card_id = f"{set_code}-{number}" if set_code and number else None

    # Supertype: "Pokémon", "Trainer", "Energy"
    raw_type = raw.get("supertype") or raw.get("type") or raw.get("cardType") or ""
    raw_lower = raw_type.lower()
    if "pokemon" in raw_lower or "pokémon" in raw_lower:
        supertype = "Pokémon"
    elif "trainer" in raw_lower:
        supertype = "Trainer"
    elif "energy" in raw_lower:
        supertype = "Energy"
    else:
        # Fallback: Energy cards often have "Energy" in their name
        name_lower = name.lower()
        if "energy" in name_lower:
            supertype = "Energy"
        else:
            supertype = "Pokémon"

    return CardEntry(
        card_name=name,
        set_code=set_code,
        card_number=number,
        card_id=card_id,
        supertype=supertype,
        quantity=quantity,
    )


def _parse_player(raw: dict, tournament_limitless_id: str) -> PlacementRow:
    """Parse a player entry from /tournaments/{id}/standings."""
    name = raw.get("player") or raw.get("name") or raw.get("playerName")
    placing = raw.get("placing") or raw.get("placement") or raw.get("rank")
    try:
        placing = int(placing) if placing is not None else None
    except (ValueError, TypeError):
        placing = None

    # Decklist — present only when the organizer has published it.
    # The Limitless API returns decklist as {"pokemon": [...], "trainer": [...], "energy": [...]}
    raw_decklist = raw.get("decklist")
    deck: Optional[DeckData] = None

    if isinstance(raw_decklist, dict):
        cards: list[CardEntry] = []
        supertype_map = {"pokemon": "Pokémon", "trainer": "Trainer", "energy": "Energy"}
        for category, supertype in supertype_map.items():
            for entry in raw_decklist.get(category, []):
                if isinstance(entry, dict):
                    ce = _parse_card_entry({**entry, "supertype": supertype})
                    if ce:
                        cards.append(ce)
    elif isinstance(raw_decklist, list):
        cards = [ce for entry in raw_decklist if isinstance(entry, dict) and (ce := _parse_card_entry(entry))]
    else:
        cards = []

    if cards or raw_decklist:
        # Deduplicate by (card_name, supertype)
        aggregated: dict[tuple[str, str], CardEntry] = {}
        for c in cards:
            key = (c.card_name.lower(), c.supertype)
            if key in aggregated:
                aggregated[key].quantity += c.quantity
            else:
                aggregated[key] = c

        # Archetype from the dedicated deck object: {"id": "...", "name": "..."}
        raw_deck_obj = raw.get("deck")
        archetype = None
        deck_id = None
        if isinstance(raw_deck_obj, dict):
            archetype = raw_deck_obj.get("name") or raw_deck_obj.get("archetype")
            deck_id = raw_deck_obj.get("id")
        elif isinstance(raw_deck_obj, str):
            archetype = raw_deck_obj

        if not deck_id:
            deck_id = raw.get("deckId") or raw.get("listId") or f"{tournament_limitless_id}-{name or placing}"

        deck = DeckData(
            limitless_id=str(deck_id),
            archetype=str(archetype) if archetype else None,
            deck_url=f"https://limitlesstcg.com/decks/list/{deck_id}",
            cards=list(aggregated.values()),
        )

    return PlacementRow(
        placement=placing,
        player_name=name,
        deck=deck,
    )


MAX_PAGES = 50  # safety cap to prevent runaway pagination


async def fetch_tournament_listing(client: httpx.AsyncClient) -> list[TournamentRow]:
    """Fetch recent PTCG Standard tournaments from the Limitless TCG API.

    The Limitless API returns tournaments newest-first (page 1 = most recent).
    We paginate until we find a tournament older than the lookback cutoff.
    """
    cutoff = date.today() - timedelta(days=settings.scraper_months_lookback * 30)
    rows = []
    page = 1

    while page <= MAX_PAGES:
        data = await fetch_json(
            client,
            f"{LIMITLESS_API}/tournaments",
            params={"game": "PTCG", "format": "standard", "page": page},
        )
        if not data:
            break

        items = data if isinstance(data, list) else data.get("data", [])
        if not items:
            break

        if page == 1:
            logger.info("Limitless API first item keys: %s", list(items[0].keys()) if items else [])

        found_older = False
        for item in items:
            raw_date = item.get("date") or item.get("startDate") or item.get("eventDate")
            if not raw_date:
                logger.debug("Item missing date field: %s", item)
                continue
            parsed_date = _parse_date(str(raw_date))
            if parsed_date is None:
                continue
            if parsed_date < cutoff:
                found_older = True
                continue

            limitless_id = str(item.get("id") or item.get("tournamentId") or "")
            if not limitless_id:
                continue

            player_count = item.get("players") or item.get("playerCount") or 0
            if player_count < settings.scraper_min_players:
                continue

            rows.append(
                TournamentRow(
                    limitless_id=limitless_id,
                    name=item.get("name") or item.get("tournamentName") or "",
                    date=parsed_date,
                    format=(item.get("format") or "Standard").capitalize(),
                    country=item.get("country") or item.get("region"),
                    player_count=player_count,
                )
            )

        # Stop paginating once we've seen a tournament older than the cutoff
        if found_older or len(items) == 0:
            break
        page += 1

    if page > MAX_PAGES:
        logger.warning("Hit max pages limit (%d) — increase MAX_PAGES if needed", MAX_PAGES)

    logger.info("Fetched %d tournaments from Limitless API (since %s)", len(rows), cutoff)
    return rows


async def fetch_tournament_players(
    client: httpx.AsyncClient, tournament_id: str
) -> list[PlacementRow]:
    """Fetch final standings for a tournament, returning only placed players."""
    data = await fetch_json(
        client,
        f"{LIMITLESS_API}/tournaments/{tournament_id}/standings",
    )
    if not data:
        return []

    players = data if isinstance(data, list) else data.get("data", [])
    placed = [p for p in players if isinstance(p, dict) and p.get("placing") is not None and p["placing"] <= 32]
    result = [_parse_player(p, tournament_id) for p in placed]
    logger.info("Tournament %s: %d placed players fetched", tournament_id, len(result))
    return result
