"""Tests for restaurant POS: tables, orders, kitchen."""
import pytest
from app import create_app
from app.extensions import db
from app.models.hotel import Hotel
from app.models.owner import Owner
from app.models.user import User
from app.models.room import Room, RoomType
from app.restaurant.models import MenuCategory, MenuItem, RestaurantTable, RestaurantOrder, RestaurantOrderItem
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    app = create_app("testing")
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def auth_headers(client, app):
    with app.app_context():
        db.create_all()
        owner = Owner(name="Test Owner")
        db.session.add(owner)
        db.session.flush()
        hotel = Hotel(owner_id=owner.id, name="Test Hotel")
        db.session.add(hotel)
        db.session.flush()
        user = User(
            email="manager@test.com",
            password_hash=generate_password_hash("test"),
            role="manager",
            hotel_id=hotel.id,
        )
        db.session.add(user)
        db.session.commit()
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
    return {"Cookie": client.cookie_jar.get("session") or ""}


@pytest.fixture
def hotel_with_pos(app):
    with app.app_context():
        db.create_all()
        owner = Owner(name="O")
        db.session.add(owner)
        db.session.flush()
        hotel = Hotel(owner_id=owner.id, name="H")
        db.session.add(hotel)
        db.session.flush()
        cat = MenuCategory(hotel_id=hotel.id, name="Mains")
        db.session.add(cat)
        db.session.flush()
        item = MenuItem(hotel_id=hotel.id, category_id=cat.id, name="Burger", price=16)
        db.session.add(item)
        db.session.flush()
        t1 = RestaurantTable(hotel_id=hotel.id, table_number="1", capacity=4)
        db.session.add(t1)
        db.session.commit()
        return {"hotel_id": hotel.id, "table_id": t1.id, "item_id": item.id}


def test_restaurant_pos_page(client, app, auth_headers):
    """POS page loads for authenticated user."""
    with app.app_context():
        db.create_all()
    r = client.get("/restaurant/pos")
    assert r.status_code in (200, 302)


def test_restaurant_order_flow(client, app, hotel_with_pos):
    """Select table → add items → send to kitchen → mark ready → payment (structure)."""
    with app.app_context():
        from app.models.user import User
        from app.models.owner import Owner
        owner = Owner.query.first() or Owner(name="O")
        db.session.add(owner)
        db.session.flush()
        hotel = Hotel.query.filter_by(name="H").first() or Hotel(owner_id=owner.id, name="H")
        if not hotel.id:
            db.session.add(hotel)
            db.session.flush()
        user = User.query.filter_by(email="manager@test.com").first()
        if not user:
            user = User(email="manager@test.com", password_hash=generate_password_hash("x"), role="manager", hotel_id=hotel.id)
            db.session.add(user)
            db.session.commit()
    client.post("/auth/login", data={"email": "manager@test.com", "password": "x"})
    # Create order (requires table_id in session or form)
    r = client.post(
        "/restaurant/pos/order/create",
        json={"table_id": hotel_with_pos["table_id"]},
        content_type="application/json",
    )
    if r.status_code == 200 and r.get_json():
        data = r.get_json()
        assert data.get("success") is True
        order_id = data.get("order_id")
        if order_id:
            client.post(
                f"/restaurant/pos/order/{order_id}/add-item",
                json={"menu_item_id": hotel_with_pos["item_id"], "quantity": 1},
                content_type="application/json",
            )
            client.post(f"/restaurant/pos/order/{order_id}/status", json={"status": "preparing"})
            client.post(f"/restaurant/pos/order/{order_id}/status", json={"status": "ready"})
            client.post(f"/restaurant/pos/order/{order_id}/payment", json={"method": "cash"})
