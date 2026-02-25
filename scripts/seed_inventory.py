"""Seed inventory categories and suppliers. Run: python -m scripts.seed_inventory"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_APP", "app")

from app import create_app
from app.extensions import db
from app.models.hotel import Hotel
from app.models.inventory import InventoryCategory, InventoryItem, Supplier


def main():
    app = create_app()
    with app.app_context():
        hotel = Hotel.query.first()
        if not hotel:
            print("No hotel found. Run seed_superadmin and seed_demo first.")
            sys.exit(1)

        # Create categories
        categories_data = [
            {"name": "Cleaning Supplies", "description": "Housekeeping cleaning products"},
            {"name": "Toiletries", "description": "Soap, shampoo, etc."},
            {"name": "Linens", "description": "Towels, sheets, pillowcases"},
            {"name": "Mini Bar", "description": "Drinks and snacks"},
            {"name": "Kitchen", "description": "Food and cooking supplies"},
        ]
        for cat_data in categories_data:
            existing = InventoryCategory.query.filter_by(
                hotel_id=hotel.id, name=cat_data["name"]
            ).first()
            if not existing:
                cat = InventoryCategory(
                    hotel_id=hotel.id,
                    name=cat_data["name"],
                    description=cat_data["description"],
                )
                db.session.add(cat)
        db.session.commit()
        print("Categories created")

        # Create suppliers
        suppliers_data = [
            {
                "name": "Hotel Supply Co",
                "contact": "John Smith",
                "email": "john@hotelsupply.com",
                "phone": "555-0101",
            },
            {
                "name": "Premium Linens",
                "contact": "Jane Doe",
                "email": "jane@premiumlinens.com",
                "phone": "555-0102",
            },
            {
                "name": "Beverage Distributors",
                "contact": "Bob Wilson",
                "email": "bob@beveragedist.com",
                "phone": "555-0103",
            },
        ]
        for sup_data in suppliers_data:
            existing = Supplier.query.filter_by(
                hotel_id=hotel.id, name=sup_data["name"]
            ).first()
            if not existing:
                supplier = Supplier(
                    hotel_id=hotel.id,
                    name=sup_data["name"],
                    contact_person=sup_data["contact"],
                    email=sup_data["email"],
                    phone=sup_data["phone"],
                )
                db.session.add(supplier)
        db.session.commit()
        print("Suppliers created")

        print("Database seeded successfully.")


if __name__ == "__main__":
    main()
