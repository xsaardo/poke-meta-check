"""One-off script: backfill card_group for all cards missing a hash-format group."""
import asyncio
import httpx
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.scraper.cards import _derive_card_id, _compute_card_group, _api_headers, POKEMONTCG_API, PAGE_SIZE


async def backfill():
    headers = _api_headers()
    page = 1
    total_updated = 0

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            batch = []
            for attempt in range(3):
                try:
                    resp = await client.get(
                        f"{POKEMONTCG_API}/cards",
                        params={"pageSize": PAGE_SIZE, "page": page, "orderBy": "id"},
                        headers=headers,
                    )
                    resp.raise_for_status()
                    batch = resp.json().get("data", [])
                    break
                except Exception as e:
                    print(f"Page {page} attempt {attempt + 1} failed: {e}", flush=True)
                    await asyncio.sleep(5)
            else:
                print(f"Giving up on page {page}, stopping.", flush=True)
                break

            if not batch:
                break

            pairs = [(_derive_card_id(c), _compute_card_group(c)) for c in batch]
            placeholders = ", ".join(f"(:id_{i}, :grp_{i})" for i in range(len(pairs)))
            params = {}
            for i, (cid, grp) in enumerate(pairs):
                params[f"id_{i}"] = cid
                params[f"grp_{i}"] = grp

            sql = f"""
                UPDATE cards SET card_group = v.grp
                FROM (VALUES {placeholders}) AS v(cid, grp)
                WHERE cards.id = v.cid
            """

            async with AsyncSessionLocal() as session:
                result = await session.execute(text(sql), params)
                await session.commit()
                total_updated += result.rowcount

            print(f"Page {page}/{'-'}: updated {result.rowcount} rows (total {total_updated})", flush=True)

            if len(batch) < PAGE_SIZE:
                break
            page += 1
            await asyncio.sleep(0.3)

    print(f"Backfill complete: {total_updated} cards updated across {page} pages", flush=True)


if __name__ == "__main__":
    asyncio.run(backfill())
