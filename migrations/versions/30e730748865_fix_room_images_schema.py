"""fix_room_images_schema

Revision ID: 30e730748865
Revises: bbb9b82f62f0
Create Date: 2026-02-18 11:30:02.887518

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '30e730748865'
down_revision = 'bbb9b82f62f0'
branch_labels = None
depends_on = None


def upgrade():
    # Fix room_images table schema using raw SQL
    op.execute("""
        ALTER TABLE room_images 
        ADD COLUMN image_filename VARCHAR(255)
    """)
    
    # Copy data from url to image_filename (extract filename from url)
    op.execute("""
        UPDATE room_images 
        SET image_filename = SUBSTRING(url FROM '[^/]+$') 
        WHERE url IS NOT NULL
    """)
    
    # Make image_filename not nullable after data migration
    op.execute("""
        ALTER TABLE room_images 
        ALTER COLUMN image_filename SET NOT NULL
    """)
    
    # Drop the old url column
    op.execute("""
        ALTER TABLE room_images 
        DROP COLUMN url
    """)


def downgrade():
    # Revert the changes using raw SQL
    # Add back the url column
    op.execute("""
        ALTER TABLE room_images 
        ADD COLUMN url VARCHAR(500)
    """)
    
    # Copy data from image_filename to url
    op.execute("""
        UPDATE room_images 
        SET url = '/static/uploads/rooms/' || image_filename 
        WHERE image_filename IS NOT NULL
    """)
    
    # Make url not nullable
    op.execute("""
        ALTER TABLE room_images 
        ALTER COLUMN url SET NOT NULL
    """)
    
    # Drop the image_filename column
    op.execute("""
        ALTER TABLE room_images 
        DROP COLUMN image_filename
    """)
