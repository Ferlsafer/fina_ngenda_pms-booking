"""Configuration for Multi-Property Hotel PMS."""
import os
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Website integration (Ngenda Hotel)
    WEBSITE_API_KEY = os.getenv("WEBSITE_API_KEY", "ngenda-hotel-website-key-2026")
    NGENDA_HOTEL_ID = int(os.getenv("NGENDA_HOTEL_ID", "0") or "0") or None
    TZS_TO_USD = float(os.getenv("TZS_TO_USD", "2500") or "2500")

    # Restaurant POS Configuration
    DEFAULT_TAX_RATE = float(os.getenv("DEFAULT_TAX_RATE", "18") or "18")  # 18% tax
    TAX_RATE_DISPLAY = int(os.getenv("TAX_RATE_DISPLAY", "18") or "18")  # Display percentage

    # Email Configuration (for password recovery, notifications)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "False").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "Ngenda Hotel <noreply@ngendahotel.com>")
    MAIL_RESET_TOKEN_EXPIRY = int(os.getenv("MAIL_RESET_TOKEN_EXPIRY", "3600"))  # 1 hour in seconds

    # Upload settings (menu images, etc.)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join("static", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    # Use DATABASE_URL for PostgreSQL, or omit for SQLite (dev only)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(os.path.dirname(os.path.dirname(__file__)), "hotel_pms_dev.sqlite")
    )


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SESSION_COOKIE_SECURE = True
    SECRET_KEY = os.getenv("SECRET_KEY", "")


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:"
    )
    WTF_CSRF_ENABLED = False  # Simplify API and form tests