"""
Unified models for Ngenda Hotel PMS.
Serves both HMS admin and Website booking blueprints.
All models include hotel_id for multi-tenancy.
"""
from datetime import datetime
from decimal import Decimal
from flask_login import UserMixin
from app.extensions import db


# =============================================================================
# CORE ENTITIES (Multi-tenancy foundation)
# =============================================================================

class Owner(db.Model):
    __tablename__ = "owners"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    hotels = db.relationship("Hotel", back_populates="owner", lazy="dynamic")


class Hotel(db.Model):
    __tablename__ = "hotels"
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("owners.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(255))
    location = db.Column(db.String(255))
    address = db.Column(db.String(500))
    city = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(255))
    currency = db.Column(db.String(3), default="TZS")
    timezone = db.Column(db.String(50), default="Africa/Dar_es_Salaam")
    default_tax_rate = db.Column(db.Numeric(5, 2), default=18)

    # Branding
    logo_url = db.Column(db.String(500))
    favicon_url = db.Column(db.String(500))
    cover_image_url = db.Column(db.String(500))

    # Social
    website_url = db.Column(db.String(200))
    facebook_url = db.Column(db.String(200))
    instagram_url = db.Column(db.String(200))
    twitter_url = db.Column(db.String(200))

    # Business details
    tax_number = db.Column(db.String(50))
    registration_number = db.Column(db.String(50))

    # Email settings
    email_header_color = db.Column(db.String(20), default='#2c3e50')
    email_footer_text = db.Column(db.Text)
    email_logo_url = db.Column(db.String(500))

    # Check-in/out times
    check_in_time = db.Column(db.String(10), default='14:00')
    check_out_time = db.Column(db.String(10), default='11:00')

    # Policies
    cancellation_policy = db.Column(db.Text)
    children_policy = db.Column(db.Text)
    pet_policy = db.Column(db.Text)
    payment_policy = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    owner = db.relationship("Owner", back_populates="hotels")
    room_types = db.relationship("RoomType", back_populates="hotel", lazy="dynamic")
    notifications = db.relationship("Notification", back_populates="hotel", lazy="dynamic")


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    permissions = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    users = db.relationship("User", backref=db.backref("role_obj", lazy=True), foreign_keys="User.role_id")


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("owners.id"), nullable=True)
    is_superadmin = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Password reset
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

    # Relationships
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic')

    @property
    def role_name(self):
        """Get role name from relationship or fallback to role string"""
        if hasattr(self, 'role_obj') and self.role_obj:
            return self.role_obj.name
        return self.role

    def can_access_hotel(self, hotel_id):
        if self.is_superadmin:
            return True
        if self.role == "owner":
            hotel = Hotel.query.get(hotel_id)
            return hotel and hotel.owner_id == self.owner_id
        if self.role == "manager":
            return self.hotel_id == hotel_id
        return False


# =============================================================================
# ROOMS & ACCOMMODATION (Website + HMS)
# =============================================================================

ROOM_STATUSES = ("Vacant", "Occupied", "Dirty", "Reserved")


class RoomType(db.Model):
    """Room type/category with website-facing fields."""
    __tablename__ = "room_types"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    base_price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    price_usd = db.Column(db.Numeric(12, 2), nullable=True)  # USD equivalent for website
    description = db.Column(db.Text)  # Full description for website detail page
    short_description = db.Column(db.String(500))  # Brief description for cards
    capacity = db.Column(db.Integer, default=2)
    size_sqm = db.Column(db.String(20))  # e.g. "30m²"
    bed_type = db.Column(db.String(100))  # e.g. "Double Bed", "King Bed"
    amenities = db.Column(db.JSON)  # ["AC", "WiFi", "Mini Bar", etc.]
    category = db.Column(db.String(50))  # classic, superior, deluxe, executive (for website filtering)
    is_active = db.Column(db.Boolean, default=True)
    tax_rate = db.Column(db.Numeric(5, 2), default=18)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    hotel = db.relationship("Hotel", back_populates="room_types")
    rooms = db.relationship("Room", back_populates="room_type", lazy="dynamic")
    images = db.relationship("RoomImage", back_populates="room_type", lazy="dynamic", cascade="all, delete-orphan")


class Room(db.Model):
    """Individual room instances (for HMS operations)."""
    __tablename__ = "rooms"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    room_type_id = db.Column(db.Integer, db.ForeignKey("room_types.id"), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Vacant")
    floor = db.Column(db.Integer)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    room_type = db.relationship("RoomType", back_populates="rooms")
    status_history = db.relationship("RoomStatusHistory", back_populates="room", lazy="dynamic", order_by="RoomStatusHistory.changed_at.desc()")
    housekeeping_tasks = db.relationship("HousekeepingTask", back_populates="room", lazy="dynamic")
    maintenance_issues = db.relationship("MaintenanceIssue", back_populates="room", lazy="dynamic")
    room_service_orders = db.relationship("RoomServiceOrder", back_populates="room", lazy="dynamic")


class RoomImage(db.Model):
    """Images for room types - stored in app/static/uploads/rooms/"""
    __tablename__ = "room_images"
    id = db.Column(db.Integer, primary_key=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey("room_types.id", ondelete="CASCADE"), nullable=False)
    image_filename = db.Column(db.String(255), nullable=False)  # Just filename, path is fixed
    is_primary = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    room_type = db.relationship("RoomType", back_populates="images")

    @property
    def url(self):
        """Get full URL for the image."""
        return f"/static/uploads/rooms/{self.image_filename}"


class RoomStatusHistory(db.Model):
    __tablename__ = "room_status_history"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20), nullable=False)
    changed_at = db.Column(db.DateTime, server_default=db.func.now())

    room = db.relationship("Room", back_populates="status_history")


# =============================================================================
# BOOKINGS & GUESTS (Unified for Website + HMS)
# =============================================================================

BOOKING_STATUSES = ("Reserved", "CheckedIn", "CheckedOut", "Cancelled")
INVOICE_STATUSES = ("Unpaid", "PartiallyPaid", "Paid")
BOOKING_SOURCES = ("website", "front_desk", "phone", "email", "walk_in", "ota", "corporate")


class Guest(db.Model):
    __tablename__ = "guests"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=False)  # Required for website bookings
    email = db.Column(db.String(255))
    id_number = db.Column(db.String(100))  # National ID or Passport
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    bookings = db.relationship("Booking", back_populates="guest", lazy="dynamic")


class Booking(db.Model):
    """
    Unified booking model handling both:
    - Website bookings (guest self-service with email confirmation)
    - HMS admin bookings (front desk manual entry)
    """
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)

    # Guest info (denormalized for quick access, also linked via guest_id)
    guest_id = db.Column(db.Integer, db.ForeignKey("guests.id"), nullable=True)  # Nullable for quick website bookings
    guest_name = db.Column(db.String(255), nullable=False)
    guest_email = db.Column(db.String(255), nullable=False)
    guest_phone = db.Column(db.String(50), nullable=False)

    # Room assignment
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=True)  # Nullable until assigned
    room_type_requested = db.Column(db.String(100))  # Room type requested (for website before assignment)

    # Dates
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    check_in_time_actual = db.Column(db.DateTime)  # Actual check-in time
    check_out_time_actual = db.Column(db.DateTime)  # Actual check-out time

    # Status & Source
    status = db.Column(db.String(20), nullable=False, default="Reserved")
    source = db.Column(db.String(50), default="website")  # website, front_desk, phone, etc.
    booking_reference = db.Column(db.String(50), unique=True, nullable=False)

    # Guest counts
    adults = db.Column(db.Integer, default=1)
    children = db.Column(db.Integer, default=0)

    # Pricing
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    amount_paid = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    balance = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    # Requests & Notes
    special_requests = db.Column(db.Text)
    internal_notes = db.Column(db.Text)  # HMS staff notes only

    # Website-specific fields
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.String(500))
    referral_source = db.Column(db.String(255))  # Google, Facebook, direct, etc.

    # Timestamps
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())
    confirmed_at = db.Column(db.DateTime)  # When booking was confirmed
    cancelled_at = db.Column(db.DateTime)
    cancellation_reason = db.Column(db.Text)

    # Relationships
    guest = db.relationship("Guest", back_populates="bookings")
    room = db.relationship("Room", backref="bookings")
    invoice = db.relationship("Invoice", back_populates="booking", uselist=False, cascade="all, delete-orphan")
    payments = db.relationship("Payment", back_populates="booking", lazy="dynamic")
    room_service_orders = db.relationship("RoomServiceOrder", back_populates="booking", lazy="dynamic")
    selcom_payments = db.relationship("SelcomPayment", back_populates="booking", lazy="dynamic")

    def calculate_balance(self):
        """Recalculate balance from payments."""
        total_paid = sum(p.amount for p in self.payments) if self.payments else 0
        self.amount_paid = total_paid
        self.balance = self.total_amount - total_paid
        return self.balance


class Invoice(db.Model):
    __tablename__ = "invoices"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    invoice_number = db.Column(db.String(50), unique=True)
    total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="Unpaid")
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    deleted_at = db.Column(db.DateTime, nullable=True)  # Soft delete

    booking = db.relationship("Booking", back_populates="invoice")
    payments = db.relationship("Payment", back_populates="invoice", lazy="dynamic")


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.String(50))  # Cash, Card, Mobile Money, Bank Transfer
    payment_type = db.Column(db.String(20), default="full")  # deposit, full, partial
    transaction_id = db.Column(db.String(100))  # External payment reference
    status = db.Column(db.String(20), default="completed")  # pending, completed, failed, refunded
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    deleted_at = db.Column(db.DateTime, nullable=True)

    booking = db.relationship("Booking", back_populates="payments")
    invoice = db.relationship("Invoice", back_populates="payments")


class SelcomPayment(db.Model):
    """Selcom payment gateway integration."""
    __tablename__ = 'selcom_payments'
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='TZS')
    payment_method = db.Column(db.String(50))  # mobile_money, card, cash, bank
    transaction_id = db.Column(db.String(100), unique=True)
    order_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')
    payment_type = db.Column(db.String(20), default='full')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    booking = db.relationship('Booking', back_populates='selcom_payments')


# =============================================================================
# HOUSEKEEPING & MAINTENANCE
# =============================================================================

class HousekeepingTask(db.Model):
    __tablename__ = "housekeeping_tasks"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    task_type = db.Column(db.String(20), nullable=False)  # cleaning, inspection, maintenance, deep_clean
    priority = db.Column(db.String(10), nullable=False, default="medium")
    status = db.Column(db.String(20), nullable=False, default="pending")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    completed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    verified_at = db.Column(db.DateTime)
    verified_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    room = db.relationship("Room", back_populates="housekeeping_tasks")
    supplies_used = db.relationship("HousekeepingSupply", back_populates="task", cascade="all, delete-orphan")


class HousekeepingSupply(db.Model):
    __tablename__ = "housekeeping_supplies"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("housekeeping_tasks.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=False)
    quantity = db.Column(db.Numeric(10, 3), nullable=False)
    notes = db.Column(db.Text)

    task = db.relationship("HousekeepingTask", back_populates="supplies_used")
    item = db.relationship("InventoryItem")


class MaintenanceIssue(db.Model):
    __tablename__ = "maintenance_issues"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=True)
    issue_type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(10), nullable=False, default="medium")
    status = db.Column(db.String(20), nullable=False, default="reported")
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)
    reported_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    assigned_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    resolution_notes = db.Column(db.Text)
    cost = db.Column(db.Numeric(10, 2))

    room = db.relationship("Room", back_populates="maintenance_issues")
    parts_used = db.relationship("MaintenancePart", back_populates="issue", cascade="all, delete-orphan")


class MaintenancePart(db.Model):
    __tablename__ = "maintenance_parts"
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey("maintenance_issues.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=False)
    quantity = db.Column(db.Numeric(10, 3), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.Text)

    issue = db.relationship("MaintenanceIssue", back_populates="parts_used")
    item = db.relationship("InventoryItem")


# =============================================================================
# INVENTORY & PURCHASING
# =============================================================================

class InventoryCategory(db.Model):
    __tablename__ = "inventory_categories"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship("InventoryItem", back_populates="category", lazy="dynamic")


class InventoryItem(db.Model):
    __tablename__ = "inventory_items"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("inventory_categories.id"), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    unit = db.Column(db.String(20), nullable=False)
    reorder_level = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    current_stock = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    average_cost = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    category = db.relationship("InventoryCategory", back_populates="items")
    movements = db.relationship("StockMovement", back_populates="item", lazy="dynamic")


class StockMovement(db.Model):
    __tablename__ = "stock_movements"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    unit_cost = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    previous_stock = db.Column(db.Numeric(12, 3), nullable=False)
    new_stock = db.Column(db.Numeric(12, 3), nullable=False)
    reference_type = db.Column(db.String(50))
    reference_id = db.Column(db.Integer)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    item = db.relationship("InventoryItem", back_populates="movements")


class Supplier(db.Model):
    __tablename__ = "suppliers"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    contact_person = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    tax_id = db.Column(db.String(50))
    payment_terms = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    purchase_orders = db.relationship("PurchaseOrder", back_populates="supplier")


class PurchaseOrder(db.Model):
    __tablename__ = "purchase_orders"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    po_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    order_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    expected_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, default="draft")
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    received_date = db.Column(db.DateTime)
    received_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    supplier = db.relationship("Supplier", back_populates="purchase_orders")
    items = db.relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderItem(db.Model):
    __tablename__ = "purchase_order_items"
    id = db.Column(db.Integer, primary_key=True)
    po_id = db.Column(db.Integer, db.ForeignKey("purchase_orders.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    unit_cost = db.Column(db.Numeric(12, 2), nullable=False)
    received_quantity = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    notes = db.Column(db.Text)

    purchase_order = db.relationship("PurchaseOrder", back_populates="items")
    item = db.relationship("InventoryItem")


# =============================================================================
# ACCOUNTING
# =============================================================================

class TaxRate(db.Model):
    __tablename__ = "tax_rates"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    rate = db.Column(db.Numeric(5, 2), nullable=False)
    apply_rooms = db.Column(db.Boolean, default=True)
    apply_restaurant = db.Column(db.Boolean, default=False)
    apply_other = db.Column(db.Boolean, default=False)
    inclusive = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)


class ChartOfAccount(db.Model):
    __tablename__ = "chart_of_accounts"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # Asset, Liability, Revenue, Expense
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    journal_lines = db.relationship("JournalLine", back_populates="account", lazy="dynamic")


class JournalEntry(db.Model):
    __tablename__ = "journal_entries"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    reference = db.Column(db.String(100))
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    deleted_at = db.Column(db.DateTime, nullable=True)

    lines = db.relationship("JournalLine", back_populates="journal_entry", lazy="dynamic")


class JournalLine(db.Model):
    __tablename__ = "journal_lines"
    id = db.Column(db.Integer, primary_key=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey("journal_entries.id"), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("chart_of_accounts.id"), nullable=False)
    debit = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    credit = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    deleted_at = db.Column(db.DateTime, nullable=True)

    journal_entry = db.relationship("JournalEntry", back_populates="lines")
    account = db.relationship("ChartOfAccount", back_populates="journal_lines")


# =============================================================================
# BUSINESS OPERATIONS
# =============================================================================

class BusinessDate(db.Model):
    __tablename__ = "business_dates"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    current_business_date = db.Column(db.Date, nullable=False)
    is_closed = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


class NightAuditLog(db.Model):
    """Audit log for night audit runs"""
    __tablename__ = "night_audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    audit_date = db.Column(db.Date, nullable=False)
    run_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="running")  # running, success, failed, partial
    summary = db.Column(db.JSON)  # Revenue, occupancy, etc.
    errors = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    runner = db.relationship("User", foreign_keys=[run_by])


class APIKey(db.Model):
    __tablename__ = "api_keys"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    key_hash = db.Column(db.String(255), nullable=False)
    key_prefix = db.Column(db.String(10), nullable=False)
    last_used_at = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    @staticmethod
    def generate_key(prefix="hk"):
        import secrets
        raw = secrets.token_urlsafe(32)
        return f"{prefix}_{raw[:8]}_{raw[8:]}"


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500))
    icon = db.Column(db.String(50))
    color = db.Column(db.String(20))
    is_read = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)

    user = db.relationship('User', back_populates='notifications')
    hotel = db.relationship('Hotel', back_populates='notifications')


class RoomServiceOrder(db.Model):
    __tablename__ = 'room_service_orders'
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'))
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'))
    guest_name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')
    delivery_time = db.Column(db.DateTime)
    special_instructions = db.Column(db.Text)
    subtotal = db.Column(db.Numeric(10, 2), default=0)
    tax = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), default=0)
    charge_to_room = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)
    delivered_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))

    room = db.relationship('Room', back_populates='room_service_orders')
    booking = db.relationship('Booking', back_populates='room_service_orders')
    items = db.relationship('RoomServiceOrderItem', back_populates='order', lazy='dynamic', cascade='all, delete-orphan')


class RoomServiceOrderItem(db.Model):
    __tablename__ = 'room_service_order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('room_service_orders.id', ondelete='CASCADE'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    order = db.relationship('RoomServiceOrder', back_populates='items')
    menu_item = db.relationship('MenuItem', back_populates='order_items')


class MenuCategory(db.Model):
    """Menu category for restaurant"""
    __tablename__ = 'menu_categories'
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('MenuItem', back_populates='category', lazy='dynamic')


class MenuItem(db.Model):
    """Menu item for restaurant"""
    __tablename__ = 'menu_items'
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('menu_categories.id'))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    cost = db.Column(db.Numeric(10, 2))
    tax_rate = db.Column(db.Numeric(5, 2), default=0)
    preparation_time = db.Column(db.Integer)
    is_available = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(500))
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    category = db.relationship('MenuCategory', back_populates='items')
    inventory_items = db.relationship('MenuItemInventory', back_populates='menu_item', cascade='all, delete-orphan')
    order_items = db.relationship('RoomServiceOrderItem', back_populates='menu_item')


class MenuItemInventory(db.Model):
    """Link menu items to inventory items"""
    __tablename__ = 'menu_item_inventory'
    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)
    quantity_needed = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    menu_item = db.relationship('MenuItem', back_populates='inventory_items')
    inventory_item = db.relationship('InventoryItem')


class RestaurantTable(db.Model):
    __tablename__ = 'restaurant_tables'
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    table_number = db.Column(db.String(10), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    section = db.Column(db.String(50))
    status = db.Column(db.String(20), default='available')
    position_x = db.Column(db.Integer, default=0)
    position_y = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('RestaurantOrder', back_populates='table', lazy='dynamic')


class RestaurantOrder(db.Model):
    __tablename__ = 'restaurant_orders'
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    table_id = db.Column(db.Integer, db.ForeignKey('restaurant_tables.id'))
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'))
    guest_name = db.Column(db.String(100))
    order_type = db.Column(db.String(20), default='dine_in')  # dine_in, takeaway, room_service, delivery
    status = db.Column(db.String(20), default='pending')  # pending, preparing, ready, completed, cancelled, split
    subtotal = db.Column(db.Numeric(10, 2), default=0)
    tax = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), default=0)
    special_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Split order support (Phase 1.4)
    parent_order_id = db.Column(db.Integer, db.ForeignKey('restaurant_orders.id'), nullable=True)
    
    # Payment tracking (Week 1 Critical)
    server_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    payment_status = db.Column(db.String(20), default='unpaid')  # unpaid, partial, paid, refunded
    payment_method = db.Column(db.String(50))  # cash, card, mobile, room_charge, null
    paid_amount = db.Column(db.Numeric(10, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    tip_amount = db.Column(db.Numeric(10, 2), default=0)
    balance_due = db.Column(db.Numeric(10, 2), default=0)

    table = db.relationship('RestaurantTable', back_populates='orders')
    items = db.relationship('RestaurantOrderItem', back_populates='order', lazy='dynamic', cascade='all, delete-orphan')
    server = db.relationship('User', foreign_keys=[server_id])
    # Parent/child order relationship for splits
    parent_order = db.relationship('RestaurantOrder', remote_side=[id], backref='child_orders')


class RestaurantOrderItem(db.Model):
    __tablename__ = 'restaurant_order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('restaurant_orders.id', ondelete='CASCADE'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, preparing, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Order modifiers (Week 2 Important)
    modifiers = db.relationship('OrderModifier', back_populates='order_item', cascade='all, delete-orphan', lazy='dynamic')
    
    order = db.relationship('RestaurantOrder', back_populates='items')
    menu_item = db.relationship('MenuItem')


class OrderModifier(db.Model):
    """Order item modifiers (no onions, extra cheese, cooking temp, etc.) - Week 2"""
    __tablename__ = 'order_modifiers'
    id = db.Column(db.Integer, primary_key=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey('restaurant_order_items.id', ondelete='CASCADE'), nullable=False)
    modifier_type = db.Column(db.String(50), nullable=False)  # no_onions, extra_cheese, cooking_temp, side_choice
    modifier_value = db.Column(db.String(100), nullable=False)  # rare, medium, well; or 'Extra', 'None'
    additional_price = db.Column(db.Numeric(5, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    order_item = db.relationship('RestaurantOrderItem', back_populates='modifiers')


class TableReservation(db.Model):
    """Table reservations for restaurant - Week 2"""
    __tablename__ = 'table_reservations'
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    table_id = db.Column(db.Integer, db.ForeignKey('restaurant_tables.id'))
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'))  # Link to hotel booking
    guest_name = db.Column(db.String(100), nullable=False)
    guest_phone = db.Column(db.String(50))
    guest_email = db.Column(db.String(100))
    party_size = db.Column(db.Integer, nullable=False)
    reservation_time = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=90)
    status = db.Column(db.String(20), default='confirmed')  # confirmed, seated, completed, cancelled, no_show
    special_requests = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    table = db.relationship('RestaurantTable')
    booking = db.relationship('Booking')
    creator = db.relationship('User', foreign_keys=[created_by])


# =============================================================================
# WEBSITE GALLERY (HMS Managed)
# =============================================================================

class GalleryImage(db.Model):
    """
    Gallery images managed from HMS Settings.
    These images appear on the public website gallery page.
    Staff can upload, categorize, and control visibility without developer help.
    """
    __tablename__ = 'gallery_images'
    
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    
    # Image file
    image_filename = db.Column(db.String(255), nullable=False)
    
    # Content
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Categorization (matches website filter tabs)
    category = db.Column(db.String(50), nullable=False)  # rooms, facilities, dining, events
    
    # Layout control (matches existing template structure)
    size_type = db.Column(db.String(20), nullable=False, default='small')  # large, medium, small
    sort_order = db.Column(db.Integer, default=0)
    
    # Visibility
    is_active = db.Column(db.Boolean, default=True)
    
    # Metadata
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())
    
    # Relationships
    hotel = db.relationship('Hotel', backref=db.backref('gallery_images', lazy='dynamic'))
    uploader = db.relationship('User', foreign_keys=[uploaded_by])
    
    @property
    def url(self):
        """Get full URL for the gallery image."""
        return f"/static/uploads/gallery/{self.image_filename}"
    
    @property
    def category_display(self):
        """Get formatted category name."""
        return self.category.title() if self.category else 'Gallery'
