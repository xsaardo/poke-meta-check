"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cards",
        sa.Column("id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("supertype", sa.String(50), nullable=False),
        sa.Column("subtypes", sa.String(255), nullable=True),
        sa.Column("set_code", sa.String(20), nullable=True),
        sa.Column("number", sa.String(20), nullable=True),
        sa.Column("rarity", sa.String(100), nullable=True),
        sa.Column("image_path", sa.String(500), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cards_name", "cards", ["name"])
    op.create_index("ix_cards_set_code", "cards", ["set_code"])

    op.create_table(
        "card_sets",
        sa.Column("id", sa.String(50), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("series", sa.String(100), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("total", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_card_sets_code", "card_sets", ["code"])
    op.create_index("ix_card_sets_name", "card_sets", ["name"])

    op.create_table(
        "card_set_memberships",
        sa.Column("card_id", sa.String(50), nullable=False),
        sa.Column("set_id", sa.String(50), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"]),
        sa.ForeignKeyConstraint(["set_id"], ["card_sets.id"]),
        sa.PrimaryKeyConstraint("card_id", "set_id"),
    )
    op.create_index("ix_card_set_memberships_set_id", "card_set_memberships", ["set_id"])

    op.create_table(
        "tournaments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("limitless_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("format", sa.String(50), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("player_count", sa.Integer(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("limitless_id"),
    )
    op.create_index("ix_tournaments_limitless_id", "tournaments", ["limitless_id"])
    op.create_index("ix_tournaments_date", "tournaments", ["date"])

    op.create_table(
        "decks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("limitless_id", sa.String(100), nullable=False),
        sa.Column("archetype", sa.String(255), nullable=True),
        sa.Column("deck_url", sa.Text(), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("limitless_id"),
    )
    op.create_index("ix_decks_limitless_id", "decks", ["limitless_id"])

    op.create_table(
        "placements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("deck_id", sa.Integer(), nullable=True),
        sa.Column("placement", sa.Integer(), nullable=True),
        sa.Column("player_name", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"]),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_placements_tournament_id", "placements", ["tournament_id"])
    op.create_index("ix_placements_deck_id", "placements", ["deck_id"])

    op.create_table(
        "deck_cards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("deck_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.String(50), nullable=True),
        sa.Column("card_name", sa.String(255), nullable=False),
        sa.Column("set_code", sa.String(20), nullable=True),
        sa.Column("card_number", sa.String(20), nullable=True),
        sa.Column("supertype", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deck_cards_deck_id", "deck_cards", ["deck_id"])
    op.create_index("ix_deck_cards_card_id", "deck_cards", ["card_id"])
    op.create_index("ix_deck_cards_card_name", "deck_cards", ["card_name"])


def downgrade() -> None:
    op.drop_table("deck_cards")
    op.drop_table("placements")
    op.drop_table("decks")
    op.drop_table("tournaments")
    op.drop_table("card_set_memberships")
    op.drop_table("card_sets")
    op.drop_table("cards")
