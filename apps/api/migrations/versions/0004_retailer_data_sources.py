"""add retailer data sources

Revision ID: 0004_retailer_sources
Revises: 0003_store_refresh
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_retailer_sources"
down_revision = "0003_store_refresh"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retailer_data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("retailer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("has_product_catalog", sa.Boolean(), nullable=True),
        sa.Column("has_prices", sa.Boolean(), nullable=True),
        sa.Column("has_stock", sa.Boolean(), nullable=True),
        sa.Column("requires_login", sa.Boolean(), nullable=True),
        sa.Column("scrape_status", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.String(length=50), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["retailer_id"], ["retailers.id"], name="fk_retailer_data_sources_retailer_id_retailers"),
        sa.UniqueConstraint("retailer_id", "source_url", name="uq_retailer_data_sources_retailer_id_source_url"),
    )
    op.create_index("ix_retailer_data_sources_retailer_id", "retailer_data_sources", ["retailer_id"])
    op.create_index("ix_retailer_data_sources_scrape_status", "retailer_data_sources", ["scrape_status"])


def downgrade() -> None:
    op.drop_index("ix_retailer_data_sources_scrape_status", table_name="retailer_data_sources")
    op.drop_index("ix_retailer_data_sources_retailer_id", table_name="retailer_data_sources")
    op.drop_table("retailer_data_sources")
