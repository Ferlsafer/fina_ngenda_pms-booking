#!/usr/bin/env python3
"""
Seed additional staff roles: Receptionist, Housekeeping, Kitchen
Run: python -m scripts.seed_staff_roles
"""
from app import create_app
from app.extensions import db
from app.models import User, Role, Hotel
from werkzeug.security import generate_password_hash


def create_roles():
    """Create standard hotel roles with permissions"""
    roles_data = [
        {
            'name': 'receptionist',
            'description': 'Front desk staff - bookings, check-in/out, guest management',
            'permissions': {
                'bookings': ['view', 'create', 'edit'],
                'guests': ['view', 'create', 'edit'],
                'rooms': ['view'],
                'dashboard': ['view'],
                'restaurant': ['view', 'create'],
                'accounting': ['view'],
            }
        },
        {
            'name': 'housekeeping',
            'description': 'Room cleaning and maintenance',
            'permissions': {
                'housekeeping': ['view', 'edit'],
                'rooms': ['view', 'edit_status'],
                'dashboard': ['view'],
                'inventory': ['view'],
            }
        },
        {
            'name': 'kitchen',
            'description': 'Restaurant and room service kitchen',
            'permissions': {
                'restaurant': ['view', 'kitchen'],
                'room_service': ['view', 'prepare'],
                'dashboard': ['view'],
            }
        },
        {
            'name': 'housekeeping_manager',
            'description': 'Manage housekeeping staff and tasks',
            'permissions': {
                'housekeeping': ['view', 'create', 'edit', 'delete'],
                'rooms': ['view', 'edit_status'],
                'staff': ['view'],
                'dashboard': ['view'],
                'inventory': ['view', 'edit'],
            }
        },
        {
            'name': 'restaurant_manager',
            'description': 'Manage restaurant operations',
            'permissions': {
                'restaurant': ['view', 'create', 'edit', 'delete'],
                'room_service': ['view', 'create', 'edit'],
                'menu': ['view', 'create', 'edit', 'delete'],
                'dashboard': ['view'],
                'accounting': ['view'],
            }
        }
    ]
    
    created_roles = []
    for role_data in roles_data:
        role = Role.query.filter_by(name=role_data['name']).first()
        if not role:
            role = Role(
                name=role_data['name'],
                description=role_data['description'],
                permissions=role_data['permissions']
            )
            db.session.add(role)
            created_roles.append(role)
            print(f"✓ Created role: {role.name}")
        else:
            role.description = role_data['description']
            role.permissions = role_data['permissions']
            created_roles.append(role)
            print(f"✓ Updated role: {role.name}")
    
    db.session.commit()
    return {r.name: r for r in created_roles}


def create_staff_users(hotel_id, roles):
    """Create sample staff users for a hotel"""
    users_data = [
        {
            'name': 'Sarah Johnson',
            'email': 'receptionist@demo.com',
            'password': 'receptionist123',
            'role': roles['receptionist'],
            'description': 'Front desk receptionist'
        },
        {
            'name': 'Maria Garcia',
            'email': 'housekeeping@demo.com',
            'password': 'housekeeping123',
            'role': roles['housekeeping'],
            'description': 'Housekeeping staff'
        },
        {
            'name': 'John Chef',
            'email': 'kitchen@demo.com',
            'password': 'kitchen123',
            'role': roles['kitchen'],
            'description': 'Kitchen staff'
        },
        {
            'name': 'Linda Smith',
            'email': 'housekeeping.manager@demo.com',
            'password': 'hkmanager123',
            'role': roles['housekeeping_manager'],
            'description': 'Housekeeping manager'
        },
        {
            'name': 'Robert Brown',
            'email': 'restaurant.manager@demo.com',
            'password': 'restmanager123',
            'role': roles['restaurant_manager'],
            'description': 'Restaurant manager'
        }
    ]
    
    created_users = []
    for user_data in users_data:
        user = User.query.filter_by(email=user_data['email']).first()
        if not user:
            user = User(
                name=user_data['name'],
                email=user_data['email'],
                password_hash=generate_password_hash(user_data['password']),
                role=user_data['role'].name,
                role_id=user_data['role'].id,
                hotel_id=hotel_id,
                active=True
            )
            db.session.add(user)
            created_users.append(user)
            print(f"✓ Created user: {user.name} ({user.email}) - {user_data['description']}")
        else:
            # Update existing user
            user.name = user_data['name']
            user.role = user_data['role'].name
            user.role_id = user_data['role'].id
            user.hotel_id = hotel_id
            created_users.append(user)
            print(f"✓ Updated user: {user.name} ({user.email})")
    
    db.session.commit()
    return created_users


def main():
    app = create_app()
    with app.app_context():
        print("=== Seeding Staff Roles and Users ===\n")
        
        # Get the demo hotel
        hotel = Hotel.query.filter_by(name='Demo Hotel').first()
        if not hotel:
            hotel = Hotel.query.first()
        
        if not hotel:
            print("✗ No hotel found. Please run seed_demo.py first.")
            return
        
        print(f"Using hotel: {hotel.name} (ID: {hotel.id})\n")
        
        # Create roles
        roles = create_roles()
        print()
        
        # Create staff users
        users = create_staff_users(hotel.id, roles)
        print()
        
        print("=== Staff Credentials ===\n")
        print("Role                  | Email                              | Password")
        print("-" * 80)
        for user in users:
            print(f"{user.role:21} | {user.email:32} | {user.role}123")
        
        print("\n=== Complete ===")


if __name__ == '__main__':
    main()
