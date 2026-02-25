"""Tests for website integration API (Ngenda Hotel)."""
import pytest
from datetime import date, timedelta
from app import create_app
from app.extensions import db
from app.models.owner import Owner
from app.models.hotel import Hotel
from app.models.room import RoomType, Room
from app.models.booking import Guest, Booking


API_KEY = "ngenda-hotel-website-key-2026"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def ngenda_hotel(app):
    """Create Ngenda Hotel and room types so API has something to return. Returns hotel id (int) for use outside session."""
    with app.app_context():
        db.create_all()
        owner = Owner.query.filter_by(email="owner@ngendahotel.com").first()
        if not owner:
            owner = Owner(name="Ngenda Group", email="owner@ngendahotel.com")
            db.session.add(owner)
            db.session.flush()
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
            db.session.flush()
        rt = RoomType.query.filter_by(hotel_id=hotel.id, name="Classic Room").first()
        if not rt:
            rt = RoomType(
                hotel_id=hotel.id,
                name="Classic Room",
                base_price=80000,
                capacity=2,
                size_sqm="25",
                bed_type="Double",
                amenities=["AC", "WiFi"],
                is_active=True,
            )
            db.session.add(rt)
            db.session.flush()
            for i in range(1, 4):
                r = Room(
                    hotel_id=hotel.id,
                    room_type_id=rt.id,
                    room_number=f"C{i:02d}",
                    status="Vacant",
                    is_active=True,
                )
                db.session.add(r)
        db.session.commit()
        hotel_id = hotel.id
        room_type_id = rt.id
    return type("NgendaHotel", (), {"id": hotel_id, "room_type_id": room_type_id})()


def test_get_rooms_requires_api_key(client):
    r = client.get("/api/rooms")
    assert r.status_code == 401
    data = r.get_json()
    assert "error" in data or "API key" in data.get("error", "").lower() or "API key" in data.get("message", "").lower()


def test_get_rooms(client, ngenda_hotel):
    r = client.get("/api/rooms", headers=HEADERS)
    assert r.status_code == 200, r.get_data(as_text=True)
    data = r.get_json()
    assert data.get("success") is True
    assert "rooms" in data
    assert len(data["rooms"]) >= 1
    room = data["rooms"][0]
    assert "price_usd" in room
    assert "price" in room
    assert "category" in room


def test_get_room_detail(client, app, ngenda_hotel):
    room_type_id = ngenda_hotel.room_type_id
    r = client.get(f"/api/rooms/{room_type_id}", headers=HEADERS)
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert "room" in data
    assert "availability" in data["room"]
    assert len(data["room"]["availability"]) == 30


def test_availability_check(client, app, ngenda_hotel):
    room_type_id = ngenda_hotel.room_type_id
    check_in = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    check_out = (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
    r = client.get(
        f"/api/availability?room_id={room_type_id}&check_in={check_in}&check_out={check_out}",
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "availability" in data
    assert data["availability"].get("room_id") == room_type_id
    assert "available_rooms" in data["availability"] or "available" in data["availability"]


def test_availability_all_rooms(client, app, ngenda_hotel):
    check_in = (date.today() + timedelta(days=14)).strftime("%Y-%m-%d")
    check_out = (date.today() + timedelta(days=16)).strftime("%Y-%m-%d")
    r = client.get(
        f"/api/availability?check_in={check_in}&check_out={check_out}",
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "availability" in data
    assert isinstance(data["availability"], list)


def test_booking_flow(client, app, ngenda_hotel):
    room_type_id = ngenda_hotel.room_type_id
    check_in = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    check_out = (date.today() + timedelta(days=33)).strftime("%Y-%m-%d")
    booking_data = {
        "guest_name": "Test Guest",
        "guest_email": "test@example.com",
        "guest_phone": "+255123456789",
        "room_id": room_type_id,
        "check_in": check_in,
        "check_out": check_out,
        "guests": 2,
    }
    r = client.post("/api/bookings", json=booking_data, headers=HEADERS)
    assert r.status_code == 201, r.get_data(as_text=True)
    data = r.get_json()
    assert data.get("success") is True
    assert "booking_id" in data
    assert "whatsapp_link" in data
    assert "BKG" in data["booking_id"]
    assert data.get("status") == "confirmed"


def test_booking_double_book_returns_409(client, app, ngenda_hotel):
    hotel_id = ngenda_hotel.id
    room_type_id = ngenda_hotel.room_type_id
    with app.app_context():
        rooms = Room.query.filter_by(room_type_id=room_type_id).all()
    check_in = date.today() + timedelta(days=60)
    check_out = check_in + timedelta(days=3)
    with app.app_context():
        guest = Guest.query.filter_by(hotel_id=hotel_id, email="fill@test.com").first()
        if not guest:
            guest = Guest(hotel_id=hotel_id, name="Fill", email="fill@test.com")
            db.session.add(guest)
            db.session.flush()
        for room in rooms:
            b = Booking(
                hotel_id=hotel_id,
                guest_id=guest.id,
                room_id=room.id,
                check_in_date=check_in,
                check_out_date=check_out,
                status="Reserved",
                total_amount=1000,
            )
            db.session.add(b)
        db.session.commit()

    booking_data = {
        "guest_name": "Another Guest",
        "guest_email": "another@example.com",
        "guest_phone": "+255999999999",
        "room_id": room_type_id,
        "check_in": check_in.strftime("%Y-%m-%d"),
        "check_out": check_out.strftime("%Y-%m-%d"),
        "guests": 2,
    }
    r = client.post("/api/bookings", json=booking_data, headers=HEADERS)
    assert r.status_code == 409
    data = r.get_json()
    assert data.get("success") is False
    assert data.get("error", {}).get("code") == "ROOM_NOT_AVAILABLE"
