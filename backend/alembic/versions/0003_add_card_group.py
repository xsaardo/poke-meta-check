"""add card_group to cards

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cards", sa.Column("card_group", sa.String(64), nullable=True))
    op.execute("UPDATE cards SET card_group = lower(name)")
    op.create_index("ix_cards_card_group", "cards", ["card_group"])


def downgrade() -> None:
    op.drop_index("ix_cards_card_group", table_name="cards")
    op.drop_column("cards", "card_group")
