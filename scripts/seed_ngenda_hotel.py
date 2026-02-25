#!/usr/bin/env python3
"""
Seed Ngenda Hotel & Apartments for website integration.
Run from project root: python scripts/seed_ngenda_hotel.py
Or: flask shell < scripts/seed_ngenda_hotel.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from app.models.owner import Owner
from app.models.hotel import Hotel
from app.models.room import RoomType, Room, RoomImage

app = create_app()

ROOMS_DATA = [
    {
        "name": "Classic Room",
        "category": "classic",
        "price": 80000,
        "size": "25",
        "capacity": 2,
        "bed_type": "Double Bed",
        "description": "Comfortable classic room with modern amenities",
        "short_description": "Comfortable classic room with modern amenities",
        "amenities": ["AC", "Netflix", "WiFi", "Work Desk"],
    },
    {
        "name": "Superior Room",
        "category": "superior",
        "price": 120000,
        "size": "35",
        "capacity": 3,
        "bed_type": "King Bed + Single",
        "description": "Spacious superior room with city view",
        "short_description": "Spacious superior room with city view",
        "amenities": ["AC", "Netflix", "WiFi", "Mini Bar", "Work Desk"],
    },
    {
        "name": "Deluxe Suite",
        "category": "deluxe",
        "price": 180000,
        "size": "50",
        "capacity": 4,
        "bed_type": "King Bed + Sofa Bed",
        "description": "Luxurious suite with separate living area",
        "short_description": "Luxurious suite with separate living area",
        "amenities": ["AC", "Netflix", "WiFi", "Mini Bar", "Kitchen", "Work Desk"],
    },
    {
        "name": "Executive Suite",
        "category": "executive",
        "price": 250000,
        "size": "70",
        "capacity": 4,
        "bed_type": "King Bed + Double",
        "description": "Premium executive suite with panoramic views",
        "short_description": "Premium executive suite with panoramic views",
        "amenities": ["AC", "Netflix", "WiFi", "Mini Bar", "Full Kitchen", "Work Desk", "Balcony"],
    },
]


def main():
    with app.app_context():
        owner = Owner.query.filter_by(email="owner@ngendahotel.com").first()
        if not owner:
            owner = Owner(
                name="Ngenda Group",
                email="owner@ngendahotel.com",
            )
            db.session.add(owner)
            db.session.flush()
            print("✅ Created owner: Ngenda Group")

        hotel = Hotel.query.filter_by(name="Ngenda Hotel & Apartments").first()
        if not hotel:
            hotel = Hotel(
                owner_id=owner.id,
                name="Ngenda Hotel & Apartments",
                address="Isyesye–Hayanga",
                city="Mbeya",
                country="Tanzania",
                phone="+255671271247",
                contact_email="info@ngendahotel.com",
                currency="TZS",
            )
            db.session.add(hotel)
            db.session.commit()
            print("✅ Created Ngenda Hotel & Apartments")
        else:
            print("ℹ️ Ngenda Hotel already exists")

        for data in ROOMS_DATA:
            room_type = RoomType.query.filter_by(
                hotel_id=hotel.id,
                name=data["name"],
            ).first()

            if not room_type:
                room_type = RoomType(
                    hotel_id=hotel.id,
                    name=data["name"],
                    description=data["description"],
                    short_description=data["short_description"],
                    base_price=data["price"],
                    capacity=data["capacity"],
                    size_sqm=data["size"],
                    bed_type=data["bed_type"],
                    amenities=data["amenities"],
                    is_active=True,
                )
                db.session.add(room_type)
                db.session.flush()
                print(f"✅ Created room type: {data['name']}")

                for i in range(1, 6):
                    room = Room(
                        hotel_id=hotel.id,
                        room_type_id=room_type.id,
                        room_number=f"{data['category'][0].upper()}{i:02d}",
                        status="Vacant",
                        is_active=True,
                    )
                    db.session.add(room)
                print(f"   Added 5 rooms")

        db.session.commit()
        print("\n🎉 Ngenda Hotel seeded successfully!")
        print(f"   Hotel ID: {hotel.id} (set NGENDA_HOTEL_ID={hotel.id} in .env if needed)")


if __name__ == "__main__":
    main()
