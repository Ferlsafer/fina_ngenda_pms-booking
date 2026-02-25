#!/usr/bin/env python3
"""Seed initial data for testing"""

from app import create_app
from app.models import Owner, Hotel, User
from app.extensions import db
from werkzeug.security import generate_password_hash

def seed_data():
    app = create_app()
    with app.app_context():
        print('Creating initial data...')
        
        # Check if data already exists
        if User.query.filter_by(email='admin@hotel.com').first():
            print('Admin user already exists, skipping seed.')
            return
        
        # Create owner
        owner = Owner(name='Demo Owner', email='owner@demo.com')
        db.session.add(owner)
        db.session.flush()
        
        # Create hotel
        hotel = Hotel(
            owner_id=owner.id, 
            name='Demo Hotel', 
            display_name='Ngenda Hotel',
            location='Dar es Salaam, Tanzania'
        )
        db.session.add(hotel)
        db.session.flush()
        
        # Create admin user (super admin - no hotel_id)
        admin = User(
            email='admin@hotel.com',
            password_hash=generate_password_hash('admin123'),
            name='Admin User',
            role='admin',
            hotel_id=None
        )
        db.session.add(admin)
        
        # Create hotel manager
        manager = User(
            email='manager@demo.com',
            password_hash=generate_password_hash('manager123'),
            name='Hotel Manager',
            role='manager',
            hotel_id=hotel.id
        )
        db.session.add(manager)
        
        db.session.commit()
        print('Initial data created successfully!')
        print('Login credentials:')
        print('  Admin: admin@hotel.com / admin123')
        print('  Manager: manager@demo.com / manager123')

if __name__ == '__main__':
    seed_data()
