"""add_due_date_to_invoices

Revision ID: c72c71ed8974
Revises: 409e3662124e
Create Date: 2026-02-18 11:52:47.460292

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c72c71ed8974'
down_revision = '409e3662124e'
branch_labels = None
depends_on = None


def upgrade():
    # Add due_date column to invoices table
    with op.batch_alter_table("invoices", schema=None) as batch_op:
        batch_op.add_column(sa.Column("due_date", sa.Date(), nullable=True))


def downgrade():
    # Remove due_date column from invoices table
    with op.batch_alter_table("invoices", schema=None) as batch_op:
        batch_op.drop_column("due_date")
