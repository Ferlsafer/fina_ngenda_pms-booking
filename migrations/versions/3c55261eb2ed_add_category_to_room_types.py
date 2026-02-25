"""add_category_to_room_types

Revision ID: 3c55261eb2ed
Revises: aa36be6f2865
Create Date: 2026-02-18 11:21:05.466694

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c55261eb2ed'
down_revision = 'aa36be6f2865'
branch_labels = None
depends_on = None


def upgrade():
    # Add category column to room_types table
    with op.batch_alter_table("room_types", schema=None) as batch_op:
        batch_op.add_column(sa.Column("category", sa.String(50), nullable=True))


def downgrade():
    # Remove category column from room_types table
    with op.batch_alter_table("room_types", schema=None) as batch_op:
        batch_op.drop_column("category")
