"""Add password reset fields to users table

Revision ID: 9a0b1c2d3e4f
Revises: 20260215183436
Create Date: 2026-02-15 21:30:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a0b1c2d3e4f'
down_revision = '20260215183436'
branch_labels = None
depends_on = None


def upgrade():
    # Add password reset fields to users table
    op.add_column('users', sa.Column('reset_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('reset_token_expires', sa.DateTime(), nullable=True))


def downgrade():
    # Remove password reset fields from users table
    op.drop_column('users', 'reset_token_expires')
    op.drop_column('users', 'reset_token')