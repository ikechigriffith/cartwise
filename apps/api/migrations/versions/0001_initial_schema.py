"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("default_start_location", postgresql.JSONB(), nullable=True),
        sa.Column("default_radius", sa.Float(), nullable=True),
        sa.Column("default_transit_mode", sa.String(length=50), nullable=True),
        sa.Column("substitution_preferences", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "retailers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("website_url", sa.Text(), nullable=True),
        sa.Column("integration_type", sa.String(length=50), nullable=False),
        sa.Column("loyalty_program_supported", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_retailers_name"),
    )
    op.create_index("ix_retailers_name", "retailers", ["name"])

    op.create_table(
        "product_families",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("subcategory", sa.String(length=100), nullable=True),
        sa.Column("common_aliases", postgresql.JSONB(), nullable=False),
        sa.Column("default_unit", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_product_families_name"),
    )
    op.create_index("ix_product_families_name", "product_families", ["name"])
    op.create_index("ix_product_families_category", "product_families", ["category"])
    op.create_index("ix_product_families_subcategory", "product_families", ["subcategory"])

    op.create_table(
        "stores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("retailer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("store_type", sa.String(length=50), nullable=False),
        sa.Column("address", postgresql.JSONB(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("service_capabilities", postgresql.JSONB(), nullable=False),
        sa.Column("store_hours", postgresql.JSONB(), nullable=True),
        sa.Column("transit_accessibility", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["retailer_id"], ["retailers.id"], name="fk_stores_retailer_id_retailers"),
    )
    op.create_index("ix_stores_retailer_id", "stores", ["retailer_id"])
    op.create_index("ix_stores_name", "stores", ["name"])

    op.create_table(
        "canonical_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_name", sa.String(length=300), nullable=False),
        sa.Column("brand", sa.String(length=150), nullable=True),
        sa.Column("is_store_brand", sa.Boolean(), nullable=False),
        sa.Column("owning_retailer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("barcode", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("subcategory", sa.String(length=100), nullable=True),
        sa.Column("size_value", sa.Float(), nullable=True),
        sa.Column("size_unit", sa.String(length=50), nullable=True),
        sa.Column("package_quantity", sa.Integer(), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=False),
        sa.Column("requirements_supported", postgresql.JSONB(), nullable=False),
        sa.Column("is_perishable", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_family_id"], ["product_families.id"], name="fk_canonical_products_product_family_id_product_families"),
        sa.ForeignKeyConstraint(["owning_retailer_id"], ["retailers.id"], name="fk_canonical_products_owning_retailer_id_retailers"),
        sa.UniqueConstraint("barcode", name="uq_canonical_products_barcode"),
    )
    op.create_index("ix_canonical_products_product_family_id", "canonical_products", ["product_family_id"])
    op.create_index("ix_canonical_products_canonical_name", "canonical_products", ["canonical_name"])
    op.create_index("ix_canonical_products_brand", "canonical_products", ["brand"])
    op.create_index("ix_canonical_products_barcode", "canonical_products", ["barcode"])
    op.create_index("ix_canonical_products_category", "canonical_products", ["category"])
    op.create_index("ix_canonical_products_subcategory", "canonical_products", ["subcategory"])

    op.create_table(
        "grocery_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_grocery_lists_user_id_users"),
    )
    op.create_index("ix_grocery_lists_user_id", "grocery_lists", ["user_id"])
    op.create_index("ix_grocery_lists_status", "grocery_lists", ["status"])

    op.create_table(
        "product_listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retailer_product_id", sa.String(length=200), nullable=True),
        sa.Column("raw_name", sa.String(length=500), nullable=False),
        sa.Column("raw_description", sa.Text(), nullable=True),
        sa.Column("raw_brand", sa.String(length=150), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("price_per_unit", sa.Numeric(10, 4), nullable=True),
        sa.Column("stock_availability", sa.String(length=50), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("price_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stock_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], name="fk_product_listings_store_id_stores"),
    )
    op.create_index("ix_product_listings_store_id", "product_listings", ["store_id"])
    op.create_index("ix_product_listings_retailer_product_id", "product_listings", ["retailer_product_id"])
    op.create_index("ix_product_listings_raw_name", "product_listings", ["raw_name"])

    op.create_table(
        "grocery_list_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("grocery_list_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("needed_amount", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("package_flexibility", sa.Boolean(), nullable=False),
        sa.Column("requirements", postgresql.JSONB(), nullable=False),
        sa.Column("preferences", postgresql.JSONB(), nullable=False),
        sa.Column("substitution_overrides", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["grocery_list_id"], ["grocery_lists.id"], name="fk_grocery_list_items_grocery_list_id_grocery_lists"),
        sa.ForeignKeyConstraint(["product_family_id"], ["product_families.id"], name="fk_grocery_list_items_product_family_id_product_families"),
    )
    op.create_index("ix_grocery_list_items_grocery_list_id", "grocery_list_items", ["grocery_list_id"])
    op.create_index("ix_grocery_list_items_product_family_id", "grocery_list_items", ["product_family_id"])

    op.create_table(
        "product_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("confidence_level", sa.String(length=20), nullable=False),
        sa.Column("mapping_method", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_listing_id"], ["product_listings.id"], name="fk_product_mappings_product_listing_id_product_listings"),
        sa.ForeignKeyConstraint(["canonical_product_id"], ["canonical_products.id"], name="fk_product_mappings_canonical_product_id_canonical_products"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], name="fk_product_mappings_reviewed_by_users"),
    )
    op.create_index("ix_product_mappings_product_listing_id", "product_mappings", ["product_listing_id"])
    op.create_index("ix_product_mappings_canonical_product_id", "product_mappings", ["canonical_product_id"])
    op.create_index("ix_product_mappings_confidence_level", "product_mappings", ["confidence_level"])
    op.create_index("ix_product_mappings_status", "product_mappings", ["status"])

    op.create_table(
        "proposed_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("grocery_list_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fulfillment_method", sa.String(length=50), nullable=False),
        sa.Column("primary_recommendation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("planned_start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("start_location", postgresql.JSONB(), nullable=False),
        sa.Column("end_location", postgresql.JSONB(), nullable=True),
        sa.Column("radius", sa.Float(), nullable=False),
        sa.Column("transit_mode", sa.String(length=50), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("freshness_labels", postgresql.JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["grocery_list_id"], ["grocery_lists.id"], name="fk_proposed_plans_grocery_list_id_grocery_lists"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_proposed_plans_user_id_users"),
    )
    op.create_index("ix_proposed_plans_grocery_list_id", "proposed_plans", ["grocery_list_id"])
    op.create_index("ix_proposed_plans_user_id", "proposed_plans", ["user_id"])

    op.create_table(
        "plan_alternatives",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("proposed_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("route", postgresql.JSONB(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("uses_uncertain_overrides", sa.Boolean(), nullable=False),
        sa.Column("confidence_notes", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["proposed_plan_id"], ["proposed_plans.id"], name="fk_plan_alternatives_proposed_plan_id_proposed_plans"),
    )
    op.create_index("ix_plan_alternatives_proposed_plan_id", "plan_alternatives", ["proposed_plan_id"])
    op.create_index("ix_plan_alternatives_type", "plan_alternatives", ["type"])

    op.create_table(
        "stops",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_alternative_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("estimated_arrival_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_departure_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("store_open_at_arrival", sa.Boolean(), nullable=True),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=True),
        sa.ForeignKeyConstraint(["plan_alternative_id"], ["plan_alternatives.id"], name="fk_stops_plan_alternative_id_plan_alternatives"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], name="fk_stops_store_id_stores"),
    )
    op.create_index("ix_stops_plan_alternative_id", "stops", ["plan_alternative_id"])
    op.create_index("ix_stops_store_id", "stops", ["store_id"])

    op.create_table(
        "item_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("stop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grocery_list_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("estimated_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_per_unit", sa.Numeric(10, 4), nullable=True),
        sa.Column("substitution_used", sa.Boolean(), nullable=False),
        sa.Column("requirements_satisfied", sa.Boolean(), nullable=False),
        sa.Column("preferences_honored", sa.Boolean(), nullable=False),
        sa.Column("freshness_label", sa.String(length=100), nullable=True),
        sa.Column("confidence_notes", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["stop_id"], ["stops.id"], name="fk_item_assignments_stop_id_stops"),
        sa.ForeignKeyConstraint(["grocery_list_item_id"], ["grocery_list_items.id"], name="fk_item_assignments_grocery_list_item_id_grocery_list_items"),
        sa.ForeignKeyConstraint(["canonical_product_id"], ["canonical_products.id"], name="fk_item_assignments_canonical_product_id_canonical_products"),
        sa.ForeignKeyConstraint(["product_listing_id"], ["product_listings.id"], name="fk_item_assignments_product_listing_id_product_listings"),
    )
    op.create_index("ix_item_assignments_stop_id", "item_assignments", ["stop_id"])
    op.create_index("ix_item_assignments_grocery_list_item_id", "item_assignments", ["grocery_list_item_id"])
    op.create_index("ix_item_assignments_canonical_product_id", "item_assignments", ["canonical_product_id"])
    op.create_index("ix_item_assignments_product_listing_id", "item_assignments", ["product_listing_id"])


def downgrade() -> None:
    op.drop_table("item_assignments")
    op.drop_table("stops")
    op.drop_table("plan_alternatives")
    op.drop_table("proposed_plans")
    op.drop_table("product_mappings")
    op.drop_table("grocery_list_items")
    op.drop_table("product_listings")
    op.drop_table("grocery_lists")
    op.drop_table("canonical_products")
    op.drop_table("stores")
    op.drop_table("product_families")
    op.drop_table("retailers")
    op.drop_table("users")
