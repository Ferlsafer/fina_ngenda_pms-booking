# 🚨 DEPLOYER INSTRUCTIONS: Fix Admin Password Reset

## Issue
Admin cannot reset their own password because the admin role is missing from the roles dropdown in the User Management UI.

## Solution
Add "admin" role to database and update admin user to use it.

---

## 📋 Pre-Deployment Checklist

- [ ] SSH access to production server
- [ ] Root/sudo access
- [ ] Application directory: `/var/www/booking-hms`
- [ ] Service name: `booking-hms`

---

## 🚀 Deployment Steps

### Step 1: Upload Scripts to Server

**Option A: Using Git (Recommended)**
```bash
cd /var/www/booking-hms
git pull origin main
```

**Option B: Using SCP from your local machine**
```bash
# From your local machine (not the server)
scp scripts/check_admin_status.py user@server:/var/www/booking-hms/scripts/
scp scripts/add_admin_role.py user@server:/var/www/booking-hms/scripts/
scp scripts/update_admin_role.py user@server:/var/www/booking-hms/scripts/
```

**Option C: Create files directly on server**
Copy the content of each script and create them using `nano` or `vim`.

---

### Step 2: Run Pre-Check (SAFE - Read Only)

```bash
cd /var/www/booking-hms
source venv/bin/activate
python scripts/check_admin_status.py
```

**Expected output if fix is needed:**
```
1. Admin Role in Database:
   ❌ NOT FOUND - Need to run add_admin_role.py

2. Admin User:
   ✅ FOUND
      ...
      Current role: manager
      Current role_id: None
   
   ⚠️  User needs to be updated to admin role

RECOMMENDED ACTIONS:
1. Run: python scripts/add_admin_role.py
2. Run: python scripts/update_admin_role.py
3. Run: sudo systemctl restart booking-hms
```

---

### Step 3: Add Admin Role to Database

```bash
python scripts/add_admin_role.py
```

**What you'll see:**
```
============================================================
ADD ADMIN ROLE TO DATABASE
============================================================

This will create the following role in the database:

  Name: admin
  Description: System administrator - full access to all features

This is SAFE and will NOT affect existing users or data.

⚠️  Type 'YES' to confirm creation:
```

**Action required:** Type `YES` and press Enter

**Expected output:**
```
✅ Admin role created successfully!

Role details:
  ID: 6
  Name: admin
  Description: System administrator - full access to all features

Next step: Run 'python scripts/update_admin_role.py'
```

---

### Step 4: Update Admin User

```bash
python scripts/update_admin_role.py
```

**What you'll see:**
```
============================================================
UPDATE ADMIN USER
============================================================

Found admin user:

  ID: 1
  Name: Admin User
  Email: admin@ngendahotel.com
  Current role: manager
  Current role_id: None

Will update to:
  New role: admin
  New role_id: 6

⚠️  This will allow editing the admin user through the UI.
⚠️  Type 'YES' to confirm:
```

**Action required:** Type `YES` and press Enter

**Expected output:**
```
✅ Admin user updated successfully!
  New role: admin
  New role_id: 6

🎉 You can now edit the admin user through the User Management UI!
   Go to: Settings → Users → Edit (admin user)
```

---

### Step 5: Restart Service

```bash
sudo systemctl restart booking-hms
```

**Verify service is running:**
```bash
sudo systemctl status booking-hms
```

**Expected output:**
```
● booking-hms.service - Ngenda Hotel Booking HMS
     Active: active (running)
```

---

### Step 6: Verify Fix

1. Open browser and go to: `http://your-server/hms/`
2. Login as admin
3. Go to **Settings → Users**
4. Click **Edit** on the admin user
5. Verify "admin" appears in the Role dropdown
6. Set a new password and click Save

**Expected result:** Password updates successfully with success message.

---

## 🔍 Troubleshooting

### Error: "Failed to create app"
```
❌ ERROR: Failed to create app: ...
```
**Solution:** Make sure virtualenv is activated:
```bash
source venv/bin/activate
```

### Error: "No module named 'app'"
**Solution:** Check you're in the correct directory:
```bash
pwd
# Should show: /var/www/booking-hms
```

### Error: "Admin role already exists"
**Solution:** This is fine! Skip to Step 4.

### Error: "No admin user found"
**Solution:** Check your admin email. The script looks for:
- `admin@ngendahotel.com` OR
- Any user with `is_superadmin=True`

### Service won't start
```bash
# Check logs
sudo journalctl -u booking-hms -f

# Try restarting
sudo systemctl daemon-reload
sudo systemctl restart booking-hms
```

---

## 🚨 Rollback (Emergency)

If something goes wrong, run these commands:

```bash
# Connect to PostgreSQL
sudo -u postgres psql hotel_pms_prod

# In PostgreSQL prompt:
UPDATE users SET role = 'manager', role_id = NULL WHERE email = 'admin@ngendahotel.com';
DELETE FROM roles WHERE name = 'admin';
\q

# Restart service
sudo systemctl restart booking-hms
```

---

## 📞 Support

If you encounter any issues:
1. Take a screenshot of the error
2. Check the logs: `sudo journalctl -u booking-hms -f`
3. Verify database connection: `sudo systemctl status postgresql`

---

## ✅ Success Criteria

- [ ] Pre-check shows admin role exists
- [ ] Admin user has role='admin' and role_id set
- [ ] Service restarted without errors
- [ ] Can edit admin user in UI
- [ ] Can set new password for admin user
- [ ] Can login with new password

---

## 📝 What Changed

### Database Changes
- Added 1 new role: `admin` to `roles` table
- Updated 1 user: admin user's `role` and `role_id` fields

### Code Changes
- Modified: `app/hms/routes.py` (added 'admin': 95 to ROLE_HIERARCHY)

### No Downtime
- Application remains running during script execution
- Brief restart required in final step (~5 seconds)

---

**Estimated time:** 5-10 minutes
**Risk level:** LOW (scripts are read-only until confirmed, changes are minimal)
