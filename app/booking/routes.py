import re
import uuid
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    jsonify, session, current_app, send_from_directory
)
from flask_login import login_required, current_user
from app.extensions import db
from sqlalchemy import text
from app.models import (
    Hotel, Room, RoomType, RoomImage, Booking, Guest, Invoice, Payment,
    ChartOfAccount, JournalEntry, JournalLine, TaxRate, GalleryImage,
    Notification, User,
    ROOM_STATUSES
)

booking_bp = Blueprint('booking', __name__)

USD_EXCHANGE_RATE = 380  # 1 USD = 380 TZS (approximate)

def get_currency():
    return session.get('currency', 'TZS')

def set_currency(currency):
    if currency in ['TZS', 'USD']:
        session['currency'] = currency

def convert_price(price_tzs, currency=None):
    currency = currency or get_currency()
    if currency == 'USD':
        return round(float(price_tzs) / USD_EXCHANGE_RATE, 2)
    return float(price_tzs)

def get_currency_symbol():
    return '$' if get_currency() == 'USD' else 'TSh'

def format_price(price_tzs):
    converted = convert_price(price_tzs)
    symbol = get_currency_symbol()
    if get_currency() == 'USD':
        return f"{symbol}{converted:,.2f}"
    return f"{symbol} {converted:,.0f}"

def get_hotel():
    """Get the configured public-facing hotel via NGENDA_HOTEL_ID, falling back to first hotel."""
    from flask import current_app
    hotel_id = current_app.config.get('NGENDA_HOTEL_ID')
    if hotel_id:
        return Hotel.query.get(hotel_id)
    return Hotel.query.first()

def get_or_create_revenue_accounts(hotel_id):
    accounts = {
        'Room Revenue': ChartOfAccount.query.filter_by(hotel_id=hotel_id, name='Room Revenue').first(),
        'Food & Beverage': ChartOfAccount.query.filter_by(hotel_id=hotel_id, name='Food & Beverage').first(),
        'Other Revenue': ChartOfAccount.query.filter_by(hotel_id=hotel_id, name='Other Revenue').first()
    }
    
    for account_name, account in accounts.items():
        if not account:
            account = ChartOfAccount(
                hotel_id=hotel_id,
                name=account_name,
                type='Revenue'
            )
            db.session.add(account)
            accounts[account_name] = account
    
    if any(not acc for acc in accounts.values()):
        db.session.commit()
    
    return accounts

def get_or_create_asset_accounts(hotel_id):
    accounts = {
        'Cash': ChartOfAccount.query.filter_by(hotel_id=hotel_id, name='Cash').first(),
        'Bank': ChartOfAccount.query.filter_by(hotel_id=hotel_id, name='Bank').first(),
        'Accounts Receivable': ChartOfAccount.query.filter_by(hotel_id=hotel_id, name='Accounts Receivable').first()
    }
    
    for account_name, account in accounts.items():
        if not account:
            account = ChartOfAccount(
                hotel_id=hotel_id,
                name=account_name,
                type='Asset'
            )
            db.session.add(account)
            accounts[account_name] = account
    
    if any(not acc for acc in accounts.values()):
        db.session.commit()
    
    return accounts

def create_journal_entry(hotel_id, date, reference, description, debit_lines, credit_lines):
    """Create a journal entry using a nested transaction for atomicity."""
    try:
        with db.session.begin_nested():
            entry = JournalEntry(
                hotel_id=hotel_id,
                date=date,
                reference=reference
            )
            db.session.add(entry)
            db.session.flush()
            for account_id, amount, description in debit_lines:
                debit_line = JournalLine(
                    journal_entry_id=entry.id,
                    account_id=account_id,
                    debit=amount,
                    credit=0
                )
                db.session.add(debit_line)

            for account_id, amount, description in credit_lines:
                credit_line = JournalLine(
                    journal_entry_id=entry.id,
                    account_id=account_id,
                    debit=0,
                    credit=amount
                )
                db.session.add(credit_line)

            db.session.commit()
            return entry

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating journal entry: {str(e)}")
        raise e

def notify_hotel_staff(hotel_id, title, message, link=None, icon='bell', color='blue'):
    """Create a Notification for every active manager/owner/receptionist at the hotel."""
    try:
        staff = User.query.filter(
            User.hotel_id == hotel_id,
            User.active == True,
            User.role.in_(['manager', 'owner', 'superadmin', 'receptionist'])
        ).all()
        for user in staff:
            notif = Notification(
                user_id=user.id,
                hotel_id=hotel_id,
                type='website',
                title=title,
                message=message,
                link=link,
                icon=icon,
                color=color,
            )
            db.session.add(notif)
    except Exception as e:
        current_app.logger.warning(f"Could not create staff notifications: {e}")


def get_room_types_with_images():
    """Get all active room types with their primary image and available room count."""
    room_types = RoomType.query.filter_by(is_active=True).all()
    result = []
    
    for rt in room_types:
        primary_image = RoomImage.query.filter_by(
            room_type_id=rt.id,
            is_primary=True
        ).first()
        images = RoomImage.query.filter_by(room_type_id=rt.id).order_by(RoomImage.sort_order).all()
        available_rooms = Room.query.filter_by(
            room_type_id=rt.id,
            is_active=True,
            status='Vacant'
        ).count()
        
        result.append({
            'id': rt.id,
            'name': rt.name,
            'description': rt.description,
            'short_description': rt.short_description,
            'category': rt.category or 'standard',
            'base_price': rt.base_price,
            'price_usd': rt.price_usd if rt.price_usd else None,
            'capacity': rt.capacity,
            'size_sqm': rt.size_sqm,
            'bed_type': rt.bed_type,
            'amenities': rt.amenities or [],
            'primary_image': primary_image.image_filename if primary_image else None,
            'images': [img.image_filename for img in images],
            'available_rooms': available_rooms
        })
    
    return result

def check_availability(room_type_id, check_in, check_out):
    """Check if rooms are available for the given dates."""
    booked_rooms = db.session.query(Room.id).filter(
        Room.room_type_id == room_type_id,
        Room.is_active == True,
        Room.id.in_(
            db.session.query(Booking.room_id).filter(
                Booking.status.in_(['Reserved', 'CheckedIn']),
                Booking.check_in_date < check_out,
                Booking.check_out_date > check_in
            )
        )
    ).all()
    booked_room_ids = [r[0] for r in booked_rooms]
    available = Room.query.filter(
        Room.room_type_id == room_type_id,
        Room.is_active == True,
        Room.status.in_(['Vacant', 'Dirty']),
        ~Room.id.in_(booked_room_ids) if booked_room_ids else True
    ).count()
    
    return available > 0

def generate_booking_reference():
    return f"NGD-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


@booking_bp.route('/')
def index():
    """Home page with room listings"""
    currency = get_currency()
    room_types = get_room_types_with_images()
    
    for rt in room_types:
        rt['display_price'] = convert_price(rt['base_price'], currency)
        rt['currency_symbol'] = get_currency_symbol()
    
    categories = set(rt['category'] for rt in room_types if rt['category'])

    return render_template('booking/index.html',
                         room_types=room_types,
                         categories=list(categories),
                         currency=currency,
                         currency_symbol=get_currency_symbol(),
                         date=date)


@booking_bp.route('/rooms')
def rooms():
    """All rooms listing page"""
    currency = get_currency()
    room_types = get_room_types_with_images()
    
    for rt in room_types:
        rt['display_price'] = convert_price(rt['base_price'], currency)
        rt['currency_symbol'] = get_currency_symbol()
    
    categories = set(rt['category'] for rt in room_types if rt['category'])

    return render_template('booking/rooms.html',
                         room_types=room_types,
                         categories=list(categories),
                         currency=currency,
                         currency_symbol=get_currency_symbol())


@booking_bp.route('/room/<int:room_id>')
def room_detail(room_id):
    """Individual room detail page"""
    currency = get_currency()
    
    room_type = RoomType.query.get_or_404(room_id)
    images = RoomImage.query.filter_by(room_type_id=room_id).order_by(RoomImage.sort_order).all()
    
    # Get similar rooms (same category)
    similar = RoomType.query.filter(
        RoomType.category == room_type.category,
        RoomType.id != room_id,
        RoomType.is_active == True
    ).limit(3).all()
    
    room_data = {
        'id': room_type.id,
        'name': room_type.name,
        'description': room_type.description,
        'short_description': room_type.short_description,
        'category': room_type.category or 'standard',
        'base_price': room_type.base_price,
        'price_usd': room_type.price_usd,
        'capacity': room_type.capacity,
        'size_sqm': room_type.size_sqm,
        'bed_type': room_type.bed_type,
        'amenities': room_type.amenities or [],
        'images': [img.image_filename for img in images],
        'primary_image': images[0].image_filename if images else None
    }
    
    room_data['display_price'] = convert_price(room_data['base_price'], currency)
    room_data['currency_symbol'] = get_currency_symbol()
    
    similar_rooms = []
    for rt in similar:
        rt_images = RoomImage.query.filter_by(room_type_id=rt.id, is_primary=True).all()
        similar_rooms.append({
            'id': rt.id,
            'name': rt.name,
            'category': rt.category,
            'base_price': rt.base_price,
            'display_price': convert_price(rt.base_price, currency),
            'currency_symbol': get_currency_symbol(),
            'primary_image': rt_images[0].image_filename if rt_images else None
        })
    
    return render_template('booking/room_detail.html',
                         room=room_data,
                         similar_rooms=similar_rooms,
                         currency=currency,
                         date=date)


@booking_bp.route('/book', methods=['GET', 'POST'])
def book():
    """Booking form and creation"""
    if request.method == 'POST':
        try:
            guest_name = request.form.get('guest_name', '').strip()
            guest_email = request.form.get('guest_email', '').strip()
            guest_phone = request.form.get('guest_phone', '').strip()
            room_type_id = request.form.get('room_type_id', type=int)
            check_in_str = request.form.get('check_in')
            check_out_str = request.form.get('check_out')
            adults = request.form.get('adults', 1, type=int)
            children = request.form.get('children', 0, type=int)
            special_requests = request.form.get('special_requests', '').strip()
            
            if not all([guest_name, guest_email, guest_phone, room_type_id, check_in_str, check_out_str]):
                flash('Please fill in all required fields.', 'error')
                return redirect(url_for('booking.book'))
            
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, guest_email):
                flash('Please enter a valid email address.', 'error')
                return redirect(url_for('booking.book'))
            
            current_app.logger.info(f"Received dates - check_in: {check_in_str}, check_out: {check_out_str}")
            
            try:
                check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
                check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
                current_app.logger.info(f"Parsed dates - check_in: {check_in}, check_out: {check_out}")
            except ValueError as e:
                flash('Invalid date format. Please use the date picker.', 'error')
                current_app.logger.error(f"Date parsing error: {e}")
                return redirect(url_for('booking.book', room_type=room_type_id))
            
            if check_out <= check_in:
                flash('Check-out date must be after check-in date.', 'error')
                current_app.logger.warning(f"Invalid date range: check_out ({check_out}) <= check_in ({check_in})")
                return redirect(url_for('booking.book', room_type=room_type_id, check_in=check_in_str, check_out=check_out_str))
            
            room_type = RoomType.query.get_or_404(room_type_id)

            if not check_availability(room_type_id, check_in, check_out):
                flash(f'Sorry, no {room_type.name} rooms available for selected dates. Please try different dates or select another room type.', 'warning')
                return redirect(url_for('booking.book', room_type=room_type_id, check_in=check_in_str, check_out=check_out_str))
            
            booked_room_ids = db.session.query(Booking.room_id).filter(
                Booking.status.in_(['Reserved', 'CheckedIn']),
                Booking.check_in_date < check_out,
                Booking.check_out_date > check_in
            ).all()
            booked_room_ids = [r[0] for r in booked_room_ids]
            
            room = Room.query.filter(
                Room.room_type_id == room_type_id,
                Room.is_active == True,
                Room.status == 'Vacant',
                ~Room.id.in_(booked_room_ids) if booked_room_ids else True
            ).first()
            
            if not room:
                flash('No available room found.', 'error')
                return redirect(url_for('booking.book'))
            
            nights = (check_out - check_in).days
            total_amount = room_type.base_price * nights
            
            guest = Guest(
                hotel_id=room_type.hotel_id,
                name=guest_name,
                phone=guest_phone,
                email=guest_email
            )
            db.session.add(guest)
            db.session.flush()
            
            booking = Booking(
                hotel_id=room_type.hotel_id,
                guest_id=guest.id,
                room_id=room.id,
                guest_name=guest_name,
                guest_email=guest_email,
                guest_phone=guest_phone,
                room_type_requested=room_type.name,
                check_in_date=check_in,
                check_out_date=check_out,
                status='Reserved',
                total_amount=total_amount,
                amount_paid=0,
                balance=total_amount,
                adults=adults,
                children=children,
                special_requests=special_requests,
                source='website',
                booking_reference=generate_booking_reference(),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')[:500]
            )
            db.session.add(booking)
            db.session.flush()
            
            invoice = Invoice(
                hotel_id=room_type.hotel_id,
                booking_id=booking.id,
                total=total_amount,
                status='Unpaid',
                invoice_number=f"INV-{booking.booking_reference}"
            )
            db.session.add(invoice)
            
            room.status = 'Reserved'

            try:
                revenue_accounts = get_or_create_revenue_accounts(room_type.hotel_id)
                if revenue_accounts.get('Room Revenue') and revenue_accounts.get('Accounts Receivable'):
                    create_journal_entry(
                        hotel_id=room_type.hotel_id,
                        date=check_in,
                        reference=f"BOOKING-{booking.booking_reference}",
                        description=f"Room revenue for booking {booking.booking_reference} - {room_type.name}",
                        debit_lines=[
                            (revenue_accounts['Accounts Receivable'].id, total_amount, f'Accounts receivable for booking {booking.booking_reference}')
                        ],
                        credit_lines=[
                            (revenue_accounts['Room Revenue'].id, total_amount, f'Room revenue for {room_type.name} - {nights} nights')
                        ]
                    )
            except Exception as je_error:
                # Continue without journal entry - it's not critical for booking
                current_app.logger.warning(f"Journal entry creation skipped: {str(je_error)}")

            db.session.commit()

            notify_hotel_staff(
                hotel_id=room_type.hotel_id,
                title=f'New booking: {booking.booking_reference}',
                message=(
                    f'{guest_name} ({guest_phone} | {guest_email}) booked '
                    f'{room_type.name} — {check_in.strftime("%d %b")} to '
                    f'{check_out.strftime("%d %b %Y")} ({nights} night{"s" if nights != 1 else ""}).'
                ),
                link=f'/hms/bookings/{booking.id}',
                icon='calendar',
                color='green',
            )
            db.session.commit()

            from app.utils.email_service import send_booking_notification_to_hotel
            send_booking_notification_to_hotel(booking, room_type, nights)

            flash(f'Booking created successfully! Your booking reference is: {booking.booking_reference}', 'success')
            return redirect(url_for('booking.booking_success', booking_id=booking.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(f"Booking creation failed: {str(e)}")
            current_app.logger.error(f"Form data received: {request.form}")
            current_app.logger.error(f"Room type ID: {room_type_id}, Check-in: {check_in_str}, Check-out: {check_out_str}")
            flash('Sorry, there was an error creating your booking. Please try again.', 'error')
            return redirect(url_for('booking.book', room_type=room_type_id, check_in=check_in_str, check_out=check_out_str))
    
    room_type_id = request.args.get('room_type_id', type=int) or request.args.get('room_type', type=int)
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')

    room_types = RoomType.query.filter_by(is_active=True).all()

    selected_room = RoomType.query.get(room_type_id) if room_type_id else None

    return render_template('booking/booking_form.html',
                         room_types=room_types,
                         selected_room_type=room_type_id,
                         selected_room=selected_room,
                         check_in=check_in,
                         check_out=check_out,
                         currency=get_currency(),
                         currency_symbol=get_currency_symbol())


@booking_bp.route('/booking-success/<int:booking_id>')
def booking_success(booking_id):
    """Booking success page"""
    booking = Booking.query.get_or_404(booking_id)
    
    nights = (booking.check_out_date - booking.check_in_date).days
    
    return render_template('booking/booking-success.html',
                         booking=booking,
                         nights=nights,
                         currency_symbol=get_currency_symbol())


@booking_bp.route('/process-payment/<int:booking_id>', methods=['POST'])
@login_required
def process_payment(booking_id):
    """Process payment and create accounting entries"""
    booking = Booking.query.get_or_404(booking_id)
    
    if request.method == 'POST':
        try:
            raw_amount = request.form.get('amount', '0')
            try:
                amount = Decimal(str(raw_amount))
            except InvalidOperation:
                flash('Invalid payment amount.', 'error')
                return redirect(url_for('booking.booking_success', booking_id=booking_id))
            payment_method = request.form.get('payment_method', 'Cash')
            notes = request.form.get('notes', '').strip()

            if amount <= 0:
                flash('Payment amount must be greater than 0.', 'error')
                return redirect(url_for('booking.booking_success', booking_id=booking_id))
            if amount > Decimal('9999999.99'):
                flash('Payment amount exceeds the maximum allowed.', 'error')
                return redirect(url_for('booking.booking_success', booking_id=booking_id))
            
            payment = Payment(
                hotel_id=booking.hotel_id,
                booking_id=booking.id,
                amount=amount,
                payment_method=payment_method,
                status='completed',
                notes=notes,
                created_by=current_user.id
            )
            db.session.add(payment)
            
            invoice = Invoice.query.filter_by(booking_id=booking_id).first()
            if invoice:
                invoice.amount_paid += amount
                invoice.balance = invoice.total - invoice.amount_paid
                if invoice.balance <= 0:
                    invoice.status = 'Paid'
                else:
                    invoice.status = 'PartiallyPaid'
            
            asset_accounts = get_or_create_asset_accounts(booking.hotel_id)
            if asset_accounts.get('Cash') and payment_method == 'Cash':
                create_journal_entry(
                    hotel_id=booking.hotel_id,
                    date=datetime.now().date(),
                    reference=f"PAYMENT-{booking.booking_reference}",
                    description=f"Payment received for booking {booking.booking_reference}",
                    debit_lines=[
                        (asset_accounts['Cash'].id, amount, f'Cash payment for booking {booking.booking_reference}')
                    ],
                    credit_lines=[
                        (asset_accounts['Accounts Receivable'].id, amount, f'Payment received for booking {booking.booking_reference}')
                    ]
                )
            elif asset_accounts.get('Bank') and payment_method != 'Cash':
                create_journal_entry(
                    hotel_id=booking.hotel_id,
                    date=datetime.now().date(),
                    reference=f"PAYMENT-{booking.booking_reference}",
                    description=f"Payment received for booking {booking.booking_reference}",
                    debit_lines=[
                        (asset_accounts['Bank'].id, amount, f'Bank payment for booking {booking.booking_reference}')
                    ],
                    credit_lines=[
                        (asset_accounts['Accounts Receivable'].id, amount, f'Payment received for booking {booking.booking_reference}')
                    ]
                )
            
            db.session.commit()
            flash(f'Payment of {amount} processed successfully!', 'success')
            return redirect(url_for('booking.booking_success', booking_id=booking_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Payment processing error: {str(e)}")
            flash('Error processing payment. Please try again.', 'error')
            return redirect(url_for('booking.booking_success', booking_id=booking_id))
    
    return render_template('booking/payment_form.html', booking=booking)


@booking_bp.route('/check-availability', methods=['GET'])
def check_availability_api():
    """AJAX endpoint to check room availability"""
    room_type_id = request.args.get('room_type_id', type=int)
    check_in_str = request.args.get('check_in')
    check_out_str = request.args.get('check_out')
    
    if not all([room_type_id, check_in_str, check_out_str]):
        return jsonify({'success': False, 'error': 'Missing required parameters'})
    
    try:
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        
        if check_out <= check_in:
            return jsonify({'success': False, 'error': 'Check-out must be after check-in'})
        
        available = check_availability(room_type_id, check_in, check_out)
        
        return jsonify({
            'success': True,
            'available': available,
            'message': 'Rooms available' if available else 'No rooms available for selected dates'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@booking_bp.route('/set-currency/<currency>')
def set_currency_route(currency):
    """Set currency preference"""
    if currency in ['TZS', 'USD']:
        set_currency(currency)
    return redirect(request.referrer or url_for('booking.index'))


@booking_bp.route('/about')
def about():
    """About page"""
    return render_template('booking/about-1.html')


@booking_bp.route('/gallery')
def gallery():
    """Gallery page."""
    hotel = get_hotel()
    if not hotel:
        flash("Hotel not found.", "danger")
        return redirect(url_for('booking.index'))
    
    large_images = GalleryImage.query.filter_by(
        hotel_id=hotel.id,
        is_active=True,
        size_type='large'
    ).order_by(GalleryImage.sort_order, GalleryImage.created_at.desc()).limit(2).all()
    
    medium_images = GalleryImage.query.filter_by(
        hotel_id=hotel.id,
        is_active=True,
        size_type='medium'
    ).order_by(GalleryImage.sort_order, GalleryImage.created_at.desc()).limit(3).all()
    
    small_images = GalleryImage.query.filter_by(
        hotel_id=hotel.id,
        is_active=True,
        size_type='small'
    ).order_by(GalleryImage.sort_order, GalleryImage.created_at.desc()).limit(12).all()
    
    # If no images uploaded yet, fall back to the static template so the page still renders
    use_static = len(large_images) == 0 and len(medium_images) == 0 and len(small_images) == 0
    
    return render_template(
        'booking/gallery-fixed.html',
        large_images=large_images,
        medium_images=medium_images,
        small_images=small_images,
        use_static=use_static
    )


@booking_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page — saves message to HMS and notifies hotel staff."""
    if request.method == 'POST':
        try:
            # Footer newsletter form only sends the 'news-letter' field; full form sends name/email/message
            newsletter_email = request.form.get('news-letter', '').strip()
            if newsletter_email:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, newsletter_email):
                    flash('Please enter a valid email address.', 'error')
                    return redirect(url_for('booking.contact'))
                current_app.logger.info(f'Newsletter subscription: {newsletter_email}')
                flash('Thank you for subscribing! We will keep you updated.', 'success')
                return redirect(url_for('booking.contact'))

            sender_name = request.form.get('username', '').strip()
            sender_email = request.form.get('email', '').strip()
            message_body = request.form.get('message', '').strip()

            if not sender_name or not sender_email or not message_body:
                flash('Please fill in all fields.', 'error')
                return redirect(url_for('booking.contact'))

            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, sender_email):
                flash('Please enter a valid email address.', 'error')
                return redirect(url_for('booking.contact'))

            current_app.logger.info(
                f'Contact form: name={sender_name}, email={sender_email}, '
                f'message={message_body[:100]}'
            )
            hotel = get_hotel()
            if hotel:
                notify_hotel_staff(
                    hotel_id=hotel.id,
                    title=f'Website message from {sender_name}',
                    message=f'{sender_name} ({sender_email}): {message_body[:200]}',
                    link='/hms/bookings',
                    icon='mail',
                    color='blue',
                )
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()

            from app.utils.email_service import send_contact_message_to_hotel
            send_contact_message_to_hotel(sender_name, sender_email, message_body)

            flash('Thank you! Your message has been received. We will get back to you shortly.', 'success')
            return redirect(url_for('booking.contact'))

        except Exception as e:
            current_app.logger.error(f'Contact form error: {str(e)}')
            flash('An error occurred. Please try again.', 'error')
            return redirect(url_for('booking.contact'))

    return render_template('booking/contact-1.html')


@booking_bp.route('/services')
def services():
    """Services page"""
    return render_template('booking/service-details.html')


@booking_bp.route('/faq')
def faq():
    """FAQ page"""
    return render_template('booking/faq.html')


@booking_bp.route('/blog')
def blog():
    """Blog page"""
    return render_template('booking/news-grid.html')
