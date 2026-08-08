"""add import tracking and store candidates

Revision ID: 0008_import_review
Revises: 0007_tradeind_location
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_import_review"
down_revision = "0007_tradeind_location"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("post_id", sa.String(length=100), nullable=True),
        sa.Column("post_url", sa.Text(), nullable=True),
        sa.Column("document_type", sa.String(length=50), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("file_sha256", sa.String(length=64), nullable=True),
        sa.Column("import_status", sa.String(length=50), nullable=False, server_default="discovered"),
        sa.Column("observations_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_url", name="uq_source_documents_source_url"),
    )
    for column in ["source", "post_id", "document_type", "observed_at", "file_sha256", "import_status"]:
        op.create_index(f"ix_source_documents_{column}", "source_documents", [column])

    op.create_table(
        "import_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_documents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("downloaded_documents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observations_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observations_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matched_store_observations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retailer_only_observations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unmatched_observations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ["source", "status", "started_at"]:
        op.create_index(f"ix_import_runs_{column}", "import_runs", [column])

    op.create_table(
        "store_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("raw_store_name", sa.String(length=300), nullable=False),
        sa.Column("normalized_name", sa.String(length=300), nullable=False),
        sa.Column("raw_area", sa.String(length=200), nullable=True),
        sa.Column("raw_region", sa.String(length=100), nullable=True),
        sa.Column("retailer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("matched_store_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="needs_review"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("observations_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["retailer_id"], ["retailers.id"], name="fk_store_candidates_retailer"),
        sa.ForeignKeyConstraint(["matched_store_id"], ["stores.id"], name="fk_store_candidates_matched_store"),
        sa.UniqueConstraint("source", "raw_store_name", "raw_area", "raw_region", name="uq_store_candidate_source_raw_location"),
    )
    for column in ["source", "raw_store_name", "normalized_name", "raw_area", "raw_region", "retailer_id", "matched_store_id", "status", "first_seen_at", "last_seen_at"]:
        op.create_index(f"ix_store_candidates_{column}", "store_candidates", [column])


def downgrade() -> None:
    op.drop_table("store_candidates")
    op.drop_table("import_runs")
    op.drop_table("source_documents")
