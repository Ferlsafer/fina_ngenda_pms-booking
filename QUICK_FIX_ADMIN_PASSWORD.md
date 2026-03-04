# 🚨 QUICK START: Fix Admin Password Reset

## Your System (NOT Docker)
- Uses: Systemd + Gunicorn + Nginx + PostgreSQL
- App directory: `/var/www/booking-hms`
- Service name: `booking-hms`

---

## 🔧 Fix in 3 Steps (5 minutes)

### Step 1: Check current status (SAFE - makes no changes)
```bash
cd /var/www/booking-hms
source venv/bin/activate
python scripts/check_admin_status.py
```

This shows:
- Whether admin role exists
- Current admin user configuration
- What needs to be fixed

---

### Step 2: Apply the fix (requires confirmation)

**Option A: Automated script (recommended)**
```bash
bash scripts/fix_admin_password.sh
```

**Option B: Manual step-by-step**
```bash
# Add admin role to database
python scripts/add_admin_role.py
# (shows what will change, type YES to confirm)

# Update admin user
python scripts/update_admin_role.py
# (shows what will change, type YES to confirm)
```

---

### Step 3: Restart and test
```bash
# Restart the service
sudo systemctl restart booking-hms

# Test in browser:
# 1. Go to Settings → Users
# 2. Click "Edit" on admin user
# 3. You should see "admin" in the role dropdown
# 4. Set new password and save
```

---

## ✅ What This Fix Does

1. **Adds 'admin' role** to the roles table (ID: 6)
2. **Updates admin user** to use the admin role
3. **Allows editing** admin users through the UI

## ❌ What This Fix Does NOT Do

- Does NOT delete any data
- Does NOT affect other users
- Does NOT change passwords automatically
- Does NOT require downtime
- Does NOT modify bookings

---

## 🚨 Rollback (if needed)

```bash
sudo -u postgres psql hotel_pms_prod

# In PostgreSQL:
UPDATE users SET role = 'manager', role_id = NULL 
WHERE email = 'admin@ngendahotel.com';

DELETE FROM roles WHERE name = 'admin';

# Exit and restart:
\q
sudo systemctl restart booking-hms
```

---

## 📁 Files Created

- `scripts/check_admin_status.py` - Pre-check (SAFE, read-only)
- `scripts/add_admin_role.py` - Add admin role (requires YES confirmation)
- `scripts/update_admin_role.py` - Update admin user (requires YES confirmation)
- `scripts/fix_admin_password.sh` - Automated script
- `FIX_ADMIN_PASSWORD_RESET.md` - Full documentation

## 📝 Files Modified

- `app/hms/routes.py` - Added 'admin': 95 to ROLE_HIERARCHY

---

## ❓ Questions?

1. Run the pre-check first: `python scripts/check_admin_status.py`
2. Review what will change before confirming
3. Both scripts show exact changes and require 'YES' to proceed
4. You can cancel anytime with Ctrl+C

**Remember:** This is production-safe with confirmation prompts!
