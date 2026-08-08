"""add store source and contact fields

Revision ID: 0002_store_contact
Revises: 0001_initial_schema
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_store_contact"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("contact_info", postgresql.JSONB(), nullable=True))
    op.add_column("stores", sa.Column("external_source", sa.String(length=50), nullable=True))
    op.add_column("stores", sa.Column("external_id", sa.String(length=100), nullable=True))
    op.add_column("stores", sa.Column("raw_tags", postgresql.JSONB(), nullable=True))
    op.create_index("ix_stores_external_source", "stores", ["external_source"])
    op.create_index("ix_stores_external_id", "stores", ["external_id"])
    op.create_unique_constraint("uq_stores_external_source_external_id", "stores", ["external_source", "external_id"])


def downgrade() -> None:
    op.drop_constraint("uq_stores_external_source_external_id", "stores", type_="unique")
    op.drop_index("ix_stores_external_id", table_name="stores")
    op.drop_index("ix_stores_external_source", table_name="stores")
    op.drop_column("stores", "raw_tags")
    op.drop_column("stores", "external_id")
    op.drop_column("stores", "external_source")
    op.drop_column("stores", "contact_info")
