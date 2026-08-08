"""add product selection reviews

Revision ID: 0011_product_selection_reviews
Revises: 0010_product_selection_identity
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0011_product_selection_reviews"
down_revision = "0010_product_selection_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_selection_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("selection_key", sa.String(length=500), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("product_family_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canonical_products_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fields_changed", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_family_id"], ["product_families.id"], name="fk_product_selection_reviews_product_family"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], name="fk_product_selection_reviews_reviewed_by"),
    )
    for column in ["selection_key", "action", "product_family_id", "reviewed_by", "reviewed_at"]:
        op.create_index(f"ix_product_selection_reviews_{column}", "product_selection_reviews", [column])


def downgrade() -> None:
    op.drop_table("product_selection_reviews")
