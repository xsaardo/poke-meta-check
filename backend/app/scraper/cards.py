"""Bulk card sync: fetches all cards from pokemontcg.io and stores them locally."""

import hashlib
import json
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Card, CardSet, CardSetMembership

logger = logging.getLogger(__name__)

POKEMONTCG_API = "https://api.pokemontcg.io/v2"
PAGE_SIZE = 250
BATCH_SIZE = 500


def _api_headers() -> dict:
    headers = {"User-Agent": "poke-meta/1.0"}
    if settings.pokemontcg_api_key:
        headers["X-Api-Key"] = settings.pokemontcg_api_key
    return headers


def _compute_card_group(card: dict) -> str:
    """Stable hash of a card's functional identity.

    Reprints (identical name/HP/attacks/abilities) share the same group.
    Cards that share a name but have different moves get distinct groups.
    """
    attacks = sorted(
        (a.get("name", "").strip(), a.get("text", "").strip(), a.get("damage", "").strip())
        for a in (card.get("attacks") or [])
    )
    abilities = sorted(
        (a.get("name", "").strip(), a.get("text", "").strip())
        for a in (card.get("abilities") or [])
    )
    rules = sorted(r.strip() for r in (card.get("rules") or []))

    fingerprint = json.dumps(
        {
            "name": card.get("name", "").strip().lower(),
            "hp": str(card.get("hp") or ""),
            "attacks": attacks,
            "abilities": abilities,
            "rules": rules,
        },
        sort_keys=True,
    )
    return hashlib.sha256(fingerprint.encode()).hexdigest()[:16]


def _derive_card_id(card: dict) -> str:
    """Derive a Limitless-compatible card ID: "{PTCGO_CODE}-{NUMBER}"."""
    set_info = card.get("set", {})
    # ptcgoCode matches the set code used by Limitless (e.g. "OBF", "SVI")
    ptcgo_code = set_info.get("ptcgoCode") or set_info.get("id", "").upper()
    number = card.get("number", "")
    return f"{ptcgo_code}-{number}"


async def sync_cards() -> dict:
    """Fetch all cards from pokemontcg.io, upsert into the local cards table."""
    headers = _api_headers()

    # Step 1: sync sets first
    await _sync_sets(headers)

    # Step 2: fetch all cards (paginated)
    logger.info("Fetching all cards from pokemontcg.io…")
    all_cards = []
    page = 1

    import asyncio as _asyncio
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            batch = []
            for attempt in range(4):
                try:
                    resp = await client.get(
                        f"{POKEMONTCG_API}/cards",
                        params={"pageSize": PAGE_SIZE, "page": page, "orderBy": "id"},
                        headers=headers,
                    )
                    resp.raise_for_status()
                    batch = resp.json().get("data", [])
                    break
                except Exception as exc:
                    wait = 5 * (attempt + 1)
                    logger.warning("Page %d attempt %d failed: %s — retrying in %ds", page, attempt + 1, exc, wait)
                    await _asyncio.sleep(wait)
            else:
                logger.error("Failed to fetch page %d after 4 attempts, stopping", page)
                break

            all_cards.extend(batch)
            logger.info("Fetched page %d: %d cards (total so far: %d)", page, len(batch), len(all_cards))

            if len(batch) < PAGE_SIZE:
                break
            page += 1
            await _asyncio.sleep(0.5)

    logger.info("Total cards fetched: %d", len(all_cards))

    # Step 3: upsert cards
    now = datetime.now(timezone.utc)
    by_id: dict[str, dict] = {}
    for card in all_cards:
        card_id = _derive_card_id(card)
        set_info = card.get("set", {})
        ptcgo_code = set_info.get("ptcgoCode") or set_info.get("id", "").upper()

        row = {
            "id": card_id,
            "name": card["name"],
            "supertype": card.get("supertype", ""),
            "subtypes": ",".join(card.get("subtypes") or []) or None,
            "set_code": ptcgo_code or None,
            "number": card.get("number") or None,
            "rarity": card.get("rarity") or None,
            "image_path": (card.get("images") or {}).get("small") or None,
            "card_group": _compute_card_group(card),
            "synced_at": now,
        }
        # Multiple sets can share a ptcgoCode (e.g. Hidden Fates + Shiny Vault),
        # producing the same card_id. Keep the entry with an image if possible.
        existing = by_id.get(card_id)
        if existing is None or (row["image_path"] and not existing["image_path"]):
            by_id[card_id] = row

    rows = list(by_id.values())

    async with AsyncSessionLocal() as session:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i: i + BATCH_SIZE]
            stmt = insert(Card).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": stmt.excluded.name,
                    "supertype": stmt.excluded.supertype,
                    "subtypes": stmt.excluded.subtypes,
                    "set_code": stmt.excluded.set_code,
                    "number": stmt.excluded.number,
                    "rarity": stmt.excluded.rarity,
                    "image_path": stmt.excluded.image_path,
                    "card_group": stmt.excluded.card_group,
                    "synced_at": stmt.excluded.synced_at,
                },
            )
            await session.execute(stmt)
        await session.commit()

    # Step 4: sync set memberships
    await _sync_card_set_memberships(all_cards)

    logger.info("Card sync complete: %d cards", len(rows))
    return {"cards": len(rows)}


async def _sync_sets(headers: dict) -> None:
    """Fetch all sets from pokemontcg.io and upsert into card_sets."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                f"{POKEMONTCG_API}/sets",
                params={"orderBy": "releaseDate", "pageSize": 500},
                headers=headers,
            )
            resp.raise_for_status()
            sets_data = resp.json().get("data", [])
        except Exception as exc:
            logger.error("Failed to fetch sets: %s", exc)
            return

    by_code: dict[str, dict] = {}
    for s in sets_data:
        ptcgo_code = s.get("ptcgoCode") or s.get("id", "").upper()
        release_raw = s.get("releaseDate")
        release_date = None
        if release_raw:
            try:
                from datetime import date
                release_date = date.fromisoformat(release_raw.replace("/", "-"))
            except ValueError:
                pass

        images = s.get("images") or {}
        row = {
            "id": s["id"],
            "code": ptcgo_code,
            "name": s.get("name", ""),
            "series": s.get("series") or None,
            "release_date": release_date,
            "total": s.get("total") or s.get("printedTotal") or None,
            "logo_url": images.get("logo") or None,
        }
        # When multiple sets share a ptcgoCode (e.g. Hidden Fates + Shiny Vault),
        # keep the one with more cards as the canonical entry for that code.
        existing = by_code.get(ptcgo_code)
        if existing is None or (row["total"] or 0) > (existing["total"] or 0):
            by_code[ptcgo_code] = row

    rows = list(by_code.values())
    if not rows:
        return

    async with AsyncSessionLocal() as session:
        stmt = insert(CardSet).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "code": stmt.excluded.code,
                "name": stmt.excluded.name,
                "series": stmt.excluded.series,
                "release_date": stmt.excluded.release_date,
                "total": stmt.excluded.total,
                "logo_url": stmt.excluded.logo_url,
            },
        )
        await session.execute(stmt)
        await session.commit()

    logger.info("Set sync complete: %d sets", len(rows))


async def _sync_card_set_memberships(all_cards: list[dict]) -> None:
    """Rebuild card→set membership records."""
    # Build (card_id, set_id) pairs using pokemontcg.io set ids
    memberships: list[tuple[str, str]] = []
    for card in all_cards:
        card_id = _derive_card_id(card)
        set_id = (card.get("set") or {}).get("id")
        if set_id:
            memberships.append((card_id, set_id))

    if not memberships:
        return

    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM card_set_memberships"))

        for i in range(0, len(memberships), BATCH_SIZE):
            batch = [
                {"card_id": cid, "set_id": sid}
                for cid, sid in memberships[i: i + BATCH_SIZE]
            ]
            stmt = insert(CardSetMembership).values(batch).on_conflict_do_nothing()
            await session.execute(stmt)

        await session.commit()

    logger.info(
        "Card set membership sync complete: %d memberships", len(memberships)
    )
