# Fix Admin Password Reset Issue - PRODUCTION SAFE

## ⚠️ Important: This is NOT a Docker deployment

Your system uses:
- **Systemd service** for process management
- **Gunicorn** as the application server
- **Nginx** as reverse proxy
- **PostgreSQL** database
- **Python virtual environment**

## The Problem
- Admin users have `is_superadmin=True` and `role='manager'`
- The user edit form shows roles from the `roles` table in a dropdown
- No "admin" role existed in the roles table
- You couldn't select a role for admin users, preventing password edits

## ✅ Safe Solution (With Confirmation Prompts)

Both scripts now:
1. **Show what will change BEFORE making changes**
2. **Require you to type 'YES' to confirm**
3. **Do nothing if you don't confirm**
4. **Are read-only until you confirm**

---

## Step-by-Step Deployment

### Step 1: SSH into your server
```bash
ssh your-server
```

### Step 2: Navigate to the application directory
```bash
cd /var/www/booking-hms
```

### Step 3: Activate the virtual environment
```bash
source venv/bin/activate
```

### Step 4: Copy the fix scripts to production
Upload these files to your server:
- `scripts/add_admin_role.py`
- `scripts/update_admin_role.py`

Or if you have git:
```bash
git pull origin main  # or your branch name
```

### Step 5: Run the first script (adds admin role to database)
```bash
python scripts/add_admin_role.py
```

**What you'll see:**
```
This will create the following role in the database:

  Name: admin
  Description: System administrator - full access to all features

This is SAFE and will NOT affect existing users or data.

⚠️  Type 'YES' to confirm creation:
```

**Type:** `YES` and press Enter

**Expected output:**
```
✅ Admin role created successfully!

Role details:
  ID: 6
  Name: admin
  Description: System administrator - full access to all features

Next step: Run 'python scripts/update_admin_role.py'
```

### Step 6: Run the second script (updates admin user)
```bash
python scripts/update_admin_role.py
```

**What you'll see:**
```
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

**Type:** `YES` and press Enter

**Expected output:**
```
✅ Admin user updated successfully!
  New role: admin
  New role_id: 6

🎉 You can now edit the admin user through the User Management UI!
   Go to: Settings → Users → Edit (admin user)
```

### Step 7: Restart the application
```bash
sudo systemctl restart booking-hms
```

### Step 8: Verify the fix
1. Open your browser and go to the HMS admin panel
2. Log in as admin
3. Go to **Settings → Users**
4. Click **Edit** on the admin user
5. You should now see "admin" in the role dropdown
6. Set a new password and click Save

---

## 🔒 Safety Features

### What these scripts do NOT do:
- ❌ Do NOT delete any data
- ❌ Do NOT affect other users
- ❌ Do NOT change passwords
- ❌ Do NOT modify bookings or reservations
- ❌ Do NOT require database downtime
- ❌ Do NOT require application restart (until step 7)

### What these scripts DO:
- ✅ Add ONE new role to the roles table
- ✅ Update ONE user's role assignment
- ✅ Show you exactly what will change
- ✅ Require explicit confirmation
- ✅ Can be safely cancelled at any time

---

## 🚨 Rollback (If Something Goes Wrong)

If you need to undo these changes:

```bash
# Connect to PostgreSQL
sudo -u postgres psql hotel_pms_prod

# Run these SQL commands:
UPDATE users SET role = 'manager', role_id = NULL WHERE email = 'admin@ngendahotel.com';
DELETE FROM roles WHERE name = 'admin';

# Exit psql
\q
```

Then restart the service:
```bash
sudo systemctl restart booking-hms
```

---

## 📋 What Was Changed in the Code

### Modified files:
1. **app/hms/routes.py** - Added 'admin': 95 to ROLE_HIERARCHY (2 locations)

### New files:
1. **scripts/add_admin_role.py** - Creates admin role (with confirmation)
2. **scripts/update_admin_role.py** - Updates admin user (with confirmation)
3. **FIX_ADMIN_PASSWORD_RESET.md** - This documentation

---

## ❓ Troubleshooting

### "No module named 'app'"
Make sure you're in the correct directory and virtualenv is activated:
```bash
cd /var/www/booking-hms
source venv/bin/activate
```

### "Admin role already exists"
This is fine! It means the first script already ran successfully. Proceed to step 6.

### "No admin user found"
Check your admin email in the script. Update this line if needed:
```python
admin_user = User.query.filter_by(email='YOUR_ADMIN_EMAIL').first()
```

### Service won't restart
Check the logs:
```bash
sudo journalctl -u booking-hms -f
```

---

## 📞 Need Help?

If you're unsure about any step:
1. Don't run the script yet
2. Take a screenshot of what you see
3. Share it for review before proceeding

**Remember:** Both scripts show you exactly what they'll do BEFORE making changes, and require you to type 'YES' to confirm.
