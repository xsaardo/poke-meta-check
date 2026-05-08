import asyncio
import logging
import re
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import func, select

from app.api.autocomplete import router as autocomplete_router
from app.api.prices import router as prices_router
from app.api.scrape import router as scrape_router
from app.api.search import router as search_router
from app.api.sets import router as sets_router
from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Card, Tournament
from app.scraper.cards import sync_cards
from app.scraper.runner import run_scrape
from app.scraper.scheduler import init_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Pokemon TCG Meta Relevance API",
    description="Search for Pokemon TCG cards and check their tournament meta relevance.",
    version="1.0.0",
    docs_url="/docs" if settings.openapi_enabled else None,
    redoc_url="/redoc" if settings.openapi_enabled else None,
    openapi_url="/openapi.json" if settings.openapi_enabled else None,
)

_default_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
]
_extra_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(search_router, prefix="/api", tags=["search"])
app.include_router(autocomplete_router, prefix="/api", tags=["autocomplete"])
app.include_router(prices_router, prefix="/api", tags=["prices"])
app.include_router(scrape_router, prefix="/api", tags=["admin"])
app.include_router(sets_router, prefix="/api", tags=["sets"])

_BACKEND_DIR = Path(__file__).parent.parent


def _run_migrations() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=_BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        logger.info(result.stdout.strip())
    if result.returncode != 0:
        safe_stderr = re.sub(r"\w[\w+.-]*://[^\s]+", "[REDACTED_URL]", result.stderr)
        logger.error("Migration failed:\n%s", safe_stderr)
        raise RuntimeError(f"Alembic migration failed: {safe_stderr}")


@app.on_event("startup")
async def startup():
    logger.info("Running database migrations…")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_migrations)
    logger.info("Migrations complete.")

    init_scheduler()

    async def _maybe_sync_cards() -> None:
        try:
            async with AsyncSessionLocal() as session:
                count = (
                    await session.execute(select(func.count()).select_from(Card))
                ).scalar_one()
            if count == 0:
                logger.info("Cards table is empty — starting initial card sync…")
                await sync_cards()
                logger.info("Initial card sync complete.")
        except Exception:
            logger.exception("Initial card sync failed")

    asyncio.create_task(_maybe_sync_cards())

    async def _maybe_scrape() -> None:
        try:
            async with AsyncSessionLocal() as session:
                count = (
                    await session.execute(select(func.count()).select_from(Tournament))
                ).scalar_one()
            if count == 0:
                logger.info("Tournaments table is empty — starting initial scrape…")
                await run_scrape()
                logger.info("Initial scrape complete.")
        except Exception:
            logger.exception("Initial scrape failed")

    asyncio.create_task(_maybe_scrape())
    logger.info("Pokemon TCG Meta API started")


@app.on_event("shutdown")
async def shutdown():
    from app.scraper.scheduler import scheduler

    scheduler.shutdown()


@app.get("/health")
async def health():
    return {"status": "ok"}
