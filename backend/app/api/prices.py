"""Card price proxy — scrapes Limitless TCG card pages with 1-hour in-memory cache."""

import re
import time
from collections import OrderedDict
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

LIMITLESS_CARD_URL = "https://limitlesstcg.com/cards"
CACHE_TTL = 3600
CACHE_MAX_SIZE = 5000


class _BoundedCache:
    def __init__(self, maxsize: int) -> None:
        self._maxsize = maxsize
        self._store: OrderedDict[str, tuple[float, "CardPrices"]] = OrderedDict()

    def get(self, key: str) -> "CardPrices | None":
        if key not in self._store:
            return None
        ts, value = self._store[key]
        if time.monotonic() - ts >= CACHE_TTL:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: "CardPrices") -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (time.monotonic(), value)
        if len(self._store) > self._maxsize:
            self._store.popitem(last=False)


_cache = _BoundedCache(maxsize=CACHE_MAX_SIZE)


class CardPrices(BaseModel):
    tcgplayer: Optional[str] = None
    cardmarket: Optional[str] = None


def _extract_prices(html: str) -> CardPrices:
    soup = BeautifulSoup(html, "lxml")
    tcgplayer = None
    cardmarket = None

    # Limitless shows prices as text like "TCGPlayer $0.25" or "Cardmarket €0.08"
    # They appear in anchor tags or text nodes near price labels
    text = soup.get_text(" ", strip=True)

    tcg_match = re.search(r"TCGPlayer\s*\$\s*([\d,.]+)", text, re.IGNORECASE)
    if tcg_match:
        tcgplayer = tcg_match.group(1)

    cm_match = re.search(r"Cardmarket\s*€\s*([\d,.]+)", text, re.IGNORECASE)
    if cm_match:
        cardmarket = cm_match.group(1)

    return CardPrices(tcgplayer=tcgplayer, cardmarket=cardmarket)


@router.get("/prices/{set_code}/{card_number}", response_model=CardPrices)
async def get_prices(set_code: str, card_number: str):
    cache_key = f"{set_code}/{card_number}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"{LIMITLESS_CARD_URL}/{set_code}/{card_number}"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                follow_redirects=True,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Card not found")
            raise HTTPException(status_code=502, detail="Price fetch failed")
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Price fetch failed")

    prices = _extract_prices(resp.text)
    _cache.set(cache_key, prices)
    return prices
