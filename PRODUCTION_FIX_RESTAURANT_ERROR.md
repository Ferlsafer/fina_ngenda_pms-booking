# 🚨 CORRECTED: Restaurant Module Fix - Internal Server Error

**Date:** 2026-02-25 (CORRECTED)  
**Priority:** CRITICAL  
**System:** Ngenda Hotel Booking HMS - Restaurant Module  
**Error:** Internal Server Error on `/hms/restaurant`

---

## ✅ ROOT CAUSE IDENTIFIED

**Production is missing the latest database migration!**

Migration **`9cd8334fbff6`** (dated 2026-02-21) has NOT been run on production.

This migration:
1. **DROPS** `updated_at` columns from `menu_categories` and `menu_items` tables
2. **ADDS** payment tracking columns to `restaurant_orders` table:
   - `server_id`
   - `payment_status`
   - `payment_method`
   - `paid_amount`
   - `discount_amount`
   - `tip_amount`
   - `balance_due`

### Why Local Works:
```
Local DB: Migration ran → Payment columns EXIST → Model works ✅
```

### Why Production Fails (500 Error):
```
Production DB: Migration NOT run → Payment columns MISSING
              → SQLAlchemy tries to query non-existent columns
              → CRASH → 500 Error ❌
```

---

## ✅ CORRECT SOLUTION

### Run the Missing Migration on Production

**SSH into server:**
```bash
ssh your-server-ip
cd /var/www/booking-hms
```

**Check current migration status:**
```bash
source venv/bin/activate
flask db current
```

**Expected output:** Production is likely at an older revision (NOT `9cd8334fbff6`)

**Run the migration:**
```bash
flask db upgrade
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade [old_revision] -> 9cd8334fbff6, add_missing_restaurant_order_columns
```

**Verify migration ran:**
```bash
flask db current
```

**Should show:** `9cd8334fbff6 (head)`

**Restart the application:**
```bash
sudo systemctl restart booking-hms
```

---

## ✅ Verify the Fix

**Check service status:**
```bash
sudo systemctl status booking-hms
```

**Test in browser:**
- `https://hotel.ngendagroup.africa/hms/restaurant` → Should load without error
- `https://hotel.ngendagroup.africa/hms/restaurant/menu` → Should show menu
- `https://hotel.ngendagroup.africa/hms/restaurant/pos` → Should show POS

**Test via Python:**
```bash
source venv/bin/activate
python3 << 'EOF'
from app import create_app
from app.models import RestaurantOrder, MenuCategory, MenuItem
app = create_app()
with app.app_context():
    try:
        # Test RestaurantOrder (has payment columns)
        orders = RestaurantOrder.query.count()
        print(f"✓ Restaurant orders: {orders}")
        
        # Test MenuCategory (updated_at should be gone)
        cats = MenuCategory.query.count()
        print(f"✓ Menu categories: {cats}")
        
        # Test MenuItem
        items = MenuItem.query.count()
        print(f"✓ Menu items: {items}")
        
        print("\n✅ All models working - migration successful!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
EOF
```

---

## 📋 Also Run: Roles Seeder

While you're at it, also fix the missing roles issue:

```bash
cd /var/www/booking-hms
source venv/bin/activate
python -m scripts.seed_staff_roles
sudo systemctl restart booking-hms
```

---

## 🔍 How to Verify What Migration Production Is On

**Check alembic_version table:**
```bash
sudo -u postgres psql hotel_pms_prod -c "SELECT * FROM alembic_version;"
```

**Expected before fix:** Some old revision (NOT `9cd8334fbff6`)  
**Expected after fix:** `9cd8334fbff6`

---

## 📝 What NOT to Do

**DO NOT** manually add `updated_at` columns to the models - this is wrong because:
1. The migration REMOVES `updated_at` (it should not exist)
2. The real issue is missing payment columns on `restaurant_orders`
3. Adding `updated_at` would cause MORE mismatches

**DO NOT** run migrations without checking current state first

---

## 📞 If Migration Fails

**Check which migration is failing:**
```bash
flask db upgrade --sql  # Shows SQL that would run
```

**Check for lock issues:**
```bash
sudo -u postgres psql hotel_pms_prod -c "SELECT * FROM pg_locks;"
```

**Force migration (if needed):**
```bash
flask db stamp 9cd8334fbff6  # Marks as run without executing
```

**Then manually add missing columns:**
```sql
-- Connect to database
sudo -u postgres psql hotel_pms_prod

-- Add payment columns to restaurant_orders
ALTER TABLE restaurant_orders ADD COLUMN IF NOT EXISTS server_id INTEGER;
ALTER TABLE restaurant_orders ADD COLUMN IF NOT EXISTS payment_status VARCHAR(20) DEFAULT 'unpaid';
ALTER TABLE restaurant_orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50);
ALTER TABLE restaurant_orders ADD COLUMN IF NOT EXISTS paid_amount NUMERIC(10,2) DEFAULT 0;
ALTER TABLE restaurant_orders ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(10,2) DEFAULT 0;
ALTER TABLE restaurant_orders ADD COLUMN IF NOT EXISTS tip_amount NUMERIC(10,2) DEFAULT 0;
ALTER TABLE restaurant_orders ADD COLUMN IF NOT EXISTS balance_due NUMERIC(10,2) DEFAULT 0;

-- Drop updated_at from menu tables
ALTER TABLE menu_categories DROP COLUMN IF EXISTS updated_at;
ALTER TABLE menu_items DROP COLUMN IF EXISTS updated_at;
ALTER TABLE menu_item_inventory DROP COLUMN IF EXISTS updated_at;

-- Create foreign key
ALTER TABLE restaurant_orders ADD CONSTRAINT restaurant_orders_server_id_fkey 
    FOREIGN KEY (server_id) REFERENCES users(id);
```

---

## ✅ Complete Production Fix Checklist

```bash
# 1. SSH into server
ssh your-server-ip
cd /var/www/booking-hms

# 2. Activate environment
source venv/bin/activate

# 3. Check current migration
flask db current

# 4. Run migration
flask db upgrade

# 5. Verify migration
flask db current  # Should show 9cd8334fbff6

# 6. Seed roles
python -m scripts.seed_staff_roles

# 7. Restart service
sudo systemctl restart booking-hms

# 8. Test in browser
# https://hotel.ngendagroup.africa/hms/restaurant
# https://hotel.ngendagroup.africa/hms/settings/users
```

---

## 📧 Summary for Deployer

```
The restaurant module is broken because production database is missing 
the latest migration (9cd8334fbff6 from Feb 21).

This migration adds payment tracking columns to restaurant_orders table.
The code expects these columns, but they don't exist on production.

Fix: Run "flask db upgrade" on production server, then restart the service.

Also run the role seeder: python -m scripts.seed_staff_roles

See PRODUCTION_FIXES_SUMMARY.md for complete instructions.
```

---

**Document Version:** 2.0 (CORRECTED)  
**Last Updated:** 2026-02-25  
**Applies To:** Production deployment at hotel.ngendagroup.africa  
**Status:** ✅ Root cause identified - missing migration
