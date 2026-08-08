"""add product selection identity fields

Revision ID: 0010_product_selection_identity
Revises: 0009_store_review
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa


revision = "0010_product_selection_identity"
down_revision = "0009_store_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product_families", sa.Column("normalized_name", sa.String(length=300), nullable=True))
    op.add_column("product_families", sa.Column("selection_key", sa.String(length=300), nullable=True))
    op.create_index("ix_product_families_normalized_name", "product_families", ["normalized_name"])
    op.create_index("ix_product_families_selection_key", "product_families", ["selection_key"])

    op.add_column("canonical_products", sa.Column("normalized_name", sa.String(length=500), nullable=True))
    op.add_column("canonical_products", sa.Column("selection_key", sa.String(length=500), nullable=True))
    op.add_column("canonical_products", sa.Column("normalized_brand", sa.String(length=150), nullable=True))
    op.create_index("ix_canonical_products_normalized_name", "canonical_products", ["normalized_name"])
    op.create_index("ix_canonical_products_selection_key", "canonical_products", ["selection_key"])
    op.create_index("ix_canonical_products_normalized_brand", "canonical_products", ["normalized_brand"])

    op.add_column("product_listings", sa.Column("normalized_name", sa.String(length=500), nullable=True))
    op.add_column("product_listings", sa.Column("selection_key", sa.String(length=500), nullable=True))
    op.add_column("product_listings", sa.Column("normalized_brand", sa.String(length=150), nullable=True))
    op.create_index("ix_product_listings_normalized_name", "product_listings", ["normalized_name"])
    op.create_index("ix_product_listings_selection_key", "product_listings", ["selection_key"])
    op.create_index("ix_product_listings_normalized_brand", "product_listings", ["normalized_brand"])
    op.create_index(
        "uq_product_listings_source_store_retailer_product",
        "product_listings",
        ["source", "store_id", "retailer_product_id"],
        unique=True,
        postgresql_where=sa.text("retailer_product_id IS NOT NULL"),
    )

    op.create_unique_constraint(
        "uq_product_mappings_listing_canonical",
        "product_mappings",
        ["product_listing_id", "canonical_product_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_product_mappings_listing_canonical", "product_mappings", type_="unique")
    op.drop_index("uq_product_listings_source_store_retailer_product", table_name="product_listings")
    op.drop_index("ix_product_listings_normalized_brand", table_name="product_listings")
    op.drop_index("ix_product_listings_selection_key", table_name="product_listings")
    op.drop_index("ix_product_listings_normalized_name", table_name="product_listings")
    op.drop_column("product_listings", "normalized_brand")
    op.drop_column("product_listings", "selection_key")
    op.drop_column("product_listings", "normalized_name")

    op.drop_index("ix_canonical_products_normalized_brand", table_name="canonical_products")
    op.drop_index("ix_canonical_products_selection_key", table_name="canonical_products")
    op.drop_index("ix_canonical_products_normalized_name", table_name="canonical_products")
    op.drop_column("canonical_products", "normalized_brand")
    op.drop_column("canonical_products", "selection_key")
    op.drop_column("canonical_products", "normalized_name")

    op.drop_index("ix_product_families_selection_key", table_name="product_families")
    op.drop_index("ix_product_families_normalized_name", table_name="product_families")
    op.drop_column("product_families", "selection_key")
    op.drop_column("product_families", "normalized_name")
