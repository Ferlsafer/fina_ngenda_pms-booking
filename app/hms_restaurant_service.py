# =============================================================================
# RESTAURANT SERVICE MODULE
# =============================================================================
"""
Restaurant Business Logic Service

This module contains all restaurant business logic, separated from Flask routes.
It provides:
- Payment processing and tracking
- Accounting integration
- Inventory deduction
- Table reservations
- Order modifiers

All methods are designed to be non-breaking and backward compatible.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from app import db
from app.models import (
    RestaurantOrder, RestaurantOrderItem, OrderModifier, MenuItem, MenuItemInventory,
    InventoryItem, RestaurantTable, TableReservation, MenuCategory,
    JournalEntry, JournalLine, ChartOfAccount, User, Booking
)

# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================

PAYMENT_STATUSES = ['unpaid', 'partial', 'paid', 'refunded']
PAYMENT_METHODS = ['cash', 'card', 'mobile', 'room_charge']
ORDER_STATUSES = ['pending', 'preparing', 'ready', 'completed', 'cancelled']
RESERVATION_STATUSES = ['confirmed', 'seated', 'completed', 'cancelled', 'no_show']

# Tax rate (can be made configurable per hotel)
DEFAULT_TAX_RATE = Decimal('0.18')  # 18% VAT


# =============================================================================
# PAYMENT SERVICE
# =============================================================================

class RestaurantPaymentService:
    """
    Handles payment processing for restaurant orders.
    """
    
    @staticmethod
    def calculate_balance(order: RestaurantOrder) -> Decimal:
        """
        Calculate balance due for an order.
        
        Args:
            order: RestaurantOrder object
            
        Returns:
            Balance due amount
        """
        total = Decimal(str(order.total))
        discount = Decimal(str(order.discount_amount or 0))
        paid = Decimal(str(order.paid_amount or 0))
        tip = Decimal(str(order.tip_amount or 0))
        
        balance = total - discount + tip - paid
        return max(Decimal('0'), balance)
    
    @staticmethod
    def process_payment(order: RestaurantOrder, amount: Decimal,
                       payment_method: str, user_id: int = None) -> Tuple[bool, str]:
        """
        Process a payment for an order.
        
        Args:
            order: RestaurantOrder object
            amount: Payment amount
            payment_method: cash, card, mobile, room_charge
            user_id: User processing the payment
            
        Returns:
            Tuple of (success, message)
        """
        if amount <= 0:
            return False, "Payment amount must be positive"
        
        if payment_method not in PAYMENT_METHODS:
            return False, f"Invalid payment method: {payment_method}"
        
        # Calculate new paid amount
        current_paid = Decimal(str(order.paid_amount or 0))
        new_paid = current_paid + amount
        
        # Update order
        order.paid_amount = new_paid
        order.payment_method = payment_method
        
        # Calculate new balance
        balance = RestaurantPaymentService.calculate_balance(order)
        order.balance_due = balance
        
        # Update payment status
        if balance <= 0:
            order.payment_status = 'paid'
        elif new_paid > 0:
            order.payment_status = 'partial'
        
        # Create accounting entry
        RestaurantAccountingService.create_payment_entry(order, amount, payment_method)
        
        return True, f"Payment of {amount:.2f} processed. Balance: {balance:.2f}"
    
    @staticmethod
    def apply_discount(order: RestaurantOrder, discount_amount: Decimal,
                      reason: str = None, user_id: int = None) -> Tuple[bool, str]:
        """
        Apply discount to an order.
        
        Args:
            order: RestaurantOrder object
            discount_amount: Discount amount
            reason: Reason for discount
            user_id: User applying discount
            
        Returns:
            Tuple of (success, message)
        """
        if discount_amount < 0:
            return False, "Discount cannot be negative"
        
        total = Decimal(str(order.total))
        if discount_amount > total:
            return False, "Discount cannot exceed order total"
        
        order.discount_amount = discount_amount
        
        # Recalculate balance
        balance = RestaurantPaymentService.calculate_balance(order)
        order.balance_due = balance
        
        # Update payment status
        if balance <= 0:
            order.payment_status = 'paid'
        
        return True, f"Discount of {discount_amount:.2f} applied. Balance: {balance:.2f}"
    
    @staticmethod
    def charge_to_room(order: RestaurantOrder, booking_id: int,
                      user_id: int = None) -> Tuple[bool, str]:
        """
        Charge order to hotel room (booking).
        
        Args:
            order: RestaurantOrder object
            booking_id: Booking to charge
            user_id: User processing the charge
            
        Returns:
            Tuple of (success, message)
        """
        booking = Booking.query.get(booking_id)
        if not booking:
            return False, "Booking not found"
        
        if booking.hotel_id != order.hotel_id:
            return False, "Booking does not belong to this hotel"
        
        # Update order
        order.booking_id = booking_id
        order.payment_method = 'room_charge'
        order.paid_amount = order.total
        order.balance_due = Decimal('0')
        order.payment_status = 'paid'
        
        # Create accounting entry
        RestaurantAccountingService.create_payment_entry(
            order, order.total, 'room_charge',
            description=f"Charged to booking {booking.booking_reference}"
        )
        
        return True, f"Order charged to room {booking.room.room_number if booking.room else 'N/A'}"


# =============================================================================
# ACCOUNTING SERVICE
# =============================================================================

class RestaurantAccountingService:
    """
    Handles accounting integration for restaurant orders.
    """
    
    @staticmethod
    def create_order_entry(order: RestaurantOrder):
        """
        Create journal entry for a restaurant order.
        
        Debit: Accounts Receivable (or Cash if paid)
        Credit: Revenue
        Credit: Tax Payable
        
        Args:
            order: RestaurantOrder object
        """
        subtotal = Decimal(str(order.subtotal or 0))
        tax = Decimal(str(order.tax or 0))
        total = Decimal(str(order.total or 0))
        
        if total <= 0:
            return
        
        # Get or create accounts
        revenue_account = RestaurantAccountingService.get_or_create_account(
            order.hotel_id, 'Revenue', 'Restaurant Revenue'
        )
        
        tax_account = RestaurantAccountingService.get_or_create_account(
            order.hotel_id, 'Liability', 'Tax Payable'
        )
        
        # Determine debit account based on payment
        if order.payment_status == 'paid':
            debit_account = RestaurantAccountingService.get_or_create_account(
                order.hotel_id, 'Asset', 'Cash'
            )
        else:
            debit_account = RestaurantAccountingService.get_or_create_account(
                order.hotel_id, 'Asset', 'Accounts Receivable'
            )

        # Create journal entry
        journal = JournalEntry(
            hotel_id=order.hotel_id,
            reference=f"REST-ORDER-{order.id}",
            date=date.today()
        )

        db.session.add(journal)
        db.session.flush()

        # Debit line
        debit_line = JournalLine(
            journal_entry_id=journal.id,
            account_id=debit_account.id,
            debit=total,
            credit=0
        )

        # Credit revenue line
        revenue_line = JournalLine(
            journal_entry_id=journal.id,
            account_id=revenue_account.id,
            debit=0,
            credit=subtotal
        )

        # Credit tax line
        tax_line = JournalLine(
            journal_entry_id=journal.id,
            account_id=tax_account.id,
            debit=0,
            credit=tax
        )

        db.session.add(debit_line)
        db.session.add(revenue_line)
        db.session.add(tax_line)
    
    @staticmethod
    def create_payment_entry(order: RestaurantOrder, amount: Decimal,
                            payment_method: str, description: str = None):
        """
        Create journal entry for a payment.
        
        Debit: Cash (or Accounts Receivable for room charge)
        Credit: Accounts Receivable
        
        Args:
            order: RestaurantOrder object
            amount: Payment amount
            payment_method: Payment method
            description: Optional description
        """
        if amount <= 0:
            return
        
        # Get accounts
        if payment_method == 'room_charge':
            debit_account = RestaurantAccountingService.get_or_create_account(
                order.hotel_id, 'Asset', 'Rooms Receivable'
            )
        else:
            debit_account = RestaurantAccountingService.get_or_create_account(
                order.hotel_id, 'Asset', 'Cash'
            )
        
        credit_account = RestaurantAccountingService.get_or_create_account(
            order.hotel_id, 'Asset', 'Accounts Receivable'
        )
        
        # Create journal entry
        journal = JournalEntry(
            hotel_id=order.hotel_id,
            reference=f"REST-PAY-{order.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            date=date.today(),
            description=description or f"Payment for order {order.id} via {payment_method}"
        )
        
        db.session.add(journal)
        db.session.flush()
        
        # Debit line (Cash/Rooms Receivable)
        debit_line = JournalLine(
            journal_entry_id=journal.id,
            account_id=debit_account.id,
            debit=amount,
            credit=0,
            reference=f"Payment {payment_method}"
        )
        
        # Credit line (Accounts Receivable)
        credit_line = JournalLine(
            journal_entry_id=journal.id,
            account_id=credit_account.id,
            debit=0,
            credit=amount,
            reference=f"Payment {payment_method}"
        )
        
        db.session.add(debit_line)
        db.session.add(credit_line)
    
    @staticmethod
    def get_or_create_account(hotel_id: int, account_type: str, name: str):
        """
        Get or create a chart of account.
        
        Args:
            hotel_id: Hotel ID
            account_type: Account type (Asset, Liability, Revenue, Expense)
            name: Account name
            
        Returns:
            ChartOfAccount object
        """
        account = ChartOfAccount.query.filter_by(
            hotel_id=hotel_id,
            type=account_type,
            name=name
        ).first()
        
        if not account:
            account = ChartOfAccount(
                hotel_id=hotel_id,
                name=name,
                type=account_type
            )
            db.session.add(account)
            db.session.flush()
        
        return account
    
    @staticmethod
    def post_daily_summary(hotel_id: int, summary_date: date = None):
        """
        Post daily sales summary to accounting.
        
        Args:
            hotel_id: Hotel ID
            summary_date: Date to summarize (default: today)
        """
        if summary_date is None:
            summary_date = date.today()
        
        # Get all completed orders for the day
        orders = RestaurantOrder.query.filter(
            RestaurantOrder.hotel_id == hotel_id,
            RestaurantOrder.status == 'completed',
            db.func.date(RestaurantOrder.completed_at) == summary_date
        ).all()
        
        if not orders:
            return
        
        # Calculate totals
        total_orders = len(orders)
        total_revenue = sum(Decimal(str(o.subtotal or 0)) for o in orders)
        total_tax = sum(Decimal(str(o.tax or 0)) for o in orders)
        total_discount = sum(Decimal(str(o.discount_amount or 0)) for o in orders)
        total_tip = sum(Decimal(str(o.tip_amount or 0)) for o in orders)
        
        # Create summary journal entry
        revenue_account = RestaurantAccountingService.get_or_create_account(
            hotel_id, 'Revenue', 'Restaurant Revenue'
        )
        
        tax_account = RestaurantAccountingService.get_or_create_account(
            hotel_id, 'Liability', 'Tax Payable'
        )
        
        cash_account = RestaurantAccountingService.get_or_create_account(
            hotel_id, 'Asset', 'Cash'
        )
        
        journal = JournalEntry(
            hotel_id=hotel_id,
            reference=f"REST-DAILY-{summary_date.strftime('%Y%m%d')}",
            date=summary_date,
            description=f"Daily restaurant summary - {total_orders} orders"
        )
        
        db.session.add(journal)
        db.session.flush()
        
        # Debit: Cash (total revenue + tax + tip - discount)
        total_debit = total_revenue + total_tax + total_tip - total_discount
        debit_line = JournalLine(
            journal_entry_id=journal.id,
            account_id=cash_account.id,
            debit=total_debit,
            credit=0,
            reference=f"Daily summary {summary_date}"
        )
        
        # Credit: Revenue
        revenue_line = JournalLine(
            journal_entry_id=journal.id,
            account_id=revenue_account.id,
            debit=0,
            credit=total_revenue,
            reference=f"Daily revenue {summary_date}"
        )
        
        # Credit: Tax Payable
        tax_line = JournalLine(
            journal_entry_id=journal.id,
            account_id=tax_account.id,
            debit=0,
            credit=total_tax,
            reference=f"Daily tax {summary_date}"
        )
        
        db.session.add(debit_line)
        db.session.add(revenue_line)
        db.session.add(tax_line)


# =============================================================================
# INVENTORY SERVICE
# =============================================================================

class RestaurantInventoryService:
    """
    Handles inventory integration for restaurant orders.
    """
    
    @staticmethod
    def deduct_inventory_for_order(order: RestaurantOrder) -> Tuple[bool, str]:
        """
        Deduct inventory when order is completed.
        
        Args:
            order: RestaurantOrder object
            
        Returns:
            Tuple of (success, message)
        """
        if order.status != 'completed':
            return False, "Can only deduct inventory for completed orders"
        
        alerts = []
        
        for order_item in order.items:
            menu_item = order_item.menu_item
            
            # Get linked inventory items
            inv_links = MenuItemInventory.query.filter_by(
                menu_item_id=menu_item.id
            ).all()
            
            for inv_link in inv_links:
                inv_item = inv_link.inventory_item
                quantity_to_deduct = float(inv_link.quantity_needed) * order_item.quantity
                
                # Deduct from stock
                if inv_item.current_stock:
                    inv_item.current_stock = Decimal(str(inv_item.current_stock)) - Decimal(str(quantity_to_deduct))
                else:
                    inv_item.current_stock = Decimal(str(-quantity_to_deduct))
                
                # Check if below reorder level
                if inv_item.current_stock < inv_item.reorder_level:
                    alerts.append(f"Low stock alert: {inv_item.name} ({inv_item.current_stock} {inv_item.unit} remaining)")
        
        if alerts:
            return True, "Inventory deducted. " + "; ".join(alerts)
        return True, "Inventory deducted successfully"
    
    @staticmethod
    def restore_inventory_for_cancelled_order(order: RestaurantOrder):
        """
        Restore inventory when order is cancelled.
        
        Args:
            order: RestaurantOrder object
        """
        for order_item in order.items:
            menu_item = order_item.menu_item
            
            # Get linked inventory items
            inv_links = MenuItemInventory.query.filter_by(
                menu_item_id=menu_item.id
            ).all()
            
            for inv_link in inv_links:
                inv_item = inv_link.inventory_item
                quantity_to_restore = float(inv_link.quantity_needed) * order_item.quantity
                
                # Restore to stock
                if inv_item.current_stock:
                    inv_item.current_stock = Decimal(str(inv_item.current_stock)) + Decimal(str(quantity_to_restore))
                else:
                    inv_item.current_stock = Decimal(str(quantity_to_restore))


# =============================================================================
# TABLE RESERVATION SERVICE
# =============================================================================

class TableReservationService:
    """
    Handles table reservations.
    """
    
    @staticmethod
    def create_reservation(hotel_id: int, guest_name: str, party_size: int,
                          reservation_time: datetime, table_id: int = None,
                          booking_id: int = None, guest_phone: str = None,
                          guest_email: str = None, special_requests: str = None,
                          duration_minutes: int = 90, created_by: int = None) -> Tuple[Optional[TableReservation], str]:
        """
        Create a table reservation.
        
        Args:
            hotel_id: Hotel ID
            guest_name: Guest name
            party_size: Number of guests
            reservation_time: Reservation datetime
            table_id: Optional specific table
            booking_id: Optional hotel booking link
            guest_phone: Guest phone
            guest_email: Guest email
            special_requests: Special requests
            duration_minutes: Reservation duration
            created_by: User creating the reservation
            
        Returns:
            Tuple of (TableReservation, error_message)
        """
        # Validate party size
        if party_size <= 0:
            return None, "Party size must be positive"
        
        # Check if table is available
        if table_id:
            table = RestaurantTable.query.get(table_id)
            if not table or table.hotel_id != hotel_id:
                return None, "Invalid table"
            
            # Check for conflicts
            conflict = TableReservationService.check_table_conflict(
                table_id, reservation_time, duration_minutes
            )
            if conflict:
                return None, f"Table {table.table_number} is not available at that time"
        
        # Create reservation
        reservation = TableReservation(
            hotel_id=hotel_id,
            table_id=table_id,
            booking_id=booking_id,
            guest_name=guest_name,
            guest_phone=guest_phone,
            guest_email=guest_email,
            party_size=party_size,
            reservation_time=reservation_time,
            duration_minutes=duration_minutes,
            special_requests=special_requests,
            created_by=created_by,
            status='confirmed'
        )
        
        db.session.add(reservation)
        
        return reservation, "Reservation created successfully"
    
    @staticmethod
    def check_table_conflict(table_id: int, reservation_time: datetime,
                            duration_minutes: int) -> Optional[TableReservation]:
        """
        Check if a table has a conflicting reservation.
        
        Args:
            table_id: Table ID
            reservation_time: Desired reservation time
            duration_minutes: Duration in minutes
            
        Returns:
            Conflicting reservation or None
        """
        end_time = reservation_time + timedelta(minutes=duration_minutes)
        
        conflict = TableReservation.query.filter(
            TableReservation.table_id == table_id,
            TableReservation.status.in_(['confirmed', 'seated']),
            TableReservation.reservation_time < end_time,
            db.func.datetime(TableReservation.reservation_time) + db.func.strftime('%M seconds', TableReservation.duration_minutes * 60) > reservation_time
        ).first()
        
        return conflict
    
    @staticmethod
    def get_available_tables(hotel_id: int, reservation_time: datetime,
                            party_size: int, duration_minutes: int = 90) -> List[RestaurantTable]:
        """
        Get available tables for a reservation.
        
        Args:
            hotel_id: Hotel ID
            reservation_time: Desired time
            party_size: Number of guests
            duration_minutes: Duration
            
        Returns:
            List of available tables
        """
        # Get tables with sufficient capacity
        tables = RestaurantTable.query.filter(
            RestaurantTable.hotel_id == hotel_id,
            RestaurantTable.capacity >= party_size
        ).all()
        
        available = []
        for table in tables:
            conflict = TableReservationService.check_table_conflict(
                table.id, reservation_time, duration_minutes
            )
            if not conflict:
                available.append(table)
        
        return available


# =============================================================================
# ANALYTICS SERVICE (Week 3)
# =============================================================================

class RestaurantAnalyticsService:
    """
    Provides restaurant analytics and reporting.
    """
    
    @staticmethod
    def get_daily_summary(hotel_id: int, summary_date: date = None) -> Dict[str, Any]:
        """
        Get daily sales summary.
        
        Args:
            hotel_id: Hotel ID
            summary_date: Date to summarize
            
        Returns:
            Summary statistics dict
        """
        if summary_date is None:
            summary_date = date.today()
        
        # Get all orders for the day
        start = datetime.combine(summary_date, datetime.min.time())
        end = datetime.combine(summary_date, datetime.max.time())
        
        orders = RestaurantOrder.query.filter(
            RestaurantOrder.hotel_id == hotel_id,
            RestaurantOrder.created_at >= start,
            RestaurantOrder.created_at <= end
        ).all()
        
        if not orders:
            return {
                'total_orders': 0,
                'total_revenue': 0,
                'average_order_value': 0,
                'pending_orders': 0,
                'completed_orders': 0
            }
        
        # Calculate metrics
        total_revenue = sum(Decimal(str(o.subtotal or 0)) for o in orders)
        completed_orders = [o for o in orders if o.status == 'completed']
        pending_orders = [o for o in orders if o.status in ['pending', 'preparing']]
        
        return {
            'total_orders': len(orders),
            'total_revenue': float(total_revenue),
            'average_order_value': float(total_revenue / len(orders)) if orders else 0,
            'pending_orders': len(pending_orders),
            'completed_orders': len(completed_orders),
            'total_tax': float(sum(Decimal(str(o.tax or 0)) for o in orders)),
            'total_discount': float(sum(Decimal(str(o.discount_amount or 0)) for o in orders)),
            'total_tips': float(sum(Decimal(str(o.tip_amount or 0)) for o in orders))
        }
    
    @staticmethod
    def get_menu_performance(hotel_id: int, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Get menu item performance analysis (Menu Engineering).
        
        Args:
            hotel_id: Hotel ID
            start_date: Start of period
            end_date: End of period
            
        Returns:
            List of menu item performance data
        """
        # Get all menu items
        items = MenuItem.query.filter_by(
            hotel_id=hotel_id,
            deleted_at=None
        ).all()
        
        start = datetime.combine(start_date, datetime.min.time())
        end = datetime.combine(end_date, datetime.max.time())
        
        # Get total items sold for popularity calculation
        total_items_sold = 0
        for item in items:
            order_items = RestaurantOrderItem.query.join(RestaurantOrder).filter(
                RestaurantOrder.hotel_id == hotel_id,
                RestaurantOrder.created_at >= start,
                RestaurantOrder.created_at <= end,
                RestaurantOrderItem.menu_item_id == item.id
            ).all()
            total_items_sold += sum(oi.quantity for oi in order_items)
        
        analysis = []
        for item in items:
            # Get sales data
            order_items = RestaurantOrderItem.query.join(RestaurantOrder).filter(
                RestaurantOrder.hotel_id == hotel_id,
                RestaurantOrder.created_at >= start,
                RestaurantOrder.created_at <= end,
                RestaurantOrderItem.menu_item_id == item.id
            ).all()
            
            quantity_sold = sum(oi.quantity for oi in order_items)
            
            # Calculate metrics
            profit_margin = 0
            if item.price and item.cost:
                profit_margin = (Decimal(str(item.price)) - Decimal(str(item.cost))) / Decimal(str(item.price))
            
            popularity = quantity_sold / total_items_sold if total_items_sold > 0 else 0
            
            # Classify item
            if profit_margin > Decimal('0.7') and popularity > Decimal('0.1'):
                classification = 'STAR'
                action = 'Maintain quality, promote heavily'
            elif profit_margin > Decimal('0.7'):
                classification = 'PUZZLE'
                action = 'Promote more, rename or reposition'
            elif popularity > Decimal('0.1'):
                classification = 'PLOWHORSE'
                action = 'Increase price, reduce portion'
            else:
                classification = 'DOG'
                action = 'Remove from menu or reengineer'
            
            analysis.append({
                'item_id': item.id,
                'item_name': item.name,
                'category': item.category.name if item.category else 'N/A',
                'price': float(item.price) if item.price else 0,
                'cost': float(item.cost) if item.cost else 0,
                'profit_margin': float(profit_margin),
                'quantity_sold': quantity_sold,
                'popularity': float(popularity),
                'classification': classification,
                'recommended_action': action
            })
        
        # Sort by profit margin
        analysis.sort(key=lambda x: x['profit_margin'], reverse=True)
        
        return analysis


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_order_total(items: List[dict], tax_rate: Decimal = DEFAULT_TAX_RATE,
                         discount: Decimal = Decimal('0')) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Calculate order totals.
    
    Args:
        items: List of dicts with 'price' and 'quantity'
        tax_rate: Tax rate
        discount: Discount amount
        
    Returns:
        Tuple of (subtotal, tax, total)
    """
    subtotal = sum(Decimal(str(item['price'])) * item['quantity'] for item in items)
    
    # Add modifier prices
    for item in items:
        if 'modifiers' in item:
            for mod in item['modifiers']:
                if 'additional_price' in mod:
                    subtotal += Decimal(str(mod['additional_price'])) * item['quantity']
    
    tax = subtotal * tax_rate
    total = subtotal + tax - discount
    
    return subtotal, tax, total
