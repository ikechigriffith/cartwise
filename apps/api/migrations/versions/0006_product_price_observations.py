"""add product price observations

Revision ID: 0006_price_observations
Revises: 0005_package_fields
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_price_observations"
down_revision = "0005_package_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_price_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("canonical_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retailer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("region_code", sa.String(length=50), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("price_per_unit", sa.Numeric(10, 4), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("raw_store_name", sa.String(length=300), nullable=True),
        sa.Column("raw_item_name", sa.String(length=500), nullable=True),
        sa.Column("match_confidence", sa.Float(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["canonical_product_id"], ["canonical_products.id"], name="fk_price_obs_canonical_product"),
        sa.ForeignKeyConstraint(["retailer_id"], ["retailers.id"], name="fk_price_obs_retailer"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], name="fk_price_obs_store"),
        sa.UniqueConstraint(
            "canonical_product_id",
            "store_id",
            "retailer_id",
            "observed_at",
            "source",
            "raw_store_name",
            name="uq_product_price_observations_source_point",
        ),
    )
    op.create_index("ix_product_price_observations_canonical_product_id", "product_price_observations", ["canonical_product_id"])
    op.create_index("ix_product_price_observations_retailer_id", "product_price_observations", ["retailer_id"])
    op.create_index("ix_product_price_observations_store_id", "product_price_observations", ["store_id"])
    op.create_index("ix_product_price_observations_region_code", "product_price_observations", ["region_code"])
    op.create_index("ix_product_price_observations_observed_at", "product_price_observations", ["observed_at"])
    op.create_index("ix_product_price_observations_source", "product_price_observations", ["source"])
    op.create_index("ix_product_price_observations_raw_store_name", "product_price_observations", ["raw_store_name"])
    op.create_index("ix_product_price_observations_raw_item_name", "product_price_observations", ["raw_item_name"])


def downgrade() -> None:
    op.drop_table("product_price_observations")
