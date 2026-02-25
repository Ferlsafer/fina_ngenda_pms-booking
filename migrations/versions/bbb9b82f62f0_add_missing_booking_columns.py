"""add_missing_booking_columns

Revision ID: bbb9b82f62f0
Revises: 3c55261eb2ed
Create Date: 2026-02-18 11:23:20.735706

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bbb9b82f62f0'
down_revision = '3c55261eb2ed'
branch_labels = None
depends_on = None


def upgrade():
    # Add only missing columns to bookings table
    with op.batch_alter_table("bookings", schema=None) as batch_op:
        # Guest info columns (missing)
        batch_op.add_column(sa.Column("guest_name", sa.String(255), nullable=False))
        batch_op.add_column(sa.Column("guest_email", sa.String(255), nullable=False))
        batch_op.add_column(sa.Column("guest_phone", sa.String(50), nullable=False))
        
        # Room assignment columns (missing room_type_requested)
        batch_op.add_column(sa.Column("room_type_requested", sa.String(100), nullable=True))
        
        # Date/time columns (missing)
        batch_op.add_column(sa.Column("check_in_time_actual", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("check_out_time_actual", sa.DateTime(), nullable=True))
        
        # Pricing columns (missing)
        batch_op.add_column(sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False))
        batch_op.add_column(sa.Column("balance", sa.Numeric(12, 2), nullable=False))
        
        # Requests and notes (missing)
        batch_op.add_column(sa.Column("internal_notes", sa.Text(), nullable=True))
        
        # Website-specific fields (missing)
        batch_op.add_column(sa.Column("ip_address", sa.String(45), nullable=True))
        batch_op.add_column(sa.Column("user_agent", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("referral_source", sa.String(255), nullable=True))
        
        # Timestamp columns (missing)
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("confirmed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("cancelled_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("cancellation_reason", sa.Text(), nullable=True))


def downgrade():
    # Remove all the added columns
    with op.batch_alter_table("bookings", schema=None) as batch_op:
        batch_op.drop_column("cancellation_reason")
        batch_op.drop_column("cancelled_at")
        batch_op.drop_column("confirmed_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("referral_source")
        batch_op.drop_column("user_agent")
        batch_op.drop_column("ip_address")
        batch_op.drop_column("internal_notes")
        batch_op.drop_column("balance")
        batch_op.drop_column("amount_paid")
        batch_op.drop_column("check_out_time_actual")
        batch_op.drop_column("check_in_time_actual")
        batch_op.drop_column("room_type_requested")
        batch_op.drop_column("guest_phone")
        batch_op.drop_column("guest_email")
        batch_op.drop_column("guest_name")
