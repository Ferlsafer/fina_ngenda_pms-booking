"""
HMS (Hotel Management System) - Consolidated Routes
Core routes for the HMS admin interface.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, current_app
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date, timedelta
from decimal import Decimal
from calendar import monthrange
import secrets
import hashlib
import uuid
import os
from functools import wraps

from app.extensions import db, limiter
from app.models import (
    Owner, Hotel, User, Role, Room, RoomType, RoomImage, RoomStatusHistory,
    Guest, Booking, Invoice, Payment, Notification, BusinessDate, NightAuditLog,
    HousekeepingTask, HousekeepingSupply, MaintenanceIssue, MaintenancePart,
    InventoryCategory, InventoryItem, StockMovement, Supplier, PurchaseOrder, PurchaseOrderItem,
    MenuCategory, MenuItem, MenuItemInventory, RestaurantTable, RestaurantOrder, RestaurantOrderItem, OrderModifier,
    RoomServiceOrder, RoomServiceOrderItem,
    ChartOfAccount, JournalEntry, JournalLine, TaxRate,
    TableReservation, GalleryImage,
    ROOM_STATUSES
)

# Import housekeeping service module for business logic
from app.hms_housekeeping_service import (
    RoomStatusManager,
    TaskPriorityScorer,
    CleaningTimeEstimator,
    TaskAssignmentEngine,
    ProductivityTracker,
    MaintenanceIntegration,
    CheckoutProcessor,
    quick_clean_room,
    quick_dirty_room,
    create_cleaning_task,
    complete_cleaning_task
)

# Import booking service module for business logic
from app.hms_booking_service import (
    BookingService,
    BookingStateMachine,
    RoomStatusService,
    AccountingIntegrationService,
    HousekeepingIntegrationService,
    get_booking_balance,
    is_room_available
)

# Import room service module for business logic
from app.hms_room_service import (
    RoomManagementService,
    RoomStatusValidator,
    RoomRevenueTracker,
    RoomNotificationService,
    safe_change_room_status,
    get_room_availability
)

# Import restaurant service module for business logic
from app.hms_restaurant_service import (
    RestaurantPaymentService,
    RestaurantAccountingService,
    RestaurantInventoryService,
    TableReservationService,
    RestaurantAnalyticsService,
    calculate_order_total
)

# Import restaurant routes for kitchen functionality
try:
    from app.hms_restaurant_full import bp as restaurant_bp
except ImportError:
    # Fallback if hms_restaurant_full is not available
    restaurant_bp = None

# =============================================================================
# DECORATORS
# =============================================================================

def role_required(*roles):
    """Decorator to restrict access to specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('hms.login'))
            
            if current_user.is_superadmin:
                return f(*args, **kwargs)
            
            user_role = current_user.role.lower() if current_user.role else 'staff'
            if user_role not in [r.lower() for r in roles]:
                flash("Access denied. Insufficient permissions.", "danger")
                return redirect(url_for('hms.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# =============================================================================
# JOURNAL ENTRY HELPERS
# =============================================================================

def create_journal_entry(hotel_id, date, reference, description, debit_lines, credit_lines):
    """Helper function to create a journal entry with multiple lines"""
    try:
        # Create journal entry
        entry = JournalEntry(
            hotel_id=hotel_id,
            date=date,
            reference=reference,
            description=description,
            created_by=current_user.id
        )
        db.session.add(entry)
        db.session.flush()  # Get the entry ID
        
        # Add debit lines
        for account_id, amount, memo in debit_lines:
            debit_line = JournalLine(
                journal_entry_id=entry.id,
                account_id=account_id,
                debit=amount,
                credit=0,
                description=memo
            )
            db.session.add(debit_line)
        
        # Add credit lines
        for account_id, amount, memo in credit_lines:
            credit_line = JournalLine(
                journal_entry_id=entry.id,
                account_id=account_id,
                debit=0,
                credit=amount,
                description=memo
            )
            db.session.add(credit_line)
        
        db.session.commit()
        return entry
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating journal entry: {str(e)}")
        raise e

def get_or_create_revenue_accounts(hotel_id):
    """Get or create standard revenue accounts for a hotel"""
    accounts = {
        'Room Revenue': ChartOfAccount.query.filter_by(hotel_id=hotel_id, name='Room Revenue', deleted_at=None).first(),
        'Food & Beverage': ChartOfAccount.query.filter_by(hotel_id=hotel_id, name='Food & Beverage', deleted_at=None).first(),
        'Other Revenue': ChartOfAccount.query.filter_by(hotel_id=hotel_id, name='Other Revenue', deleted_at=None).first()
    }
    
    # Create missing accounts if they don't exist
    for account_name, account in accounts.items():
        if not account:
            account = ChartOfAccount(
                hotel_id=hotel_id,
                name=account_name,
                type='Revenue',
                description=f'Automatically created {account_name} account'
            )
            db.session.add(account)
            accounts[account_name] = account
    
    if any(not acc for acc in accounts.values()):
        db.session.commit()
    
    return accounts

def get_or_create_asset_accounts(hotel_id):
    """Get or create standard asset accounts for a hotel"""
    accounts = {
        'Cash': ChartOfAccount.query.filter_by(hotel_id=hotel_id, name='Cash', deleted_at=None).first(),
        'Bank': ChartOfAccount.query.filter_by(hotel_id=hotel_id, name='Bank', deleted_at=None).first(),
        'Accounts Receivable': ChartOfAccount.query.filter_by(hotel_id=hotel_id, name='Accounts Receivable', deleted_at=None).first()
    }
    
    # Create missing accounts if they don't exist
    for account_name, account in accounts.items():
        if not account:
            account = ChartOfAccount(
                hotel_id=hotel_id,
                name=account_name,
                type='Asset',
                description=f'Automatically created {account_name} account'
            )
            db.session.add(account)
            accounts[account_name] = account
    
    if any(not acc for acc in accounts.values()):
        db.session.commit()
    
    return accounts

# =============================================================================
# ACCESS CONTROL HELPERS
# =============================================================================

def get_allowed_hotel_ids():
    """Return list of hotel IDs the current user is allowed to access."""
    if not current_user.is_authenticated:
        return []
    if current_user.is_superadmin:
        return [h.id for h in Hotel.query.all()]
    if current_user.role == "owner" and current_user.owner_id:
        return [h.id for h in Hotel.query.filter_by(owner_id=current_user.owner_id).all()]
    if current_user.hotel_id:
        return [current_user.hotel_id]
    return []


def get_current_hotel_id():
    """Get currently selected hotel ID from session."""
    if not current_user.is_authenticated:
        return None
    if not current_user.is_superadmin and current_user.hotel_id:
        return current_user.hotel_id
    hotel_id = session.get('hotel_id')
    if hotel_id:
        return int(hotel_id)
    if current_user.is_superadmin:
        first = Hotel.query.first()
        return first.id if first else None
    return None


def require_hotel_access(hotel_id):
    """Return True if current user can access this hotel_id."""
    if not hotel_id:
        return False
    allowed = get_allowed_hotel_ids()
    return hotel_id in allowed


def can_access_module(module_name):
    """Check if current user can access a module."""
    if not current_user.is_authenticated:
        return False
    if current_user.is_superadmin:
        return True
    user_role = current_user.role.lower() if current_user.role else 'staff'
    module_access = {
        'dashboard': ['all'],
        'bookings': ['manager', 'owner', 'superadmin', 'receptionist'],
        'rooms': ['manager', 'owner', 'superadmin', 'receptionist'],
        'housekeeping': ['manager', 'owner', 'superadmin', 'housekeeping', 'housekeeping_manager'],
        'restaurant': ['manager', 'owner', 'superadmin', 'receptionist', 'kitchen', 'restaurant_manager'],
        'inventory': ['manager', 'owner', 'superadmin', 'housekeeping', 'housekeeping_manager'],
        'accounting': ['manager', 'owner', 'superadmin', 'restaurant_manager'],
        'night_audit': ['manager', 'owner', 'superadmin'],
        'room_service': ['manager', 'owner', 'superadmin', 'kitchen', 'restaurant_manager', 'receptionist'],
        'settings': ['manager', 'owner', 'superadmin', 'restaurant_manager', 'housekeeping_manager'],
    }
    allowed_roles = module_access.get(module_name, ['manager', 'owner', 'superadmin'])
    return 'all' in allowed_roles or user_role in allowed_roles

hms_bp = Blueprint('hms', __name__, url_prefix='/hms')


# =============================================================================
# ACCESS CONTROL HELPERS
# =============================================================================

def get_allowed_hotel_ids():
    if not current_user.is_authenticated:
        return []
    if current_user.is_superadmin:
        return [h.id for h in Hotel.query.all()]
    if current_user.role == "owner" and current_user.owner_id:
        return [h.id for h in Hotel.query.filter_by(owner_id=current_user.owner_id).all()]
    if current_user.hotel_id:
        return [current_user.hotel_id]
    return []


def get_current_hotel_id():
    if not current_user.is_authenticated:
        return None
    if not current_user.is_superadmin and current_user.hotel_id:
        return current_user.hotel_id
    hotel_id = session.get('hotel_id')
    if hotel_id:
        return int(hotel_id)
    if current_user.is_superadmin:
        first = Hotel.query.first()
        return first.id if first else None
    return None


def require_hotel_access(hotel_id):
    if not hotel_id:
        return False
    return hotel_id in get_allowed_hotel_ids()


# =============================================================================
# AUTH ROUTES
# =============================================================================

@hms_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("hms/auth/login.html")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            if not user.is_superadmin and user.hotel_id:
                session['hotel_id'] = user.hotel_id
            next_url = request.args.get("next") or url_for('hms.dashboard')
            return redirect(next_url)
        flash("Invalid email or password.", "danger")
    return render_template("hms/auth/login.html")


@hms_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('hms.login'))


@hms_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Request password reset"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        if not email:
            flash('Please enter your email address.', 'danger')
            return render_template('hms/auth/forgot_password.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            import secrets
            from datetime import datetime, timedelta
            
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expires = datetime.utcnow() + timedelta(seconds=current_app.config.get('MAIL_RESET_TOKEN_EXPIRY', 3600))
            db.session.commit()
            
            # Send email
            try:
                from app.utils.email_service import send_password_reset_email
                send_password_reset_email(user, token)
                flash('If an account exists with that email, a password reset link has been sent.', 'info')
            except Exception as e:
                current_app.logger.error(f"Email send failed: {str(e)}")
                # Fallback: show token for development
                flash(f'Email not configured. Reset token (dev only): {token}', 'warning')
        else:
            # Always show same message to prevent email enumeration
            flash('If an account exists with that email, a password reset link has been sent.', 'info')
        
        return redirect(url_for('hms.forgot_password'))
    
    return render_template('hms/auth/forgot_password.html')


@hms_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    from datetime import datetime
    
    user = User.query.filter_by(reset_token=token).first()
    
    # Validate token
    if not user:
        flash('Invalid reset token.', 'danger')
        return redirect(url_for('hms.forgot_password'))
    
    if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
        flash('Reset token has expired. Please request a new one.', 'danger')
        return redirect(url_for('hms.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate password
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('hms/auth/reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('hms/auth/reset_password.html', token=token)
        
        # Update password
        user.password_hash = generate_password_hash(password)
        user.reset_token = None  # Invalidate token
        user.reset_token_expires = None
        db.session.commit()
        
        flash('Password updated successfully. You can now login.', 'success')
        return redirect(url_for('hms.login'))
    
    return render_template('hms/auth/reset_password.html', token=token)


# =============================================================================
# DASHBOARD
# =============================================================================

@hms_bp.route('/')
@login_required
def dashboard():
    hotel_ids = get_allowed_hotel_ids()
    active_hotel_id = get_current_hotel_id()

    if not hotel_ids:
        flash("No hotel assigned.", "warning")
        return redirect(url_for("hms.login"))

    # Get user role
    user_role = current_user.role.lower() if current_user.role else 'staff'
    if current_user.is_superadmin:
        user_role = 'superadmin'

    # Restrict main dashboard to manager, owner, superadmin only
    if user_role not in ['manager', 'owner', 'superadmin']:
        # Redirect other roles to their specific dashboards
        if user_role == 'housekeeping':
            return redirect(url_for('hms.housekeeping_dashboard'))
        elif user_role == 'kitchen':
            return redirect(url_for('hms.kitchen_dashboard'))
        elif user_role == 'restaurant':
            return redirect(url_for('hms.restaurant_dashboard'))
        elif user_role == 'receptionist':
            return redirect(url_for('hms.bookings'))
        else:
            flash("Access denied. Insufficient permissions.", "danger")
            return redirect(url_for('hms.login'))

    # Filter queries by hotel
    q_rooms = Room.query.filter(Room.hotel_id.in_(hotel_ids))
    q_bookings = Booking.query.filter(Booking.hotel_id.in_(hotel_ids))

    if active_hotel_id:
        q_rooms = q_rooms.filter(Room.hotel_id == active_hotel_id)
        q_bookings = q_bookings.filter(Booking.hotel_id == active_hotel_id)

    total_rooms = q_rooms.count()
    occupied_rooms = q_rooms.filter(Room.status == "Occupied").count()
    total_bookings = q_bookings.count()

    today = date.today()
    revenue_today = db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).filter(
        Payment.hotel_id.in_(hotel_ids), Payment.deleted_at.is_(None),
        db.func.date(Payment.created_at) == today
    ).scalar() or 0

    check_ins_today = q_bookings.filter(
        db.func.date(Booking.check_in_date) == today, Booking.status != 'cancelled'
    ).count()

    check_outs_today = q_bookings.filter(
        db.func.date(Booking.check_out_date) == today, Booking.status != 'cancelled'
    ).count()

    total_occupied = q_rooms.filter(Room.status.in_(['Occupied', 'Dirty'])).count()
    occupancy_rate = round((total_occupied / total_rooms * 100) if total_rooms > 0 else 0, 1)

    stats = {
        "total_rooms": total_rooms,
        "occupied_rooms": occupied_rooms,
        "revenue_today": float(revenue_today),
        "total_bookings": total_bookings,
        "check_ins_today": check_ins_today,
        "check_outs_today": check_outs_today,
        "occupancy_rate": occupancy_rate
    }

    # Show only 3 recent bookings (View All button shows more)
    recent_bookings = q_bookings.order_by(Booking.created_at.desc()).limit(3).all()

    # Revenue chart data (last 7 days)
    revenue_labels = []
    revenue_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        revenue_labels.append(d.strftime("%a %d"))
        rev = db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).filter(
            Payment.hotel_id.in_(hotel_ids) if not active_hotel_id else (Payment.hotel_id == active_hotel_id),
            Payment.deleted_at.is_(None),
            db.func.date(Payment.created_at) == d
        ).scalar()
        revenue_data.append(float(rev) if rev else 0)

    # Get notifications for current user
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        is_archived=False
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    # Convert to alerts format
    alerts = []
    for n in notifications:
        alerts.append({
            'title': n.title,
            'message': n.message,
            'level': n.color or 'info',
            'severity': 'high' if n.color == 'danger' else 'medium',
            'type': n.type,
            'link': n.link,
            'icon': n.icon
        })
    
    # Add mock alerts if no notifications
    if not alerts:
        alerts = [
            {'title': 'Welcome!', 'message': 'Your HMS dashboard is ready', 'level': 'info', 'severity': 'low', 'type': 'system'},
        ]

    return render_template("hms/dashboard/index.html", stats=stats, recent_bookings=recent_bookings,
                          active_hotel_id=active_hotel_id, user=current_user,
                          revenue_labels=revenue_labels, revenue_data=revenue_data,
                          alerts=alerts)


# =============================================================================
# ROOMS
# =============================================================================

@hms_bp.route('/rooms')
@login_required
def rooms():
    hotel_ids = get_allowed_hotel_ids()
    if not hotel_ids:
        flash("No hotel assigned.", "warning")
        return redirect(url_for("hms.dashboard"))

    current_hid = get_current_hotel_id()
    q = Room.query.filter(Room.hotel_id.in_(hotel_ids)).order_by(Room.room_number)
    if current_hid:
        q = q.filter(Room.hotel_id == current_hid)

    rooms = q.all()
    room_types = RoomType.query.filter_by(hotel_id=current_hid).all() if current_hid else []

    return render_template("hms/rooms/list.html", rooms=rooms, room_types=room_types, ROOM_STATUSES=ROOM_STATUSES)


@hms_bp.route('/rooms/types')
@login_required
def rooms_types():
    hotel_ids = get_allowed_hotel_ids()
    hid = get_current_hotel_id() or (hotel_ids[0] if hotel_ids else None)
    if not hid:
        flash("No hotel assigned.", "warning")
        return redirect(url_for("hms.dashboard"))

    types = RoomType.query.filter_by(hotel_id=hid).all()
    return render_template("hms/rooms/types.html", room_types=types)


@hms_bp.route('/rooms/types/add', methods=['GET', 'POST'])
@login_required
def rooms_type_add():
    hotel_ids = get_allowed_hotel_ids()
    hid = get_current_hotel_id() or (hotel_ids[0] if hotel_ids else None)
    if not hid or not require_hotel_access(hid):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.rooms_types"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        base_price = request.form.get("base_price", type=float)
        capacity = request.form.get("capacity", type=int)
        size_sqm = request.form.get("size_sqm", "").strip()
        bed_type = request.form.get("bed_type", "").strip()
        amenities_input = request.form.get("amenities", "").strip()
        short_description = request.form.get("short_description", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()  # classic, superior, deluxe, executive
        price_usd = request.form.get("price_usd", type=float)
        
        if not name or base_price is None:
            flash("Name and base price required.", "danger")
            return redirect(url_for("hms.rooms_type_add"))

        amenities = [a.strip() for a in amenities_input.split(',') if a.strip()] if amenities_input else []

        rt = RoomType(
            hotel_id=hid, 
            name=name, 
            base_price=base_price, 
            capacity=capacity,
            size_sqm=size_sqm, 
            bed_type=bed_type, 
            amenities=amenities, 
            is_active=True,
            short_description=short_description,
            description=description,
            category=category,
            price_usd=price_usd
        )
        db.session.add(rt)
        db.session.flush()  # Get the ID

        # Handle image uploads
        if 'room_images' in request.files:
            files = request.files.getlist('room_images')
            for i, file in enumerate(files):
                if file and file.filename:
                    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
                    filename = f"room_type_{rt.id}_{uuid.uuid4().hex[:8]}.{ext}"
                    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'rooms')
                    os.makedirs(upload_dir, exist_ok=True)
                    file.save(os.path.join(upload_dir, filename))
                    
                    room_image = RoomImage(
                        room_type_id=rt.id, 
                        image_filename=filename, 
                        is_primary=(i == 0)
                    )
                    db.session.add(room_image)

        db.session.commit()
        flash("Room type added successfully.", "success")
        return redirect(url_for("hms.rooms_types"))

    return render_template("hms/rooms/type_form.html")


@hms_bp.route('/rooms/add', methods=['GET', 'POST'])
@login_required
def rooms_add():
    hotel_ids = get_allowed_hotel_ids()
    hid = get_current_hotel_id() or (hotel_ids[0] if hotel_ids else None)
    if not hid or not require_hotel_access(hid):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.rooms"))

    if request.method == "POST":
        room_number = request.form.get("room_number", "").strip()
        room_type_id = request.form.get("room_type_id", type=int)
        status = request.form.get("status", "Vacant")

        if not room_number or not room_type_id:
            flash("Room number and type required.", "danger")
            return redirect(url_for("hms.rooms_add"))

        try:
            # Use RoomManagementService for safe room creation
            room, message = RoomManagementService.create_room(
                hotel_id=hid,
                room_number=room_number,
                room_type_id=room_type_id,
            )
            
            if room:
                db.session.add(room)
                db.session.commit()
                flash(f"Room {room_number} added. {message}", "success")
            else:
                flash(f"Failed to add room: {message}", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Failed to add room: {str(e)}", "danger")
        
        return redirect(url_for("hms.rooms"))

    types = RoomType.query.filter_by(hotel_id=hid).all()
    return render_template("hms/rooms/form.html", room_types=types, ROOM_STATUSES=ROOM_STATUSES)


@hms_bp.route('/rooms/<int:room_id>/update', methods=['POST'])
@login_required
def rooms_update(room_id):
    """Update room details with validation"""
    room = Room.query.get_or_404(room_id)
    if not require_hotel_access(room.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.rooms"))

    if request.method == "POST":
        room_number = request.form.get("room_number", "").strip()
        room_type_id = request.form.get("room_type_id", type=int)
        floor = request.form.get("floor", type=int)
        status = request.form.get("status", "Vacant")
        reason = request.form.get("reason", "Room details updated")

        if not room_number or not room_type_id:
            flash("Room number and type required.", "danger")
            return redirect(url_for("hms.rooms"))

        rt = RoomType.query.filter_by(id=room_type_id, hotel_id=room.hotel_id).first()
        if not rt:
            flash("Invalid room type.", "danger")
            return redirect(url_for("hms.rooms"))

        room.room_number = room_number
        room.room_type_id = rt.id
        if floor:
            room.floor = floor
        
        # Use safe status change if status is being updated
        if status and status != room.status:
            success, message = RoomManagementService.change_room_status(
                room, status, reason=reason, user_id=current_user.id
            )
            if success:
                flash(f"Room updated. {message}", "success")
            else:
                flash(f"Room updated but status change failed: {message}", "warning")
        else:
            flash("Room updated successfully.", "success")
        
        db.session.commit()

    return redirect(url_for("hms.rooms"))


@hms_bp.route('/rooms/<int:room_id>/change-status', methods=['POST'])
@login_required
def rooms_change_status(room_id):
    """Change room status with full validation and safety checks"""
    room = Room.query.get_or_404(room_id)
    if not require_hotel_access(room.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.rooms"))

    new_status = request.form.get("status")
    reason = request.form.get("reason", "Manual status change")
    
    if new_status not in ("Vacant", "Occupied", "Dirty", "Reserved", "Maintenance"):
        flash("Invalid status.", "danger")
        return redirect(url_for("hms.rooms"))
    
    try:
        # Use RoomManagementService for safe status change with validation
        success, message = RoomManagementService.change_room_status(
            room,
            new_status,
            reason=reason,
            user_id=current_user.id
        )
        
        if success:
            db.session.commit()
            flash(f"Room status updated. {message}", "success")
        else:
            flash(f"Cannot change status: {message}", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to change room status: {str(e)}", "danger")
    
    return redirect(url_for("hms.rooms"))


@hms_bp.route('/rooms/<int:room_id>/delete', methods=['POST'])
@login_required
def rooms_delete(room_id):
    room = Room.query.get_or_404(room_id)
    if not require_hotel_access(room.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.rooms"))

    # Check if room is occupied
    if room.status == "Occupied":
        flash("Cannot delete an occupied room.", "warning")
        return redirect(url_for("hms.rooms"))

    # Check for active bookings (bookings that reference this room)
    from app.models import Booking
    active_bookings = Booking.query.filter_by(room_id=room.id).filter(
        Booking.status.in_(['Reserved', 'CheckedIn', 'CheckedOut'])
    ).all()
    
    if active_bookings:
        flash(f"Cannot delete room {room.room_number} because it has {len(active_bookings)} associated booking(s). Please remove or reassign the booking(s) first.", "warning")
        return redirect(url_for("hms.rooms"))

    room_number = room.room_number
    db.session.delete(room)
    db.session.commit()

    flash(f"Room {room_number} has been deleted.", "success")
    return redirect(url_for("hms.rooms"))


# =============================================================================
# TRANSACTION BLOCKING MIDDLEWARE
# =============================================================================

def check_business_date_lock():
    """Check if current business date is locked and block transactions"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        return False
    
    biz_date = BusinessDate.query.filter_by(hotel_id=hotel_id).first()
    if biz_date and biz_date.is_closed and biz_date.current_business_date == date.today():
        return True
    
    return False

# =============================================================================
# BOOKINGS
# =============================================================================

@hms_bp.route('/bookings', methods=['GET', 'POST'])
@login_required
def bookings():
    if request.method == "POST":
        if check_business_date_lock():
            flash("Transactions are blocked due to business date lock.", "danger")
            return redirect(url_for("hms.bookings"))
    hotel_ids = get_allowed_hotel_ids()
    if not hotel_ids:
        flash("No hotel assigned.", "warning")
        return redirect(url_for("hms.dashboard"))

    current_hid = get_current_hotel_id()
    q = Booking.query.filter(Booking.hotel_id.in_(hotel_ids)).order_by(Booking.check_in_date.desc())
    if current_hid:
        q = q.filter(Booking.hotel_id == current_hid)

    bookings = q.all()
    return render_template("hms/bookings/list.html", bookings=bookings)


@hms_bp.route('/bookings/new', methods=['GET', 'POST'])
@login_required
def bookings_new():
    hotel_ids = get_allowed_hotel_ids()
    hid = get_current_hotel_id() or (hotel_ids[0] if hotel_ids else None)

    if not hid or not require_hotel_access(hid):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.bookings"))

    if request.method == "POST":
        # Phase 2 Fix: Check if business date is locked
        is_locked, lock_msg = check_business_date_lock()
        if is_locked:
            flash(lock_msg, "error")
            return redirect(url_for("hms.bookings"))
        
        # Guest handling
        guest_id = request.form.get("guest_id", type=int)
        is_new_guest = request.form.get("is_new_guest") == "on"

        if is_new_guest or not guest_id:
            name = request.form.get("guest_name", "").strip()
            phone = request.form.get("guest_phone", "").strip()
            email = request.form.get("guest_email", "").strip()
            if not name:
                flash("Guest name is required.", "danger")
                return redirect(url_for("hms.bookings_new"))

            guest = Guest(hotel_id=hid, name=name, phone=phone, email=email)
            db.session.add(guest)
            db.session.flush()
        else:
            guest = Guest.query.filter_by(id=guest_id, hotel_id=hid).first()
            if not guest:
                flash("Guest not found.", "danger")
                return redirect(url_for("hms.bookings_new"))

        # Booking details
        room_id = request.form.get("room_id", type=int)
        check_in_str = request.form.get("check_in")
        check_out_str = request.form.get("check_out")
        adults = request.form.get("adults", 1, type=int)
        children = request.form.get("children", 0, type=int)
        special_requests = request.form.get("special_requests", "").strip()
        source = request.form.get("source", "front_desk")

        if not all([room_id, check_in_str, check_out_str]):
            flash("Room and dates are required.", "danger")
            return redirect(url_for("hms.bookings_new"))

        room = Room.query.filter_by(id=room_id, hotel_id=hid).first()
        if not room:
            flash("Invalid room.", "danger")
            return redirect(url_for("hms.bookings_new"))

        try:
            check_in_d = datetime.strptime(check_in_str, "%Y-%m-%d").date()
            check_out_d = datetime.strptime(check_out_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid dates.", "danger")
            return redirect(url_for("hms.bookings_new"))

        if check_out_d <= check_in_d:
            flash("Check-out must be after check-in.", "danger")
            return redirect(url_for("hms.bookings_new"))

        try:
            # Use BookingService to create booking with proper validation
            booking, message = BookingService.create_booking(
                hotel_id=hid,
                guest=guest,
                room=room,
                check_in_date=check_in_d,
                check_out_date=check_out_d,
                adults=adults,
                children=children,
                special_requests=special_requests,
                source=source,
                user_id=current_user.id
            )
            
            if booking:
                db.session.commit()
                flash(f"Booking created for {guest.name}. Reference: {booking.booking_reference}", "success")
                return redirect(url_for("hms.bookings"))
            else:
                flash(message, "danger")
                return redirect(url_for("hms.bookings_new"))
                
        except Exception as e:
            db.session.rollback()
            flash(f"Failed to create booking: {str(e)}", "danger")
            return redirect(url_for("hms.bookings_new"))

    # GET - show form
    guests = Guest.query.filter_by(hotel_id=hid).order_by(Guest.name).limit(100).all()

    # Get room categories
    room_types = RoomType.query.filter_by(hotel_id=hid, is_active=True).all()
    categories = list(set(rt.category for rt in room_types if rt.category))
    prices = {rt.category: float(rt.base_price) for rt in room_types if rt.category}

    today = date.today().strftime('%Y-%m-%d')

    return render_template("hms/bookings/form.html", guests=guests,
                          categories=categories, prices=prices, today=today)


@hms_bp.route('/bookings/<int:booking_id>/check-in', methods=['POST'])
@login_required
def bookings_check_in(booking_id):
    """Check in a guest - uses BookingService for proper lifecycle management"""
    booking = Booking.query.get_or_404(booking_id)
    if not require_hotel_access(booking.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.bookings"))

    # Phase 2 Fix: Check if business date is locked
    is_locked, lock_msg = check_business_date_lock()
    if is_locked:
        flash(lock_msg, "error")
        return redirect(url_for("hms.bookings"))

    try:
        # Use BookingService for proper check-in with validation
        success, message = BookingService.check_in(booking, user_id=current_user.id)

        if success:
            db.session.commit()
            flash(message, "success")
        else:
            flash(message, "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Check-in failed: {str(e)}", "danger")

    return redirect(url_for("hms.bookings"))


@hms_bp.route('/bookings/<int:booking_id>/check-out', methods=['POST'])
@login_required
def bookings_check_out(booking_id):
    """Check out a guest - uses BookingService with balance validation"""
    booking = Booking.query.get_or_404(booking_id)
    if not require_hotel_access(booking.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.bookings"))

    # Phase 2 Fix: Check if business date is locked
    is_locked, lock_msg = check_business_date_lock()
    if is_locked:
        flash(lock_msg, "error")
        return redirect(url_for("hms.bookings"))

    try:
        # Use BookingService for proper check-out with balance validation
        success, message = BookingService.check_out(booking, user_id=current_user.id)

        if success:
            db.session.commit()
            flash(message, "success")
        else:
            # If balance issue, redirect to payment
            if "balance" in message.lower():
                return redirect(url_for('hms.bookings_payment', booking_id=booking.id))
            flash(message, "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Check-out failed: {str(e)}", "danger")

    return redirect(url_for("hms.bookings"))


@hms_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
def bookings_cancel(booking_id):
    """Cancel a booking with proper fee calculation and refund"""
    booking = Booking.query.get_or_404(booking_id)
    if not require_hotel_access(booking.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.bookings"))

    # Validate booking can be cancelled
    if booking.status != "Reserved":
        flash(f"Cannot cancel booking with status {booking.status}. Only Reserved bookings can be cancelled.", "warning")
        return redirect(url_for("hms.bookings"))

    try:
        # Use BookingService for proper cancellation with fee calculation
        reason = request.form.get('cancellation_reason', '').strip()
        success, message = BookingService.cancel_booking(
            booking,
            reason=reason,
            user_id=current_user.id
        )
        
        if success:
            db.session.commit()
            flash(f"Booking cancelled successfully. {message}", "success")
        else:
            flash(message, "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to cancel booking: {str(e)}", "danger")

    return redirect(url_for("hms.bookings"))


@hms_bp.route('/bookings/<int:booking_id>/no-show', methods=['POST'])
@login_required
def bookings_no_show(booking_id):
    """Mark booking as no-show with fee"""
    booking = Booking.query.get_or_404(booking_id)
    if not require_hotel_access(booking.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.bookings"))

    # Validate booking can be marked as no-show
    if booking.status != "Reserved":
        flash(f"Cannot mark no-show for booking with status {booking.status}. Only Reserved bookings can be marked as no-show.", "warning")
        return redirect(url_for("hms.bookings"))

    # Validate check-in date has passed
    if booking.check_in_date >= date.today():
        flash("Cannot mark as no-show before check-in date.", "warning")
        return redirect(url_for("hms.bookings"))

    try:
        # Use BookingService for proper no-show handling with fee
        success, message = BookingService.mark_no_show(
            booking,
            user_id=current_user.id
        )
        
        if success:
            db.session.commit()
            flash(f"No-show recorded. {message}", "success")
        else:
            flash(message, "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to mark no-show: {str(e)}", "danger")

    return redirect(url_for("hms.bookings"))


@hms_bp.route('/bookings/<int:booking_id>/payment', methods=['GET', 'POST'])
@login_required
def bookings_payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if not require_hotel_access(booking.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.bookings"))

    inv = booking.invoice
    if not inv:
        flash("No invoice for this booking.", "danger")
        return redirect(url_for("hms.bookings"))

    if request.method == "POST":
        # Phase 2 Fix: Check if business date is locked
        is_locked, lock_msg = check_business_date_lock()
        if is_locked:
            flash(lock_msg, "error")
            return redirect(url_for("hms.bookings"))
        
        amount = request.form.get("amount", type=float)
        method = request.form.get("payment_method", "Cash")

        if not amount or amount <= 0:
            flash("Invalid amount.", "danger")
            return redirect(url_for("hms.bookings_payment", booking_id=booking_id))

        paid = sum(p.amount for p in inv.payments if p.deleted_at is None)
        inv.status = "Paid" if paid + Decimal(str(amount)) >= inv.total else "PartiallyPaid"

        pay = Payment(hotel_id=booking.hotel_id, invoice_id=inv.id,
                     amount=Decimal(str(amount)), payment_method=method, booking_id=booking.id)
        db.session.add(pay)
        
        # Create journal entry for this payment
        # Debit: Cash/Bank account (Asset increases)
        # Credit: Revenue account (Revenue increases)
        try:
            # Get or create default accounts
            cash_account = ChartOfAccount.query.filter(
                ChartOfAccount.hotel_id == booking.hotel_id,
                ChartOfAccount.type == "Asset",
                ChartOfAccount.name == "Cash"
            ).first()
            if not cash_account:
                cash_account = ChartOfAccount(
                    hotel_id=booking.hotel_id,
                    name="Cash",
                    type="Asset"
                )
                db.session.add(cash_account)
                db.session.flush()
            
            revenue_account = ChartOfAccount.query.filter(
                ChartOfAccount.hotel_id == booking.hotel_id,
                ChartOfAccount.type == "Revenue",
                ChartOfAccount.name == "Room Revenue"
            ).first()
            if not revenue_account:
                revenue_account = ChartOfAccount(
                    hotel_id=booking.hotel_id,
                    name="Room Revenue",
                    type="Revenue"
                )
                db.session.add(revenue_account)
                db.session.flush()
            
            # Create journal entry
            journal_entry = JournalEntry(
                hotel_id=booking.hotel_id,
                reference=f"PAY-{pay.id}",
                date=date.today(),
                description=f"Payment for booking {booking.booking_reference or booking.id}"
            )
            db.session.add(journal_entry)
            db.session.flush()
            
            # Debit line (Cash increases)
            debit_line = JournalLine(
                journal_entry_id=journal_entry.id,
                account_id=cash_account.id,
                debit=Decimal(str(amount)),
                credit=0,
                payment_id=pay.id,
                invoice_id=inv.id
            )
            db.session.add(debit_line)
            
            # Credit line (Revenue increases)
            credit_line = JournalLine(
                journal_entry_id=journal_entry.id,
                account_id=revenue_account.id,
                debit=0,
                credit=Decimal(str(amount)),
                payment_id=pay.id,
                invoice_id=inv.id
            )
            db.session.add(credit_line)
            
        except Exception as e:
            # Log error but don't fail the payment
            current_app.logger.error(f"Failed to create journal entry: {e}")
        
        db.session.commit()

        flash("Payment recorded.", "success")
        return redirect(url_for("hms.bookings"))

    paid_total = sum(p.amount for p in inv.payments if p.deleted_at is None)
    return render_template("hms/bookings/payment.html", booking=booking, invoice=inv, paid_total=paid_total)


@hms_bp.route('/bookings/available-rooms')
@login_required
def bookings_available_rooms():
    """AJAX endpoint for available rooms"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        return jsonify({'success': False, 'error': 'No hotel selected'}), 400

    check_in_str = request.args.get("check_in")
    check_out_str = request.args.get("check_out")

    if not check_in_str or not check_out_str:
        return jsonify({'success': False, 'error': 'Dates required'}), 400

    try:
        check_in_d = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        check_out_d = datetime.strptime(check_out_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date format'}), 400

    if check_out_d <= check_in_d:
        return jsonify({'success': False, 'error': 'Check-out must be after check-in'}), 400

    all_rooms = Room.query.filter(Room.hotel_id == hotel_id, Room.is_active == True).all()
    booked_room_ids = db.session.query(Booking.room_id).filter(
        Booking.hotel_id == hotel_id, Booking.status.in_(("Reserved", "CheckedIn")),
        Booking.check_in_date < check_out_d, Booking.check_out_date > check_in_d
    ).all()
    booked_room_ids = [r[0] for r in booked_room_ids]

    available = []
    for room in all_rooms:
        if room.id not in booked_room_ids:
            nights = (check_out_d - check_in_d).days
            available.append({
                'id': room.id,
                'room_number': room.room_number,
                'room_type': room.room_type.name,
                'base_price': float(room.room_type.base_price),
                'total_price': float(room.room_type.base_price * nights)
            })

    return jsonify({'success': True, 'rooms': available, 'count': len(available)})


@hms_bp.route('/bookings/guests/search')
@login_required
def bookings_guests_search():
    """AJAX endpoint for guest search"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        return jsonify({'success': False, 'error': 'No hotel selected'}), 400

    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({'success': True, 'guests': []})

    guests = Guest.query.filter(
        Guest.hotel_id == hotel_id,
        db.or_(Guest.name.ilike(f"%{query}%"), Guest.phone.ilike(f"%{query}%"),
               Guest.email.ilike(f"%{query}%"))
    ).order_by(Guest.name).limit(20).all()

    result = [{
        'id': g.id, 'name': g.name, 'phone': g.phone or '', 'email': g.email or ''
    } for g in guests]

    return jsonify({'success': True, 'guests': result})


@hms_bp.route('/api/available-rooms')
@login_required
def api_available_rooms():
    """Get available rooms by category and dates"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        return jsonify({'success': False, 'error': 'No hotel selected'}), 400
    
    category = request.args.get('category', '')
    check_in_str = request.args.get('check_in', '')
    check_out_str = request.args.get('check_out', '')
    
    if not all([category, check_in_str, check_out_str]):
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400
    
    try:
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date format'}), 400
    
    if check_out <= check_in:
        return jsonify({'success': False, 'error': 'Check-out must be after check-in'}), 400
    
    # Get room types in category
    room_types = RoomType.query.filter_by(hotel_id=hotel_id, category=category, is_active=True).all()
    room_type_ids = [rt.id for rt in room_types]
    
    if not room_type_ids:
        return jsonify({'success': True, 'rooms': []})
    
    # Get booked rooms for the period
    booked_room_ids = db.session.query(Booking.room_id).filter(
        Booking.hotel_id == hotel_id,
        Booking.room_id.isnot(None),
        Booking.status.in_(['Reserved', 'CheckedIn']),
        Booking.check_in_date < check_out,
        Booking.check_out_date > check_in
    ).all()
    booked_room_ids = [r[0] for r in booked_room_ids]
    
    # Get available rooms
    available_rooms = Room.query.filter(
        Room.hotel_id == hotel_id,
        Room.room_type_id.in_(room_type_ids),
        Room.is_active == True,
        Room.status.in_(['Vacant', 'Dirty']),
        ~Room.id.in_(booked_room_ids) if booked_room_ids else True
    ).all()
    
    rooms_data = []
    for room in available_rooms:
        rooms_data.append({
            'id': room.id,
            'room_number': room.room_number,
            'status': room.status,
            'room_type': {
                'id': room.room_type.id,
                'name': room.room_type.name,
                'base_price': float(room.room_type.base_price)
            }
        })
    
    return jsonify({'success': True, 'rooms': rooms_data})


# =============================================================================
# HOUSEKEEPING
# =============================================================================

@hms_bp.route('/housekeeping')
@login_required
def housekeeping():
    """Housekeeping dashboard with task management"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    # Get all rooms with their status
    rooms = Room.query.filter_by(hotel_id=hotel_id).order_by(Room.floor, Room.room_number).all()

    # Get housekeeping tasks by status - sorted by priority
    pending_tasks = HousekeepingTask.query.filter_by(
        hotel_id=hotel_id, status='pending'
    ).order_by(HousekeepingTask.priority.desc(), HousekeepingTask.created_at.desc()).all()

    in_progress_tasks = HousekeepingTask.query.filter_by(
        hotel_id=hotel_id, status='in_progress'
    ).all()

    completed_today = HousekeepingTask.query.filter(
        HousekeepingTask.hotel_id == hotel_id,
        HousekeepingTask.status == 'completed',
        db.func.date(HousekeepingTask.completed_at) == date.today()
    ).count()

    # Count by room status
    status_counts = {
        'Vacant': len([r for r in rooms if r.status == 'Vacant']),
        'Occupied': len([r for r in rooms if r.status == 'Occupied']),
        'Dirty': len([r for r in rooms if r.status == 'Dirty']),
        'Reserved': len([r for r in rooms if r.status == 'Reserved'])
    }

    return render_template("hms/housekeeping/index.html",
                         rooms=rooms,
                         status_counts=status_counts,
                         pending_tasks=pending_tasks,
                         in_progress_tasks=in_progress_tasks,
                         completed_today=completed_today)


@hms_bp.route('/housekeeping/task/create/<int:room_id>', methods=['POST'])
@login_required
def housekeeping_create_task(room_id):
    """Create housekeeping task for room"""
    room = Room.query.get_or_404(room_id)
    if not require_hotel_access(room.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.housekeeping"))

    task_type = request.form.get('task_type', 'regular_clean')
    priority = request.form.get('priority', 'normal')
    notes = request.form.get('notes', '')

    try:
        # Use service function to create task with proper validation
        task = create_cleaning_task(
            room=room,
            task_type=task_type,
            priority=priority,
            notes=notes,
            user_id=current_user.id
        )
        
        db.session.commit()
        
        flash(f"Task created for room {room.room_number}", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to create task: {str(e)}", "danger")
    
    return redirect(url_for("hms.housekeeping"))


@hms_bp.route('/housekeeping/task/<int:task_id>/assign', methods=['POST'])
@login_required
def housekeeping_assign_task(task_id):
    """Assign task to staff member"""
    task = HousekeepingTask.query.get_or_404(task_id)
    if not require_hotel_access(task.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.housekeeping"))

    staff_id = request.form.get('staff_id', type=int)
    
    try:
        if staff_id:
            # Validate staff member exists and has appropriate role
            staff = User.query.get(staff_id)
            if not staff or staff.hotel_id != task.hotel_id:
                flash("Invalid staff member selected.", "danger")
                return redirect(url_for("hms.housekeeping"))
            
            task.completed_by = staff_id
            task.status = 'in_progress'
            task.started_at = datetime.utcnow()
            
            db.session.commit()
            flash("Task assigned", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to assign task: {str(e)}", "danger")

    return redirect(url_for("hms.housekeeping"))


@hms_bp.route('/housekeeping/task/<int:task_id>/start', methods=['POST'])
@login_required
def housekeeping_start_task(task_id):
    """Start a task"""
    task = HousekeepingTask.query.get_or_404(task_id)
    if not require_hotel_access(task.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.housekeeping"))

    try:
        # Validate task can be started
        if task.status != 'pending':
            flash(f"Task cannot be started (current status: {task.status})", "warning")
            return redirect(url_for("hms.housekeeping"))
        
        task.status = 'in_progress'
        task.started_at = datetime.utcnow()
        
        # Auto-assign to current user if not assigned
        if not task.completed_by:
            task.completed_by = current_user.id
        
        db.session.commit()
        flash("Task started", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to start task: {str(e)}", "danger")
    
    return redirect(url_for("hms.housekeeping"))


@hms_bp.route('/housekeeping/task/<int:task_id>/complete', methods=['POST'])
@login_required
def housekeeping_complete_task(task_id):
    """Complete task and mark room as clean"""
    task = HousekeepingTask.query.get_or_404(task_id)
    if not require_hotel_access(task.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.housekeeping"))

    try:
        # Validate task can be completed
        if task.status != 'in_progress':
            flash(f"Task must be in progress to complete (current: {task.status})", "warning")
            return redirect(url_for("hms.housekeeping"))
        
        # Use service function to complete task with proper validation
        success, message = complete_cleaning_task(task, user_id=current_user.id)
        
        if success:
            db.session.commit()
            flash(message, "success")
        else:
            flash(message, "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to complete task: {str(e)}", "danger")
    
    return redirect(url_for("hms.housekeeping"))


@hms_bp.route('/housekeeping/room/<int:room_id>/clean', methods=['POST'])
@login_required
def housekeeping_clean_room(room_id):
    """Quick clean - mark room as clean"""
    room = Room.query.get_or_404(room_id)
    if not require_hotel_access(room.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.housekeeping"))

    try:
        # Use service function with proper validation
        success, message = quick_clean_room(room, user_id=current_user.id)
        
        if success:
            db.session.commit()
            flash(message, "success")
        else:
            flash(message, "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to clean room: {str(e)}", "danger")

    return redirect(url_for("hms.housekeeping"))


@hms_bp.route('/housekeeping/room/<int:room_id>/dirty', methods=['POST'])
@login_required
def housekeeping_dirty_room(room_id):
    """Mark room as dirty"""
    room = Room.query.get_or_404(room_id)
    if not require_hotel_access(room.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.housekeeping"))

    try:
        # Use service function with proper validation
        success, message = quick_dirty_room(room, user_id=current_user.id)
        
        if success:
            db.session.commit()
            flash(message, "success")
        else:
            flash(message, "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to mark room dirty: {str(e)}", "danger")

    return redirect(url_for("hms.housekeeping"))


# =============================================================================
# ACCOUNTING
# =============================================================================

@hms_bp.route('/accounting')
@login_required
def accounting():
    """Accounting dashboard"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    if not can_access_module('accounting'):
        flash("Access denied. Accountant or Manager role required.", "danger")
        return redirect(url_for("hms.dashboard"))

    # Get summary stats
    today = date.today()
    first_day = today.replace(day=1)

    # Get revenue and expense account IDs
    revenue_accounts = ChartOfAccount.query.filter_by(
        hotel_id=hotel_id, type="Revenue"
    ).all()
    revenue_account_ids = [a.id for a in revenue_accounts]
    
    expense_accounts = ChartOfAccount.query.filter_by(
        hotel_id=hotel_id, type="Expense"
    ).all()
    expense_account_ids = [a.id for a in expense_accounts]

    # Revenue this month (sum of credits to revenue accounts + payments)
    revenue = 0
    if revenue_account_ids:
        # Revenue from journal entries
        revenue_from_journal = db.session.query(db.func.coalesce(db.func.sum(JournalLine.credit), 0)).join(
            JournalEntry
        ).filter(
            JournalEntry.hotel_id == hotel_id,
            JournalEntry.date >= first_day,
            JournalEntry.deleted_at.is_(None),
            JournalLine.account_id.in_(revenue_account_ids),
            JournalLine.deleted_at.is_(None)
        ).scalar()
        revenue += revenue_from_journal
    
    # Revenue from payments this month
    revenue_from_payments = db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).filter(
        Payment.hotel_id == hotel_id,
        Payment.created_at >= first_day,
        Payment.status == 'completed',
        Payment.deleted_at.is_(None)
    ).scalar()
    revenue += revenue_from_payments

    # Expenses this month (sum of debits to expense accounts)
    expenses = 0
    if expense_account_ids:
        expenses = db.session.query(db.func.coalesce(db.func.sum(JournalLine.debit), 0)).join(
            JournalEntry
        ).filter(
            JournalEntry.hotel_id == hotel_id,
            JournalEntry.date >= first_day,
            JournalEntry.deleted_at.is_(None),
            JournalLine.account_id.in_(expense_account_ids),
            JournalLine.deleted_at.is_(None)
        ).scalar()

    # Recent journal entries
    recent_entries = JournalEntry.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).order_by(JournalEntry.date.desc()).limit(10).all()

    # Recent payments
    recent_payments = Payment.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).order_by(Payment.created_at.desc()).limit(10).all()

    return render_template("hms/accounting/index.html",
                         revenue=revenue,
                         expenses=expenses,
                         profit=revenue - expenses,
                         revenue_from_journal=revenue_from_journal if revenue_account_ids else 0,
                         revenue_from_payments=revenue_from_payments,
                         recent_entries=recent_entries,
                         recent_payments=recent_payments,
                         today=today)


@hms_bp.route('/accounting/chart')
@login_required
def accounting_chart():
    """Chart of Accounts"""
    hotel_id = get_current_hotel_id()
    if not hotel_id or not can_access_module('accounting'):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.dashboard"))
    
    accounts = ChartOfAccount.query.filter_by(hotel_id=hotel_id).order_by(
        ChartOfAccount.type, ChartOfAccount.name
    ).all()
    
    # Calculate balances
    for account in accounts:
        lines = JournalLine.query.filter_by(account_id=account.id).all()
        account.balance = sum((line.debit or 0) - (line.credit or 0) for line in lines)
    
    return render_template("hms/accounting/chart.html", accounts=accounts)


@hms_bp.route('/accounting/entries')
@login_required
def accounting_entries():
    """Journal Entries"""
    hotel_id = get_current_hotel_id()
    if not hotel_id or not can_access_module('accounting'):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.dashboard"))
    
    entries = JournalEntry.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).order_by(JournalEntry.date.desc()).limit(50).all()
    
    return render_template("hms/accounting/entries.html", entries=entries)


@hms_bp.route('/accounting/entry/create', methods=['GET', 'POST'])
@login_required
def accounting_entry_create():
    """Create journal entry"""
    hotel_id = get_current_hotel_id()
    if not hotel_id or not can_access_module('accounting'):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.dashboard"))
    
    if request.method == 'POST':
        entry_date = request.form.get("date", date.today().isoformat())
        reference = request.form.get("reference", "")
        account_ids = request.form.getlist("account_id[]")
        debits = request.form.getlist("debit[]")
        credits = request.form.getlist("credit[]")
        
        try:
            # Create journal entry
            entry = JournalEntry(
                hotel_id=hotel_id,
                date=datetime.strptime(entry_date, '%Y-%m-%d').date(),
                reference=reference
            )
            db.session.add(entry)
            db.session.flush()
            
            # Create journal lines
            total_debit = 0
            total_credit = 0
            
            for acc_id, debit_val, credit_val in zip(account_ids, debits, credits):
                if acc_id and (debit_val or credit_val):
                    debit = float(debit_val) if debit_val else 0
                    credit = float(credit_val) if credit_val else 0
                    
                    if debit > 0 or credit > 0:
                        line = JournalLine(
                            journal_entry_id=entry.id,
                            account_id=int(acc_id),
                            debit=debit,
                            credit=credit
                        )
                        db.session.add(line)
                        total_debit += debit
                        total_credit += credit
            
            # Verify balance
            if abs(total_debit - total_credit) > 0.01:
                db.session.rollback()
                flash("Debits and credits must balance!", "danger")
                return redirect(url_for("hms.accounting_entry_create"))
            
            db.session.commit()
            flash("Journal entry created successfully!", "success")
            return redirect(url_for("hms.accounting_entries"))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating entry: {str(e)}", "danger")
            return redirect(url_for("hms.accounting_entry_create"))
    
    # GET - show form
    from datetime import date
    accounts = ChartOfAccount.query.filter_by(hotel_id=hotel_id).all()
    return render_template("hms/accounting/entry_form.html", accounts=accounts, today=date.today())


@hms_bp.route('/accounting/reports')
@login_required
def accounting_reports():
    """Financial Reports"""
    hotel_id = get_current_hotel_id()
    if not hotel_id or not can_access_module('accounting'):
        flash("Access denied.", "danger")
        return redirect(url_for("hms.dashboard"))
    
    # Get period from query params
    period = request.args.get('period', 'this_month')
    today = date.today()
    
    # Calculate date range
    if period == 'today':
        start_date = today
        end_date = today
    elif period == 'this_week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif period == 'this_month':
        start_date = today.replace(day=1)
        end_date = today.replace(day=monthrange(today.year, today.month)[1])
    else:
        start_date = today.replace(day=1)
        end_date = today
    
    # Get revenue and expenses
    revenue = db.session.query(db.func.coalesce(db.func.sum(JournalLine.credit), 0)).join(
        JournalEntry
    ).filter(
        JournalEntry.hotel_id == hotel_id,
        JournalEntry.date >= start_date,
        JournalEntry.date <= end_date,
        JournalEntry.deleted_at.is_(None)
    ).scalar()
    
    expenses = db.session.query(db.func.coalesce(db.func.sum(JournalLine.debit), 0)).join(
        JournalEntry
    ).filter(
        JournalEntry.hotel_id == hotel_id,
        JournalEntry.date >= start_date,
        JournalEntry.date <= end_date,
        JournalEntry.deleted_at.is_(None)
    ).scalar()
    
    return render_template("hms/accounting/reports.html",
                         revenue=revenue,
                         expenses=expenses,
                         profit=revenue - expenses,
                         start_date=start_date,
                         end_date=end_date,
                         period=period)


# =============================================================================
# INVENTORY
# =============================================================================

@hms_bp.route('/inventory')
@login_required
def inventory():
    """Inventory dashboard"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))
    
    # Get summary stats
    total_items = InventoryItem.query.filter_by(hotel_id=hotel_id, deleted_at=None).count()
    low_stock = InventoryItem.query.filter(
        InventoryItem.hotel_id == hotel_id,
        InventoryItem.deleted_at.is_(None),
        InventoryItem.current_stock <= InventoryItem.reorder_level
    ).count()
    
    # Get low stock items
    low_stock_items = InventoryItem.query.filter(
        InventoryItem.hotel_id == hotel_id,
        InventoryItem.deleted_at.is_(None),
        InventoryItem.current_stock <= InventoryItem.reorder_level
    ).limit(10).all()
    
    return render_template("hms/inventory/index.html",
                         total_items=total_items,
                         low_stock=low_stock,
                         low_stock_items=low_stock_items)


@hms_bp.route('/inventory/items')
@login_required
def inventory_items():
    """Inventory items list"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))
    
    items = InventoryItem.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).order_by(InventoryItem.name).all()
    
    # Get categories for filter dropdown
    categories = InventoryCategory.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).order_by(InventoryCategory.name).all()
    
    return render_template("hms/inventory/items.html", items=items, categories=categories)


@hms_bp.route('/inventory/items/add', methods=['GET', 'POST'])
@login_required
def inventory_item_add():
    """Add inventory item"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))
    
    def render_inventory_add_form():
        """Helper function to render the add item form"""
        categories = InventoryCategory.query.filter_by(
            hotel_id=hotel_id,
            deleted_at=None
        ).order_by(InventoryCategory.name).all()
        return render_template("hms/inventory/item_form.html", 
                             categories=categories, 
                             item=None, 
                             title="Add Inventory Item")
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            category_id = request.form.get('category_id')
            unit = request.form.get('unit', '').strip()
            reorder_level = request.form.get('reorder_level', '0')
            current_stock = request.form.get('current_stock', '0')
            average_cost = request.form.get('average_cost', '0')
            
            # Validation
            if not name:
                flash("Item name is required.", "error")
                return render_inventory_add_form()
            
            if not category_id:
                flash("Category is required.", "error")
                return render_inventory_add_form()
            
            if not unit:
                flash("Unit is required.", "error")
                return render_inventory_add_form()
            
            # Auto-generate SKU from item name
            import re
            sku_base = re.sub(r'[^a-zA-Z0-9]', '', name.upper())[:8]
            sku_count = InventoryItem.query.filter_by(hotel_id=hotel_id, deleted_at=None).filter(
                InventoryItem.sku.like(f'{sku_base}%')
            ).count()
            sku = f"{sku_base}-{sku_count + 1:03d}"
            
            # Check if SKU already exists (unlikely but possible)
            existing_item = InventoryItem.query.filter_by(sku=sku, hotel_id=hotel_id, deleted_at=None).first()
            if existing_item:
                flash(f"Item with SKU '{sku}' already exists.", "error")
                return render_inventory_add_form()
            
            # Create new inventory item
            item = InventoryItem(
                hotel_id=hotel_id,
                category_id=int(category_id),
                sku=sku,
                name=name,
                description=description,
                unit=unit,
                reorder_level=float(reorder_level) if reorder_level else 0,
                current_stock=float(current_stock) if current_stock else 0,
                average_cost=float(average_cost) if average_cost else 0
            )
            
            db.session.add(item)
            db.session.commit()
            
            flash(f"Inventory item '{name}' added successfully.", "success")
            return redirect(url_for('hms.inventory_items'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding inventory item: {str(e)}")
            flash("An error occurred while adding the item. Please try again.", "error")
            return render_inventory_add_form()
    
    return render_inventory_add_form()


@hms_bp.route('/inventory/suppliers')
@login_required
def inventory_suppliers():
    """Suppliers list"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))
    
    suppliers = Supplier.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).order_by(Supplier.name).all()
    
    return render_template("hms/inventory/suppliers.html", suppliers=suppliers)


@hms_bp.route('/inventory/suppliers/add', methods=['GET', 'POST'])
@login_required
def supplier_add():
    """Add supplier"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))
    
    def render_supplier_form():
        """Helper function to render the supplier form"""
        return render_template("hms/inventory/supplier_form.html", 
                             supplier=None, 
                             title="Add Supplier")
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            contact_person = request.form.get('contact_person', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()
            tax_id = request.form.get('tax_id', '').strip()
            payment_terms = request.form.get('payment_terms', '').strip()
            notes = request.form.get('notes', '').strip()
            
            # Validation
            if not name:
                flash("Supplier name is required.", "error")
                return render_supplier_form()
            
            # Check if supplier already exists
            existing_supplier = Supplier.query.filter_by(name=name, hotel_id=hotel_id, deleted_at=None).first()
            if existing_supplier:
                flash(f"Supplier '{name}' already exists.", "error")
                return render_supplier_form()
            
            # Create new supplier
            supplier = Supplier(
                hotel_id=hotel_id,
                name=name,
                contact_person=contact_person or None,
                email=email or None,
                phone=phone or None,
                address=address or None,
                tax_id=tax_id or None,
                payment_terms=payment_terms or None,
                notes=notes or None
            )
            
            db.session.add(supplier)
            db.session.commit()
            
            flash(f"Supplier '{name}' added successfully.", "success")
            return redirect(url_for('hms.inventory_suppliers'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding supplier: {str(e)}")
            flash("An error occurred while adding the supplier. Please try again.", "error")
            return render_supplier_form()
    
    return render_supplier_form()


@hms_bp.route('/inventory/purchase-orders')
@login_required
def inventory_purchase_orders():
    """Purchase orders list"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))
    
    orders = PurchaseOrder.query.filter_by(
        hotel_id=hotel_id
    ).order_by(PurchaseOrder.order_date.desc()).limit(50).all()
    
    # Get suppliers for filter dropdown
    suppliers = Supplier.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).order_by(Supplier.name).all()
    
    return render_template("hms/inventory/purchase_orders.html", orders=orders, suppliers=suppliers)


@hms_bp.route('/inventory/purchase-orders/add', methods=['GET', 'POST'])
@login_required
def purchase_order_add():
    """Add purchase order"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))
    
    if request.method == 'POST':
        try:
            # Get form data
            supplier_id = request.form.get('supplier_id')
            expected_date = request.form.get('expected_date')
            notes = request.form.get('notes', '').strip()
            
            # Get items data
            item_ids = request.form.getlist('item_id[]')
            quantities = request.form.getlist('quantity[]')
            unit_costs = request.form.getlist('unit_cost[]')
            item_notes = request.form.getlist('item_notes[]')
            
            # Validation
            if not supplier_id:
                flash("Supplier is required.", "error")
                return render_purchase_order_form()
            
            if not item_ids or not any(item_ids):
                flash("At least one item is required.", "error")
                return render_purchase_order_form()
            
            # Generate PO number
            from datetime import datetime
            po_count = PurchaseOrder.query.filter_by(hotel_id=hotel_id).count()
            po_number = f"PO-{datetime.now().strftime('%Y%m%d')}-{po_count + 1:04d}"
            
            # Create purchase order
            purchase_order = PurchaseOrder(
                hotel_id=hotel_id,
                po_number=po_number,
                supplier_id=int(supplier_id),
                expected_date=datetime.strptime(expected_date, '%Y-%m-%d').date() if expected_date else None,
                notes=notes,
                created_by=current_user.id
            )
            
            db.session.add(purchase_order)
            db.session.flush()  # Get the PO ID
            
            # Add items
            total_amount = 0
            for i, item_id in enumerate(item_ids):
                if item_id and i < len(quantities) and i < len(unit_costs):
                    quantity = float(quantities[i]) if quantities[i] else 0
                    unit_cost = float(unit_costs[i]) if unit_costs[i] else 0
                    
                    if quantity > 0 and unit_cost > 0:
                        item_total = quantity * unit_cost
                        total_amount += item_total
                        
                        po_item = PurchaseOrderItem(
                            po_id=purchase_order.id,
                            item_id=int(item_id),
                            quantity=quantity,
                            unit_cost=unit_cost,
                            notes=item_notes[i] if i < len(item_notes) else None
                        )
                        db.session.add(po_item)
            
            purchase_order.total_amount = total_amount
            db.session.commit()
            
            flash(f"Purchase Order '{po_number}' created successfully.", "success")
            return redirect(url_for('hms.inventory_purchase_orders'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding purchase order: {str(e)}")
            flash("An error occurred while creating the purchase order. Please try again.", "error")
            return render_purchase_order_form()
    
    return render_purchase_order_form()


def render_purchase_order_form():
    """Helper function to render the purchase order form"""
    hotel_id = get_current_hotel_id()
    
    suppliers = Supplier.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).order_by(Supplier.name).all()
    
    items = InventoryItem.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).order_by(InventoryItem.name).all()
    
    return render_template("hms/inventory/purchase_order_form.html", 
                         suppliers=suppliers, 
                         items=items, 
                         purchase_order=None, 
                         title="New Purchase Order")




# =============================================================================
# RESTAURANT / POS - Full Implementation
# =============================================================================

# Restaurant constants (Week 1-3)
ORDER_STATUSES = ['pending', 'preparing', 'ready', 'completed', 'cancelled']
PAYMENT_STATUSES = ['unpaid', 'partial', 'paid', 'refunded']
PAYMENT_METHODS = ['cash', 'card', 'mobile', 'room_charge']

@hms_bp.route('/restaurant')
@login_required
def restaurant():
    """Restaurant dashboard"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    menu_items = MenuItem.query.filter_by(hotel_id=hotel_id, deleted_at=None).count()
    tables = RestaurantTable.query.filter_by(hotel_id=hotel_id).count()
    categories = MenuCategory.query.filter_by(hotel_id=hotel_id, deleted_at=None).count()
    
    # Get today's orders count
    from datetime import datetime, date
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    today_orders = RestaurantOrder.query.filter(
        RestaurantOrder.hotel_id == hotel_id,
        RestaurantOrder.created_at >= today_start,
        RestaurantOrder.created_at <= today_end
    ).count()
    
    # Get pending orders
    pending_orders = RestaurantOrder.query.filter_by(
        hotel_id=hotel_id,
        status='pending'
    ).count()
    
    # Get available tables (not occupied)
    available_tables = RestaurantTable.query.filter_by(
        hotel_id=hotel_id,
        status='available'
    ).count()

    return render_template("hms/restaurant/index.html", 
                         menu_items=menu_items, 
                         tables=tables,
                         categories=categories,
                         today_orders=today_orders,
                         pending_orders=pending_orders,
                         available_tables=available_tables)


@hms_bp.route('/restaurant/menu')
@login_required
def restaurant_menu():
    """Menu management"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))
    
    categories = MenuCategory.query.filter_by(hotel_id=hotel_id, deleted_at=None).order_by(MenuCategory.display_order, MenuCategory.name).all()
    items = MenuItem.query.filter_by(hotel_id=hotel_id, deleted_at=None).all()
    
    for category in categories:
        category.item_count = MenuItem.query.filter_by(category_id=category.id, deleted_at=None).count()
    
    return render_template("hms/restaurant/menu.html", categories=categories, items=items)


@hms_bp.route('/restaurant/menu/item/add', methods=['GET', 'POST'])
@login_required
def menu_item_add():
    """Add menu item"""
    hotel_id = get_current_hotel_id()
    
    if request.method == 'POST':
        # Skip CSRF check for now
        if not hotel_id:
            flash("Please select a hotel first.", "warning")
            return redirect(url_for('hms.dashboard'))
        
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category_id = request.form.get('category_id', type=int)
        price = request.form.get('price', type=float)
        preparation_time = request.form.get('preparation_time', type=int)
        is_available = request.form.get('is_available') == 'on'
        
        if not name:
            flash("Name is required.", "danger")
            categories = MenuCategory.query.filter_by(hotel_id=hotel_id, deleted_at=None).all() if hotel_id else []
            return render_template("hms/restaurant/item_form.html", categories=categories, item=None)
        
        if not price:
            flash("Price is required.", "danger")
            categories = MenuCategory.query.filter_by(hotel_id=hotel_id, deleted_at=None).all() if hotel_id else []
            return render_template("hms/restaurant/item_form.html", categories=categories, item=None)
        
        item = MenuItem(
            hotel_id=hotel_id,
            category_id=category_id,
            name=name,
            description=description,
            price=price,
            preparation_time=preparation_time,
            is_available=is_available
        )
        db.session.add(item)
        db.session.commit()
        
        flash(f"Menu item '{name}' added successfully.", "success")
        return redirect(url_for('hms.restaurant_menu'))
    
    # GET request
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for('hms.dashboard'))
    
    categories = MenuCategory.query.filter_by(hotel_id=hotel_id, deleted_at=None).all()
    return render_template("hms/restaurant/item_form.html", categories=categories, item=None)


@hms_bp.route('/restaurant/menu/item/<int:item_id>/delete', methods=['POST'])
@login_required
def menu_item_delete(item_id):
    """Delete menu item"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    item = MenuItem.query.get_or_404(item_id)
    if item.hotel_id != hotel_id:
        flash("Access denied.", "danger")
        return redirect(url_for('hms.restaurant_menu'))

    item_name = item.name
    item.deleted_at = datetime.utcnow()
    db.session.commit()

    flash(f"Menu item '{item_name}' deleted successfully.", "success")
    return redirect(url_for('hms.restaurant_menu'))


@hms_bp.route('/restaurant/pos')
@login_required
def restaurant_pos():
    """POS interface with room service integration"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))
    
    tables = RestaurantTable.query.filter_by(hotel_id=hotel_id).order_by(RestaurantTable.table_number).all()
    menu_items = MenuItem.query.filter_by(hotel_id=hotel_id, deleted_at=None, is_available=True).all()
    
    # Get active room service orders
    room_service_orders = RoomServiceOrder.query.filter_by(
        hotel_id=hotel_id
    ).filter(
        RoomServiceOrder.status.in_(['pending', 'accepted', 'preparing', 'ready'])
    ).order_by(RoomServiceOrder.created_at.desc()).limit(10).all()
    
    return render_template("hms/restaurant/pos.html", 
                         tables=tables, 
                         menu_items=menu_items,
                         room_service_orders=room_service_orders)


@hms_bp.route('/restaurant/pos/order/create', methods=['POST'])
@login_required
def pos_order_create():
    """Create new order from POS (supports dine-in and room service)"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        return jsonify({'success': False, 'error': 'No hotel selected. Please contact management.', 'message': 'No hotel selected'}), 400

    table_id = request.form.get('table_id', type=int)
    room_service_order_id = request.form.get('room_service_order_id', type=int)
    order_type = request.form.get('order_type', 'dine_in')

    # Validate table
    if table_id:
        table = RestaurantTable.query.get(table_id)
        if not table:
            return jsonify({'success': False, 'error': 'Invalid table selected', 'message': 'Please select a valid table'}), 400

    # Get payment info (Week 1 Critical)
    payment_method = request.form.get('payment_method', None)
    try:
        paid_amount = float(request.form.get('paid_amount', 0) or 0)
    except (ValueError, TypeError):
        paid_amount = 0
    try:
        discount_amount = float(request.form.get('discount_amount', 0) or 0)
    except (ValueError, TypeError):
        discount_amount = 0
    server_id = request.form.get('server_id', type=int) or current_user.id

    # Validate room charge payment (Phase 1.3 Fix)
    booking_id = None
    if payment_method == 'room_charge':
        booking_id = request.form.get('booking_id', type=int)
        if not booking_id:
            return jsonify({
                'success': False,
                'error': 'Booking number required for room charge',
                'message': 'Please enter a valid booking/room number'
            }), 400
        
        # Validate booking exists and is active
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({
                'success': False,
                'error': 'Booking not found',
                'message': f'No booking found with number {booking_id}'
            }), 400
        
        if booking.status not in ['Reserved', 'CheckedIn']:
            return jsonify({
                'success': False,
                'error': 'Guest not checked in',
                'message': f'Guest in booking {booking_id} is not checked in (Status: {booking.status})'
            }), 400
        
        if booking.hotel_id != hotel_id:
            return jsonify({
                'success': False,
                'error': 'Booking not from this hotel',
                'message': 'Cannot charge to booking from a different hotel'
            }), 400

    server_id = request.form.get('server_id', type=int) or current_user.id

    # Validate items
    item_ids = request.form.getlist('item_id[]')
    quantities = request.form.getlist('quantity[]')

    if not item_ids:
        return jsonify({'success': False, 'error': 'No items in order', 'message': 'Please add at least one item to the order'}), 400

    # Validate quantities
    for i, qty in enumerate(quantities):
        try:
            qty_int = int(qty)
            if qty_int <= 0:
                return jsonify({'success': False, 'error': f'Invalid quantity for item {i+1}', 'message': 'Quantities must be greater than 0'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': f'Invalid quantity format for item {i+1}', 'message': 'Please enter valid quantities'}), 400

    # Create restaurant order
    order = RestaurantOrder(
        hotel_id=hotel_id,
        table_id=table_id,
        order_type=order_type,
        status='pending',
        server_id=server_id,
        payment_status='unpaid',
        payment_method=payment_method,
        discount_amount=Decimal(str(discount_amount))
    )

    # If linked to room service or room charge
    if room_service_order_id:
        order.booking_id = room_service_order_id
        order.guest_name = f"Room Service #{room_service_order_id}"
    elif booking_id:  # Phase 1.3 Fix: Link booking for room charge
        order.booking_id = booking_id
        booking = Booking.query.get(booking_id)
        order.guest_name = f"Room Charge - {booking.guest_name}"

    db.session.add(order)
    db.session.flush()

    # Add order items
    item_ids = request.form.getlist('item_id[]')
    quantities = request.form.getlist('quantity[]')
    notes_list = request.form.getlist('notes[]')
    if not notes_list:
        notes_list = [''] * len(item_ids)

    total = Decimal('0')
    for item_id, quantity, notes in zip(item_ids, quantities, notes_list):
        if item_id and quantity:
            try:
                menu_item = MenuItem.query.get(int(item_id))
                if menu_item:
                    qty = int(quantity)
                    if qty <= 0:
                        continue
                    order_item = RestaurantOrderItem(
                        order_id=order.id,
                        menu_item_id=menu_item.id,
                        quantity=qty,
                        unit_price=menu_item.price,
                        notes=notes if notes else None
                    )
                    db.session.add(order_item)
                    total += Decimal(str(menu_item.price)) * qty
            except (ValueError, TypeError):
                continue

    # Calculate totals with tax (using config value)
    tax_rate = Decimal(str(current_app.config.get('DEFAULT_TAX_RATE', 18))) / 100
    order.subtotal = total
    order.tax = total * tax_rate
    order.total = order.subtotal + order.tax
    
    # Process payment if provided (Week 1 Critical)
    if paid_amount > 0:
        order.paid_amount = Decimal(str(paid_amount))
        balance = RestaurantPaymentService.calculate_balance(order)
        order.balance_due = balance
        
        if balance <= 0:
            order.payment_status = 'paid'
        else:
            order.payment_status = 'partial'
    
    # Update table status if dine-in
    if table_id:
        table = RestaurantTable.query.get(table_id)
        if table:
            table.status = 'occupied'

    db.session.flush()
    
    # Create accounting entry for the order (Week 1 Critical)
    RestaurantAccountingService.create_order_entry(order)

    db.session.commit()

    # Generate user-friendly message
    payment_status_msg = 'Order created successfully'
    if paid_amount > 0:
        if order.payment_status == 'paid':
            payment_status_msg = 'Order created and paid in full'
        elif order.payment_status == 'partial':
            payment_status_msg = f'Order created with partial payment (${order.balance_due} remaining)'

    return jsonify({
        'success': True, 
        'order_id': order.id, 
        'total': float(order.total), 
        'balance_due': float(order.balance_due),
        'message': payment_status_msg
    })


@hms_bp.route('/restaurant/pos/order/<int:order_id>/status', methods=['POST'])
@login_required
def pos_order_status(order_id):
    """Update order status with payment and inventory integration"""
    order = RestaurantOrder.query.get_or_404(order_id)
    if not require_hotel_access(order.hotel_id):
        return jsonify({'success': False, 'error': 'Access denied', 'message': 'You do not have permission to modify this order'}), 403

    data = request.get_json(force=True, silent=True) or request.form
    status = data.get('status')

    # Validate status
    if not status:
        return jsonify({'success': False, 'error': 'Status required', 'message': 'Please provide an order status'}), 400

    # Handle payment if provided (Week 1 Critical)
    try:
        payment_amount = float(data.get('payment_amount', 0) or 0)
    except (ValueError, TypeError):
        payment_amount = 0
    payment_method = data.get('payment_method', None)

    if status not in ORDER_STATUSES:
        return jsonify({'success': False, 'error': f'Invalid status. Must be one of: {", ".join(ORDER_STATUSES)}', 'message': 'Invalid order status selected'}), 400

    old_status = order.status
    order.status = status

    # When order is completed, deduct inventory (Week 1 Critical)
    if status == 'completed' and old_status != 'completed':
        success, message = RestaurantInventoryService.deduct_inventory_for_order(order)
        if not success:
            # Log warning but don't fail the order completion
            current_app.logger.warning(f"Inventory deduction failed for order {order.id}: {message}")
        order.completed_at = datetime.utcnow()

        # Release table
        if order.table_id:
            table = RestaurantTable.query.get(order.table_id)
            if table:
                table.status = 'available'

    # When order is cancelled, restore inventory
    elif status == 'cancelled' and old_status != 'cancelled':
        RestaurantInventoryService.restore_inventory_for_cancelled_order(order)

        # Release table
        if order.table_id:
            table = RestaurantTable.query.get(order.table_id)
            if table:
                table.status = 'available'

    # Process payment if provided
    if payment_amount > 0 and payment_method:
        success, message = RestaurantPaymentService.process_payment(
            order, Decimal(str(payment_amount)), payment_method, current_user.id
        )

    db.session.commit()
    
    # Generate user-friendly message based on status
    status_messages = {
        'pending': 'Order is pending',
        'preparing': 'Order is being prepared',
        'ready': 'Order is ready for serving',
        'completed': 'Order completed successfully',
        'cancelled': 'Order has been cancelled'
    }
    message = status_messages.get(status, f'Order status updated to {status}')

    return jsonify({
        'success': True,
        'status': order.status,
        'balance_due': float(order.balance_due) if order.balance_due else 0,
        'message': message
    })


@hms_bp.route('/restaurant/pos/orders/active', methods=['GET'])
@login_required
def get_active_orders():
    """Get all active orders for real-time polling"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        return jsonify({'success': False, 'error': 'No hotel selected'}), 400

    # Get all active orders (not completed or cancelled)
    active_orders = RestaurantOrder.query.filter(
        RestaurantOrder.hotel_id == hotel_id,
        RestaurantOrder.status.in_(['pending', 'preparing', 'ready'])
    ).order_by(RestaurantOrder.created_at.desc()).all()

    orders_data = []
    for order in active_orders:
        table_info = None
        if order.table_id:
            table = RestaurantTable.query.get(order.table_id)
            if table:
                table_info = {'id': table.id, 'number': table.table_number}

        orders_data.append({
            'id': order.id,
            'table': table_info,
            'status': order.status,
            'total': float(order.total),
            'balance_due': float(order.balance_due) if order.balance_due else 0,
            'payment_status': order.payment_status,
            'created_at': order.created_at.isoformat(),
            'items_count': order.items.count()
        })

    return jsonify({'success': True, 'orders': orders_data})


@hms_bp.route('/restaurant/pos/order/<int:order_id>/split', methods=['POST'])
@login_required
def split_order(order_id):
    """Split an order into multiple child orders (Phase 1.4 Fix)"""
    order = RestaurantOrder.query.get_or_404(order_id)
    if not require_hotel_access(order.hotel_id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json(force=True, silent=True) or request.form
    split_ways = int(data.get('split_ways', 2))
    split_type = data.get('split_type', 'equal')  # 'equal' or 'custom'

    if split_ways < 2:
        return jsonify({'success': False, 'error': 'Split ways must be >= 2'}), 400

    # Get order items for splitting
    order_items = list(order.items.all())
    if not order_items:
        return jsonify({'success': False, 'error': 'No items in order to split'}), 400

    # Calculate per-person amounts
    per_person_amount = float(order.total) / split_ways
    
    # Phase 1.4 Fix: Actually create split child orders
    try:
        from datetime import datetime
        split_orders = []
        
        # Distribute items across split orders
        items_per_split = len(order_items) // split_ways
        remaining_items = len(order_items) % split_ways
        
        item_index = 0
        for i in range(split_ways):
            # Calculate items for this split
            num_items = items_per_split + (1 if i < remaining_items else 0)
            split_items = order_items[item_index:item_index + num_items]
            item_index += num_items
            
            # Calculate total for this split
            split_total = sum(item.unit_price * item.quantity for item in split_items)
            split_tax = split_total * (float(order.tax) / float(order.subtotal)) if order.subtotal > 0 else 0
            
            # Create child order
            child_order = RestaurantOrder(
                hotel_id=order.hotel_id,
                table_id=order.table_id,
                booking_id=order.booking_id,
                guest_name=f"{order.guest_name} (Split {i+1}/{split_ways})",
                order_type=order.order_type,
                status='pending',
                server_id=order.server_id,
                payment_status='unpaid',
                payment_method=order.payment_method,
                discount_amount=order.discount_amount / split_ways if order.discount_amount else 0,
                special_instructions=f"Split from order #{order.id}",
                parent_order_id=order.id  # Link to parent order
            )
            
            db.session.add(child_order)
            db.session.flush()
            
            # Copy items to child order
            for item in split_items:
                child_item = RestaurantOrderItem(
                    order_id=child_order.id,
                    menu_item_id=item.menu_item_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    notes=item.notes
                )
                db.session.add(child_item)
            
            # Calculate final totals
            child_order.subtotal = split_total
            child_order.tax = Decimal(str(split_tax))
            child_order.total = split_total + split_tax
            
            split_orders.append(child_order)
        
        # Mark parent order as split/cancelled
        order.status = 'split'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Bill split into {split_ways} orders',
            'per_person': round(per_person_amount, 2),
            'total': float(order.total),
            'split_order_ids': [o.id for o in split_orders],
            'split_orders': [{
                'id': o.id,
                'guest_name': o.guest_name,
                'total': float(o.total)
            } for o in split_orders]
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to split order: {str(e)}'
        }), 500


@hms_bp.route('/restaurant/kitchen')
@login_required
def restaurant_kitchen():
    """Kitchen display"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    pending = RestaurantOrder.query.filter_by(hotel_id=hotel_id, status='pending').order_by(RestaurantOrder.created_at).all()
    preparing = RestaurantOrder.query.filter_by(hotel_id=hotel_id, status='preparing').order_by(RestaurantOrder.created_at).all()
    ready = RestaurantOrder.query.filter_by(hotel_id=hotel_id, status='ready').order_by(RestaurantOrder.completed_at).all()

    from datetime import datetime
    now = datetime.utcnow()

    return render_template("hms/restaurant/kitchen.html", 
                         pending=pending, 
                         preparing=preparing, 
                         ready=ready,
                         now=now)


@hms_bp.route('/restaurant/kitchen/orders', methods=['GET'])
@login_required
def kitchen_get_orders():
    """API endpoint: Get all kitchen orders for real-time updates"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        return jsonify({'success': False, 'error': 'No hotel selected'}), 400

    from datetime import datetime
    now = datetime.utcnow()
    
    # Get all active orders (pending, preparing, ready)
    orders = RestaurantOrder.query.filter_by(
        hotel_id=hotel_id
    ).filter(
        RestaurantOrder.status.in_(['pending', 'preparing', 'ready'])
    ).order_by(RestaurantOrder.created_at).all()
    
    result = []
    for order in orders:
        minutes_since_order = int((now - order.created_at).total_seconds() / 60) if order.created_at else 0
        
        order_data = {
            'id': order.id,
            'status': order.status,
            'order_type': order.order_type,
            'minutes_since_order': minutes_since_order,
            'special_instructions': order.special_instructions or '',
            'table': order.table_id is not None,
            'table_number': order.table.table_number if order.table else None,
            'items': []
        }
        
        for item in order.items:
            order_data['items'].append({
                'quantity': item.quantity,
                'name': item.menu_item.name if item.menu_item else 'Unknown',
                'notes': item.notes or ''
            })
        
        result.append(order_data)
    
    return jsonify({
        'success': True,
        'orders': result
    })


@hms_bp.route('/restaurant/kitchen/order/<int:order_id>/status', methods=['POST'])
@login_required
def kitchen_order_status(order_id):
    """Update order status from kitchen"""
    order = RestaurantOrder.query.get_or_404(order_id)
    if not require_hotel_access(order.hotel_id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    data = request.get_json(force=True, silent=True) or request.form
    status = data.get('status')
    if status not in ('pending', 'preparing', 'ready', 'served', 'completed'):
        return jsonify({'success': False, 'error': 'Invalid status'}), 400
    
    order.status = status
    db.session.commit()
    
    return jsonify({'success': True, 'status': order.status})


@hms_bp.route('/pos/order/<int:order_id>/add-item', methods=['POST'])
@login_required
def pos_order_add_item(order_id):
    """Add item to order"""
    from app.hms_restaurant_service import RestaurantInventoryService
    
    order = RestaurantOrder.query.get_or_404(order_id)
    if not require_hotel_access(order.hotel_id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    data = request.get_json(force=True, silent=True) or request.form
    menu_item_id = data.get('menu_item_id') or data.get('data-item-id') or data.get('item_id')
    quantity = int(data.get('quantity', 1))
    
    if not menu_item_id:
        return jsonify({'success': False, 'error': 'menu_item_id required'}), 400
    
    item = MenuItem.query.get(int(menu_item_id))
    if not item or item.hotel_id != order.hotel_id:
        return jsonify({'success': False, 'error': 'Invalid item'}), 400
    
    # Add item to order using service
    try:
        result = RestaurantInventoryService.add_item_to_order(
            hotel_id=order.hotel_id,
            order_id=order.id,
            menu_item_id=menu_item_id,
            quantity=quantity,
            user_id=current_user.id
        )
        
        if result['success']:
            # Create order item record
            order_item = RestaurantOrderItem(
                order_id=order.id,
                menu_item_id=menu_item_id,
                quantity=quantity,
                unit_price=item.price
            )
            db.session.add(order_item)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Item {item.name} added to order #{order.id}',
                'order_item_id': order_item.id
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to add item'),
                'message': result.get('message', 'Failed to add item to order')
            }), 500
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding item to order: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while adding item',
            'message': 'Failed to add item to order'
        }), 500


@hms_bp.route('/restaurant/category/add', methods=['GET', 'POST'])
@login_required
def category_create():
    """Create new category"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        display_order = request.form.get('display_order', 0, type=int)

        if not name:
            flash("Category name is required.", "danger")
            return redirect(url_for('hms.category_create'))

        category = MenuCategory(
            hotel_id=hotel_id,
            name=name,
            description=description,
            display_order=display_order
        )
        db.session.add(category)
        db.session.commit()

        flash(f"Category '{name}' created successfully.", "success")
        return redirect(url_for('hms.restaurant_menu'))

    return render_template("hms/restaurant/category_form.html", category=None)


@hms_bp.route('/restaurant/category/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def category_edit(category_id):
    """Edit category"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    category = MenuCategory.query.get_or_404(category_id)
    if category.hotel_id != hotel_id:
        flash("Access denied.", "danger")
        return redirect(url_for('hms.restaurant_menu'))

    if request.method == 'POST':
        category.name = request.form.get('name', '').strip()
        category.description = request.form.get('description', '').strip()
        category.display_order = request.form.get('display_order', 0, type=int)

        if not category.name:
            flash("Category name is required.", "danger")
            return redirect(url_for('hms.category_edit', category_id=category_id))

        db.session.commit()
        flash(f"Category '{category.name}' updated successfully.", "success")
        return redirect(url_for('hms.restaurant_menu'))

    return render_template("hms/restaurant/category_form.html", category=category)


@hms_bp.route('/restaurant/category/<int:category_id>/delete', methods=['POST'])
@login_required
def category_delete(category_id):
    """Delete category (soft delete - Phase 1.6 Fix)"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    category = MenuCategory.query.get_or_404(category_id)
    if category.hotel_id != hotel_id:
        flash("Access denied.", "danger")
        return redirect(url_for('hms.restaurant_menu'))

    category_name = category.name
    
    # Phase 1.6 Fix: Soft delete instead of hard delete
    from datetime import datetime
    category.deleted_at = datetime.utcnow()
    db.session.commit()

    flash(f"Category '{category_name}' deleted successfully.", "success")
    return redirect(url_for('hms.restaurant_menu'))


@hms_bp.route('/restaurant/tables')
@login_required
def restaurant_tables():
    """Table management"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    tables = RestaurantTable.query.filter_by(hotel_id=hotel_id).order_by(RestaurantTable.table_number).all()
    return render_template("hms/restaurant/tables.html", tables=tables)


@hms_bp.route('/restaurant/tables/map')
@login_required
def restaurant_table_map():
    """Table map view - drag and drop layout editor (Phase 1.7)"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    tables = RestaurantTable.query.filter_by(hotel_id=hotel_id).order_by(RestaurantTable.table_number).all()
    return render_template("hms/restaurant/table_map.html", tables=tables)


@hms_bp.route('/restaurant/tables/layout', methods=['POST'])
@login_required
def save_table_layout():
    """Save table positions from drag-drop (Phase 1.7)"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        return jsonify({'success': False, 'error': 'No hotel selected'}), 400

    data = request.get_json(force=True, silent=True) or request.form
    positions = data.get('positions', [])
    
    try:
        # Update table positions
        for pos in positions:
            table_id = pos.get('id')
            x = pos.get('x', 0)
            y = pos.get('y', 0)
            
            if table_id:
                table = RestaurantTable.query.get(table_id)
                if table and table.hotel_id == hotel_id:
                    table.position_x = x
                    table.position_y = y
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Table layout saved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to save layout: {str(e)}'
        }), 500


@hms_bp.route('/restaurant/table/add', methods=['POST'])
@login_required
def table_add():
    """Add new table"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.restaurant_tables"))
    
    table_number = request.form.get('table_number', '').strip()
    capacity = request.form.get('capacity', 2, type=int)
    section = request.form.get('section', 'Main').strip()
    
    if not table_number:
        flash("Table number is required.", "danger")
        return redirect(url_for('hms.restaurant_tables'))
    
    table = RestaurantTable(
        hotel_id=hotel_id,
        table_number=table_number,
        capacity=capacity,
        section=section
    )
    db.session.add(table)
    db.session.commit()
    
    flash(f"Table {table_number} added successfully.", "success")
    return redirect(url_for('hms.restaurant_tables'))


# =============================================================================
# ROOM SERVICE
# =============================================================================

@hms_bp.route('/room-service')
@login_required
def room_service():
    """Room service dashboard"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))
    
    # Get active orders
    active_orders = RoomServiceOrder.query.filter_by(
        hotel_id=hotel_id
    ).filter(
        RoomServiceOrder.status.in_(['pending', 'accepted', 'preparing', 'ready', 'out_for_delivery'])
    ).order_by(RoomServiceOrder.created_at.desc()).limit(20).all()
    
    return render_template("hms/room_service/index.html",
                         active_orders=active_orders)


@hms_bp.route('/room-service/orders')
@login_required
def room_service_orders():
    """Room service orders list"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    status = request.args.get('status', '')
    query = RoomServiceOrder.query.filter_by(hotel_id=hotel_id)

    if status:
        query = query.filter_by(status=status)

    orders = query.order_by(RoomServiceOrder.created_at.desc()).limit(50).all()

    return render_template("hms/room_service/orders.html",
                         orders=orders,
                         current_status=status)


@hms_bp.route('/room-service/order/create', methods=['GET', 'POST'])
@login_required
def room_service_order_create():
    """Create new room service order"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    if request.method == 'POST':
        room_id = request.form.get('room_id', type=int)
        booking_id = request.form.get('booking_id', type=int)
        guest_name = request.form.get('guest_name', '').strip()
        delivery_time_str = request.form.get('delivery_time', '')
        special_instructions = request.form.get('special_instructions', '').strip()
        charge_to_room = request.form.get('charge_to_room') == 'on'

        # Validate items
        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')

        if not item_ids:
            flash("Please add at least one item to the order", "danger")
            return redirect(url_for('hms.room_service_order_create'))

        # Create order
        delivery_time = None
        if delivery_time_str:
            try:
                delivery_time = datetime.strptime(delivery_time_str, '%Y-%m-%dT%H:%M')
            except:
                pass

        order = RoomServiceOrder(
            hotel_id=hotel_id,
            room_id=room_id,
            booking_id=booking_id,
            guest_name=guest_name,
            status='pending',
            delivery_time=delivery_time,
            special_instructions=special_instructions,
            charge_to_room=charge_to_room
        )
        db.session.add(order)
        db.session.flush()

        # Add items
        total = Decimal('0')
        for item_id, quantity in zip(item_ids, quantities):
            if item_id and quantity:
                menu_item = MenuItem.query.get(int(item_id))
                if menu_item:
                    qty = int(quantity)
                    order_item = RoomServiceOrderItem(
                        order_id=order.id,
                        menu_item_id=menu_item.id,
                        quantity=qty,
                        unit_price=menu_item.price
                    )
                    db.session.add(order_item)
                    total += Decimal(str(menu_item.price)) * qty

        # Calculate totals
        tax_rate = Decimal(str(current_app.config.get('DEFAULT_TAX_RATE', 18))) / 100
        order.subtotal = total
        order.tax = total * tax_rate
        order.total = order.subtotal + order.tax

        db.session.commit()

        flash(f"Room service order #{order.id} created successfully!", "success")
        return redirect(url_for('hms.room_service_orders'))

    # GET: Show form
    rooms = Room.query.filter_by(hotel_id=hotel_id, is_active=True).all()
    bookings = Booking.query.filter_by(hotel_id=hotel_id).filter(
        Booking.status.in_(['CheckedIn', 'Reserved'])
    ).all()
    menu_items = MenuItem.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None,
        is_available=True
    ).all()

    return render_template("hms/room_service/order_form.html",
                         rooms=rooms,
                         bookings=bookings,
                         menu_items=menu_items)


@hms_bp.route('/room-service/order/<int:order_id>/detail')
@login_required
def room_service_order_detail(order_id):
    """View order details"""
    order = RoomServiceOrder.query.get_or_404(order_id)
    if not require_hotel_access(order.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for('hms.room_service_orders'))

    return render_template("hms/room_service/order_detail.html", order=order)


@hms_bp.route('/room-service/order/<int:order_id>/status', methods=['POST'])
@login_required
def room_service_order_status(order_id):
    """Update order status"""
    order = RoomServiceOrder.query.get_or_404(order_id)
    if not require_hotel_access(order.hotel_id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json(force=True, silent=True) or request.form
    status = data.get('status')

    valid_statuses = ['pending', 'accepted', 'preparing', 'ready', 'out_for_delivery', 'delivered', 'cancelled']
    if status not in valid_statuses:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    old_status = order.status
    order.status = status

    # Mark as delivered
    if status == 'delivered':
        order.delivered_at = datetime.utcnow()
        order.delivered_by = current_user.id

    db.session.commit()

    status_messages = {
        'accepted': 'Order accepted',
        'preparing': 'Order is being prepared',
        'ready': 'Order is ready for delivery',
        'out_for_delivery': 'Order is out for delivery',
        'delivered': 'Order delivered successfully',
        'cancelled': 'Order cancelled'
    }
    message = status_messages.get(status, f'Order status updated to {status}')

    return jsonify({
        'success': True,
        'status': order.status,
        'message': message
    })


@hms_bp.route('/room-service/kitchen')
@login_required
def room_service_kitchen():
    """Kitchen display for room service"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    pending = RoomServiceOrder.query.filter_by(
        hotel_id=hotel_id, status='pending'
    ).order_by(RoomServiceOrder.created_at).all()

    preparing = RoomServiceOrder.query.filter_by(
        hotel_id=hotel_id, status='preparing'
    ).order_by(RoomServiceOrder.created_at).all()

    ready = RoomServiceOrder.query.filter_by(
        hotel_id=hotel_id, status='ready'
    ).order_by(RoomServiceOrder.created_at).all()

    return render_template("hms/room_service/kitchen.html",
                         pending=pending,
                         preparing=preparing,
                         ready=ready)


@hms_bp.route('/room-service/delivery')
@login_required
def room_service_delivery():
    """Delivery management dashboard"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    # Get orders ready for delivery
    ready_orders = RoomServiceOrder.query.filter_by(
        hotel_id=hotel_id, status='ready'
    ).order_by(RoomServiceOrder.created_at).all()

    # Get out for delivery
    delivery_orders = RoomServiceOrder.query.filter_by(
        hotel_id=hotel_id, status='out_for_delivery'
    ).order_by(RoomServiceOrder.created_at).all()

    return render_template("hms/room_service/delivery.html",
                         ready_orders=ready_orders,
                         delivery_orders=delivery_orders)


# =============================================================================
# NIGHT AUDIT
# =============================================================================

def check_business_date_lock(transaction_date=None):
    """
    Check if business date is locked for transactions.
    Returns (is_locked, message) tuple.
    
    Usage:
        is_locked, msg = check_business_date_lock(date.today())
        if is_locked:
            flash(msg, "error")
            return redirect(...)
    """
    from datetime import date
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        return False, None
    
    if transaction_date is None:
        transaction_date = date.today()
    
    biz_date = BusinessDate.query.filter_by(hotel_id=hotel_id).first()
    if not biz_date:
        return False, None  # No business date configured, allow transactions
    
    # Check if transaction date matches locked business date
    if biz_date.is_closed and biz_date.current_business_date == transaction_date:
        return True, f"Cannot process transaction - business day {transaction_date.strftime('%B %d, %Y')} is locked"
    
    return False, None


@hms_bp.route('/night-audit')
@login_required
def night_audit():
    """Night audit dashboard with comprehensive reports"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    # Get business date
    biz_date = BusinessDate.query.filter_by(hotel_id=hotel_id).first()
    today = date.today()
    
    # Get recent audit logs
    audit_logs = NightAuditLog.query.filter_by(
        hotel_id=hotel_id
    ).order_by(NightAuditLog.audit_date.desc()).limit(10).all()
    
    # Phase 2: Generate comprehensive reports
    # Today's statistics
    from decimal import Decimal
    
    # Revenue today
    room_revenue_account = ChartOfAccount.query.filter_by(
        hotel_id=hotel_id,
        name='Room Revenue'
    ).first()
    
    today_revenue = Decimal('0')
    if room_revenue_account:
        revenue_lines = db.session.query(JournalLine).join(JournalEntry).filter(
            JournalEntry.hotel_id == hotel_id,
            JournalEntry.date == today,
            JournalLine.account_id == room_revenue_account.id
        ).all()
        today_revenue = sum(line.credit for line in revenue_lines) if revenue_lines else Decimal('0')
    
    # Occupancy stats
    total_rooms = Room.query.filter_by(hotel_id=hotel_id, is_active=True).count()
    occupied_rooms = Booking.query.filter(
        Booking.hotel_id == hotel_id,
        Booking.check_in_date <= today,
        Booking.check_out_date > today,
        Booking.status.in_(['CheckedIn', 'Reserved'])
    ).count()
    occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
    
    # Payments today
    payments_today = Payment.query.filter_by(
        hotel_id=hotel_id
    ).filter(
        db.func.date(Payment.created_at) == today
    ).count()
    
    total_payments_amount = db.session.query(db.func.sum(Payment.amount)).filter_by(
        hotel_id=hotel_id
    ).filter(
        db.func.date(Payment.created_at) == today
    ).scalar() or Decimal('0')
    
    # Bookings today
    arrivals_today = Booking.query.filter_by(
        hotel_id=hotel_id,
        check_in_date=today
    ).count()
    
    departures_today = Booking.query.filter_by(
        hotel_id=hotel_id,
        check_out_date=today
    ).count()

    return render_template("hms/night_audit/index.html",
                         biz_date=biz_date,
                         today=today,
                         audit_logs=audit_logs,
                         # Report data
                         today_revenue=today_revenue,
                         total_rooms=total_rooms,
                         occupied_rooms=occupied_rooms,
                         occupancy_rate=round(occupancy_rate, 1),
                         payments_today=payments_today,
                         total_payments_amount=total_payments_amount,
                         arrivals_today=arrivals_today,
                         departures_today=departures_today)


@hms_bp.route('/night-audit/run', methods=['POST'])
@login_required
def run_night_audit():
    """Run night audit process with revenue posting (Phase 2 Complete)"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    from datetime import datetime, timedelta
    from decimal import Decimal
    
    try:
        today = date.today()
        errors = []
        warnings = []
        revenue_posted = Decimal('0')
        rooms_charged = 0
        
        # Start audit log
        audit_log = NightAuditLog(
            hotel_id=hotel_id,
            audit_date=today,
            run_by=current_user.id,
            started_at=datetime.now(),
            status='running'
        )
        db.session.add(audit_log)
        db.session.flush()
        
        current_app.logger.info(f"Starting night audit for hotel {hotel_id}")
        
        # Get or create business date
        
        # Get or create business date
        biz_date = BusinessDate.query.filter_by(hotel_id=hotel_id).first()
        if not biz_date:
            biz_date = BusinessDate(
                hotel_id=hotel_id,
                current_business_date=today,
                is_closed=False
            )
            db.session.add(biz_date)
            db.session.flush()
        
        # Phase 2 Fix: Pre-close validation checklist
        unpaid_bookings = Booking.query.filter_by(
            hotel_id=hotel_id,
            check_in_date=today
        ).filter(
            Booking.balance > 0
        ).count()
        
        if unpaid_bookings > 0:
            warnings.append(f"{unpaid_bookings} bookings have outstanding balance")
        
        pending_orders = RestaurantOrder.query.filter_by(
            hotel_id=hotel_id,
            status='pending'
        ).count()
        
        if pending_orders > 0:
            warnings.append(f"{pending_orders} restaurant orders still pending")
        
        checked_in = Booking.query.filter_by(
            hotel_id=hotel_id,
            status='CheckedIn'
        ).count()
        
        if checked_in > 0:
            warnings.append(f"{checked_in} guests still checked in")
        
        # If day is already closed, show error
        if biz_date.is_closed:
            audit_log.status = 'failed'
            audit_log.errors = "Day already closed"
            audit_log.completed_at = datetime.now()
            db.session.commit()
            
            flash("Business day is already closed and locked.", "warning")
            return redirect(url_for("hms.night_audit"))
        
        # Phase 2 Fix: POST ROOM REVENUE before closing
        # Find all occupied rooms (checked in but not checked out)
        occupied_bookings = Booking.query.filter_by(
            hotel_id=hotel_id,
            status='CheckedIn'
        ).all()
        
        # Get or create Room Revenue account
        room_revenue_account = ChartOfAccount.query.filter_by(
            hotel_id=hotel_id,
            name='Room Revenue'
        ).first()
        if not room_revenue_account:
            room_revenue_account = ChartOfAccount(
                hotel_id=hotel_id,
                name='Room Revenue',
                type='Revenue'
            )
            db.session.add(room_revenue_account)
            db.session.flush()
        
        # Get Cash/AR account
        ar_account = ChartOfAccount.query.filter_by(
            hotel_id=hotel_id,
            name='Accounts Receivable'
        ).first()
        if not ar_account:
            ar_account = ChartOfAccount(
                hotel_id=hotel_id,
                name='Accounts Receivable',
                type='Asset'
            )
            db.session.add(ar_account)
            db.session.flush()
        
        # Charge each occupied room
        for booking in occupied_bookings:
            try:
                if booking.room and booking.room.room_type:
                    room_rate = booking.room.room_type.base_price or Decimal('0')
                    
                    if room_rate > 0:
                        # Add charge to booking invoice
                        if booking.invoice:
                            booking.invoice.total += room_rate
                            booking.invoice.status = 'Unpaid'
                            booking.balance += room_rate
                            
                            # Create journal entry
                            journal = JournalEntry(
                                hotel_id=hotel_id,
                                date=today,
                                description=f"Room charge for {booking.room.room_number} - {booking.booking_reference}"
                            )
                            db.session.add(journal)
                            db.session.flush()
                            
                            # Debit: Accounts Receivable
                            debit_line = JournalLine(
                                journal_entry_id=journal.id,
                                account_id=ar_account.id,
                                debit=room_rate,
                                credit=Decimal('0')
                            )
                            db.session.add(debit_line)
                            
                            # Credit: Room Revenue
                            credit_line = JournalLine(
                                journal_entry_id=journal.id,
                                account_id=room_revenue_account.id,
                                debit=Decimal('0'),
                                credit=room_rate
                            )
                            db.session.add(credit_line)
                            
                            revenue_posted += room_rate
                            rooms_charged += 1
            except Exception as e:
                errors.append(f"Error charging room {booking.room.room_number if booking.room else 'Unknown'}: {str(e)}")
                continue
        
        # Close current day AND advance to next day
        biz_date.is_closed = True
        biz_date.current_business_date = today + timedelta(days=1)
        biz_date.updated_at = datetime.now()
        
        # Complete audit log
        audit_log.status = 'success' if not errors else 'partial'
        audit_log.completed_at = datetime.now()
        audit_log.summary = {
            'unpaid_bookings': unpaid_bookings,
            'pending_orders': pending_orders,
            'checked_in_guests': checked_in,
            'rooms_charged': rooms_charged,
            'revenue_posted': float(revenue_posted),
            'warnings': warnings,
            'errors': errors
        }
        audit_log.notes = f"Day closed. Advanced to {biz_date.current_business_date}. Posted ${revenue_posted} from {rooms_charged} rooms."
        audit_log.errors = '\n'.join(errors) if errors else None
        
        db.session.commit()
        
        # Show results
        flash(f"✅ Night audit completed successfully!", "success")
        flash(f"🔒 Business day CLOSED for {today.strftime('%B %d, %Y')}", "info")
        flash(f"📅 New business date: {biz_date.current_business_date.strftime('%B %d, %Y')}", "info")
        flash(f"💰 Room revenue posted: ${revenue_posted:,.2f} from {rooms_charged} rooms", "success")
        
        if warnings:
            for warning in warnings:
                flash(f"⚠️ {warning}", "warning")
        
        if errors:
            for error in errors:
                flash(f"❌ {error}", "danger")
        
        return jsonify({
            'success': True,
            'message': 'Night audit completed successfully',
            'revenue_posted': float(revenue_posted),
            'rooms_charged': rooms_charged,
            'business_date': biz_date.current_business_date.strftime('%B %d, %Y'),
            'new_business_date': biz_date.current_business_date + timedelta(days=1).strftime('%B %d, %Y'),
            'warnings': warnings,
            'errors': errors
        })

    except Exception as e:
        db.session.rollback()
        audit_log.status = 'failed'
        audit_log.errors = str(e)
        audit_log.completed_at = datetime.now()
        db.session.commit()
        
        current_app.logger.error(f"Night audit error: {str(e)}")
        flash("❌ Error running night audit. Please check logs.", "danger")

    return redirect(url_for("hms.night_audit"))


def generate_night_audit_summary(hotel_id, audit_date):
    """Generate comprehensive night audit summary"""
    
    # Get room revenue
    room_revenue_account = ChartOfAccount.query.filter_by(
        hotel_id=hotel_id, 
        name='Room Revenue'
    ).first()
    
    total_revenue = 0
    if room_revenue_account:
        revenue_lines = db.session.query(JournalLine).join(JournalEntry).filter(
            JournalEntry.hotel_id == hotel_id,
            JournalEntry.date == audit_date,
            JournalLine.account_id == room_revenue_account.id
        ).all()
        
        total_revenue = sum(line.credit for line in revenue_lines)
    
    # Get payments
    payments = Payment.query.filter_by(
        hotel_id=hotel_id,
        created_at=audit_date
    ).with_entities(Payment.amount).all()
    
    total_payments = sum(payment[0] for payment in payments) if payments else 0
    
    # Get occupancy
    total_rooms = Room.query.filter_by(hotel_id=hotel_id, is_active=True).count()
    occupied_rooms = Booking.query.filter(
        Booking.hotel_id == hotel_id,
        Booking.check_in_date <= audit_date,
        Booking.check_out_date > audit_date,
        Booking.status.in_(['Reserved', 'CheckedIn'])
    ).count()
    
    occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
    
    # Get transaction counts
    total_bookings = Booking.query.filter_by(hotel_id=hotel_id, check_in_date=audit_date).count()
    total_payments_count = Payment.query.filter_by(hotel_id=hotel_id, created_at=audit_date).count()
    
    return {
        'total_revenue': total_revenue,
        'total_payments': total_payments,
        'occupancy_rate': occupancy_rate,
        'total_bookings': total_bookings,
        'total_payments_count': total_payments_count,
        'occupied_rooms': occupied_rooms,
        'total_rooms': total_rooms
    }


# =============================================================================
# SETTINGS
# =============================================================================

@hms_bp.route('/settings')
@login_required
def settings():
    """Settings dashboard"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))
    
    hotel = Hotel.query.get(hotel_id)
    users = User.query.filter_by(hotel_id=hotel_id).all()
    
    return render_template("hms/settings/index.html", hotel=hotel, users=users)


@hms_bp.route('/settings/users', methods=['GET', 'POST'])
@login_required
def settings_users():
    """User management"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.settings"))

    # Role hierarchy for permission checks
    ROLE_HIERARCHY = {
        'superadmin': 100,
        'owner': 90,
        'manager': 80,
        'restaurant_manager': 70,
        'housekeeping_manager': 70,
        'receptionist': 60,
        'housekeeping': 50,
        'kitchen': 50,
        'staff': 40
    }

    current_role = current_user.role.lower() if current_user.role else 'staff'
    if current_user.is_superadmin:
        current_role = 'superadmin'
    
    current_level = ROLE_HIERARCHY.get(current_role, 0)

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role_id = request.form.get('role_id', type=int)
        active = request.form.get('active') == '1'

        if not name or not email:
            flash("Name and email are required.", "danger")
            return redirect(url_for('hms.settings_users'))

        if not role_id:
            flash("Role is required.", "danger")
            return redirect(url_for('hms.settings_users'))

        # Get role name from role_id
        role = Role.query.get(role_id)
        if not role:
            flash("Invalid role selected.", "danger")
            return redirect(url_for('hms.settings_users'))

        # Role hierarchy check - can't create/update roles >= own role
        target_role = role.name.lower()
        target_level = ROLE_HIERARCHY.get(target_role, 0)
        
        if not current_user.is_superadmin and target_level >= current_level:
            flash(f"You cannot create or update users with '{role.name}' role or higher.", "danger")
            return redirect(url_for('hms.settings_users'))

        if user_id:
            # Update existing user
            user = User.query.get_or_404(user_id)
            if user.hotel_id != hotel_id and not current_user.is_superadmin:
                flash("Access denied.", "danger")
                return redirect(url_for('hms.settings_users'))

            user.name = name
            user.email = email
            user.role_id = role_id
            user.role = role.name  # Set the role string
            user.active = active

            if password:
                from werkzeug.security import generate_password_hash
                user.password_hash = generate_password_hash(password)

            flash(f"User '{user.name}' updated successfully.", "success")
        else:
            # Create new user
            from werkzeug.security import generate_password_hash
            if not password:
                flash("Password is required for new users.", "danger")
                return redirect(url_for('hms.settings_users'))

            user = User(
                hotel_id=hotel_id,
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role_id=role_id,
                role=role.name,  # Set the role string
                active=active
            )
            db.session.add(user)
            flash(f"User '{user.name}' created successfully.", "success")

        db.session.commit()
        return redirect(url_for('hms.settings_users'))

    users = User.query.filter_by(hotel_id=hotel_id).all()
    # Filter roles based on user's hierarchy level
    if current_user.is_superadmin:
        roles = Role.query.all()
    else:
        roles = [r for r in Role.query.all() if ROLE_HIERARCHY.get(r.name.lower(), 0) < current_level]

    return render_template("hms/settings/users.html", users=users, roles=roles)


@hms_bp.route('/settings/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def settings_users_reset_password(user_id):
    """Reset user password"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.settings"))

    user = User.query.get_or_404(user_id)
    if user.hotel_id != hotel_id and not current_user.is_superadmin:
        flash("Access denied.", "danger")
        return redirect(url_for('hms.settings_users'))

    # Generate temporary password
    import secrets
    temp_password = secrets.token_urlsafe(8)

    from werkzeug.security import generate_password_hash
    user.password_hash = generate_password_hash(temp_password)
    db.session.commit()

    flash(f"Password reset for {user.name}. Temporary password: {temp_password}", "warning")
    return redirect(url_for('hms.settings_users'))


@hms_bp.route('/settings/users/set-password', methods=['POST'])
@login_required
def settings_users_set_password():
    """Set password for a user (manager/admin function)"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.settings"))

    user_id = request.form.get('user_id', type=int)
    password = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    if not user_id:
        flash("User ID is required.", "danger")
        return redirect(url_for('hms.settings_users'))

    if not password:
        flash("Password is required.", "danger")
        return redirect(url_for('hms.settings_users'))

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "danger")
        return redirect(url_for('hms.settings_users'))

    if password != confirm_password:
        flash("Passwords do not match.", "danger")
        return redirect(url_for('hms.settings_users'))

    user = User.query.get_or_404(user_id)
    
    # Check permissions
    if user.hotel_id != hotel_id and not current_user.is_superadmin:
        flash("Access denied.", "danger")
        return redirect(url_for('hms.settings_users'))

    # Check role hierarchy
    ROLE_HIERARCHY = {
        'superadmin': 100,
        'owner': 90,
        'manager': 80,
        'restaurant_manager': 70,
        'housekeeping_manager': 70,
        'receptionist': 60,
        'housekeeping': 50,
        'kitchen': 50,
        'staff': 40
    }

    current_role = current_user.role.lower() if current_user.role else 'staff'
    if current_user.is_superadmin:
        current_role = 'superadmin'

    target_role = user.role.lower() if user.role else 'staff'
    current_level = ROLE_HIERARCHY.get(current_role, 0)
    target_level = ROLE_HIERARCHY.get(target_role, 0)

    if not current_user.is_superadmin and target_level >= current_level:
        flash(f"You cannot change password for users with '{user.role}' role or higher.", "danger")
        return redirect(url_for('hms.settings_users'))

    # Set new password
    from werkzeug.security import generate_password_hash
    user.password_hash = generate_password_hash(password)
    db.session.commit()

    flash(f"Password updated for {user.name}.", "success")
    return redirect(url_for('hms.settings_users'))


@hms_bp.route('/settings/users/<int:user_id>/delete', methods=['POST'])
@login_required
def settings_users_delete(user_id):
    """Delete user"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.settings"))

    user = User.query.get_or_404(user_id)
    if user.hotel_id != hotel_id and not current_user.is_superadmin:
        flash("Access denied.", "danger")
        return redirect(url_for('hms.settings_users'))

    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for('hms.settings_users'))

    user_name = user.name
    db.session.delete(user)
    db.session.commit()

    flash(f"User '{user_name}' deleted successfully.", "success")
    return redirect(url_for('hms.settings_users'))


@hms_bp.route('/settings/hotel')
@login_required
def settings_hotel():
    """Hotel settings"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.settings"))
    
    hotel = Hotel.query.get(hotel_id)
    return render_template("hms/settings/hotel.html", hotel=hotel)


@hms_bp.route('/settings/taxes')
@login_required
def settings_taxes():
    """Tax configuration"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.settings"))
    
    taxes = TaxRate.query.filter_by(hotel_id=hotel_id).all()
    return render_template("hms/settings/taxes.html", taxes=taxes)


@hms_bp.route('/settings/roles')
@login_required
def settings_roles():
    """Roles management"""
    roles = Role.query.all()
    return render_template("hms/settings/roles.html", roles=roles)


# =============================================================================
# GALLERY MANAGEMENT (Website Gallery Images)
# =============================================================================

@hms_bp.route('/settings/gallery')
@login_required
def settings_gallery():
    """View all gallery images"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.settings"))
    
    # Get all gallery images for current hotel
    images = GalleryImage.query.filter_by(
        hotel_id=hotel_id
    ).order_by(GalleryImage.sort_order, GalleryImage.created_at.desc()).all()
    
    return render_template("hms/settings/gallery.html", images=images)


@hms_bp.route('/settings/gallery/upload', methods=['GET', 'POST'])
@login_required
@role_required('manager', 'owner', 'superadmin')
def settings_gallery_upload():
    """Upload new gallery image"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.settings"))
    
    if request.method == 'POST':
        # Check if file is present
        if 'image' not in request.files:
            flash("No image file selected.", "danger")
            return redirect(request.url)
        
        file = request.files['image']
        
        if file.filename == '':
            flash("No image file selected.", "danger")
            return redirect(request.url)
        
        # Validate file extension
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
        filename = file.filename.lower()
        ext = filename.rsplit('.', 1)[1] if '.' in filename else ''
        
        if ext not in allowed_extensions:
            flash(f"Invalid file type. Allowed: {', '.join(allowed_extensions)}", "danger")
            return redirect(request.url)
        
        # Validate file size (max 5MB)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            flash("File too large. Maximum size: 5MB", "danger")
            return redirect(request.url)
        
        # Generate unique filename
        import uuid
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        
        # Save file
        upload_folder = os.path.join(current_app.root_path, 'static/uploads/gallery')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'facilities').strip()
        size_type = request.form.get('size_type', 'small').strip()
        sort_order = request.form.get('sort_order', 0, type=int)
        is_active = request.form.get('is_active') == 'on'
        
        # Validate required fields
        if not title:
            flash("Title is required.", "danger")
            os.remove(file_path)
            return redirect(request.url)
        
        if category not in ['rooms', 'facilities', 'dining', 'events']:
            flash("Invalid category.", "danger")
            os.remove(file_path)
            return redirect(request.url)
        
        if size_type not in ['large', 'medium', 'small']:
            flash("Invalid size type.", "danger")
            os.remove(file_path)
            return redirect(request.url)
        
        # Create database record
        try:
            gallery_image = GalleryImage(
                hotel_id=hotel_id,
                image_filename=unique_filename,
                title=title,
                description=description,
                category=category,
                size_type=size_type,
                sort_order=sort_order,
                is_active=is_active,
                uploaded_by=current_user.id
            )
            db.session.add(gallery_image)
            db.session.commit()
            
            flash(f"Image '{title}' uploaded successfully!", "success")
            return redirect(url_for('hms.settings_gallery'))
            
        except Exception as e:
            db.session.rollback()
            # Clean up uploaded file
            if os.path.exists(file_path):
                os.remove(file_path)
            flash(f"Error uploading image: {str(e)}", "danger")
            return redirect(request.url)
    
    # GET request - show upload form
    return render_template("hms/settings/gallery_upload.html")


@hms_bp.route('/settings/gallery/<int:image_id>/toggle', methods=['POST'])
@login_required
@role_required('manager', 'owner', 'superadmin')
def settings_gallery_toggle(image_id):
    """Toggle image visibility (active/inactive)"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        return jsonify({'success': False, 'error': 'No hotel selected'}), 400
    
    image = GalleryImage.query.get(image_id)
    if not image:
        return jsonify({'success': False, 'error': 'Image not found'}), 404
    
    # Check hotel ownership
    if image.hotel_id != hotel_id and not current_user.is_superadmin:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    # Toggle active status
    image.is_active = not image.is_active
    db.session.commit()
    
    return jsonify({
        'success': True,
        'is_active': image.is_active
    })


@hms_bp.route('/settings/gallery/<int:image_id>/delete', methods=['POST'])
@login_required
@role_required('manager', 'owner', 'superadmin')
def settings_gallery_delete(image_id):
    """Delete gallery image"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.settings"))
    
    image = GalleryImage.query.get(image_id)
    if not image:
        flash("Image not found.", "danger")
        return redirect(url_for('hms.settings_gallery'))
    
    # Check hotel ownership
    if image.hotel_id != hotel_id and not current_user.is_superadmin:
        flash("Access denied.", "danger")
        return redirect(url_for('hms.settings_gallery'))
    
    # Delete file from disk
    file_path = os.path.join(current_app.root_path, 'static/uploads/gallery', image.image_filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete database record
    try:
        db.session.delete(image)
        db.session.commit()
        flash("Image deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting image: {str(e)}", "danger")
    
    return redirect(url_for('hms.settings_gallery'))


@hms_bp.route('/settings/gallery/<int:image_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('manager', 'owner', 'superadmin')
def settings_gallery_edit(image_id):
    """Edit gallery image details"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.settings"))
    
    image = GalleryImage.query.get(image_id)
    if not image:
        flash("Image not found.", "danger")
        return redirect(url_for('hms.settings_gallery'))
    
    # Check hotel ownership
    if image.hotel_id != hotel_id and not current_user.is_superadmin:
        flash("Access denied.", "danger")
        return redirect(url_for('hms.settings_gallery'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'facilities').strip()
        size_type = request.form.get('size_type', 'small').strip()
        sort_order = request.form.get('sort_order', 0, type=int)
        is_active = request.form.get('is_active') == 'on'
        
        # Validate required fields
        if not title:
            flash("Title is required.", "danger")
            return redirect(request.url)
        
        if category not in ['rooms', 'facilities', 'dining', 'events']:
            flash("Invalid category.", "danger")
            return redirect(request.url)
        
        if size_type not in ['large', 'medium', 'small']:
            flash("Invalid size type.", "danger")
            return redirect(request.url)
        
        # Update record
        try:
            image.title = title
            image.description = description
            image.category = category
            image.size_type = size_type
            image.sort_order = sort_order
            image.is_active = is_active
            db.session.commit()
            
            flash(f"Image '{title}' updated successfully!", "success")
            return redirect(url_for('hms.settings_gallery'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating image: {str(e)}", "danger")
            return redirect(request.url)
    
    # GET request - show edit form
    return render_template("hms/settings/gallery_edit.html", image=image)


# =============================================================================
# ROLE-SPECIFIC DASHBOARDS
# =============================================================================

@hms_bp.route('/housekeeping/dashboard')
@login_required
@role_required('housekeeping', 'manager', 'owner', 'superadmin')
def housekeeping_dashboard():
    """Housekeeping staff dashboard"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    # Get rooms by status
    vacant_rooms = Room.query.filter_by(hotel_id=hotel_id, status='Vacant').count()
    occupied_rooms = Room.query.filter_by(hotel_id=hotel_id, status='Occupied').count()
    dirty_rooms = Room.query.filter_by(hotel_id=hotel_id, status='Dirty').count()
    maintenance_rooms = Room.query.filter_by(hotel_id=hotel_id, status='Maintenance').count()

    # Get housekeeping tasks
    pending_tasks = HousekeepingTask.query.filter_by(
        hotel_id=hotel_id, status='pending'
    ).count()
    in_progress_tasks = HousekeepingTask.query.filter_by(
        hotel_id=hotel_id, status='in_progress'
    ).count()
    completed_tasks_today = HousekeepingTask.query.filter(
        HousekeepingTask.hotel_id == hotel_id,
        HousekeepingTask.status == 'completed',
        db.func.date(HousekeepingTask.completed_at) == date.today()
    ).count()

    stats = {
        'vacant_rooms': vacant_rooms,
        'occupied_rooms': occupied_rooms,
        'dirty_rooms': dirty_rooms,
        'maintenance_rooms': maintenance_rooms,
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks_today': completed_tasks_today
    }

    return render_template("hms/housekeeping/dashboard.html", stats=stats)


@hms_bp.route('/kitchen/dashboard')
@login_required
@role_required('kitchen', 'manager', 'owner', 'superadmin')
def kitchen_dashboard():
    """Kitchen staff dashboard"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    # Get room service orders by status
    pending_orders = RoomServiceOrder.query.filter_by(
        hotel_id=hotel_id, status='pending'
    ).count()
    preparing_orders = RoomServiceOrder.query.filter_by(
        hotel_id=hotel_id, status='preparing'
    ).count()
    ready_orders = RoomServiceOrder.query.filter_by(
        hotel_id=hotel_id, status='ready'
    ).count()
    delivered_today = RoomServiceOrder.query.filter(
        RoomServiceOrder.hotel_id == hotel_id,
        RoomServiceOrder.status == 'delivered',
        db.func.date(RoomServiceOrder.created_at) == date.today()
    ).count()

    # Get restaurant orders
    restaurant_pending = RestaurantOrder.query.filter_by(
        hotel_id=hotel_id, status='pending'
    ).count()

    stats = {
        'pending_orders': pending_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
        'delivered_today': delivered_today,
        'restaurant_pending': restaurant_pending
    }

    return render_template("hms/restaurant/kitchen_dashboard.html", stats=stats)


@hms_bp.route('/restaurant/dashboard')
@login_required
@role_required('restaurant', 'manager', 'owner', 'superadmin')
def restaurant_dashboard():
    """Restaurant staff dashboard"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("hms.dashboard"))

    # Get today's orders
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    today_orders = RestaurantOrder.query.filter(
        RestaurantOrder.hotel_id == hotel_id,
        RestaurantOrder.created_at >= today_start,
        RestaurantOrder.created_at <= today_end
    ).count()

    # Get tables
    total_tables = RestaurantTable.query.filter_by(hotel_id=hotel_id).count()
    available_tables = RestaurantTable.query.filter_by(
        hotel_id=hotel_id, status='available'
    ).count()
    occupied_tables = total_tables - available_tables

    # Get pending orders
    pending_orders = RestaurantOrder.query.filter_by(
        hotel_id=hotel_id, status='pending'
    ).count()

    stats = {
        'today_orders': today_orders,
        'total_tables': total_tables,
        'available_tables': available_tables,
        'occupied_tables': occupied_tables,
        'pending_orders': pending_orders
    }

    return render_template("hms/restaurant/dashboard.html", stats=stats)


# =============================================================================
# NOTIFICATIONS
# =============================================================================

@hms_bp.route('/notifications')
@login_required
def notifications_index():
    """Notifications index page"""
    # Get all notifications for current user
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).limit(50).all()
    
    return render_template("hms/notifications/index.html", notifications=notifications)


@hms_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def notification_mark_read(notification_id):
    """Mark single notification as read"""
    notification = Notification.query.get_or_404(notification_id)
    
    # Only allow user to mark their own notifications
    if notification.user_id != current_user.id and not current_user.is_superadmin:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})


@hms_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def notifications_mark_all_read():
    """Mark all notifications as read for current user"""
    Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    
    return jsonify({'success': True})


@hms_bp.route('/notifications/unread-count', methods=['GET'])
@login_required
def notifications_unread_count():
    """Get unread notification count"""
    count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    
    return jsonify({'count': count})


@hms_bp.route('/notifications/<int:notification_id>/archive', methods=['POST'])
@login_required
def notification_archive(notification_id):
    """Archive a notification"""
    notification = Notification.query.get_or_404(notification_id)
    
    # Only allow user to archive their own notifications
    if notification.user_id != current_user.id and not current_user.is_superadmin:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    notification.is_archived = True
    db.session.commit()
    
    return jsonify({'success': True})


@hms_bp.route('/notifications/clear-all', methods=['POST'])
@login_required
def notifications_clear_all():
    """Clear all archived notifications"""
    Notification.query.filter_by(
        user_id=current_user.id,
        is_archived=True
    ).delete()
    db.session.commit()
    
    return jsonify({'success': True})


