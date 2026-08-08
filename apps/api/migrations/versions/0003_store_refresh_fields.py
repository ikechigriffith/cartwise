"""add store refresh fields

Revision ID: 0003_store_refresh
Revises: 0002_store_contact
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_store_refresh"
down_revision = "0002_store_contact"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("stores", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("stores", sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("stores", sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("stores", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_stores_is_active", "stores", ["is_active"])
    op.create_index("ix_stores_needs_review", "stores", ["needs_review"])


def downgrade() -> None:
    op.drop_index("ix_stores_needs_review", table_name="stores")
    op.drop_index("ix_stores_is_active", table_name="stores")
    op.drop_column("stores", "verified_at")
    op.drop_column("stores", "needs_review")
    op.drop_column("stores", "source_updated_at")
    op.drop_column("stores", "last_seen_at")
    op.drop_column("stores", "is_active")
