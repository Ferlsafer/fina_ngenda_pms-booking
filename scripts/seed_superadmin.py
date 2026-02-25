"""Create a superadmin user for testing. Run from project root: python -m scripts.seed_superadmin"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_APP", "app")

from app import create_app
from app.extensions import db
from app.models.user import User
from werkzeug.security import generate_password_hash

def main():
    app = create_app()
    with app.app_context():
        if User.query.filter_by(email="admin@hotel.com").first():
            print("Superadmin already exists.")
            return
        u = User(
            email="admin@hotel.com",
            password_hash=generate_password_hash("admin123"),
            role="superadmin",
            is_superadmin=True,
            hotel_id=None,
            owner_id=None,
        )
        db.session.add(u)
        db.session.commit()
        print("Superadmin created: admin@hotel.com / admin123")

if __name__ == "__main__":
    main()
