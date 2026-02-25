#!/usr/bin/env python3
from app import create_app
from app.models import RestaurantTable, MenuItem, Hotel

app = create_app()
with app.app_context():
    hotel = Hotel.query.first()
    if hotel:
        print(f"✅ Hotel found: {hotel.name}")
        tables = RestaurantTable.query.filter_by(hotel_id=hotel.id).count()
        print(f"{'✅' if tables > 0 else '❌'} Tables: {tables}")
        items = MenuItem.query.filter_by(hotel_id=hotel.id, is_available=True).count()
        print(f"{'✅' if items > 0 else '❌'} Menu items: {items}")
        if tables == 0:
            print("\n⚠️ NO TABLES - Go to Restaurant → Tables to add!")
        if items == 0:
            print("\n⚠️ NO MENU ITEMS - Go to Restaurant → Menu to add!")
    else:
        print("❌ NO HOTEL - Create hotel first!")
