"""Website integration: RoomType Room Booking RoomImage fields

Revision ID: c1f2a3b4c5d6
Revises: 1784ac28345f
Create Date: 2026-02-15

"""
from alembic import op
import sqlalchemy as sa


revision = "c1f2a3b4c5d6"
down_revision = "8a47e4b66718"
branch_labels = None
depends_on = None


def upgrade():
    # RoomType: description, short_description, capacity, size_sqm, bed_type, amenities, is_active
    with op.batch_alter_table("room_types", schema=None) as batch_op:
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("short_description", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("capacity", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("size_sqm", sa.String(20), nullable=True))
        batch_op.add_column(sa.Column("bed_type", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("amenities", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=True))

    # Room: is_active
    with op.batch_alter_table("rooms", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=True))

    # RoomImage
    op.create_table(
        "room_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("room_type_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["room_type_id"], ["room_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Booking: adults, children, source, booking_reference, special_requests
    with op.batch_alter_table("bookings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("adults", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("children", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("source", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("booking_reference", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("special_requests", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("bookings", schema=None) as batch_op:
        batch_op.drop_column("special_requests")
        batch_op.drop_column("booking_reference")
        batch_op.drop_column("source")
        batch_op.drop_column("children")
        batch_op.drop_column("adults")

    op.drop_table("room_images")

    with op.batch_alter_table("rooms", schema=None) as batch_op:
        batch_op.drop_column("is_active")

    with op.batch_alter_table("room_types", schema=None) as batch_op:
        batch_op.drop_column("is_active")
        batch_op.drop_column("amenities")
        batch_op.drop_column("bed_type")
        batch_op.drop_column("size_sqm")
        batch_op.drop_column("capacity")
        batch_op.drop_column("short_description")
        batch_op.drop_column("description")
