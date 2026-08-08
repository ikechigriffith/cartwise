"""add store aliases and candidate reviews

Revision ID: 0009_store_review
Revises: 0008_import_review
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_store_review"
down_revision = "0008_import_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("raw_name", sa.String(length=300), nullable=False),
        sa.Column("normalized_name", sa.String(length=300), nullable=False),
        sa.Column("raw_area", sa.String(length=200), nullable=True),
        sa.Column("raw_region", sa.String(length=100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], name="fk_store_aliases_store"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], name="fk_store_aliases_approved_by"),
        sa.UniqueConstraint("source", "raw_name", "raw_area", "raw_region", name="uq_store_alias_source_raw_location"),
    )
    for column in ["store_id", "source", "raw_name", "normalized_name", "raw_area", "raw_region", "approved_by", "approved_at"]:
        op.create_index(f"ix_store_aliases_{column}", "store_aliases", [column])

    op.create_table(
        "store_candidate_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("existing_store_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_store_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fields_changed", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("observations_backfilled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["store_candidates.id"], name="fk_store_candidate_reviews_candidate"),
        sa.ForeignKeyConstraint(["existing_store_id"], ["stores.id"], name="fk_store_candidate_reviews_existing_store"),
        sa.ForeignKeyConstraint(["created_store_id"], ["stores.id"], name="fk_store_candidate_reviews_created_store"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], name="fk_store_candidate_reviews_reviewed_by"),
    )
    for column in ["candidate_id", "action", "existing_store_id", "created_store_id", "reviewed_by", "reviewed_at"]:
        op.create_index(f"ix_store_candidate_reviews_{column}", "store_candidate_reviews", [column])


def downgrade() -> None:
    op.drop_table("store_candidate_reviews")
    op.drop_table("store_aliases")
