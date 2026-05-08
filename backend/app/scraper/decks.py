"""Deck data structures — deck content comes from the Limitless TCG /players API response."""

# Re-export the dataclasses defined in tournaments.py for backward-compat imports
from app.scraper.tournaments import CardEntry, DeckData, PlacementRow  # noqa: F401
