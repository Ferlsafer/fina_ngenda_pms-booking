"""
Business Date Lock Middleware
Prevents transactions when business day is locked
"""

from functools import wraps
from flask import flash, redirect, url_for
from datetime import datetime, date
from app.models import BusinessDate
from app.extensions import db


def business_date_lock_required(f):
    """Decorator to prevent transactions on locked business days"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if business date is locked
        hotel_id = get_current_hotel_id()
        if hotel_id:
            biz_date = BusinessDate.query.filter_by(hotel_id=hotel_id).first()
            if not biz_date:
                from datetime import datetime
                today = date.today()
                biz_date = BusinessDate(
                    hotel_id=hotel_id,
                    current_business_date=today,
                    is_closed=True,
                    updated_at=datetime.now()
                )
                db.session.add(biz_date)
                db.session.commit()
                print(f'✅ Created and locked business date: {today}')
            else:
                print(f'📅 Existing business date: {biz_date.current_business_date}')
                print(f'🔒 Status: {"Locked" if biz_date.is_closed else "Open"}')
            
            if biz_date and biz_date.is_closed and biz_date.current_business_date == date.today():
                flash("🔒 Business day is locked. No transactions can be recorded.", "danger")
                return redirect(url_for("hms.night_audit"))
        
        return f(*args, **kwargs)
    return decorated_function


def get_current_hotel_id():
    """Get current hotel ID - this should be imported from routes"""
    try:
        from app.hms.routes import get_current_hotel_id
        return get_current_hotel_id()
    except ImportError:
        # Fallback for testing
        return 1
