# Inventory & Restaurant Integration - Complete Implementation

## Overview

This implementation connects the Inventory module with the Restaurant/Kitchen module, allowing:
1. **CSRF Fix** - Supplier form now works correctly
2. **Ingredient Management** - Link menu items to inventory ingredients
3. **Stock Tracking** - Kitchen can see which ingredients are linked to menu items
4. **Availability Alerts** - Visual indicators when stock is low for menu items

---

## Fixes Applied

### 1. CSRF Token Missing on Supplier Form ✅

**Problem:** Adding a supplier threw "missing token" error

**Solution:** Added CSRF token to `app/templates/hms/inventory/supplier_form.html`

**File Modified:**
- `app/templates/hms/inventory/supplier_form.html` (line 17)

**Change:**
```html
<form class="card" method="POST" action="{{ url_for('hms.supplier_add') }}">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  <div class="card-body">
```

---

### 2. Inventory-Restaurant Integration ✅

**Problem:** Kitchen couldn't select ingredients from inventory when preparing orders

**Solution:** Created new "Manage Ingredients" feature that links menu items to inventory items

**Files Created:**
1. `app/templates/hms/inventory/menu_ingredients.html` - UI for managing ingredients
2. Routes in `app/hms/routes.py`:
   - `/inventory/menu-ingredients` - View/manage ingredients
   - `/inventory/menu-ingredients/add/<menu_item_id>` - Add ingredient
   - `/inventory/menu-ingredients/remove/<link_id>` - Remove ingredient

**Files Modified:**
1. `app/hms/routes.py` - Added 3 new routes
2. `app/templates/hms/restaurant/menu.html` - Added "Manage Ingredients" button

---

## Features

### Manage Menu Ingredients

**Access:** 
- From Restaurant → Menu → "Manage Ingredients" button
- Direct: `/hms/inventory/menu-ingredients`

**What it does:**
1. **Select Menu Item** - Choose from dropdown of all menu items
2. **View Linked Ingredients** - See all inventory items linked to the menu item
3. **Add Ingredients** - Link new inventory items with quantity needed
4. **Remove Ingredients** - Unlink ingredients from menu item
5. **Stock Availability** - Visual cards showing how many servings can be made

**Stock Indicators:**
- 🟢 **Green** - Enough stock for multiple servings
- 🟡 **Yellow** - Low stock warning
- Shows exact number of servings possible per ingredient

---

## How It Works

### Data Model

Uses existing `MenuItemInventory` model:
```python
class MenuItemInventory(db.Model):
    """Link menu items to inventory items"""
    menu_item_id = db.Column(db.Integer, ForeignKey('menu_items.id'))
    inventory_item_id = db.Column(db.Integer, ForeignKey('inventory_items.id'))
    quantity_needed = db.Column(db.Float)  # Amount needed for ONE serving
```

### Example Usage

**Scenario:** Creating "Burger" menu item

1. Go to **Restaurant → Menu**
2. Click **"Manage Ingredients"**
3. Select **"Burger"** from dropdown
4. Add ingredients:
   - Beef Patty: 0.2 kg
   - Bun: 1 piece
   - Cheese: 0.05 kg
   - Lettuce: 0.03 kg

5. System shows:
   - Current stock for each ingredient
   - How many burgers can be made (limited by lowest stock ingredient)

### Kitchen Integration

When kitchen receives an order:
1. Chef can see which menu items are ordered
2. Each menu item shows linked ingredients
3. Chef can check inventory stock before accepting order
4. System can warn if ingredients are low (future enhancement)

---

## Testing Guide

### Test 1: Add Supplier (CSRF Fix)

1. Login to HMS Admin
2. Go to **Inventory → Suppliers**
3. Click **"Add Supplier"**
4. Fill in form:
   - Company Name: "Test Supplies Ltd"
   - Contact Person: "John Doe"
   - Email: "test@supplies.com"
   - Phone: "+255 123 456 789"
5. Click **"Add Supplier"**
6. ✅ Should save successfully (no CSRF error)

### Test 2: Link Menu Item to Ingredients

1. Go to **Restaurant → Menu**
2. Click **"Manage Ingredients"** (new blue button)
3. Select a menu item (e.g., "Burger")
4. From "Add Ingredient" form:
   - Select inventory item: "Beef Patty"
   - Quantity Needed: 0.2
5. Click **"Add Ingredient"**
6. ✅ Ingredient appears in "Linked Ingredients" table
7. ✅ Stock availability card shows at bottom

### Test 3: View Stock Availability

1. After linking 3-4 ingredients to a menu item
2. Check the "Stock Availability" card at bottom
3. Each ingredient shows:
   - Number of servings possible
   - Green checkmark if stock is good
   - Yellow warning if stock is low

### Test 4: Remove Ingredient

1. In "Linked Ingredients" table
2. Click **"Remove"** button
3. Confirm deletion
4. ✅ Ingredient is removed from list

---

## URLs

| Feature | URL |
|---------|-----|
| Suppliers List | `/hms/inventory/suppliers` |
| Add Supplier | `/hms/inventory/suppliers/add` |
| Manage Ingredients | `/hms/inventory/menu-ingredients` |
| Menu (with new button) | `/hms/restaurant/menu` |

---

## Future Enhancements

### Phase 2 (Recommended)

1. **Automatic Stock Deduction**
   - When order is completed, deduct ingredients from inventory
   - Track actual vs expected usage

2. **Low Stock Alerts**
   - Warn kitchen when menu item ingredients are low
   - Auto-disable menu items when critical ingredients run out

3. **Recipe Costing**
   - Calculate true cost of menu items based on ingredient costs
   - Suggest optimal pricing

4. **Purchase Order Integration**
   - Auto-generate POs when ingredients fall below reorder level
   - Link suppliers to specific ingredients

### Phase 3 (Advanced)

1. **Waste Tracking**
   - Record spoiled/wasted ingredients
   - Adjust stock levels accordingly

2. **Production Planning**
   - Forecast ingredient needs based on bookings
   - Plan purchases for high-occupancy periods

3. **Multi-Recipe Support**
   - Allow multiple recipes per menu item
   - Seasonal recipe variations

---

## Database Schema

### Existing Tables Used

```sql
-- Menu items table
menu_items (
  id, hotel_id, category_id, name, description, 
  price, cost, is_available, ...
)

-- Inventory items table
inventory_items (
  id, hotel_id, category_id, sku, name, 
  current_stock, reorder_level, unit, ...
)

-- Link table (already existed)
menu_item_inventory (
  id, menu_item_id, inventory_item_id, quantity_needed
)
```

### No New Tables Created

The `MenuItemInventory` model already existed - we just added the UI and routes to use it!

---

## Code Changes Summary

### Routes Added (app/hms/routes.py)

```python
@hms_bp.route('/inventory/menu-ingredients')
def manage_menu_ingredients():
    """Display ingredient management UI"""

@hms_bp.route('/inventory/menu-ingredients/add/<int:menu_item_id>', methods=['POST'])
def add_menu_ingredient(menu_item_id):
    """Link ingredient to menu item"""

@hms_bp.route('/inventory/menu-ingredients/remove/<int:link_id>', methods=['POST'])
def remove_menu_ingredient(link_id):
    """Unlink ingredient from menu item"""
```

### Templates Created/Modified

**Created:**
- `app/templates/hms/inventory/menu_ingredients.html`

**Modified:**
- `app/templates/hms/inventory/supplier_form.html` - Added CSRF token
- `app/templates/hms/restaurant/menu.html` - Added "Manage Ingredients" button

---

## Troubleshooting

### Issue: "Manage Ingredients" button not showing

**Solution:** Clear browser cache or hard refresh (Ctrl+F5)

### Issue: No menu items in dropdown

**Solution:** 
1. Create menu items first: Restaurant → Menu → "Add Menu Item"
2. Ensure menu items are not deleted (`deleted_at IS NULL`)

### Issue: No inventory items in dropdown

**Solution:**
1. Create inventory items first: Inventory → Items → "Add Item"
2. Ensure items are not deleted

### Issue: CSRF error when adding supplier

**Solution:**
1. Verify supplier_form.html has CSRF token on line 17
2. Restart the Flask application
3. Clear browser cookies and try again

---

## Support

For issues or questions about this integration:
1. Check this documentation
2. Verify all files were updated correctly
3. Check Flask logs for error messages
4. Ensure database migrations are up to date

---

**Version:** 1.0  
**Last Updated:** March 4, 2026  
**Status:** Production Ready ✅
