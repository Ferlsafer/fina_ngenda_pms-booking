#!/usr/bin/env python3
"""
Add admin role to the roles table
This allows editing admin users through the UI

PRODUCTION SAFE - Requires confirmation before making changes

Run: python scripts/add_admin_role.py
"""
import sys
from app import create_app
from app.extensions import db
from app.models import Role


def add_admin_role():
    """Add admin role to database"""
    try:
        app = create_app()
    except Exception as e:
        print(f"❌ ERROR: Failed to create app: {e}")
        print("   Make sure you're in the project directory and virtualenv is activated.")
        sys.exit(1)
    
    with app.app_context():
        try:
            # Check if admin role already exists
            admin_role = Role.query.filter_by(name='admin').first()
            
            if admin_role:
                print("✅ Admin role already exists!")
                print(f"   ID: {admin_role.id}, Name: {admin_role.name}")
                print("\nNo changes needed. You can proceed to update_admin_role.py")
                return True
            
            # Show what will be created
            print("=" * 60)
            print("ADD ADMIN ROLE TO DATABASE")
            print("=" * 60)
            print()
            print("This will create the following role in the database:\n")
            print("  Name: admin")
            print("  Description: System administrator - full access to all features")
            print()
            print("This is SAFE and will NOT affect existing users or data.")
            print("It only adds a new role option to the roles table.")
            print()
            print("⚠️  Type 'YES' to confirm creation: ", end='')
            sys.stdout.flush()
            confirm = input().strip()
            
            if confirm != 'YES':
                print("\n❌ Cancelled. No changes made.")
                return False
            
            # Create admin role with full permissions
            admin_role = Role(
                name='admin',
                description='System administrator - full access to all features',
                permissions={
                    'users': ['view', 'create', 'edit', 'delete'],
                    'bookings': ['view', 'create', 'edit', 'delete'],
                    'guests': ['view', 'create', 'edit', 'delete'],
                    'rooms': ['view', 'create', 'edit', 'delete'],
                    'dashboard': ['view'],
                    'restaurant': ['view', 'create', 'edit', 'delete'],
                    'accounting': ['view', 'create', 'edit', 'delete'],
                    'reports': ['view'],
                    'settings': ['view', 'edit'],
                    'inventory': ['view', 'create', 'edit', 'delete'],
                    'housekeeping': ['view', 'create', 'edit', 'delete'],
                }
            )
            
            db.session.add(admin_role)
            db.session.commit()
            
            print("\n✅ Admin role created successfully!")
            print(f"\nRole details:")
            print(f"  ID: {admin_role.id}")
            print(f"  Name: {admin_role.name}")
            print(f"  Description: {admin_role.description}")
            print("\nNext step: Run 'python scripts/update_admin_role.py'")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERROR: Failed to create admin role: {e}")
            print("   No changes were made to the database.")
            return False


if __name__ == '__main__':
    success = add_admin_role()
    sys.exit(0 if success else 1)
