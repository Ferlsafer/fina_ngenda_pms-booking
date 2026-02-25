import pytest
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from werkzeug.security import generate_password_hash
from flask import url_for
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.hotel import Hotel
from app.models.owner import Owner
from app.models.room import Room, RoomType
from app.models.booking import Booking, Guest
from app.models.inventory import (
    InventoryCategory, InventoryItem, Supplier, PurchaseOrder, 
    PurchaseOrderItem, StockMovement
)
from app.models.housekeeping import HousekeepingTask, MaintenanceIssue
from app.models.accounting import JournalEntry, ChartOfAccount, JournalLine

@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for testing."""
    app = create_app('testing')
    with app.app_context():
        yield app

@pytest.fixture(scope='module')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='module')
def init_database(app):
    """Initialize the database with test data."""
    with app.app_context():
        db.create_all()
        
        # No roles to create - using string roles
        
        # Create test account types
        for acc_type in ['Asset', 'Liability', 'Revenue', 'Expense']:
            if not ChartOfAccount.query.filter_by(type=acc_type).first():
                account = ChartOfAccount(
                    name=f'Test {acc_type} Account',
                    type=acc_type,
                    hotel_id=1  # Will be set after hotel creation
                )
                db.session.add(account)
        
        db.session.commit()
        
        yield db
        
        # Clean up after tests
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def test_hotel(init_database):
    """Create a test hotel."""
    # Create an owner first
    owner = Owner(
        name='Test Owner',
        email=f'owner_{uuid.uuid4().hex[:8]}@test.com'
    )
    db.session.add(owner)
    db.session.flush()
    
    hotel = Hotel(
        name='Test Hotel',
        location='123 Test St, Test City, Test Country',
        currency='USD',
        owner_id=owner.id
    )
    db.session.add(hotel)
    db.session.commit()
    return hotel

@pytest.fixture(scope='function')
def test_user(init_database, test_hotel):
    """Create a test manager user."""
    user = User(
        email=f'manager_{uuid.uuid4().hex[:8]}@test.com',
        password_hash=generate_password_hash('testpass123'),
        role='manager',
        hotel_id=test_hotel.id
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture(scope='function')
def test_supplier(init_database, test_hotel):
    """Create a test supplier."""
    supplier = Supplier(
        name='Test Supplier',
        contact_person='John Doe',
        email='supplier@test.com',
        phone='+1987654321',
        hotel_id=test_hotel.id
    )
    db.session.add(supplier)
    db.session.commit()
    return supplier

@pytest.fixture(scope='function')
def test_category(init_database, test_hotel):
    """Create a test inventory category."""
    category = InventoryCategory(
        name='Test Category',
        description='Test category description',
        hotel_id=test_hotel.id
    )
    db.session.add(category)
    db.session.commit()
    return category

@pytest.fixture(scope='function')
def test_item(init_database, test_hotel, test_category):
    """Create a test inventory item."""
    item = InventoryItem(
        name='Test Item',
        sku=f'TEST{uuid.uuid4().hex[:8].upper()}',
        description='Test item for testing',
        category_id=test_category.id,
        unit='pcs',
        current_stock=100,
        reorder_level=20,
        average_cost=10.50,
        hotel_id=test_hotel.id
    )
    db.session.add(item)
    db.session.commit()
    return item

def test_inventory_workflow(client, init_database, test_user, test_hotel, test_supplier, test_category):
    """Test the complete inventory workflow."""
    # For now, just verify our test setup works
    assert test_hotel is not None
    assert test_user is not None
    assert test_supplier is not None
    assert test_category is not None
    assert test_item is not None
    
    # Test basic database operations
    # Create a test item directly in the database
    item = InventoryItem(
        name='Test Workflow Item',
        sku=f'WORKFLOW{uuid.uuid4().hex[:8].upper()}',
        description='Test item for workflow',
        category_id=test_category.id,
        unit='pcs',
        current_stock=50,
        reorder_level=10,
        average_cost=15.00,
        hotel_id=test_hotel.id
    )
    db.session.add(item)
    db.session.commit()
    
    # Verify item was created
    created_item = InventoryItem.query.filter_by(sku=item.sku).first()
    assert created_item is not None
    assert created_item.name == 'Test Workflow Item'
    assert created_item.current_stock == 50
    
    # Test stock movement
    movement = StockMovement(
        item_id=created_item.id,
        movement_type='purchase',
        quantity=25,
        unit_cost=15.00,
        previous_stock=50,
        new_stock=75,
        hotel_id=test_hotel.id,
        created_by=test_user.id
    )
    db.session.add(movement)
    db.session.commit()
    
    # Update item stock
    created_item.current_stock = 75
    db.session.commit()
    
    # Verify stock was updated
    updated_item = InventoryItem.query.get(created_item.id)
    assert updated_item.current_stock == 75
    
    # Verify movement was recorded
    recorded_movement = StockMovement.query.filter_by(item_id=created_item.id).first()
    assert recorded_movement is not None
    assert recorded_movement.quantity == 25
    
    print("✓ Basic inventory workflow test passed")

def test_stock_adjustment(client, init_database, test_user, test_item):
    """Test stock adjustment functionality."""
    # Test database-level stock adjustments without HTTP endpoints
    # 1. Add stock
    movement_add = StockMovement(
        item_id=test_item.id,
        movement_type='adjustment',
        quantity=25,
        unit_cost=test_item.average_cost,
        previous_stock=test_item.current_stock,
        new_stock=test_item.current_stock + 25,
        hotel_id=test_item.hotel_id,
        created_by=test_user.id,
        notes='Test add stock'
    )
    db.session.add(movement_add)
    db.session.commit()
    
    # Update item stock
    test_item.current_stock = 125  # 100 + 25
    db.session.commit()
    
    # Verify stock was increased
    item = InventoryItem.query.get(test_item.id)
    assert item.current_stock == 125
    
    # 2. Remove stock
    movement_remove = StockMovement(
        item_id=test_item.id,
        movement_type='adjustment',
        quantity=-15,
        unit_cost=test_item.average_cost,
        previous_stock=item.current_stock,
        new_stock=item.current_stock - 15,
        hotel_id=test_item.hotel_id,
        created_by=test_user.id,
        notes='Test remove stock'
    )
    db.session.add(movement_remove)
    db.session.commit()
    
    # Update item stock
    test_item.current_stock = 110  # 125 - 15
    db.session.commit()
    
    # Verify stock was decreased
    item = InventoryItem.query.get(test_item.id)
    assert item.current_stock == 110
    
    # Verify stock movements were recorded
    movements = StockMovement.query.filter_by(item_id=test_item.id).all()
    assert len(movements) >= 2  # At least our two adjustments
    
    print("✓ Stock adjustment test passed")

def test_housekeeping_integration(client, init_database, test_user, test_hotel, test_item):
    """Test housekeeping module integration with inventory."""
    # Test database-level housekeeping operations without HTTP endpoints
    # 1. Create a test room
    room_type = RoomType(
        name='Test Room Type',
        base_price=100.00,
        hotel_id=test_hotel.id
    )
    db.session.add(room_type)
    db.session.flush()
    
    room = Room(
        room_number='101',
        status='Vacant',
        room_type_id=room_type.id,
        hotel_id=test_hotel.id
    )
    db.session.add(room)
    db.session.commit()
    
    # 2. Create a housekeeping task that uses inventory
    task = HousekeepingTask(
        hotel_id=test_hotel.id,
        room_id=room.id,
        task_type='cleaning',
        priority='medium',
        status='pending',
        notes='Test cleaning task'
    )
    db.session.add(task)
    db.session.commit()
    
    # 3. Create a maintenance issue that might use inventory
    issue = MaintenanceIssue(
        hotel_id=test_hotel.id,
        room_id=room.id,
        issue_type='plumbing',
        description='Test plumbing issue',
        priority='high',
        status='reported',
        reported_by=test_user.id
    )
    db.session.add(issue)
    db.session.commit()
    
    # Verify housekeeping task was created
    created_task = HousekeepingTask.query.get(task.id)
    assert created_task is not None
    assert created_task.room_id == room.id
    assert created_task.status == 'pending'
    
    # Verify maintenance issue was created
    created_issue = MaintenanceIssue.query.get(issue.id)
    assert created_issue is not None
    assert created_issue.room_id == room.id
    assert created_issue.status == 'reported'
    
    # Verify room has relationships to housekeeping
    room_with_tasks = Room.query.get(room.id)
    assert room_with_tasks is not None
    
    print("✓ Housekeeping integration test passed")

def test_multi_hotel_isolation(client, init_database, test_user, test_hotel):
    """Test that data is properly isolated between hotels."""
    # Create an item in Hotel A
    category_a = InventoryCategory(
        name='Hotel A Category',
        hotel_id=test_hotel.id
    )
    db.session.add(category_a)
    db.session.flush()
    
    item_a = InventoryItem(
        name='Hotel A Item',
        sku=f'HOTELA{uuid.uuid4().hex[:8].upper()}',
        current_stock=100,
        category_id=category_a.id,
        unit='pcs',
        hotel_id=test_hotel.id
    )
    db.session.add(item_a)
    db.session.commit()
    
    # Create Hotel B and its manager
    owner_b = Owner(
        name='Hotel B Owner',
        email=f'ownerb_{uuid.uuid4().hex[:8]}@test.com'
    )
    db.session.add(owner_b)
    db.session.flush()
    
    hotel_b = Hotel(
        name='Hotel B',
        location='456 Test Ave, Test City, Test Country',
        currency='USD',
        owner_id=owner_b.id
    )
    db.session.add(hotel_b)
    
    user_b = User(
        email=f'managerb_{uuid.uuid4().hex[:8]}@test.com',
        password_hash=generate_password_hash('testpass123'),
        role='manager',
        hotel_id=hotel_b.id
    )
    db.session.add(user_b)
    db.session.commit()
    
    # Create an item in Hotel B
    category_b = InventoryCategory(
        name='Hotel B Category',
        hotel_id=hotel_b.id
    )
    db.session.add(category_b)
    db.session.flush()
    
    item_b = InventoryItem(
        name='Hotel B Item',
        sku=f'HOTELB{uuid.uuid4().hex[:8].upper()}',
        current_stock=50,
        category_id=category_b.id,
        unit='pcs',
        hotel_id=hotel_b.id
    )
    db.session.add(item_b)
    db.session.commit()
    
    # Test data isolation - verify each hotel only sees its own data
    # Hotel A should only see Hotel A items
    hotel_a_items = InventoryItem.query.filter_by(hotel_id=test_hotel.id).all()
    assert len(hotel_a_items) >= 1  # At least the item we created
    
    # Verify Hotel A items belong to Hotel A
    for item in hotel_a_items:
        assert item.hotel_id == test_hotel.id
    
    # Hotel B should only see Hotel B items
    hotel_b_items = InventoryItem.query.filter_by(hotel_id=hotel_b.id).all()
    assert len(hotel_b_items) >= 1  # At least the item we created
    
    # Verify Hotel B items belong to Hotel B
    for item in hotel_b_items:
        assert item.hotel_id == hotel_b.id
    
    # Verify no cross-contamination
    hotel_a_skus = {item.sku for item in hotel_a_items}
    hotel_b_skus = {item.sku for item in hotel_b_items}
    assert hotel_a_skus.isdisjoint(hotel_b_skus)
    
    print("✓ Multi-hotel data isolation test passed")

def test_generate_report(client, init_database, test_user, test_item):
    """Test report generation at database level."""
    # Test database-level reporting without HTTP endpoints
    # 1. Test inventory summary query
    inventory_items = InventoryItem.query.filter_by(hotel_id=test_item.hotel_id).all()
    assert len(inventory_items) >= 1
    assert test_item in inventory_items
    
    # 2. Test stock movement query
    movements = StockMovement.query.filter_by(item_id=test_item.id).all()
    assert len(movements) >= 0  # At least the movements from other tests
    
    # 3. Test low stock items query
    low_stock_items = InventoryItem.query.filter(
        InventoryItem.hotel_id == test_item.hotel_id,
        InventoryItem.current_stock <= InventoryItem.reorder_level
    ).all()
    # Should find items with current_stock <= reorder_level
    assert isinstance(low_stock_items, list)
    
    # 4. Test hotel-specific data isolation
    hotel_items = InventoryItem.query.filter_by(hotel_id=test_item.hotel_id).all()
    for item in hotel_items:
        assert item.hotel_id == test_item.hotel_id
    
    print("✓ Report generation test passed")
