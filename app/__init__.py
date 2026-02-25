"""
Ngenda Hotel PMS - Application Factory
Unified Flask app for HMS Admin and Website Booking.
"""
import os
from flask import Flask, redirect, url_for
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

    # Configuration
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

    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)
    
    # Exempt restaurant routes from CSRF for now
    csrf.exempt('app.hms.routes.menu_item_add')
    csrf.exempt('app.hms.routes.category_create')
    csrf.exempt('app.hms.routes.pos_order_create')
    csrf.exempt('app.hms.routes.pos_order_status')
    csrf.exempt('app.hms.routes.table_add')

    # Login manager
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
        # For API authentication if needed
        return None

    # Context processors
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
            """Check if current user can access a module."""
            if not current_user.is_authenticated:
                return False
            if current_user.is_superadmin:
                return True
            user_role = current_user.role.lower() if current_user.role else 'staff'
            module_access = {
                'dashboard': ['manager', 'owner', 'superadmin'],
                'bookings': ['manager', 'owner', 'superadmin', 'receptionist'],
                'rooms': ['manager', 'owner', 'superadmin', 'receptionist'],
                'housekeeping': ['manager', 'owner', 'superadmin', 'receptionist', 'housekeeping'],
                'restaurant': ['manager', 'owner', 'superadmin', 'receptionist', 'restaurant'],
                'kitchen': ['manager', 'owner', 'superadmin', 'kitchen', 'restaurant'],
                'inventory': ['manager', 'owner', 'superadmin'],
                'accounting': ['manager', 'owner', 'superadmin'],
                'reports': ['manager', 'owner', 'superadmin', 'receptionist'],
                'settings': ['manager', 'owner', 'superadmin'],
            }
            allowed = module_access.get(module_name, ['manager', 'owner', 'superadmin'])
            return user_role in allowed
        
        def get_currency():
            """Get current currency from session"""
            return session.get('currency', 'TZS')
        
        def get_currency_symbol():
            """Get currency symbol"""
            return '$' if get_currency() == 'USD' else 'TSh'
        
        def convert_price(price_tzs):
            """Convert TZS price to current currency"""
            if get_currency() == 'USD':
                return round(float(price_tzs) / 380, 2)
            return float(price_tzs)
        
        def format_price(price_tzs):
            """Format price with currency"""
            converted = convert_price(price_tzs)
            symbol = get_currency_symbol()
            if get_currency() == 'USD':
                return f"{symbol}{converted:,.2f}"
            return f"{symbol} {converted:,.0f}"
        
        return {
            'get_unread_notifications': get_unread_notifications,
            'get_recent_notifications': get_recent_notifications,
            'can_access_module': can_access_module,
            'get_currency': get_currency,
            'get_currency_symbol': get_currency_symbol,
            'convert_price': convert_price,
            'format_price': format_price,
        }

    # Register blueprints
    app.register_blueprint(hms_bp)
    app.register_blueprint(booking_bp)
    
    # Add custom Jinja filters
    @app.template_filter('format_number')
    def format_number_filter(value):
        """Format number with commas"""
        try:
            return f"{float(value):,.0f}"
        except (ValueError, TypeError):
            return value

    # Create database tables
    with app.app_context():
        db.create_all()

    # Root redirect
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('hms.dashboard'))
        return redirect(url_for('booking.index'))

    return app
