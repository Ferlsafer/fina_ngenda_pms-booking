# Restaurant Module - Complete Audit & Improvement Plan

## 📊 Current Architecture Overview

### **What the Restaurant Module Does:**

```
┌─────────────────────────────────────────────────────────┐
│                  RESTAURANT MODULE                       │
├─────────────────────────────────────────────────────────┤
│ 1. Menu Management (categories, items, pricing)         │
│ 2. POS (Point of Sale) System                           │
│ 3. Table Management (capacity, status, map)             │
│ 4. Order Management (dine-in, takeaway, room service)   │
│ 5. Kitchen Display System (KDS)                         │
│ 6. Order Status Tracking                                │
└─────────────────────────────────────────────────────────┘
```

---

## 🔍 Current Routes Analysis

### **1. `/restaurant` (GET)**
**Purpose:** Restaurant dashboard
**Current State:** ✅ Basic stats display

**Shows:**
- Menu items count
- Tables count
- Categories count
- Today's orders
- Pending orders
- Available tables

**Missing:**
- ❌ Revenue today
- ❌ Average order value
- ❌ Popular items
- ❌ Table turnover rate

---

### **2. `/restaurant/menu` (GET)**
**Purpose:** Menu management
**Current State:** ✅ Functional

**Features:**
- View all categories and items
- Item count per category

**Missing:**
- ❌ Edit item inline
- ❌ Bulk availability toggle
- ❌ Item images
- ❌ Nutritional info
- ❌ Allergen information

---

### **3. `/restaurant/menu/item/add` (GET/POST)**
**Purpose:** Add menu item
**Current State:** ⚠️ Basic

**What Works:**
- ✅ Add item with name, price, category
- ✅ Set availability
- ✅ Preparation time

**Issues:**
```python
# ❌ PROBLEM 1: No cost tracking
item = MenuItem(
    price=price,  # Selling price only
    # No cost field → Can't calculate profit margin!
)

# ❌ PROBLEM 2: No inventory integration
# Menu items don't deduct from inventory when sold

# ❌ PROBLEM 3: No image upload
# Items can't have photos
```

---

### **4. `/restaurant/pos` (GET)**
**Purpose:** Point of Sale interface
**Current State:** ⚠️ Basic

**What Works:**
- ✅ Select menu items
- ✅ Create orders (dine-in, takeaway, room service)
- ✅ Add to cart

**Issues:**
```python
# ❌ PROBLEM 1: No payment integration
# Can't process payments at POS

# ❌ PROBLEM 2: No discount support
# Can't apply discounts, promotions

# ❌ PROBLEM 3: No split bills
# Can't split bill by seat or amount

# ❌ PROBLEM 4: No receipt printing
# No thermal printer integration
```

---

### **5. `/restaurant/kitchen` (GET)**
**Purpose:** Kitchen Display System (KDS)
**Current State:** ✅ Functional

**What Works:**
- ✅ View pending orders
- ✅ View preparing orders
- ✅ View ready orders
- ✅ Change order status

**Missing:**
- ❌ Order priority (VIP, rush)
- ❌ Preparation time tracking
- ❌ Delayed order alerts
- ❌ Course management (appetizer, main, dessert)

---

### **6. `/restaurant/tables` (GET)**
**Purpose:** Table management
**Current State:** ⚠️ Very basic

**What Works:**
- ✅ View table list
- ✅ Add table
- ✅ Set capacity

**Issues:**
```python
# ❌ PROBLEM 1: No table map visualization
# Tables shown as list, not floor plan

# ❌ PROBLEM 2: No table status tracking
# Status exists but not properly used

# ❌ PROBLEM 3: No reservation integration
# Tables don't link to bookings
```

---

## 📋 Model Analysis

### **MenuCategory:**
```python
- id, hotel_id, name, description
- display_order, is_active, deleted_at
```
**Missing:**
- ❌ Icon/image
- ❌ Color coding
- ❌ Active hours (breakfast/lunch/dinner)

---

### **MenuItem:**
```python
- id, hotel_id, category_id
- name, description, price
- cost (exists but not used!)
- tax_rate, preparation_time
- is_available, deleted_at
```
**Missing:**
- ❌ Image URL (exists but not used)
- ❌ Allergen info
- ❌ Nutritional data
- ❌ Spice level
- ❌ Vegetarian/vegan flags
- ❌ Popularity score

---

### **RestaurantTable:**
```python
- id, hotel_id, table_number
- capacity, section
- status, position_x, position_y
```
**Good:** Has position fields for map!
**Missing:**
- ❌ Shape (round, square, booth)
- ❌ Minimum spend
- ❌ Time limit

---

### **RestaurantOrder:**
```python
- id, hotel_id, table_id, booking_id
- guest_name, order_type
- status, subtotal, tax, total
- special_instructions
```
**Missing:**
- ❌ Server/waiter assigned
- ❌ Payment status
- ❌ Payment method
- ❌ Discount amount
- ❌ Tip/gratuity
- ❌ Course sequence

---

### **RestaurantOrderItem:**
```python
- id, order_id, menu_item_id
- quantity, unit_price
- notes, status
```
**Missing:**
- ❌ Modifiers (extra cheese, no onions)
- ❌ Side dishes
- ❌ Cooking preference (rare, medium, well)

---

## 🎯 CRITICAL INTEGRATION GAPS

### **Gap 1: Restaurant ↔ Inventory (NONE)**

**Current State:**
```python
# ❌ When order is placed:
order = RestaurantOrder(...)
# No inventory deduction!

# MenuItemInventory exists but NEVER used!
menu_item_inventory = MenuItemInventory.query.filter(...)
# Returns empty - not integrated!
```

**Problem:**
- No automatic stock deduction when items sold
- Can't track food cost percentage
- No low stock alerts
- Can't calculate actual profit per dish

**Solution:**
```python
def place_order(items):
    for item in items:
        # Deduct inventory
        for inv_link in item.inventory_items:
            inv_link.inventory_item.current_stock -= inv_link.quantity_needed * item.quantity
            
            # Check reorder level
            if inv_link.inventory_item.current_stock < inv_link.inventory_item.reorder_level:
                create_low_stock_alert(inv_link.inventory_item)
```

---

### **Gap 2: Restaurant ↔ Accounting (PARTIAL)**

**Current State:**
```python
# Orders created but no accounting entries!
order = RestaurantOrder(total=100)
# No journal entry created!
```

**Problem:**
- Revenue not tracked in accounting
- No accounts receivable for dine-in
- No tax liability tracking
- Can't reconcile daily sales

**Solution:**
```python
def create_order_accounting(order):
    # Debit: Cash/Accounts Receivable
    # Credit: Revenue
    # Credit: Tax Payable
    
    journal = JournalEntry(
        reference=f"REST-ORDER-{order.id}",
        description=f"Restaurant order {order.table_number}"
    )
    
    # Debit line
    debit = JournalLine(
        account_id=cash_account.id,
        debit=order.total
    )
    
    # Credit lines
    revenue_credit = JournalLine(
        account_id=revenue_account.id,
        credit=order.subtotal
    )
    
    tax_credit = JournalLine(
        account_id=tax_account.id,
        credit=order.tax
    )
```

---

### **Gap 3: Restaurant ↔ Room Service (DUPLICATION)**

**Current State:**
```python
# TWO separate order systems:
RestaurantOrder  # For restaurant
RoomServiceOrder # For room service

# Same functionality, different tables!
# Should be unified!
```

**Problem:**
- Duplicate code
- Different status workflows
- Hard to get total F&B revenue
- Kitchen sees two different systems

**Solution:**
```python
# Single Order model with type field
class FoodOrder(db.Model):
    order_type = Column(String)  # 'dine_in', 'takeaway', 'room_service', 'delivery'
    
    # Common fields
    table_id  # For dine-in
    room_id   # For room service
    booking_id  # Link to hotel booking
```

---

### **Gap 4: Restaurant ↔ Housekeeping (NONE)**

**Current State:**
```python
# Table cleaned by housekeeping?
# No integration!

# Table status changes to 'Dirty' after guest leaves?
# No automatic notification!
```

**Problem:**
- Dirty tables not cleaned promptly
- No task creation for table cleaning
- Table turnover slow

**Solution:**
```python
def guest_leaves_table(table):
    table.status = 'Dirty'
    
    # Create housekeeping task
    task = HousekeepingTask(
        task_type='table_cleaning',
        notes=f'Clean table {table.table_number}',
        priority='high'
    )
```

---

### **Gap 5: Restaurant ↔ Booking (WEAK)**

**Current State:**
```python
# RestaurantOrder has booking_id
order.booking_id = booking.id

# But never used!
# No table reservation for hotel guests
```

**Problem:**
- Hotel guests can't reserve tables
- No pre-arrival dining booking
- No breakfast inclusion tracking

**Solution:**
```python
# When booking created with breakfast
if booking.includes_breakfast:
    # Auto-create table reservation
    reservation = TableReservation(
        booking_id=booking.id,
        table_id=assigned_table,
        meal_period='breakfast',
        time='07:00'
    )
```

---

## 🔧 REQUIRED IMPROVEMENTS

### **Priority 1: Inventory Integration**

**Implementation:**
```python
class RestaurantService:
    @staticmethod
    def create_order(items, table_id=None, booking_id=None):
        # Create order
        order = RestaurantOrder(...)
        
        # Deduct inventory
        for item in items:
            RestaurantService.deduct_inventory(item)
        
        # Create accounting entry
        RestaurantService.create_accounting_entry(order)
        
        return order
    
    @staticmethod
    def deduct_inventory(order_item):
        menu_item = order_item.menu_item
        
        # Get linked inventory items
        for inv_link in menu_item.inventory_items:
            inv_item = inv_link.inventory_item
            quantity_to_deduct = inv_link.quantity_needed * order_item.quantity
            
            inv_item.current_stock -= quantity_to_deduct
            
            # Check if below reorder level
            if inv_item.current_stock < inv_item.reorder_level:
                create_purchase_order_suggestion(inv_item)
```

---

### **Priority 2: Accounting Integration**

**Implementation:**
```python
class RestaurantAccounting:
    @staticmethod
    def post_daily_sales(hotel_id, date):
        """Post daily restaurant sales to accounting"""
        
        orders = RestaurantOrder.query.filter(
            RestaurantOrder.hotel_id == hotel_id,
            db.func.date(RestaurantOrder.created_at) == date
        ).all()
        
        total_sales = sum(o.subtotal for o in orders)
        total_tax = sum(o.tax for o in orders)
        
        # Create journal entry
        entry = JournalEntry(
            hotel_id=hotel_id,
            reference=f"REST-DAILY-{date}",
            description=f"Restaurant sales for {date}"
        )
        
        # Debit: Cash/AR
        debit = JournalLine(
            account_id=cash_account.id,
            debit=total_sales + total_tax
        )
        
        # Credit: Revenue
        revenue_credit = JournalLine(
            account_id=revenue_account.id,
            credit=total_sales
        )
        
        # Credit: Tax Payable
        tax_credit = JournalLine(
            account_id=tax_account.id,
            credit=total_tax
        )
```

---

### **Priority 3: Table Management Enhancement**

**Implementation:**
```python
class TableManagement:
    @staticmethod
    def get_table_status(table):
        """Get comprehensive table status"""
        
        # Check current order
        active_order = RestaurantOrder.query.filter_by(
            table_id=table.id,
            status.in_(['pending', 'preparing', 'ready'])
        ).first()
        
        if active_order:
            return {
                'status': 'Occupied',
                'order_id': active_order.id,
                'duration': datetime.utcnow() - active_order.created_at,
                'revenue': active_order.total
            }
        
        # Check upcoming reservations
        reservation = TableReservation.query.filter(
            TableReservation.table_id == table.id,
            TableReservation.time >= datetime.utcnow(),
            TableReservation.status == 'confirmed'
        ).first()
        
        if reservation:
            return {
                'status': 'Reserved',
                'reserved_until': reservation.time,
                'guest': reservation.guest_name
            }
        
        # Check if dirty
        if table.status == 'Dirty':
            return {
                'status': 'Dirty',
                'needs_cleaning': True
            }
        
        return {'status': 'Available'}
```

---

### **Priority 4: Menu Engineering**

**Implementation:**
```python
class MenuEngineering:
    @staticmethod
    def analyze_menu_performance(hotel_id, start_date, end_date):
        """Analyze menu items by profitability and popularity"""
        
        items = MenuItem.query.filter_by(
            hotel_id=hotel_id,
            deleted_at=None
        ).all()
        
        analysis = []
        
        for item in items:
            # Get sales data
            order_items = RestaurantOrderItem.query.join(RestaurantOrder).filter(
                RestaurantOrder.hotel_id == hotel_id,
                RestaurantOrder.created_at >= start_date,
                RestaurantOrder.created_at <= end_date,
                RestaurantOrderItem.menu_item_id == item.id
            ).all()
            
            quantity_sold = sum(oi.quantity for oi in order_items)
            
            # Calculate metrics
            profit_margin = (item.price - (item.cost or 0)) / item.price if item.price else 0
            popularity = quantity_sold / total_items_sold if total_items_sold else 0
            
            # Classify item
            if profit_margin > 0.7 and popularity > 0.1:
                classification = 'STAR'  # High profit, high popularity
            elif profit_margin > 0.7:
                classification = 'PUZZLE'  # High profit, low popularity
            elif popularity > 0.1:
                classification = 'PLOWHORSE'  # Low profit, high popularity
            else:
                classification = 'DOG'  # Low profit, low popularity
            
            analysis.append({
                'item': item.name,
                'profit_margin': profit_margin,
                'quantity_sold': quantity_sold,
                'popularity': popularity,
                'classification': classification,
                'action': get_recommended_action(classification)
            })
        
        return analysis

def get_recommended_action(classification):
    actions = {
        'STAR': 'Maintain quality, promote heavily',
        'PUZZLE': 'Promote more, rename or reposition',
        'PLOWHORSE': 'Increase price, reduce portion',
        'DOG': 'Remove from menu or reengineer'
    }
    return actions.get(classification, 'Review')
```

---

### **Priority 5: Kitchen Efficiency**

**Implementation:**
```python
class KitchenManagement:
    @staticmethod
    def get_order_priority(order):
        """Calculate order priority for kitchen"""
        
        priority_score = 0
        
        # VIP guest
        if order.booking_id:
            booking = Booking.query.get(order.booking_id)
            if booking and booking.guest and booking.guest.is_vip:
                priority_score += 50
        
        # Long wait time
        wait_time = (datetime.utcnow() - order.created_at).total_seconds() / 60
        if wait_time > 30:
            priority_score += 30
        elif wait_time > 20:
            priority_score += 20
        
        # Order type
        if order.order_type == 'room_service':
            priority_score += 10  # Hotel guests priority
        
        # Number of items
        item_count = order.items.count()
        if item_count > 5:
            priority_score += 10
        
        return priority_score
    
    @staticmethod
    def estimate_preparation_time(order):
        """Estimate when order will be ready"""
        
        menu_items = [oi.menu_item for oi in order.items]
        
        # Get max preparation time (items prepared in parallel)
        max_prep_time = max(item.preparation_time or 15 for item in menu_items)
        
        # Add queue time (orders ahead in queue)
        orders_ahead = RestaurantOrder.query.filter(
            RestaurantOrder.status.in_(['pending', 'preparing']),
            RestaurantOrder.created_at < order.created_at
        ).count()
        
        queue_time = orders_ahead * 5  # 5 min per order
        
        return max_prep_time + queue_time
```

---

## 📊 Database Schema Additions

```sql
-- Table Reservations
CREATE TABLE table_reservations (
    id SERIAL PRIMARY KEY,
    hotel_id INTEGER REFERENCES hotels(id),
    table_id INTEGER REFERENCES restaurant_tables(id),
    booking_id INTEGER REFERENCES bookings(id),
    guest_name VARCHAR(100),
    guest_phone VARCHAR(50),
    party_size INTEGER,
    reservation_time TIMESTAMP,
    duration_minutes INTEGER DEFAULT 90,
    status VARCHAR(20) DEFAULT 'confirmed',
    special_requests TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Order Modifiers
CREATE TABLE order_modifiers (
    id SERIAL PRIMARY KEY,
    order_item_id INTEGER REFERENCES restaurant_order_items(id),
    modifier_type VARCHAR(50),  -- 'no_onions', 'extra_cheese', 'cooking_temp'
    modifier_value VARCHAR(100),
    additional_price NUMERIC(5,2) DEFAULT 0
);

-- Daily Sales Summary
CREATE TABLE restaurant_daily_summary (
    id SERIAL PRIMARY KEY,
    hotel_id INTEGER REFERENCES hotels(id),
    summary_date DATE,
    total_orders INTEGER,
    total_revenue NUMERIC(12,2),
    total_tax NUMERIC(10,2),
    total_discount NUMERIC(10,2),
    average_order_value NUMERIC(10,2),
    top_selling_item_id INTEGER REFERENCES menu_items(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Waiter/Server Assignment
ALTER TABLE restaurant_orders ADD COLUMN server_id INTEGER REFERENCES users(id);
ALTER TABLE restaurant_orders ADD COLUMN payment_status VARCHAR(20) DEFAULT 'unpaid';
ALTER TABLE restaurant_orders ADD COLUMN payment_method VARCHAR(50);
ALTER TABLE restaurant_orders ADD COLUMN discount_amount NUMERIC(10,2) DEFAULT 0;
ALTER TABLE restaurant_orders ADD COLUMN tip_amount NUMERIC(10,2) DEFAULT 0;
```

---

## 🚀 Implementation Priority

### **Week 1: Critical Fixes**
1. ✅ Inventory integration (deduct on order)
2. ✅ Accounting entries for orders
3. ✅ Payment status tracking
4. ✅ Server assignment

### **Week 2: Enhanced Features**
1. Table map visualization
2. Table reservations
3. Order modifiers
4. Split bills

### **Week 3: Analytics**
1. Menu engineering report
2. Daily sales summary
3. Popular items report
4. Revenue by meal period

### **Week 4: Advanced**
1. Kitchen display optimization
2. Preparation time tracking
3. Customer preferences
4. Loyalty integration

---

## ⚠️ SAFETY RULES

### **1. Don't Break Room Service**
- Room service orders must continue working
- Keep `RoomServiceOrder` for backward compatibility
- Add new features to `RestaurantOrder`

### **2. Don't Break Accounting**
- Test all journal entries
- Ensure debits = credits
- Verify tax calculations

### **3. Don't Break Inventory**
- Only deduct when order confirmed
- Add back when order cancelled
- Handle partial cancellations

---

## 📝 Summary

### **Current State:**
- ✅ Basic menu management
- ✅ Basic order taking
- ✅ Kitchen display
- ⚠️ No inventory integration
- ⚠️ No accounting integration
- ⚠️ No table management
- ❌ No analytics

### **Needed Improvements:**
1. ✅ Inventory deduction on order
2. ✅ Accounting entries
3. ✅ Payment tracking
4. ✅ Table reservations
5. ✅ Menu engineering
6. ✅ Kitchen efficiency tools

---

**Ready to implement these improvements?** 🚀
