"""
Add parent_order_id column to restaurant_orders table
Phase 1.4 Split Bill Support
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Check if column exists
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'restaurant_orders' 
            AND column_name = 'parent_order_id'
        """)).fetchone()
        
        if result:
            print("✅ Column 'parent_order_id' already exists")
        else:
            print("Adding 'parent_order_id' column to restaurant_orders table...")
            db.session.execute(text("""
                ALTER TABLE restaurant_orders 
                ADD COLUMN parent_order_id INTEGER
            """))
            db.session.commit()
            print("✅ Column 'parent_order_id' added successfully")
        
        # Also add 'split' to status check constraint if using PostgreSQL
        print("\nNote: You may need to manually update the status CHECK constraint")
        print("to include 'split' as a valid value if your database uses constraints.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.session.rollback()
        import traceback
        traceback.print_exc()
        sys.exit(1)
