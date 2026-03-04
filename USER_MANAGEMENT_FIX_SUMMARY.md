# User Management Fix - Superadmin Role Issue

## Problem

Superadmin and admin users could edit other users' information, but **could not update their own profile** because:

1. The 'admin' and 'superadmin' roles were missing from the database `roles` table
2. The superadmin user had `role_id: NULL` (not linked to any role in the database)
3. When editing, the role dropdown couldn't select 'superadmin' because it didn't exist
4. Role selection was mandatory, blocking the form submission

## Solution Applied

### 1. Added Missing Roles to Database

Created `add_admin_roles.py` script that:
- Adds 'superadmin' role (ID: 6)
- Adds 'admin' role (ID: 7)
- Updates existing superadmin users to link to the new role

**Run once:**
```bash
source venv/bin/activate
python3 add_admin_roles.py
```

### 2. Fixed Backend Validation (`app/hms/routes.py`)

Updated the user update logic to:
- Allow editing users without changing their role (keeps existing role if dropdown is empty)
- This prevents superadmin from being forced to select a different role when editing themselves

**Changes:**
```python
# Before: Role always required
if not role_id:
    flash("Role is required.", "danger")

# After: Role optional when editing (keeps existing)
if user_id:
    if not role_id and user_to_edit.role_id:
        role_id = user_to_edit.role_id  # Keep existing
```

### 3. Fixed Frontend Template (`app/templates/hms/settings/users.html`)

Updated JavaScript to:
- Pass `data-role-name` attribute along with `data-role`
- Dynamically add role option to dropdown if not found (handles superadmin case)

**Changes:**
```javascript
// If role wasn't found in dropdown (e.g., superadmin), add it
if (roleSelect.value === '' && roleName) {
    var option = document.createElement('option');
    option.value = role;
    option.text = roleName;
    option.selected = true;
    roleSelect.add(option);
}
```

## Verification

### Before Fix
```
=== Available Roles ===
  ID: 1, Name: receptionist
  ID: 2, Name: housekeeping
  ID: 3, Name: kitchen
  ID: 4, Name: housekeeping_manager
  ID: 5, Name: restaurant_manager

Superadmin user:
  Role: superadmin
  Role ID: None  ❌ NULL - not linked to database role
```

### After Fix
```
=== All Roles ===
  ID: 1, Name: receptionist
  ID: 2, Name: housekeeping
  ID: 3, Name: kitchen
  ID: 4, Name: housekeeping_manager
  ID: 5, Name: restaurant_manager
  ID: 6, Name: superadmin  ✓ Added
  ID: 7, Name: admin  ✓ Added

Superadmin user:
  Role: superadmin
  Role ID: 6  ✓ Linked to database role
```

## Testing

1. **Login as superadmin**: `admin@hotel.com`
2. **Go to**: Settings → Users
3. **Click "Edit"** on your own profile (the one with "You" label)
4. **Verify**:
   - Role dropdown shows "superadmin" selected
   - You can change your name/email
   - You can change password (optional)
   - Form submits successfully

## Files Modified

1. `add_admin_roles.py` - New script to add admin/superadmin roles
2. `app/hms/routes.py` - Fixed role validation logic, added error handling
3. `app/templates/hms/settings/users.html` - Fixed JavaScript to handle missing roles

### Changes in `app/hms/routes.py`:

1. **Role validation fix** (lines 3772-3786):
   - Allow editing users without changing role (keeps existing role if dropdown empty)
   - Prevents superadmin from being forced to select different role

2. **Duplicate email check** (lines 3793-3806):
   - Check for existing email before creating/updating
   - Show friendly error message instead of database error

3. **Hotel validation** (lines 3825-3828):
   - Validate hotel_id exists before creating user
   - Prevents foreign key constraint violations

4. **Error handling** (lines 3845-3857):
   - Try/except around database commit
   - Rollback on error
   - User-friendly error messages for duplicate emails, unique constraints

## Deployment

### For Local/Development
```bash
# Run the role addition script
source venv/bin/activate
python3 add_admin_roles.py

# Restart the app
python3 run.py
```

### For Production
```bash
# SSH to server
cd /var/www/booking-hms

# Activate venv
source venv/bin/activate

# Pull changes
git pull

# Run the role addition script
python3 add_admin_roles.py

# Restart service
sudo systemctl restart booking-hms
```

## Notes

- The `add_admin_roles.py` script is **idempotent** - safe to run multiple times
- It only adds roles if they don't exist
- It only updates users if their role_id is NULL or incorrect
- No data loss - only adds missing roles and links existing users

## Related Issues Fixed

✅ Superadmin can now edit their own profile
✅ Admin role available for future use
✅ Role dropdown works for all users including superadmin
✅ No more "Role is required" error when editing own profile
✅ Role hierarchy still enforced (can't assign higher roles)
✅ Better error handling for duplicate emails
✅ Proper error messages instead of Internal Server Error
✅ Hotel validation before creating users
✅ All form labels are now highly visible (dark color)
✅ Badge text is now readable (white text on colored backgrounds)
