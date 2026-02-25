#!/usr/bin/env python3
"""Create sample rooms for each room type."""
import sys
sys.path.insert(0, '.')

from app import create_app
from app.extensions import db
from app.models import Room, RoomType

app = create_app()

with app.app_context():
    room_types = RoomType.query.filter_by(is_active=True).all()
    
    print(f'Found {len(room_types)} room types')
    
    # Create rooms for each type
    rooms_to_create = {
        'Classic': 5,
        'Superior': 4,
        'Executive': 3,
        'Deluxe': 4
    }
    
    for rt in room_types:
        # Find how many rooms to create
        count = 3  # default
        for key, num in rooms_to_create.items():
            if key.lower() in rt.name.lower():
                count = num
                break
        
        # Check existing rooms
        existing = Room.query.filter_by(room_type_id=rt.id).count()
        print(f'\n{rt.name}: {existing} existing rooms')
        
        # Create rooms if needed
        for i in range(existing, count):
            room_number = f"{rt.category[:3].upper()}{101 + i}" if rt.category else f"RM{101 + i}"
            room = Room(
                hotel_id=1,
                room_type_id=rt.id,
                room_number=room_number,
                status='Vacant',
                is_active=True
            )
            db.session.add(room)
            print(f'  + Created room {room_number}')
    
    db.session.commit()
    print('\n✓ Rooms created successfully!')
    
    # Summary
    for rt in room_types:
        rooms = Room.query.filter_by(room_type_id=rt.id).all()
        print(f'\n{rt.name}:')
        for r in rooms:
            print(f'  - {r.room_number} ({r.status})')
