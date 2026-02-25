# 🚨 URGENT: Production Fix Required - Missing Staff Roles

**Date:** 2026-02-25  
**Priority:** HIGH  
**System:** Ngenda Hotel Booking HMS  

---

## The Problem

When you try to edit or add staff members in the Settings → Users page, the **role dropdown is empty** on the production server.

**Why:** The deployment script creates the database structure but doesn't populate the default roles (Manager, Receptionist, Housekeeping, Kitchen, etc.).

---

## ✅ Quick Fix (5 Minutes)

### Run These Commands on the Production Server:

```bash
# 1. SSH into server
ssh your-server-ip

# 2. Go to app directory
cd /var/www/booking-hms

# 3. Activate Python environment
source venv/bin/activate

# 4. Run the role seeder
python -m scripts.seed_staff_roles
```

### Expected Output:
```
=== Seeding Staff Roles and Users ===
Using hotel: Ngenda Hotel (ID: 1)

✓ Created role: receptionist
✓ Created role: housekeeping
✓ Created role: kitchen
✓ Created role: housekeeping_manager
✓ Created role: restaurant_manager

=== Complete ===
```

### Then Test:
1. Go to: `http://your-server-ip/hms/settings/users`
2. Click "Add user" or "Edit" on any user
3. **Role dropdown should now show all roles** ✅

---

## 📋 For ALL Future Deployments

I've updated the `deploy.sh` script to automatically run the role seeder. The script now includes:

**Step 7: Creating Default Roles** (runs automatically after creating admin user)

```bash
python -m scripts.seed_staff_roles 2>/dev/null || echo "⚠ Note: Roles may already exist"
```

### Updated Deployment Checklist:

After running `deploy.sh`, verify:

- ✅ Database migrations completed
- ✅ Admin user created  
- ✅ **Default roles seeded** ← NEW STEP
- ✅ Service is running
- ✅ Role dropdown works in Settings → Users

---

## 🔒 Security Note

The seeder creates sample staff users with default passwords. **After running:**

1. **Change all default passwords** in Settings → Users, OR
2. **Delete sample users** (optional - roles will remain)

---

## 📞 If Issues Occur

Check application logs:
```bash
sudo journalctl -u booking-hms -f --no-pager
```

Restart service if needed:
```bash
sudo systemctl restart booking-hms
```

---

## 📄 Full Documentation

See `PRODUCTION_FIX_MISSING_ROLES.md` for detailed troubleshooting and explanations.

---

**Action Required:** Please run the fix commands above ASAP so staff management works properly.
