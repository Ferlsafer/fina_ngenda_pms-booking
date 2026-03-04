#!/usr/bin/env python3
"""
Add missing 'admin' and 'superadmin' roles to the database.
This fixes the issue where superadmin cannot edit their own profile.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app, db
from app.models import Role, User

def add_admin_roles():
    app = create_app()
    with app.app_context():
        # Check existing roles
        existing_roles = {r.name.lower(): r for r in Role.query.all()}
        print(f"Existing roles: {list(existing_roles.keys())}")
        
        # Roles to add
        admin_roles = [
            ('superadmin', 'System Administrator - Full access to all properties and settings'),
            ('admin', 'Property Administrator - Full access to property operations'),
        ]
        
        for role_name, description in admin_roles:
            if role_name.lower() not in existing_roles:
                role = Role(name=role_name, description=description)
                db.session.add(role)
                print(f"✓ Added role: {role_name}")
            else:
                print(f"  Role already exists: {role_name}")
        
        db.session.commit()
        
        # Verify roles
        print("\n=== All Roles ===")
        for role in Role.query.order_by(Role.id).all():
            print(f"  ID: {role.id}, Name: {role.name}")
        
        # Fix superadmin users - assign them to the new superadmin role
        superadmin_role = Role.query.filter_by(name='superadmin').first()
        if superadmin_role:
            superadmin_users = User.query.filter_by(is_superadmin=True).all()
            for user in superadmin_users:
                if user.role_id is None or user.role != 'superadmin':
                    user.role_id = superadmin_role.id
                    user.role = 'superadmin'
                    print(f"✓ Fixed superadmin user: {user.email}")
            
            db.session.commit()
        
        print("\n✓ Done! Superadmin can now edit their profile.")

if __name__ == '__main__':
    add_admin_roles()
