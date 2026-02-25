"""add_price_usd_to_room_types

Revision ID: aa36be6f2865
Revises: add_performance_indexes
Create Date: 2026-02-18 11:20:00.285473

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aa36be6f2865'
down_revision = 'add_performance_indexes'
branch_labels = None
depends_on = None


def upgrade():
    # Add price_usd column to room_types table
    with op.batch_alter_table("room_types", schema=None) as batch_op:
        batch_op.add_column(sa.Column("price_usd", sa.Numeric(12, 2), nullable=True))


def downgrade():
    # Remove price_usd column from room_types table
    with op.batch_alter_table("room_types", schema=None) as batch_op:
        batch_op.drop_column("price_usd")
