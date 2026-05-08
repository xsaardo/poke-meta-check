from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Card(Base):
    __tablename__ = "cards"

    # String ID in format "{SET_CODE}-{NUMBER}", e.g. "OBF-125"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    supertype: Mapped[str] = mapped_column(String(50))   # "Pokémon", "Trainer", "Energy"
    subtypes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # CSV e.g. "Basic,V"
    set_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    rarity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # CDN URL
    card_group: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    limitless_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date, index=True)
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "Standard", "Expanded"
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    player_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    placements: Mapped[list["Placement"]] = relationship(back_populates="tournament")


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    limitless_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    archetype: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deck_url: Mapped[str] = mapped_column(Text)
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    placements: Mapped[list["Placement"]] = relationship(back_populates="deck")
    cards: Mapped[list["DeckCard"]] = relationship(
        back_populates="deck", cascade="all, delete-orphan"
    )


class Placement(Base):
    __tablename__ = "placements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    deck_id: Mapped[Optional[int]] = mapped_column(ForeignKey("decks.id"), nullable=True, index=True)
    placement: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # numeric rank e.g. 1, 2, 3
    player_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    tournament: Mapped["Tournament"] = relationship(back_populates="placements")
    deck: Mapped[Optional["Deck"]] = relationship(back_populates="placements")


class DeckCard(Base):
    __tablename__ = "deck_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deck_id: Mapped[int] = mapped_column(ForeignKey("decks.id"), index=True)
    card_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    card_name: Mapped[str] = mapped_column(String(255), index=True)
    set_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    card_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    supertype: Mapped[str] = mapped_column(String(50))  # "Pokémon", "Trainer", "Energy"
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    deck: Mapped["Deck"] = relationship(back_populates="cards")


class CardSet(Base):
    __tablename__ = "card_sets"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # pokemontcg.io id e.g. "sv3pt5"
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # PTCGO code e.g. "OBF"
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    series: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    release_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class CardSetMembership(Base):
    __tablename__ = "card_set_memberships"

    card_id: Mapped[str] = mapped_column(String(50), ForeignKey("cards.id"), primary_key=True)
    set_id: Mapped[str] = mapped_column(String(50), ForeignKey("card_sets.id"), primary_key=True, index=True)
