"""add retailer contact info column

Revision ID: 0012_add_retailer_contact_info
Revises: 0011_product_selection_reviews
Create Date: 2026-08-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0012_add_retailer_contact_info"
down_revision = "0011_product_selection_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("retailers", sa.Column("contact_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("retailers", "contact_info")
