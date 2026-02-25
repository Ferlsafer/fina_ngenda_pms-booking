"""Add name column to users

Revision ID: 20260215183436
Revises: add_hotel_branding_fields
Create Date: 2026-02-15 18:34:36.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '20260215183436'
down_revision = 'add_hotel_branding_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Check if columns already exist
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('bookings')]
    
    # Add columns to bookings only if they don't exist
    with op.batch_alter_table('bookings') as batch_op:
        if 'booking_reference' not in columns:
            batch_op.add_column(sa.Column('booking_reference', sa.String(length=50), nullable=True))
        
        if 'special_requests' not in columns:
            batch_op.add_column(sa.Column('special_requests', sa.Text(), nullable=True))
        
        if 'source' not in columns:
            batch_op.add_column(sa.Column('source', sa.String(length=50), nullable=True))
    
    # Create unique constraint
    try:
        op.create_unique_constraint('uq_bookings_booking_reference', 'bookings', ['booking_reference'])
    except:
        pass  # Constraint already exists

    # Add is_active to rooms
    room_columns = [col['name'] for col in inspector.get_columns('rooms')]
    with op.batch_alter_table('rooms') as batch_op:
        if 'is_active' not in room_columns:
            batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'))


def downgrade():
    # Remove columns from rooms
    with op.batch_alter_table('rooms') as batch_op:
        batch_op.drop_column('is_active')

    # Remove columns from bookings
    with op.batch_alter_table('bookings') as batch_op:
        batch_op.drop_constraint('uq_bookings_booking_reference', type_='unique')
        batch_op.drop_column('source')
        batch_op.drop_column('special_requests')
        batch_op.drop_column('booking_reference')
