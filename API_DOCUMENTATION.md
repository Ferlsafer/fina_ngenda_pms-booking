# HMS Finale - Booking API Documentation

## Overview
This is a comprehensive Hotel Management System (HMS) built with Flask that includes a public booking website and internal management system. The system handles multi-property hotel operations with room management, bookings, payments, and more.

## Tech Stack
- **Backend**: Flask 3.x with SQLAlchemy
- **Database**: PostgreSQL (psycopg2-binary)
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF
- **Rate Limiting**: Flask-Limiter
- **Email**: Flask-Mail
- **Server**: Gunicorn

## System Architecture

### Core Models

#### Hotel Management
```python
class Hotel(db.Model):
    - id, name, display_name, location, address
    - currency (default: TZS), timezone
    - check_in_time, check_out_time
    - policies (cancellation, children, pets, payment)
    - contact info and social media links

class Owner(db.Model):
    - id, name, email
    - owns multiple hotels

class User(UserMixin, db.Model):
    - id, name, email, password_hash
    - role (superadmin, manager, owner, receptionist, etc.)
    - hotel_id, owner_id
    - permissions and access control
```

#### Room Management
```python
class RoomType(db.Model):
    - id, hotel_id, name, base_price, price_usd
    - description, capacity, size_sqm, bed_type
    - amenities (JSON), category
    - tax_rate, is_active

class Room(db.Model):
    - id, hotel_id, room_type_id, room_number
    - status (Vacant, Occupied, Dirty, Reserved, Maintenance)
    - floor, description, is_active

class RoomImage(db.Model):
    - id, room_type_id, image_filename
    - is_primary, sort_order
```

#### Booking System
```python
class Booking(db.Model):
    - id, hotel_id, guest_id, room_id
    - guest_name, guest_email, guest_phone
    - check_in_date, check_out_date
    - status (Reserved, CheckedIn, CheckedOut, Cancelled)
    - source (website, front_desk, phone, email, walk_in, ota, corporate)
    - booking_reference (unique)
    - adults, children, special_requests
    - total_amount, amount_paid, balance
    - ip_address, user_agent, referral_source

class Guest(db.Model):
    - id, hotel_id, name, phone, email
    - address, id_type, id_number, nationality
    - created_at

class Invoice(db.Model):
    - id, hotel_id, booking_id, invoice_number
    - total, status (Unpaid, PartiallyPaid, Paid)
    - due_date, created_at

class Payment(db.Model):
    - id, hotel_id, booking_id, invoice_id
    - amount, payment_method, payment_type
    - transaction_id, status, notes
    - created_at
```

## API Endpoints

### Public Booking Website (Blueprint: `booking`)

#### Room Discovery
- `GET /` - Home page with room listings
- `GET /rooms` - All rooms listing page
- `GET /room/<int:room_id>` - Individual room detail page
- `GET /check-availability` - AJAX endpoint to check room availability
  - Parameters: `room_type_id`, `check_in`, `check_out`
  - Returns: `{'success': bool, 'available': bool, 'message': str}`

#### Booking Process
- `GET /book` - Booking form page
- `POST /book` - Create new booking
  - Parameters: `guest_name`, `guest_email`, `guest_phone`, 
                `room_type_id`, `check_in`, `check_out`,
                `adults`, `children`, `special_requests`
  - Creates: Guest, Booking, Invoice records
  - Updates: Room status to 'Reserved'
  - Sends: Notifications to hotel staff

#### Payment Processing
- `POST /process-payment/<int:booking_id>` - Process payment (requires login)
  - Parameters: `amount`, `payment_method`, `notes`
  - Creates: Payment record
  - Updates: Invoice status and balance
  - Creates: Accounting journal entries

#### Utility Pages
- `GET /booking-success/<int:booking_id>` - Booking confirmation page
- `GET /set-currency/<currency>` - Set currency preference (TZS/USD)
- `GET /about` - About page
- `GET /gallery` - Gallery page
- `GET /contact` - Contact page (POST submits messages)
- `GET /services` - Services page
- `GET /faq` - FAQ page
- `GET /blog` - Blog page

### Internal Management System (Blueprint: `hms`)

#### Authentication
- `GET/POST /hms/login` - Staff login
- `GET /hms/logout` - Staff logout
- `GET/POST /hms/forgot-password` - Password reset request
- `GET/POST /hms/reset-password/<token>` - Password reset confirmation

#### Dashboard
- `GET /hms/` - Main dashboard (role-based redirection)
  - Statistics: rooms, bookings, revenue, occupancy
  - Today's arrivals and departures
  - Recent bookings and notifications

#### Room Management
- `GET /hms/rooms` - Room listing
- `GET/POST /hms/rooms/add` - Add new room
- `POST /hms/rooms/<int:room_id>/update` - Update room details
- `POST /hms/rooms/<int:room_id>/change-status` - Change room status
- `POST /hms/rooms/<int:room_id>/delete` - Delete room
- `GET /hms/rooms/types` - Room types listing
- `GET/POST /hms/rooms/types/add` - Add room type
- `POST /hms/rooms/types/<int:type_id>/update` - Update room type
- `POST /hms/rooms/types/<int:type_id>/delete` - Delete room type

#### Booking Management
- `GET/POST /hms/bookings` - Booking management interface
- Additional booking endpoints (full list in routes.py)

## Key Business Logic

### Booking State Machine
```python
BOOKING_STATUS_TRANSITIONS = {
    'Reserved': ['CheckedIn', 'Cancelled', 'NoShow'],
    'CheckedIn': ['CheckedOut'],
    'CheckedOut': [],  # Terminal state
    'Cancelled': [],   # Terminal state
    'NoShow': []       # Terminal state
}
```

### Room Status Management
- **Vacant**: Available for booking
- **Reserved**: Booked but not checked in
- **Occupied**: Guest checked in
- **Dirty**: Room needs cleaning
- **Maintenance**: Room under maintenance

### Availability Checking
The system checks room availability by:
1. Filtering by room type and active status
2. Excluding rooms with existing bookings in the date range
3. Checking current room status (Vacant/Dirty available)

### Payment Processing
- Supports multiple payment methods (Cash, Bank, Card, Mobile)
- Automatic accounting journal entries
- Invoice status updates (Unpaid → PartiallyPaid → Paid)

### Currency Support
- Multi-currency support (TZS, USD)
- Exchange rate conversion (1 USD = 380 TZS)
- Session-based currency preference

## Data Relationships

```
Owner → Hotels → RoomTypes → Rooms → Bookings
                    ↓
                 RoomImages
                    ↓
Guests → Bookings → Invoices → Payments
                    ↓
               HousekeepingTasks
```

## Security Features
- Role-based access control
- Rate limiting on sensitive endpoints
- Password hashing with Werkzeug
- CSRF protection via Flask-WTF
- Input validation and sanitization

## Integration Points
- Email notifications (Flask-Mail)
- Payment gateway (Selcom integration)
- Accounting system (Chart of Accounts, Journal Entries)
- Housekeeping management
- Restaurant management (separate module)

## Development Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Configure database in `.env`
3. Run migrations: `flask db upgrade`
4. Start server: `python run.py` or `gunicorn`

## Database Schema
The system uses PostgreSQL with SQLAlchemy ORM. Key tables:
- `hotels`, `owners`, `users`
- `room_types`, `rooms`, `room_images`
- `guests`, `bookings`, `invoices`, `payments`
- `housekeeping_tasks`, `maintenance_issues`
- `chart_of_accounts`, `journal_entries`, `journal_lines`

## Booking Flow
1. Guest selects room type and dates
2. System checks availability
3. Guest fills booking form
4. System creates guest, booking, invoice records
5. Room status changes to 'Reserved'
6. Hotel staff receive notifications
7. Payment processing (optional)
8. Check-in/check-out process through HMS

This API documentation provides the foundation for rebuilding the booking website with modern frontend technology while maintaining the robust backend system.
