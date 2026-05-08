"""APScheduler weekly cron jobs for scraping and card sync."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.scraper.runner import run_scrape
from app.scraper.cards import sync_cards

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def init_scheduler():
    """Register weekly jobs. Both run every Sunday at 03:00 UTC."""
    scheduler.add_job(
        run_scrape,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=0, timezone="UTC"),
        id="weekly_scrape",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        sync_cards,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=30, timezone="UTC"),
        id="weekly_card_sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info(
        "Scheduler started — weekly scrape Sun 03:00 UTC, card sync Sun 03:30 UTC"
    )
