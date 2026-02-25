#!/usr/bin/env python3
"""
Create admin user for Ngenda Hotel PMS
Run this after deploying the database
"""
import os
from app import create_app
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash

def create_admin():
    app = create_app()
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(email='admin@ngendahotel.com').first()
        if admin:
            print("⚠️  Admin user already exists")
            return
        
        user = User(
            email='admin@ngendahotel.com',
            name='Admin User',
            password_hash=generate_password_hash('Admin123!'),
            role='manager',
            hotel_id=1,
            is_superadmin=True
        )
        db.session.add(user)
        db.session.commit()
        print("✅ Admin user created!")
        print("\nLogin credentials:")
        print("  Email: admin@ngendahotel.com")
        print("  Password: Admin123!")
        print("\n⚠️  Change password after first login!")

if __name__ == '__main__':
    create_admin()
