"""add regulation_mark to cards

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cards", sa.Column("regulation_mark", sa.String(10), nullable=True))
    op.create_index("ix_cards_regulation_mark", "cards", ["regulation_mark"])


def downgrade() -> None:
    op.drop_index("ix_cards_regulation_mark", table_name="cards")
    op.drop_column("cards", "regulation_mark")
