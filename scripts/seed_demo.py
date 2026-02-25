"""Create demo owner, hotel, manager. Run: python -m scripts.seed_demo"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_APP", "app")

from app import create_app
from app.extensions import db
from app.models.owner import Owner
from app.models.hotel import Hotel
from app.models.user import User
from werkzeug.security import generate_password_hash

def main():
    app = create_app()
    with app.app_context():
        owner = Owner.query.filter_by(email="owner@demo.com").first()
        if not owner:
            owner = Owner(name="Demo Owner", email="owner@demo.com")
            db.session.add(owner)
            db.session.flush()
        hotel = Hotel.query.filter_by(owner_id=owner.id, name="Demo Hotel").first()
        if not hotel:
            hotel = Hotel(owner_id=owner.id, name="Demo Hotel", location="City Center", currency="USD", timezone="UTC")
            db.session.add(hotel)
            db.session.flush()
        manager = User.query.filter_by(email="manager@demo.com").first()
        if not manager:
            manager = User(
                email="manager@demo.com",
                password_hash=generate_password_hash("manager123"),
                role="manager",
                hotel_id=hotel.id,
                owner_id=None,
                is_superadmin=False,
            )
            db.session.add(manager)
        db.session.commit()
        print("Demo data: owner@demo.com (create owner user manually if needed)")
        print("  Hotel: Demo Hotel (id=%s)" % hotel.id)
        print("  Manager: manager@demo.com / manager123")

if __name__ == "__main__":
    main()
