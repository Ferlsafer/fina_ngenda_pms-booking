#!/usr/bin/env python3
"""
Update existing admin user to use the admin role
Run AFTER add_admin_role.py

PRODUCTION SAFE - Requires confirmation before making changes

Run: python scripts/update_admin_role.py
"""
import sys
from app import create_app
from app.extensions import db
from app.models import User, Role


def update_admin_user():
    """Update admin user to use the admin role"""
    try:
        app = create_app()
    except Exception as e:
        print(f"❌ ERROR: Failed to create app: {e}")
        print("   Make sure you're in the project directory and virtualenv is activated.")
        sys.exit(1)
    
    with app.app_context():
        try:
            # Find admin role
            admin_role = Role.query.filter_by(name='admin').first()
            
            if not admin_role:
                print("❌ Admin role not found!")
                print("   Please run: python scripts/add_admin_role.py first")
                return False
            
            # Find admin user (by email or is_superadmin flag)
            admin_user = User.query.filter_by(email='admin@ngendahotel.com').first()
            
            if not admin_user:
                # Try finding any superadmin
                admin_user = User.query.filter_by(is_superadmin=True).first()
            
            if not admin_user:
                print("❌ No admin user found!")
                print("   Check if admin user was created during deployment.")
                return False
            
            # Check if already updated
            if admin_user.role == 'admin' and admin_user.role_id == admin_role.id:
                print("✅ Admin user is already using the admin role!")
                print(f"   User: {admin_user.name} ({admin_user.email})")
                print(f"   Role: {admin_user.role} (ID: {admin_user.role_id})")
                print("\nNo changes needed. You can proceed to restart the service.")
                return True
            
            # Show what will be updated
            print("=" * 60)
            print("UPDATE ADMIN USER")
            print("=" * 60)
            print()
            print("Found admin user:\n")
            print(f"  ID: {admin_user.id}")
            print(f"  Name: {admin_user.name}")
            print(f"  Email: {admin_user.email}")
            print(f"  Current role: {admin_user.role}")
            print(f"  Current role_id: {admin_user.role_id}")
            print(f"\nWill update to:")
            print(f"  New role: admin")
            print(f"  New role_id: {admin_role.id}")
            print(f"\n⚠️  This will allow editing the admin user through the UI.")
            print(f"⚠️  Type 'YES' to confirm: ", end='')
            sys.stdout.flush()
            confirm = input().strip()
            
            if confirm != 'YES':
                print("\n❌ Cancelled. No changes made.")
                return False
            
            # Update the admin user's role
            admin_user.role = 'admin'
            admin_user.role_id = admin_role.id
            
            db.session.commit()
            
            print("\n✅ Admin user updated successfully!")
            print(f"  New role: {admin_user.role}")
            print(f"  New role_id: {admin_user.role_id}")
            print("\n🎉 You can now edit the admin user through the User Management UI!")
            print("   Go to: Settings → Users → Edit (admin user)")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERROR: Failed to update admin user: {e}")
            print("   No changes were made to the database.")
            return False


if __name__ == '__main__':
    success = update_admin_user()
    sys.exit(0 if success else 1)
