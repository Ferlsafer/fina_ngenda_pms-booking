#!/usr/bin/env python3
"""Create test hotel and user for development."""
import sys
sys.path.insert(0, '.')

from app import create_app
from app.extensions import db
from app.models import Hotel, Owner, User, Room, RoomType
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Check existing data
    hotels = Hotel.query.all()
    print(f'Existing hotels: {len(hotels)}')
    for h in hotels:
        print(f'  - {h.name} (ID: {h.id})')

    # If no hotels, create test hotel
    if not hotels:
        # Create owner first
        owner = Owner(name='Test Owner', email='owner@ngendatest.com')
        db.session.add(owner)
        db.session.flush()
        
        # Create hotel
        hotel = Hotel(
            name='Ngenda Test Hotel',
            display_name='Ngenda Hotel & Apartments',
            location='Tanzania',
            address='Arusha, Tanzania',
            currency='TZS',
            phone='+255 123 456 789',
            email='info@ngendatest.com',
            owner_id=owner.id
        )
        db.session.add(hotel)
        db.session.flush()
        print(f'Created hotel: {hotel.name} (ID: {hotel.id})')
        
        # Create test user (manager)
        user = User(
            name='Test Manager',
            email='manager@ngendatest.com',
            password_hash=generate_password_hash('test123'),
            role='manager',
            hotel_id=hotel.id,
            owner_id=owner.id,
            is_superadmin=False,
            active=True
        )
        db.session.add(user)
        
        # Create test room types
        room_types = [
            RoomType(
                hotel_id=hotel.id,
                name='Classic Balcony Room',
                base_price=299000,
                capacity=3,
                size_sqm='30m²',
                bed_type='Double Bed',
                amenities=['AC', 'WiFi', 'Balcony', 'Mini Bar'],
                category='classic',
                short_description='Comfortable room with balcony',
                description='A cozy classic room featuring a private balcony with mountain views.',
                is_active=True
            ),
            RoomType(
                hotel_id=hotel.id,
                name='Superior Double Room',
                base_price=399000,
                capacity=3,
                size_sqm='35m²',
                bed_type='Double Bed',
                amenities=['AC', 'WiFi', 'Mini Bar', 'Room Service', 'Safe'],
                category='superior',
                short_description='Enhanced comfort with premium amenities',
                description='Spacious superior room with premium amenities and elegant decor.',
                is_active=True
            ),
            RoomType(
                hotel_id=hotel.id,
                name='Executive Master Suite',
                base_price=450000,
                capacity=2,
                size_sqm='55m²',
                bed_type='King Bed',
                amenities=['AC', 'WiFi', 'Mini Bar', 'Room Service', 'Safe', 'Bathtub', 'Mountain View'],
                category='executive',
                short_description='Luxury suite with separate living area',
                description='Our finest accommodation featuring a separate living area and luxury amenities.',
                is_active=True
            ),
            RoomType(
                hotel_id=hotel.id,
                name='Deluxe Double Room',
                base_price=350000,
                capacity=2,
                size_sqm='40m²',
                bed_type='Double Bed',
                amenities=['AC', 'WiFi', 'Mini Bar', 'Room Service'],
                category='deluxe',
                short_description='Modern deluxe room with all comforts',
                description='Well-appointed deluxe room perfect for business or leisure travelers.',
                is_active=True
            )
        ]
        for rt in room_types:
            db.session.add(rt)
        
        db.session.commit()
        
        print(f'Created test user: {user.email} / password: test123')
        print(f'Created {len(room_types)} room types')
        print('\n=== Test Data Created Successfully ===')
        print('Login URL: http://localhost:5000/hms/login')
        print('Email: manager@ngendatest.com')
        print('Password: test123')
    else:
        print('\nHotels already exist, skipping creation')
        print('Existing hotels:')
        for h in hotels:
            print(f'  - {h.name} (ID: {h.id})')
