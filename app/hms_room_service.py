# =============================================================================
# ROOM MANAGEMENT SERVICE MODULE
# =============================================================================
"""
Room Management Business Logic Service

This module contains all room management business logic, separated from Flask routes.
It provides:
- Room status transition validation (safety first)
- Cross-module conflict detection
- Integration with Housekeeping, Booking, Accounting
- Revenue tracking
- Automatic notifications

All methods are designed to be non-breaking and backward compatible.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from app import db
from app.models import (
    Room, RoomType, Booking, HousekeepingTask, MaintenanceIssue,
    RoomServiceOrder, Notification, JournalEntry, JournalLine,
    ChartOfAccount, RoomStatusHistory
)
from app.hms_housekeeping_service import RoomStatusManager

# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================

# Room status transition rules (SAFETY FIRST)
# Format: current_status: [allowed_next_statuses]
VALID_ROOM_TRANSITIONS = {
    'Vacant': ['Dirty', 'Reserved', 'Maintenance', 'Occupied'],
    'Dirty': ['Vacant', 'Maintenance'],
    'Occupied': ['Dirty', 'Maintenance'],
    'Reserved': ['Occupied', 'Vacant', 'Dirty', 'Maintenance'],
    'Maintenance': ['Vacant', 'Dirty']
}

# Blocked transitions with reasons
BLOCKED_TRANSITIONS = {
    ('Occupied', 'Vacant'): "Cannot mark occupied room as vacant. Must check out guest first.",
    ('Dirty', 'Occupied'): "Cannot assign guest to dirty room. Must clean first.",
    ('Dirty', 'Reserved'): "Cannot reserve dirty room. Must clean first.",
}

# Revenue loss account types
REVENUE_LOSS_ACCOUNTS = {
    'maintenance': 'Revenue Loss - Maintenance',
    'ooo': 'Revenue Loss - Out of Order',
    'comp': 'Complimentary Room Loss'
}


# =============================================================================
# ROOM STATUS VALIDATOR
# =============================================================================

class RoomStatusValidator:
    """
    Validates room status changes with comprehensive checks.
    Prevents unsafe transitions and conflicts.
    """
    
    @staticmethod
    def validate_transition(current_status: str, new_status: str) -> Tuple[bool, str]:
        """
        Validate if a room status transition is allowed.
        
        Args:
            current_status: Current room status
            new_status: Desired new status
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if transition is explicitly blocked
        if (current_status, new_status) in BLOCKED_TRANSITIONS:
            return False, BLOCKED_TRANSITIONS[(current_status, new_status)]
        
        # Check if transition is in allowed list
        allowed = VALID_ROOM_TRANSITIONS.get(current_status, [])
        
        if new_status not in allowed:
            return False, f"Cannot transition from {current_status} to {new_status}"
        
        return True, ""
    
    @staticmethod
    def check_booking_conflicts(room: Room, new_status: str) -> Tuple[bool, str]:
        """
        Check if status change conflicts with bookings.
        
        Args:
            room: Room object
            new_status: New status to set
            
        Returns:
            Tuple of (no_conflict, error_message)
        """
        # Check for current/upcoming bookings when marking OOO
        if new_status == 'Maintenance':
            upcoming = Booking.query.filter(
                Booking.room_id == room.id,
                Booking.status == 'Reserved',
                Booking.check_in_date <= date.today() + timedelta(days=7),
                Booking.check_out_date >= date.today()
            ).first()
            
            if upcoming:
                days_until = (upcoming.check_in_date - date.today()).days
                return False, f"Room has upcoming booking in {days_until} days (Guest: {upcoming.guest_name})"
        
        # Check if trying to mark occupied room with active booking as dirty
        if new_status == 'Dirty' and room.status == 'Occupied':
            # This is actually OK - guest checking out
            pass
        
        return True, ""
    
    @staticmethod
    def check_housekeeping_conflicts(room: Room, new_status: str) -> Tuple[bool, str]:
        """
        Check if status change conflicts with housekeeping tasks.
        
        Args:
            room: Room object
            new_status: New status to set
            
        Returns:
            Tuple of (no_conflict, error_message)
        """
        # Don't mark vacant if cleaning in progress
        if new_status == 'Vacant':
            in_progress = HousekeepingTask.query.filter(
                HousekeepingTask.room_id == room.id,
                HousekeepingTask.status == 'in_progress'
            ).first()
            
            if in_progress:
                return False, "Cleaning task in progress. Wait for completion."
        
        return True, ""
    
    @staticmethod
    def check_room_service_conflicts(room: Room, new_status: str) -> Tuple[bool, str]:
        """
        Check if status change conflicts with room service orders.
        
        Args:
            room: Room object
            new_status: New status to set
            
        Returns:
            Tuple of (no_conflict, error_message)
        """
        # Don't mark vacant with pending orders
        if new_status == 'Vacant':
            pending = RoomServiceOrder.query.filter(
                RoomServiceOrder.room_id == room.id,
                RoomServiceOrder.status.in_(['pending', 'preparing', 'ready', 'out_for_delivery'])
            ).first()
            
            if pending:
                return False, f"Pending room service order #{pending.id}. Complete or cancel first."
        
        return True, ""
    
    @staticmethod
    def check_maintenance_conflicts(room: Room, new_status: str) -> Tuple[bool, str]:
        """
        Check if status change conflicts with maintenance issues.
        
        Args:
            room: Room object
            new_status: New status to set
            
        Returns:
            Tuple of (no_conflict, error_message)
        """
        # Don't mark occupied/vacant with critical maintenance open
        if new_status in ['Vacant', 'Occupied']:
            critical = MaintenanceIssue.query.filter(
                MaintenanceIssue.room_id == room.id,
                MaintenanceIssue.status.in_(['reported', 'in_progress']),
                MaintenanceIssue.priority == 'critical'
            ).first()
            
            if critical:
                return False, f"Critical maintenance issue open: {critical.issue_type}"
        
        return True, ""
    
    @staticmethod
    def comprehensive_validate(room: Room, new_status: str) -> Tuple[bool, str]:
        """
        Run all validation checks.
        
        Args:
            room: Room object
            new_status: New status to set
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # 1. Validate transition rules
        valid, error = RoomStatusValidator.validate_transition(room.status, new_status)
        if not valid:
            return False, error
        
        # 2. Check booking conflicts
        valid, error = RoomStatusValidator.check_booking_conflicts(room, new_status)
        if not valid:
            return False, error
        
        # 3. Check housekeeping conflicts
        valid, error = RoomStatusValidator.check_housekeeping_conflicts(room, new_status)
        if not valid:
            return False, error
        
        # 4. Check room service conflicts
        valid, error = RoomStatusValidator.check_room_service_conflicts(room, new_status)
        if not valid:
            return False, error
        
        # 5. Check maintenance conflicts
        valid, error = RoomStatusValidator.check_maintenance_conflicts(room, new_status)
        if not valid:
            return False, error
        
        return True, "All validations passed"


# =============================================================================
# ROOM REVENUE TRACKER
# =============================================================================

class RoomRevenueTracker:
    """
    Tracks revenue impact of room status changes.
    Integrates with Accounting module.
    """
    
    @staticmethod
    def calculate_daily_revenue_loss(room: Room) -> Decimal:
        """
        Calculate expected daily revenue loss for room.
        
        Args:
            room: Room object
            
        Returns:
            Expected daily revenue loss
        """
        if not room.room_type:
            return Decimal('0')
        
        # Base rate
        base_rate = Decimal(str(room.room_type.base_price))
        
        # Adjust for historical occupancy (simplified - could be more sophisticated)
        # Assume 70% average occupancy
        expected_daily_revenue = base_rate * Decimal('0.7')
        
        return expected_daily_revenue.quantize(Decimal('0.01'))
    
    @staticmethod
    def start_revenue_loss_tracking(room: Room, reason: str,
                                   user_id: Optional[int] = None) -> Optional[int]:
        """
        Start tracking revenue loss when room goes OOO/Maintenance.
        
        Args:
            room: Room object
            reason: Reason for OOO
            user_id: User marking OOO
            
        Returns:
            Tracking record ID or None
        """
        # For now, we just log to journal
        # In future, could create dedicated tracking table
        
        daily_loss = RoomRevenueTracker.calculate_daily_revenue_loss(room)
        
        # Create memorandum journal entry
        try:
            # Get revenue account
            revenue_account = ChartOfAccount.query.filter_by(
                hotel_id=room.hotel_id,
                type="Revenue",
                name="Room Revenue"
            ).first()
            
            if not revenue_account:
                return None
            
            # Create memo entry (not posted to GL, just for tracking)
            memo = JournalEntry(
                hotel_id=room.hotel_id,
                reference=f"OOO-ROOM-{room.id}-{date.today().strftime('%Y%m%d')}",
                date=date.today(),
                description=f"Room {room.room_number} out of order. Expected daily loss: {daily_loss}. Reason: {reason}"
            )
            
            db.session.add(memo)
            db.session.flush()
            
            return memo.id
            
        except Exception as e:
            # Don't fail the operation, just log error
            db.session.rollback()
            return None
    
    @staticmethod
    def stop_revenue_loss_tracking(room: Room, start_date: date,
                                  user_id: Optional[int] = None) -> Optional[Decimal]:
        """
        Stop tracking revenue loss and calculate total.
        
        Args:
            room: Room object
            start_date: When room went OOO
            user_id: User marking room available
            
        Returns:
            Total revenue loss or None
        """
        end_date = date.today()
        days_ooo = (end_date - start_date).days
        
        if days_ooo <= 0:
            return None
        
        daily_loss = RoomRevenueTracker.calculate_daily_revenue_loss(room)
        total_loss = daily_loss * days_ooo
        
        # Create memorandum journal entry
        try:
            revenue_account = ChartOfAccount.query.filter_by(
                hotel_id=room.hotel_id,
                type="Revenue",
                name="Room Revenue"
            ).first()
            
            if not revenue_account:
                return total_loss
            
            # Create memo entry
            memo = JournalEntry(
                hotel_id=room.hotel_id,
                reference=f"OOO-END-{room.id}-{end_date.strftime('%Y%m%d')}",
                date=end_date,
                description=f"Room {room.room_number} back in service. Total OOO days: {days_ooo}. Total revenue loss: {total_loss}"
            )
            
            db.session.add(memo)
            
            return total_loss
            
        except Exception as e:
            db.session.rollback()
            return total_loss


# =============================================================================
# ROOM NOTIFICATION SERVICE
# =============================================================================

class RoomNotificationService:
    """
    Sends notifications when room status changes.
    Notifies relevant departments automatically.
    """
    
    @staticmethod
    def notify_status_change(room: Room, old_status: str, new_status: str,
                            reason: str, user_id: Optional[int] = None):
        """
        Send notifications to relevant departments.
        
        Args:
            room: Room object
            old_status: Previous status
            new_status: New status
            reason: Reason for change
            user_id: User making the change
        """
        notifications = []
        
        # Housekeeping notifications
        if new_status == 'Dirty':
            notifications.append({
                'department': 'housekeeping',
                'title': f'Room {room.room_number} Needs Cleaning',
                'message': f'Room is now dirty. Reason: {reason}',
                'color': 'warning',
                'type': 'housekeeping'
            })
        
        elif new_status == 'Vacant' and old_status == 'Dirty':
            notifications.append({
                'department': 'housekeeping',
                'title': f'Room {room.room_number} Cleaned',
                'message': f'Room cleaning completed. Ready for inspection.',
                'color': 'success',
                'type': 'housekeeping'
            })
        
        # Front desk notifications
        if new_status == 'Maintenance':
            notifications.append({
                'department': 'front_desk',
                'title': f'Room {room.room_number} Out of Order',
                'message': f'Room is now OOO. Reason: {reason}. Cannot sell until fixed.',
                'color': 'danger',
                'type': 'operational'
            })
        
        elif new_status == 'Vacant' and old_status == 'Maintenance':
            notifications.append({
                'department': 'front_desk',
                'title': f'Room {room.room_number} Available',
                'message': f'Room is back in service. Ready for check-in.',
                'color': 'success',
                'type': 'operational'
            })
        
        elif new_status == 'Vacant':
            notifications.append({
                'department': 'front_desk',
                'title': f'Room {room.room_number} Ready for Check-in',
                'message': f'Room is clean and vacant.',
                'color': 'success',
                'type': 'operational'
            })
        
        # Management notifications (for critical changes)
        if new_status == 'Maintenance':
            notifications.append({
                'department': 'management',
                'title': f'Revenue Alert: Room {room.room_number} OOO',
                'message': f'Room out of order. Expected daily revenue loss: {RoomRevenueTracker.calculate_daily_revenue_loss(room)}',
                'color': 'warning',
                'type': 'financial'
            })
        
        # Create notifications
        for notif_data in notifications:
            try:
                # Get a user to notify (use the user who made the change, or get first user from department)
                notif_user_id = user_id
                if not notif_user_id:
                    # Fallback: get first user from hotel
                    from app.models import User
                    first_user = User.query.filter_by(hotel_id=room.hotel_id).first()
                    if first_user:
                        notif_user_id = first_user.id
                
                if notif_user_id:
                    notif = Notification(
                        user_id=notif_user_id,
                        hotel_id=room.hotel_id,
                        title=notif_data['title'],
                        message=notif_data['message'],
                        color=notif_data['color'],
                        type=notif_data['type'],
                        link=f"/hms/rooms"
                    )
                    db.session.add(notif)
            except Exception as e:
                # Don't fail the operation for notification errors
                pass
        
        # Flush all notifications at once
        try:
            db.session.flush()
        except:
            db.session.rollback()


# =============================================================================
# MAIN ROOM MANAGEMENT SERVICE
# =============================================================================

class RoomManagementService:
    """
    Main room management service.
    Orchestrates all room operations with safety and integration.
    """
    
    @staticmethod
    def change_room_status(room: Room, new_status: str,
                          reason: str = "Manual status change",
                          user_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Safely change room status with full validation and integration.
        
        This is the SAFE alternative to: room.status = new_status
        
        Args:
            room: Room object
            new_status: New status to set
            reason: Reason for status change
            user_id: User making the change
            
        Returns:
            Tuple of (success, message)
        """
        # 1. Comprehensive validation
        valid, error = RoomStatusValidator.comprehensive_validate(room, new_status)
        if not valid:
            return False, f"Validation failed: {error}"
        
        # 2. Store old status for audit and notifications
        old_status = room.status
        
        # 3. Track revenue impact if going OOO
        if new_status == 'Maintenance' and old_status != 'Maintenance':
            RoomRevenueTracker.start_revenue_loss_tracking(
                room, reason, user_id
            )
        
        # 4. Stop revenue tracking if coming back from OOO
        if old_status == 'Maintenance' and new_status in ['Vacant', 'Dirty']:
            # Try to find when room went OOO (simplified - would need better tracking in production)
            RoomRevenueTracker.stop_revenue_loss_tracking(
                room, date.today() - timedelta(days=1), user_id
            )
        
        # 5. Update room status
        room.status = new_status
        
        # 6. Create audit trail
        history = RoomStatusHistory(
            hotel_id=room.hotel_id,
            room_id=room.id,
            old_status=old_status,
            new_status=new_status
        )
        db.session.add(history)
        
        # 7. Send notifications
        RoomNotificationService.notify_status_change(
            room, old_status, new_status, reason, user_id
        )
        
        # 8. Integration with Housekeeping (auto-create tasks)
        if new_status == 'Dirty' and old_status == 'Occupied':
            # Guest checked out - create cleaning task
            task = HousekeepingTask(
                hotel_id=room.hotel_id,
                room_id=room.id,
                task_type='checkout_clean',
                priority='high',
                status='pending',
                notes=f"Checkout cleaning. Reason: {reason}"
            )
            db.session.add(task)
        
        return True, f"Room status changed from {old_status} to {new_status}"
    
    @staticmethod
    def create_room(hotel_id: int, room_number: str,
                   room_type_id: int, floor: Optional[int] = None,
                   description: str = '') -> Tuple[Optional[Room], str]:
        """
        Create new room with validation.
        
        Args:
            hotel_id: Hotel ID
            room_number: Room number
            room_type_id: Room type ID
            floor: Floor number
            description: Room description
            
        Returns:
            Tuple of (Room, error_message)
        """
        # Validate room number uniqueness
        existing = Room.query.filter_by(
            hotel_id=hotel_id,
            room_number=room_number,
            is_active=True
        ).first()
        
        if existing:
            return None, f"Room {room_number} already exists"
        
        # Validate room type
        room_type = RoomType.query.filter_by(
            id=room_type_id,
            hotel_id=hotel_id
        ).first()
        
        if not room_type:
            return None, "Invalid room type"
        
        # Create room
        room = Room(
            hotel_id=hotel_id,
            room_number=room_number,
            room_type_id=room_type_id,
            status='Vacant',
            floor=floor,
            description=description,
            is_active=True
        )
        
        return room, "Room created successfully"
    
    @staticmethod
    def delete_room(room: Room) -> Tuple[bool, str]:
        """
        Safely delete room with dependency checks.
        
        Args:
            room: Room object
            
        Returns:
            Tuple of (success, error_message)
        """
        # Check if occupied
        if room.status == 'Occupied':
            return False, "Cannot delete occupied room"
        
        # Check for active bookings
        active_bookings = Booking.query.filter_by(
            room_id=room.id
        ).filter(
            Booking.status.in_(['Reserved', 'CheckedIn', 'CheckedOut'])
        ).count()
        
        if active_bookings > 0:
            return False, f"Cannot delete: {active_bookings} active booking(s) exist"
        
        # Check for pending housekeeping tasks
        pending_tasks = HousekeepingTask.query.filter_by(
            room_id=room.id,
            status='pending'
        ).count()
        
        if pending_tasks > 0:
            return False, f"Cannot delete: {pending_tasks} pending housekeeping task(s)"
        
        # Note: We don't delete historical data (tasks, maintenance, etc.)
        # Just mark room as inactive
        
        room.is_active = False
        
        return True, "Room marked as inactive"


# =============================================================================
# HELPER FUNCTIONS (Backward Compatible)
# =============================================================================

def safe_change_room_status(room: Room, new_status: str,
                           reason: str = "", user_id: int = None) -> Tuple[bool, str]:
    """
    Safe wrapper for room status changes.
    Use this instead of: room.status = new_status
    
    Args:
        room: Room object
        new_status: New status
        reason: Reason for change
        user_id: User making change
        
    Returns:
        Tuple of (success, message)
    """
    return RoomManagementService.change_room_status(room, new_status, reason, user_id)


def get_room_availability(hotel_id: int, check_in: date,
                         check_out: date, room_type_id: int = None) -> List[Room]:
    """
    Get available rooms for given dates.
    
    Args:
        hotel_id: Hotel ID
        check_in: Check-in date
        check_out: Check-out date
        room_type_id: Optional room type filter
        
    Returns:
        List of available rooms
    """
    # Get all active rooms
    q = Room.query.filter_by(hotel_id=hotel_id, is_active=True)
    
    if room_type_id:
        q = q.filter_by(room_type_id=room_type_id)
    
    all_rooms = q.all()
    
    # Filter out booked rooms
    booked_room_ids = Booking.query.filter(
        Booking.hotel_id == hotel_id,
        Booking.room_id.in_([r.id for r in all_rooms]),
        Booking.status.in_(['Reserved', 'CheckedIn']),
        Booking.check_in_date < check_out,
        Booking.check_out_date > check_in
    ).with_entities(Booking.room_id).all()
    
    booked_ids = [r[0] for r in booked_room_ids]
    
    available = [r for r in all_rooms if r.id not in booked_ids and r.status in ['Vacant', 'Dirty']]
    
    return available
