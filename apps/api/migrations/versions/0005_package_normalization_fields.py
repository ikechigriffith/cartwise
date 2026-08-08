"""add package normalization fields

Revision ID: 0005_package_fields
Revises: 0004_retailer_sources
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_package_fields"
down_revision = "0004_retailer_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product_listings", sa.Column("package_quantity", sa.Float(), nullable=True))
    op.add_column("product_listings", sa.Column("unit_size_value", sa.Float(), nullable=True))
    op.add_column("product_listings", sa.Column("unit_size_unit", sa.String(length=50), nullable=True))
    op.add_column("product_listings", sa.Column("total_size_value", sa.Float(), nullable=True))
    op.add_column("product_listings", sa.Column("total_size_unit", sa.String(length=50), nullable=True))
    op.add_column("product_listings", sa.Column("normalized_size_value", sa.Float(), nullable=True))
    op.add_column("product_listings", sa.Column("normalized_size_unit", sa.String(length=50), nullable=True))
    op.add_column("product_listings", sa.Column("computed_price_per_unit", sa.Numeric(10, 4), nullable=True))
    op.add_column("product_listings", sa.Column("computed_price_unit", sa.String(length=50), nullable=True))
    op.add_column("product_listings", sa.Column("unit_price_confidence", sa.String(length=50), nullable=True))
    op.add_column("product_listings", sa.Column("unit_price_needs_review", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("product_listings", "unit_price_needs_review")
    op.drop_column("product_listings", "unit_price_confidence")
    op.drop_column("product_listings", "computed_price_unit")
    op.drop_column("product_listings", "computed_price_per_unit")
    op.drop_column("product_listings", "normalized_size_unit")
    op.drop_column("product_listings", "normalized_size_value")
    op.drop_column("product_listings", "total_size_unit")
    op.drop_column("product_listings", "total_size_value")
    op.drop_column("product_listings", "unit_size_unit")
    op.drop_column("product_listings", "unit_size_value")
    op.drop_column("product_listings", "package_quantity")
