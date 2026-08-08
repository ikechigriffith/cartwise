"""add tradeind raw location fields

Revision ID: 0007_tradeind_location
Revises: 0006_price_observations
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_tradeind_location"
down_revision = "0006_price_observations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product_price_observations", sa.Column("raw_region", sa.String(length=100), nullable=True))
    op.add_column("product_price_observations", sa.Column("raw_area", sa.String(length=200), nullable=True))
    op.create_index("ix_product_price_observations_raw_region", "product_price_observations", ["raw_region"])
    op.create_index("ix_product_price_observations_raw_area", "product_price_observations", ["raw_area"])
    op.drop_constraint("uq_product_price_observations_source_point", "product_price_observations", type_="unique")
    op.create_unique_constraint(
        "uq_price_obs_source_location",
        "product_price_observations",
        ["canonical_product_id", "observed_at", "source", "source_url", "raw_region", "raw_area", "raw_store_name"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_price_obs_source_location", "product_price_observations", type_="unique")
    op.create_unique_constraint(
        "uq_product_price_observations_source_point",
        "product_price_observations",
        ["canonical_product_id", "store_id", "retailer_id", "observed_at", "source", "raw_store_name"],
    )
    op.drop_index("ix_product_price_observations_raw_area", table_name="product_price_observations")
    op.drop_index("ix_product_price_observations_raw_region", table_name="product_price_observations")
    op.drop_column("product_price_observations", "raw_area")
    op.drop_column("product_price_observations", "raw_region")
