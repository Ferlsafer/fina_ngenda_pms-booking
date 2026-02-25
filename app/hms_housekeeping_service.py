# =============================================================================
# HOUSEKEEPING SERVICE MODULE
# =============================================================================
"""
Housekeeping Business Logic Service

This module contains all housekeeping business logic, separated from Flask routes.
It provides:
- Room status transition validation
- Task priority scoring
- Smart task assignment
- Cleaning time estimation
- Productivity tracking
- Maintenance integration

All methods are designed to be non-breaking and backward compatible.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from app import db
from app.models import (
    Room, HousekeepingTask, HousekeepingSupply, MaintenanceIssue,
    Booking, Hotel, User, InventoryItem, RoomStatusHistory
)

# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================

# Valid room status transitions
# Format: current_status: [allowed_next_statuses]
VALID_STATUS_TRANSITIONS = {
    'Vacant': ['Dirty', 'Reserved', 'Maintenance', 'Occupied'],  # Added 'Occupied' for direct check-in
    'Dirty': ['Vacant', 'Maintenance'],
    'Occupied': ['Dirty', 'Maintenance'],
    'Reserved': ['Occupied', 'Vacant', 'Dirty'],
    'Maintenance': ['Vacant', 'Dirty']
}

# Task type priority weights (higher = more urgent)
TASK_TYPE_PRIORITY = {
    'vip_clean': 100,
    'express_clean': 90,
    'checkout_clean': 80,
    'regular_clean': 60,
    'service': 50,
    'inspection': 40,
    'deep_clean': 30,
    'maintenance': 70
}

# Cleaning time estimates by room type (in minutes)
# These are defaults and can be overridden by room_type if field exists
CLEANING_TIME_ESTIMATES = {
    'Standard': 30,
    'Deluxe': 45,
    'Suite': 60,
    'Executive': 50,
    'default': 40
}

# Priority score thresholds
PRIORITY_HIGH = 80
PRIORITY_MEDIUM = 50
PRIORITY_LOW = 0


# =============================================================================
# ROOM STATUS MANAGEMENT
# =============================================================================

class RoomStatusManager:
    """
    Manages room status transitions with validation and audit trail.
    Ensures data integrity and prevents invalid status changes.
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
        if current_status == new_status:
            return False, "Room is already in this status"
        
        allowed_transitions = VALID_STATUS_TRANSITIONS.get(current_status, [])
        
        if new_status not in allowed_transitions:
            return False, f"Cannot transition from {current_status} to {new_status}"
        
        return True, ""
    
    @staticmethod
    def can_check_in(room: Room) -> Tuple[bool, str]:
        """
        Check if a room is ready for guest check-in.
        
        Args:
            room: Room object
            
        Returns:
            Tuple of (can_check_in, reason)
        """
        if room.status == 'Vacant':
            return True, ""
        elif room.status == 'Dirty':
            return False, "Room needs cleaning before check-in"
        elif room.status == 'Occupied':
            return False, "Room is currently occupied"
        elif room.status == 'Maintenance':
            return False, "Room is under maintenance"
        elif room.status == 'Reserved':
            return True, ""
        else:
            return False, f"Invalid room status: {room.status}"
    
    @staticmethod
    def can_mark_ooo(room: Room) -> Tuple[bool, str]:
        """
        Check if a room can be marked as Out of Order.
        
        Args:
            room: Room object
            
        Returns:
            Tuple of (can_mark_ooo, reason)
        """
        if room.status == 'Occupied':
            return False, "Cannot mark occupied room as Out of Order"
        return True, ""
    
    @staticmethod
    def change_status(room: Room, new_status: str, 
                     user_id: Optional[int] = None,
                     reason: Optional[str] = None) -> Tuple[bool, str]:
        """
        Safely change room status with validation and audit trail.
        
        Args:
            room: Room object
            new_status: New status to set
            user_id: ID of user making the change (not stored - model limitation)
            reason: Optional reason for the change (not stored - model limitation)
            
        Returns:
            Tuple of (success, message)
        """
        # Validate transition
        is_valid, error_msg = RoomStatusManager.validate_transition(
            room.status, new_status
        )
        
        if not is_valid:
            return False, error_msg
        
        # Store old status for history
        old_status = room.status
        
        # Update room status
        room.status = new_status
        
        # Create audit trail entry (only fields supported by model)
        if old_status != new_status:
            history = RoomStatusHistory(
                hotel_id=room.hotel_id,
                room_id=room.id,
                old_status=old_status,
                new_status=new_status
                # Note: changed_by and reason not stored - model doesn't support them
            )
            db.session.add(history)
        
        return True, f"Room status changed from {old_status} to {new_status}"


# =============================================================================
# TASK PRIORITY SCORING
# =============================================================================

class TaskPriorityScorer:
    """
    Calculates priority scores for housekeeping tasks based on multiple factors.
    """
    
    @staticmethod
    def calculate_priority_score(task: HousekeepingTask, 
                                 check_ins_today: List[int] = None,
                                 vip_rooms: List[int] = None) -> int:
        """
        Calculate priority score for a task.
        
        Factors considered:
        - Task type (checkout, stayover, VIP, etc.)
        - Room has check-in today
        - Room is VIP
        - Time since task creation
        - Guest waiting (for service requests)
        
        Args:
            task: HousekeepingTask object
            check_ins_today: List of room IDs with check-ins today
            vip_rooms: List of VIP room IDs
            
        Returns:
            Priority score (0-100)
        """
        if check_ins_today is None:
            check_ins_today = []
        if vip_rooms is None:
            vip_rooms = []
        
        score = 0
        
        # Base score from task type
        task_type_base = TASK_TYPE_PRIORITY.get(task.task_type, 50)
        score += task_type_base
        
        # Bonus for check-in today rooms (highest priority)
        if task.room_id in check_ins_today:
            score += 40
        
        # Bonus for VIP rooms
        if task.room_id in vip_rooms:
            score += 30
        
        # Bonus for old tasks (prevent starvation)
        if task.created_at:
            hours_old = (datetime.utcnow() - task.created_at).total_seconds() / 3600
            if hours_old > 4:
                score += min(20, int(hours_old - 4) * 2)
        
        # Cap score at 100
        return min(100, score)
    
    @staticmethod
    def get_priority_label(score: int) -> str:
        """Convert numeric score to human-readable label."""
        if score >= PRIORITY_HIGH:
            return "High"
        elif score >= PRIORITY_MEDIUM:
            return "Medium"
        else:
            return "Low"
    
    @staticmethod
    def sort_tasks_by_priority(tasks: List[HousekeepingTask],
                               check_ins_today: List[int] = None,
                               vip_rooms: List[int] = None) -> List[HousekeepingTask]:
        """
        Sort tasks by calculated priority score (highest first).
        
        Args:
            tasks: List of HousekeepingTask objects
            check_ins_today: List of room IDs with check-ins today
            vip_rooms: List of VIP room IDs
            
        Returns:
            Sorted list of tasks
        """
        return sorted(
            tasks,
            key=lambda t: TaskPriorityScorer.calculate_priority_score(
                t, check_ins_today, vip_rooms
            ),
            reverse=True
        )


# =============================================================================
# CLEANING TIME ESTIMATION
# =============================================================================

class CleaningTimeEstimator:
    """
    Estimates cleaning duration based on room type and task type.
    """
    
    @staticmethod
    def get_base_cleaning_time(room: Room) -> int:
        """
        Get base cleaning time in minutes for a room.
        
        Args:
            room: Room object
            
        Returns:
            Estimated cleaning time in minutes
        """
        if room.room_type and room.room_type.name:
            return CLEANING_TIME_ESTIMATES.get(
                room.room_type.name,
                CLEANING_TIME_ESTIMATES['default']
            )
        return CLEANING_TIME_ESTIMATES['default']
    
    @staticmethod
    def get_task_multiplier(task_type: str) -> float:
        """
        Get time multiplier based on task type.
        
        Args:
            task_type: Type of housekeeping task
            
        Returns:
            Time multiplier (1.0 = base time)
        """
        multipliers = {
            'regular_clean': 1.0,
            'checkout_clean': 1.3,
            'express_clean': 0.7,
            'deep_clean': 2.0,
            'service': 0.5,
            'inspection': 0.3,
            'vip_clean': 1.5,
            'maintenance': 1.0
        }
        return multipliers.get(task_type, 1.0)
    
    @staticmethod
    def estimate_completion_time(task: HousekeepingTask) -> datetime:
        """
        Estimate when a task will be completed.
        
        Args:
            task: HousekeepingTask object
            
        Returns:
            Estimated completion datetime
        """
        if not task.room:
            return datetime.utcnow() + timedelta(minutes=30)
        
        base_time = CleaningTimeEstimator.get_base_cleaning_time(task.room)
        multiplier = CleaningTimeEstimator.get_task_multiplier(task.task_type)
        
        estimated_minutes = int(base_time * multiplier)
        
        # Start from task creation or now if already started
        start_time = task.started_at or task.created_at or datetime.utcnow()
        
        return start_time + timedelta(minutes=estimated_minutes)
    
    @staticmethod
    def estimate_completion_time_minutes(room: Room, task_type: str) -> int:
        """
        Get estimated cleaning time in minutes.
        
        Args:
            room: Room object
            task_type: Type of task
            
        Returns:
            Estimated time in minutes
        """
        base_time = CleaningTimeEstimator.get_base_cleaning_time(room)
        multiplier = CleaningTimeEstimator.get_task_multiplier(task_type)
        return int(base_time * multiplier)


# =============================================================================
# SMART TASK ASSIGNMENT
# =============================================================================

class TaskAssignmentEngine:
    """
    Intelligently assigns tasks to housekeeping staff based on:
    - Workload balancing
    - Floor/zone proximity
    - Staff availability
    - Task priority
    """
    
    @staticmethod
    def get_staff_workload(hotel_id: int, 
                          date: datetime = None) -> Dict[int, int]:
        """
        Get current task count for each housekeeping staff member.
        
        Args:
            hotel_id: Hotel ID
            date: Date to check (defaults to today)
            
        Returns:
            Dict mapping user_id to task count
        """
        if date is None:
            date = datetime.utcnow().date()
        
        # Get all active tasks assigned to staff today
        active_tasks = HousekeepingTask.query.filter(
            HousekeepingTask.hotel_id == hotel_id,
            HousekeepingTask.status.in_(['pending', 'in_progress']),
            HousekeepingTask.completed_by.isnot(None)
        ).all()
        
        workload = {}
        for task in active_tasks:
            if task.completed_by:
                workload[task.completed_by] = workload.get(task.completed_by, 0) + 1
        
        return workload
    
    @staticmethod
    def get_staff_on_floor(hotel_id: int, floor: int) -> List[int]:
        """
        Get list of staff members currently working on a specific floor.
        
        Note: This is a placeholder for future implementation when
        staff location tracking is added.
        
        Args:
            hotel_id: Hotel ID
            floor: Floor number
            
        Returns:
            List of user IDs
        """
        # For now, return empty list
        # Future: integrate with staff location tracking
        return []
    
    @staticmethod
    def find_best_staff_for_task(task: HousekeepingTask,
                                 available_staff: List[User] = None) -> Optional[User]:
        """
        Find the best staff member to assign a task to.
        
        Selection criteria:
        1. Staff with lowest current workload
        2. Staff already working on same floor
        3. Staff with appropriate role
        
        Args:
            task: HousekeepingTask to assign
            available_staff: List of available staff users
            
        Returns:
            Best User object or None
        """
        if available_staff is None:
            # Get all housekeeping staff for this hotel
            available_staff = User.query.filter(
                User.hotel_id == task.hotel_id,
                User.role.in_(['housekeeping', 'manager'])
            ).all()
        
        if not available_staff:
            return None
        
        # Get current workload for all staff
        workload = TaskAssignmentEngine.get_staff_workload(task.hotel_id)
        
        # Sort staff by workload (least busy first)
        sorted_staff = sorted(
            available_staff,
            key=lambda s: workload.get(s.id, 0)
        )
        
        # Return staff with lowest workload
        return sorted_staff[0] if sorted_staff else None
    
    @staticmethod
    def auto_assign_tasks(pending_tasks: List[HousekeepingTask],
                         available_staff: List[User] = None) -> List[Tuple[HousekeepingTask, Optional[User]]]:
        """
        Automatically assign pending tasks to available staff.
        
        Args:
            pending_tasks: List of pending tasks to assign
            available_staff: List of available staff
            
        Returns:
            List of (task, assigned_staff) tuples
        """
        assignments = []
        
        # Sort tasks by priority first
        sorted_tasks = TaskPriorityScorer.sort_tasks_by_priority(pending_tasks)
        
        for task in sorted_tasks:
            best_staff = TaskAssignmentEngine.find_best_staff_for_task(
                task, available_staff
            )
            assignments.append((task, best_staff))
        
        return assignments


# =============================================================================
# PRODUCTIVITY TRACKING
# =============================================================================

class ProductivityTracker:
    """
    Tracks housekeeping staff productivity metrics.
    """
    
    @staticmethod
    def get_task_duration(task: HousekeepingTask) -> Optional[int]:
        """
        Get actual task duration in minutes.
        
        Args:
            task: HousekeepingTask object
            
        Returns:
            Duration in minutes or None if not completed
        """
        if not task.completed_at or not task.started_at:
            return None
        
        duration = (task.completed_at - task.started_at).total_seconds() / 60
        return int(duration)
    
    @staticmethod
    def get_staff_productivity(user_id: int,
                              hotel_id: int,
                              start_date: datetime = None,
                              end_date: datetime = None) -> Dict[str, Any]:
        """
        Get productivity metrics for a staff member.
        
        Args:
            user_id: Staff user ID
            hotel_id: Hotel ID
            start_date: Start of period
            end_date: End of period
            
        Returns:
            Dict with productivity metrics
        """
        if start_date is None:
            start_date = datetime.utcnow().date()
        if end_date is None:
            end_date = datetime.utcnow().date()
        
        # Get completed tasks in period
        completed_tasks = HousekeepingTask.query.filter(
            HousekeepingTask.hotel_id == hotel_id,
            HousekeepingTask.completed_by == user_id,
            HousekeepingTask.status == 'completed',
            HousekeepingTask.completed_at >= start_date,
            HousekeepingTask.completed_at <= end_date + timedelta(days=1)
        ).all()
        
        if not completed_tasks:
            return {
                'tasks_completed': 0,
                'avg_duration_minutes': 0,
                'total_time_minutes': 0
            }
        
        # Calculate metrics
        durations = [
            ProductivityTracker.get_task_duration(t)
            for t in completed_tasks
            if ProductivityTracker.get_task_duration(t) is not None
        ]
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        total_time = sum(durations) if durations else 0
        
        return {
            'tasks_completed': len(completed_tasks),
            'avg_duration_minutes': round(avg_duration, 1),
            'total_time_minutes': total_time,
            'tasks': completed_tasks
        }
    
    @staticmethod
    def get_re_clean_rate(room_id: int, 
                         days: int = 30) -> float:
        """
        Get re-clean rate for a room (how often it needs cleaning twice).
        
        Args:
            room_id: Room ID
            days: Number of days to look back
            
        Returns:
            Re-clean rate as percentage
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        tasks = HousekeepingTask.query.filter(
            HousekeepingTask.room_id == room_id,
            HousekeepingTask.created_at >= cutoff
        ).all()
        
        if len(tasks) <= 1:
            return 0.0
        
        # Count tasks that were created within 24h of previous task completion
        re_clean_count = 0
        for i in range(1, len(tasks)):
            prev_task = tasks[i-1]
            curr_task = tasks[i]
            
            if prev_task.completed_at:
                hours_between = (curr_task.created_at - prev_task.completed_at).total_seconds() / 3600
                if hours_between < 24:
                    re_clean_count += 1
        
        return (re_clean_count / len(tasks)) * 100


# =============================================================================
# MAINTENANCE INTEGRATION
# =============================================================================

class MaintenanceIntegration:
    """
    Integrates housekeeping with maintenance reporting.
    """
    
    @staticmethod
    def create_maintenance_issue_from_task(task: HousekeepingTask,
                                          issue_description: str,
                                          priority: str = 'medium',
                                          reported_by_user_id: int = None) -> Optional[MaintenanceIssue]:
        """
        Create a maintenance issue from a housekeeping task.
        
        Args:
            task: HousekeepingTask object
            issue_description: Description of the maintenance issue
            priority: Issue priority (low, medium, high)
            reported_by_user_id: User reporting the issue
            
        Returns:
            Created MaintenanceIssue or None
        """
        if not task.room:
            return None
        
        issue = MaintenanceIssue(
            hotel_id=task.hotel_id,
            room_id=task.room.id,
            issue_type='maintenance',
            description=issue_description,
            priority=priority,
            status='reported',
            reported_by=reported_by_user_id or task.completed_by
        )
        
        db.session.add(issue)
        
        # Add note to housekeeping task
        if task.notes:
            task.notes += f"\n\n[Maintenance Issue Created: #{issue.id}]"
        else:
            task.notes = f"[Maintenance Issue Created: #{issue.id}]"
        
        return issue
    
    @staticmethod
    def mark_room_ooo(room: Room, 
                     reason: str,
                     reported_by_user_id: int = None) -> Optional[MaintenanceIssue]:
        """
        Mark a room as Out of Order and create maintenance issue.
        
        Args:
            room: Room to mark as OOO
            reason: Reason for OOO status
            reported_by_user_id: User reporting the issue
            
        Returns:
            Created MaintenanceIssue or None
        """
        # Validate room can be marked OOO
        can_mark, error_msg = RoomStatusManager.can_mark_ooo(room)
        if not can_mark:
            return None
        
        # Create maintenance issue
        issue = MaintenanceIssue(
            hotel_id=room.hotel_id,
            room_id=room.id,
            issue_type='out_of_order',
            description=reason,
            priority='high',
            status='reported',
            reported_by=reported_by_user_id
        )
        
        db.session.add(issue)
        
        # Change room status to Maintenance
        RoomStatusManager.change_status(
            room, 'Maintenance',
            user_id=reported_by_user_id,
            reason=f"Out of Order: {reason}"
        )
        
        return issue


# =============================================================================
# CHECKOUT PROCESSING
# =============================================================================

class CheckoutProcessor:
    """
    Handles housekeeping tasks related to guest checkout.
    """
    
    @staticmethod
    def process_checkout(room: Room, 
                        user_id: Optional[int] = None) -> HousekeepingTask:
        """
        Process a guest checkout by creating cleaning task.
        
        This is the recommended way to handle checkouts:
        1. Room status becomes "Dirty" (not immediately Vacant)
        2. Cleaning task is automatically created
        3. Room becomes "Vacant" only after cleaning is complete
        
        Args:
            room: Room object
            user_id: User processing the checkout
            
        Returns:
            Created HousekeepingTask
        """
        # Change room status to Dirty (not Vacant yet!)
        RoomStatusManager.change_status(
            room, 'Dirty',
            user_id=user_id,
            reason="Guest checkout - awaiting cleaning"
        )
        
        # Create high-priority cleaning task
        task = HousekeepingTask(
            hotel_id=room.hotel_id,
            room_id=room.id,
            task_type='checkout_clean',
            priority='high',
            status='pending',
            notes=f"Checkout cleaning - Room {room.room_number}"
        )
        
        db.session.add(task)
        
        return task


# =============================================================================
# HELPER FUNCTIONS (Backward Compatible)
# =============================================================================

def quick_clean_room(room: Room, user_id: Optional[int] = None) -> Tuple[bool, str]:
    """
    Quick clean a room (bypass task system).
    Legacy function for backward compatibility.
    
    Args:
        room: Room object
        user_id: User performing the action
        
    Returns:
        Tuple of (success, message)
    """
    # Validate transition
    if room.status not in ['Dirty', 'Maintenance']:
        return False, f"Cannot clean room in {room.status} status"
    
    return RoomStatusManager.change_status(
        room, 'Vacant',
        user_id=user_id,
        reason="Quick clean completed"
    )


def quick_dirty_room(room: Room, user_id: Optional[int] = None) -> Tuple[bool, str]:
    """
    Mark a room as dirty (bypass task system).
    Legacy function for backward compatibility.
    
    Args:
        room: Room object
        user_id: User performing the action
        
    Returns:
        Tuple of (success, message)
    """
    if room.status not in ['Vacant', 'Reserved']:
        return False, f"Cannot mark {room.status} room as dirty"
    
    return RoomStatusManager.change_status(
        room, 'Dirty',
        user_id=user_id,
        reason="Marked as dirty"
    )


def create_cleaning_task(room: Room, 
                        task_type: str = 'regular_clean',
                        priority: str = 'normal',
                        notes: str = '',
                        user_id: Optional[int] = None) -> HousekeepingTask:
    """
    Create a cleaning task for a room.
    Legacy function for backward compatibility.
    
    Args:
        room: Room object
        task_type: Type of cleaning task
        priority: Task priority
        notes: Task notes
        user_id: User creating the task
        
    Returns:
        Created HousekeepingTask
    """
    task = HousekeepingTask(
        hotel_id=room.hotel_id,
        room_id=room.id,
        task_type=task_type,
        priority=priority,
        status='pending',
        notes=notes
    )
    
    db.session.add(task)
    
    # Mark room as dirty if it's a cleaning task
    if task_type in ['regular_clean', 'checkout_clean', 'deep_clean']:
        RoomStatusManager.change_status(
            room, 'Dirty',
            user_id=user_id,
            reason=f"Cleaning task created: {task_type}"
        )
    
    return task


def complete_cleaning_task(task: HousekeepingTask, 
                          user_id: Optional[int] = None) -> Tuple[bool, str]:
    """
    Complete a cleaning task and mark room as clean.
    Legacy function for backward compatibility.
    
    Args:
        task: HousekeepingTask object
        user_id: User completing the task
        
    Returns:
        Tuple of (success, message)
    """
    if task.status != 'in_progress':
        return False, "Task must be in progress to complete"
    
    task.status = 'completed'
    task.completed_at = datetime.utcnow()
    task.completed_by = user_id or task.completed_by
    
    # Mark room as Vacant (clean)
    if task.room:
        RoomStatusManager.change_status(
            task.room, 'Vacant',
            user_id=user_id,
            reason=f"Cleaning completed - Task #{task.id}"
        )
    
    return True, "Task completed successfully"
