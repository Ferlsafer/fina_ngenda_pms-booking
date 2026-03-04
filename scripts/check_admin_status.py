#!/usr/bin/env python3
"""
PRE-CHECK: Show current admin user and roles status
SAFE TO RUN - Read-only, makes no changes

Run: python scripts/check_admin_status.py
"""
import sys
from app import create_app
from app.extensions import db
from app.models import User, Role


def check_status():
    """Check and display admin user and role status"""
    try:
        app = create_app()
    except Exception as e:
        print(f"❌ ERROR: Failed to create app: {e}")
        print("   Make sure you're in the project directory and virtualenv is activated.")
        sys.exit(1)
    
    with app.app_context():
        print("=" * 60)
        print("ADMIN USER STATUS CHECK")
        print("=" * 60)
        print()
        
        # Check if admin role exists
        try:
            admin_role = Role.query.filter_by(name='admin').first()
        except Exception as e:
            print(f"❌ ERROR: Failed to query roles: {e}")
            sys.exit(1)
        
        print("1. Admin Role in Database:")
        if admin_role:
            print(f"   ✅ EXISTS - ID: {admin_role.id}, Name: {admin_role.name}")
        else:
            print(f"   ❌ NOT FOUND - Need to run add_admin_role.py")
        print()
        
        # Find admin user
        try:
            admin_user = User.query.filter_by(email='admin@ngendahotel.com').first()
            
            if not admin_user:
                admin_user = User.query.filter_by(is_superadmin=True).first()
        except Exception as e:
            print(f"❌ ERROR: Failed to query users: {e}")
            sys.exit(1)
        
        print("2. Admin User:")
        if admin_user:
            print(f"   ✅ FOUND")
            print(f"      ID: {admin_user.id}")
            print(f"      Name: {admin_user.name}")
            print(f"      Email: {admin_user.email}")
            print(f"      Current role: {admin_user.role}")
            print(f"      Current role_id: {admin_user.role_id}")
            print(f"      Is superadmin: {admin_user.is_superadmin}")
            
            if admin_user.role == 'admin' and admin_user.role_id:
                print(f"\n   ✅ User is already using the admin role!")
                print(f"      You should be able to edit this user in the UI.")
            else:
                print(f"\n   ⚠️  User needs to be updated to admin role")
                print(f"      Run: python scripts/update_admin_role.py")
        else:
            print(f"   ❌ No admin user found!")
            print(f"      Check if admin user was created during deployment.")
        print()
        
        # List all roles
        try:
            print("3. All Roles in Database:")
            roles = Role.query.all()
            for role in roles:
                marker = " ← ADMIN ROLE" if role.name == 'admin' else ""
                print(f"   - {role.id}: {role.name}{marker}")
            
            if not roles:
                print("   (No roles found)")
        except Exception as e:
            print(f"   ❌ ERROR: Failed to list roles: {e}")
        print()
        
        print("=" * 60)
        print("RECOMMENDED ACTIONS:")
        print("=" * 60)
        
        if not admin_role:
            print("1. Run: python scripts/add_admin_role.py")
            print("2. Run: python scripts/update_admin_role.py")
            print("3. Run: sudo systemctl restart booking-hms")
        elif admin_user and admin_user.role != 'admin':
            print("1. Run: python scripts/update_admin_role.py")
            print("2. Run: sudo systemctl restart booking-hms")
        elif not admin_user:
            print("⚠️  No admin user found. Check deployment.")
        else:
            print("✅ Everything looks good! No action needed.")
        
        print()


if __name__ == '__main__':
    check_status()
