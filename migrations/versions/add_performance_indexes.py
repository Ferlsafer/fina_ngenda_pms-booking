"""Add performance indexes

Revision ID: add_performance_indexes
Revises: 408e6a775312
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_performance_indexes'
down_revision = '8e62f8423756'
branch_labels = None
depends_on = None


def upgrade():
    # ============================================
    # USERS & AUTHENTICATION
    # ============================================
    
    # Email lookups (login, user search)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    
    # Hotel-based user lookups
    op.create_index('ix_users_hotel_id', 'users', ['hotel_id'])
    
    # Role-based access control
    op.create_index('ix_users_role', 'users', ['role'])
    
    # Password reset tokens
    try:
        op.create_index('ix_users_reset_token', 'users', ['reset_token'])
    except:
        pass
    
    # Last login for activity tracking
    try:
        op.create_index('ix_users_last_login_at', 'users', ['last_login_at'])
    except:
        pass


    # ============================================
    # HOTELS & OWNERS
    # ============================================
    
    # Owner's hotels lookup
    op.create_index('ix_hotels_owner_id', 'hotels', ['owner_id'])
    
    # Hotel name search
    op.create_index('ix_hotels_name', 'hotels', ['name'])


    # ============================================
    # BOOKINGS (High traffic table)
    # ============================================
    
    # Guest bookings lookup
    op.create_index('ix_bookings_guest_id', 'bookings', ['guest_id'])
    
    # Room bookings lookup (availability check)
    op.create_index('ix_bookings_room_id', 'bookings', ['room_id'])
    
    # Date range queries (availability, calendar)
    op.create_index('ix_bookings_check_in', 'bookings', ['check_in_date'])
    op.create_index('ix_bookings_check_out', 'bookings', ['check_out_date'])
    
    # Composite index for availability checks
    op.create_index('ix_bookings_room_dates', 'bookings', 
                    ['room_id', 'check_in_date', 'check_out_date'])
    
    # Status filtering (active bookings, check-ins)
    op.create_index('ix_bookings_status', 'bookings', ['status'])
    
    # Hotel bookings
    op.create_index('ix_bookings_hotel_id', 'bookings', ['hotel_id'])
    
    # Booking reference lookup
    op.create_index('ix_bookings_reference', 'bookings', ['booking_reference'])
    
    # Recent bookings
    op.create_index('ix_bookings_created_at', 'bookings', ['created_at'])


    # ============================================
    # GUESTS
    # ============================================
    
    # Guest search by name
    op.create_index('ix_guests_name', 'guests', ['name'])
    
    # Guest search by phone
    op.create_index('ix_guests_phone', 'guests', ['phone'])
    
    # Guest search by email
    op.create_index('ix_guests_email', 'guests', ['email'])
    
    # Hotel guests
    op.create_index('ix_guests_hotel_id', 'guests', ['hotel_id'])


    # ============================================
    # ROOMS & ROOM TYPES
    # ============================================
    
    # Room type's rooms
    op.create_index('ix_rooms_room_type_id', 'rooms', ['room_type_id'])
    
    # Room number lookup
    op.create_index('ix_rooms_room_number', 'rooms', ['room_number'])
    
    # Status filtering (housekeeping, availability)
    op.create_index('ix_rooms_status', 'rooms', ['status'])
    
    # Hotel rooms
    op.create_index('ix_rooms_hotel_id', 'rooms', ['hotel_id'])
    
    # Room type hotel lookup
    op.create_index('ix_room_types_hotel_id', 'room_types', ['hotel_id'])
    
    # Room type name search
    op.create_index('ix_room_types_name', 'room_types', ['name'])


    # ============================================
    # INVOICES & PAYMENTS
    # ============================================
    
    # Invoice booking lookup
    op.create_index('ix_invoices_booking_id', 'invoices', ['booking_id'])
    
    # Invoice status filtering
    op.create_index('ix_invoices_status', 'invoices', ['status'])
    
    # Payment invoice lookup
    op.create_index('ix_payments_invoice_id', 'payments', ['invoice_id'])
    
    # Payment date range queries
    op.create_index('ix_payments_created_at', 'payments', ['created_at'])


    # ============================================
    # RESTAURANT (Menu, Orders)
    # ============================================
    
    # Menu items by category
    op.create_index('ix_menu_items_category_id', 'menu_items', ['category_id'])
    
    # Available menu items
    op.create_index('ix_menu_items_is_available', 'menu_items', ['is_available'])
    
    # Menu items by hotel
    op.create_index('ix_menu_items_hotel_id', 'menu_items', ['hotel_id'])
    
    # Menu categories by hotel
    op.create_index('ix_menu_categories_hotel_id', 'menu_categories', ['hotel_id'])
    
    # Restaurant orders by table
    op.create_index('ix_restaurant_orders_table_id', 'restaurant_orders', ['table_id'])
    
    # Order status (kitchen display)
    op.create_index('ix_restaurant_orders_status', 'restaurant_orders', ['status'])
    
    # Order items lookup
    op.create_index('ix_restaurant_order_items_order_id', 'restaurant_order_items', ['order_id'])
    
    # Restaurant tables by hotel
    op.create_index('ix_restaurant_tables_hotel_id', 'restaurant_tables', ['hotel_id'])


    # ============================================
    # ACCOUNTING
    # ============================================
    
    # Journal entries by date
    op.create_index('ix_journal_entries_date', 'journal_entries', ['date'])
    
    # Journal entries by hotel
    op.create_index('ix_journal_entries_hotel_id', 'journal_entries', ['hotel_id'])
    
    # Journal lines by entry
    op.create_index('ix_journal_lines_entry_id', 'journal_lines', ['journal_entry_id'])
    
    # Journal lines by account
    op.create_index('ix_journal_lines_account_id', 'journal_lines', ['account_id'])
    
    # Chart of accounts by hotel
    op.create_index('ix_chart_of_accounts_hotel_id', 'chart_of_accounts', ['hotel_id'])
    
    # Account type filtering
    op.create_index('ix_chart_of_accounts_type', 'chart_of_accounts', ['type'])


    # ============================================
    # NOTIFICATIONS
    # ============================================
    
    # User notifications
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    
    # Unread notifications
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
    
    # Recent notifications
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])


def downgrade():
    # Drop all indexes in reverse order
    
    # Notifications
    op.drop_index('ix_notifications_created_at', 'notifications')
    op.drop_index('ix_notifications_is_read', 'notifications')
    op.drop_index('ix_notifications_user_id', 'notifications')
    
    # Accounting
    op.drop_index('ix_chart_of_accounts_type', 'chart_of_accounts')
    op.drop_index('ix_chart_of_accounts_hotel_id', 'chart_of_accounts')
    op.drop_index('ix_journal_lines_account_id', 'journal_lines')
    op.drop_index('ix_journal_lines_entry_id', 'journal_lines')
    op.drop_index('ix_journal_entries_hotel_id', 'journal_entries')
    op.drop_index('ix_journal_entries_date', 'journal_entries')
    
    # Restaurant
    op.drop_index('ix_restaurant_tables_hotel_id', 'restaurant_tables')
    op.drop_index('ix_restaurant_order_items_order_id', 'restaurant_order_items')
    op.drop_index('ix_restaurant_orders_status', 'restaurant_orders')
    op.drop_index('ix_restaurant_orders_table_id', 'restaurant_orders')
    op.drop_index('ix_menu_items_hotel_id', 'menu_items')
    op.drop_index('ix_menu_items_is_available', 'menu_items')
    op.drop_index('ix_menu_items_category_id', 'menu_items')
    op.drop_index('ix_menu_categories_hotel_id', 'menu_categories')
    
    # Invoices & Payments
    op.drop_index('ix_payments_created_at', 'payments')
    op.drop_index('ix_payments_invoice_id', 'payments')
    op.drop_index('ix_invoices_status', 'invoices')
    op.drop_index('ix_invoices_booking_id', 'invoices')
    
    # Rooms
    op.drop_index('ix_room_types_name', 'room_types')
    op.drop_index('ix_room_types_hotel_id', 'room_types')
    op.drop_index('ix_rooms_hotel_id', 'rooms')
    op.drop_index('ix_rooms_status', 'rooms')
    op.drop_index('ix_rooms_room_number', 'rooms')
    op.drop_index('ix_rooms_room_type_id', 'rooms')
    
    # Guests
    op.drop_index('ix_guests_hotel_id', 'guests')
    op.drop_index('ix_guests_email', 'guests')
    op.drop_index('ix_guests_phone', 'guests')
    op.drop_index('ix_guests_name', 'guests')
    
    # Bookings
    op.drop_index('ix_bookings_created_at', 'bookings')
    op.drop_index('ix_bookings_reference', 'bookings')
    op.drop_index('ix_bookings_hotel_id', 'bookings')
    op.drop_index('ix_bookings_status', 'bookings')
    op.drop_index('ix_bookings_room_dates', 'bookings')
    op.drop_index('ix_bookings_check_out', 'bookings')
    op.drop_index('ix_bookings_check_in', 'bookings')
    op.drop_index('ix_bookings_room_id', 'bookings')
    op.drop_index('ix_bookings_guest_id', 'bookings')
    
    # Hotels
    op.drop_index('ix_hotels_name', 'hotels')
    op.drop_index('ix_hotels_owner_id', 'hotels')
    
    # Users
    try:
        op.drop_index('ix_users_last_login_at', 'users')
    except:
        pass
    try:
        op.drop_index('ix_users_reset_token', 'users')
    except:
        pass
    op.drop_index('ix_users_role', 'users')
    op.drop_index('ix_users_hotel_id', 'users')
    op.drop_index('ix_users_email', 'users')
