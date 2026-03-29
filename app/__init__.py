import os
from flask import Flask, redirect, url_for, session, request as flask_request
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

from app.extensions import db, limiter
from app.hms.routes import hms_bp
from app.booking.routes import booking_bp

migrate = Migrate()
csrf = CSRFProtect()
mail = Mail()


def create_app(config_object=None):
    app = Flask(__name__)

    if config_object:
        app.config.from_object(config_object)
    else:
        # Read from environment variables (PostgreSQL required)
        database_url = os.environ.get('DATABASE_URL')
        
        # Validate PostgreSQL is configured
        if not database_url or not database_url.startswith('postgresql://'):
            raise ValueError(
                "DATABASE_URL must be set to a PostgreSQL database. "
                "Example: postgresql://user:password@localhost/hotel_pms_prod"
            )
        
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
        
        if not app.config['SECRET_KEY']:
            raise ValueError("SECRET_KEY must be set in environment variables")
        
        app.config['UPLOAD_FOLDER'] = 'app/static/uploads'
        app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
        app.config['WTF_CSRF_ENABLED'] = True
        app.config['FLASK_ENV'] = os.environ.get('FLASK_ENV', 'production')

    db.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)
    
    # Security headers on every response
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Only send HSTS on HTTPS responses
        if flask_request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'hms.login'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    @login_manager.request_loader
    def load_user_from_request(request):
        return None

    @app.context_processor
    def inject_globals():
        """Inject global variables into all templates."""
        from app.models import Notification
        
        def get_unread_notifications():
            if not current_user.is_authenticated:
                return 0
            return Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()
        
        def get_recent_notifications(limit=5):
            if not current_user.is_authenticated:
                return []
            return Notification.query.filter_by(
                user_id=current_user.id
            ).order_by(Notification.created_at.desc()).limit(limit).all()
        
        def can_access_module(module_name):
            """Check if current user can access a module.

            Role model:
              superadmin  – creates hotels and managers; full system access
              manager     – full control of their assigned hotel (staff, ops, settings)
              owner       – portfolio read access across all their hotels; no write
              receptionist/housekeeping/restaurant/kitchen – operational roles for their hotel
            """
            if not current_user.is_authenticated:
                return False
            if current_user.is_superadmin:
                return True
            user_role = current_user.role.lower() if current_user.role else 'staff'
            module_access = {
                # Operations — manager runs the hotel; owner views
                'dashboard':    ['manager', 'owner'],
                'bookings':     ['manager', 'owner', 'receptionist'],
                'rooms':        ['manager', 'owner', 'receptionist'],
                'housekeeping': ['manager', 'owner', 'receptionist', 'housekeeping'],
                'restaurant':   ['manager', 'owner', 'receptionist', 'restaurant'],
                'kitchen':      ['manager', 'owner', 'kitchen', 'restaurant'],
                'room_service': ['manager', 'owner', 'receptionist', 'restaurant'],
                'inventory':    ['manager', 'owner'],
                'accounting':   ['manager', 'owner'],
                'reports':      ['manager', 'owner'],
                'night_audit':  ['manager'],
                # Settings — manager manages their hotel; owner cannot configure
                'settings':     ['manager'],
                'users':        ['manager'],
            }
            allowed = module_access.get(module_name, ['manager'])
            return user_role in allowed
        
        def get_currency():
            return session.get('currency', 'TZS')

        def get_currency_symbol():
            return '$' if get_currency() == 'USD' else 'TSh'

        def convert_price(price_tzs):
            """Convert TZS price to current currency (hardcoded 380 rate)."""
            if get_currency() == 'USD':
                return round(float(price_tzs) / 380, 2)
            return float(price_tzs)
        
        def format_price(price_tzs):
            converted = convert_price(price_tzs)
            symbol = get_currency_symbol()
            if get_currency() == 'USD':
                return f"{symbol}{converted:,.2f}"
            return f"{symbol} {converted:,.0f}"
        
        def get_allowed_hotel_ids():
            """Return hotel IDs the current user can access."""
            if not current_user.is_authenticated:
                return []
            from app.models import Hotel
            if current_user.is_superadmin:
                return [h.id for h in Hotel.query.all()]
            if current_user.role == 'owner' and current_user.owner_id:
                return [h.id for h in Hotel.query.filter_by(owner_id=current_user.owner_id).all()]
            if current_user.hotel_id:
                return [current_user.hotel_id]
            return []

        def get_current_hotel_id():
            """Return the active hotel ID for the current user/session."""
            if not current_user.is_authenticated:
                return None
            if not current_user.is_superadmin and current_user.hotel_id:
                return current_user.hotel_id
            hid = session.get('hotel_id')
            if hid:
                return int(hid)
            if current_user.is_superadmin:
                from app.models import Hotel
                first = Hotel.query.first()
                return first.id if first else None
            return None

        def get_current_hotel():
            """Return the active Hotel object."""
            from app.models import Hotel
            hid = get_current_hotel_id()
            return Hotel.query.get(hid) if hid else None

        def get_hotel_by_id(hotel_id):
            """Return Hotel by id (for template use)."""
            from app.models import Hotel
            return Hotel.query.get(hotel_id)

        return {
            'get_unread_notifications': get_unread_notifications,
            'get_recent_notifications': get_recent_notifications,
            'can_access_module': can_access_module,
            'get_currency': get_currency,
            'get_currency_symbol': get_currency_symbol,
            'convert_price': convert_price,
            'format_price': format_price,
            'get_allowed_hotel_ids': get_allowed_hotel_ids,
            'get_current_hotel_id': get_current_hotel_id,
            'get_current_hotel': get_current_hotel,
            'get_hotel_by_id': get_hotel_by_id,
        }

    app.register_blueprint(hms_bp)
    app.register_blueprint(booking_bp)

    @app.template_filter('format_number')
    def format_number_filter(value):
        try:
            return f"{float(value):,.0f}"
        except (ValueError, TypeError):
            return value

    with app.app_context():
        db.create_all()

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('hms.dashboard'))
        return redirect(url_for('booking.index'))

    return app
