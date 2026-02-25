"""add_missing_columns_to_payments

Revision ID: bef10a7aecb5
Revises: c72c71ed8974
Create Date: 2026-02-18 13:10:29.282992

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bef10a7aecb5'
down_revision = 'c72c71ed8974'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to payments table
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("booking_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("payment_type", sa.String(20), nullable=True, server_default='full'))
        batch_op.add_column(sa.Column("transaction_id", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("status", sa.String(20), nullable=True, server_default='completed'))
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))
    
    # Add foreign key constraints
    op.execute("""
        ALTER TABLE payments 
        ADD CONSTRAINT fk_payments_booking_id 
        FOREIGN KEY (booking_id) REFERENCES bookings(id)
    """)


def downgrade():
    # Remove foreign key constraint and columns
    op.execute("ALTER TABLE payments DROP CONSTRAINT IF EXISTS fk_payments_booking_id")
    
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.drop_column("notes")
        batch_op.drop_column("status")
        batch_op.drop_column("transaction_id")
        batch_op.drop_column("payment_type")
        batch_op.drop_column("booking_id")
