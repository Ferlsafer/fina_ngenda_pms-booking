# Password Management Guide

## Overview

The Hotel PMS system provides multiple ways to manage passwords:

1. **Self-Service**: Users can change their own passwords
2. **Manager Reset**: Managers can reset staff passwords
3. **Forgot Password**: Email-based password reset

---

## 1. Change Your Own Password

### How to Change Password

1. **Log in** to the system
2. Click on your **name/email** in the top-right corner
3. Select **"Change Password"** from the dropdown menu
4. Enter your details:
   - Current password
   - New password (minimum 6 characters)
   - Confirm new password
5. Click **"Update Password"**

### Password Requirements

- ✅ Minimum 6 characters
- ✅ Must be different from current password
- ✅ Both "New Password" and "Confirm Password" must match

### Access

**URL:** `/auth/change-password`

**Available to:** All logged-in users

---

## 2. Manager Reset Staff Password

### How Managers Can Reset Staff Passwords

1. **Log in** as Manager or Super Admin
2. Go to **Settings → Users**
3. Find the staff member in the user list
4. Click **"Reset Password"** button
5. A temporary password will be generated and displayed
6. **Share the temporary password** with the staff member securely
7. Staff member must change password on next login

### Security Features

- ✅ Managers can only reset passwords for their hotel staff
- ✅ Super Admins can reset any password
- ✅ Cannot reset your own password this way (use Change Password)
- ✅ Temporary password is randomly generated (8 characters)
- ✅ Confirmation required before reset

### Access

**URL:** `/settings/user/<user_id>/reset-password` (POST)

**Available to:**
- Hotel Managers (for their hotel staff only)
- Super Admins (all users)

---

## 3. Forgot Password (Self-Service Reset)

### How It Works

1. Go to login page
2. Click **"Forgot Password?"**
3. Enter your email address
4. Check email for reset link
5. Click link and enter new password
6. Login with new password

### For Production

The forgot password feature requires email configuration. In production:

1. Configure SMTP settings in `.env`:
   ```
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   MAIL_USE_TLS=True
   ```

2. The system will email a secure reset link to the user

### Access

**URL:** `/auth/forgot-password`

**Available to:** Anyone (no login required)

---

## Password Security Best Practices

### For Users

1. **Use Strong Passwords**
   - Minimum 8 characters (recommended)
   - Mix of uppercase, lowercase, numbers, symbols
   - Avoid personal information
   - Use passphrases (e.g., "Coffee-Train-Blue-Sky")

2. **Protect Your Password**
   - Never share with others
   - Don't write it down
   - Use a password manager
   - Enable 2FA if available

3. **Regular Updates**
   - Change every 90 days
   - Change immediately if compromised
   - Don't reuse old passwords

### For Managers

1. **When Resetting Staff Passwords**
   - Generate temporary password
   - Share securely (in person or encrypted message)
   - Require staff to change on next login
   - Document the reset (for audit trail)

2. **Monitor Account Activity**
   - Review last login dates
   - Deactivate inactive accounts
   - Remove access for departed staff

3. **Role-Based Access**
   - Assign minimum required permissions
   - Regular access reviews
   - Follow principle of least privilege

---

## Technical Implementation

### Password Storage

- Passwords are **hashed** using Werkzeug's `generate_password_hash()`
- Uses **scrypt** or **pbkdf2:sha256** algorithm
- **Never** stored in plain text
- Salt is automatically generated and stored with hash

### Code Examples

#### Change Own Password
```python
from werkzeug.security import generate_password_hash, check_password_hash

# Verify current password
if not check_password_hash(user.password_hash, current_password):
    flash('Current password is incorrect.', 'danger')
    return

# Update to new password
user.password_hash = generate_password_hash(new_password)
db.session.commit()
```

#### Generate Temporary Password
```python
import secrets

# Generate secure random password
temp_password = secrets.token_urlsafe(8)

# Set as user's password
user.password_hash = generate_password_hash(temp_password)
db.session.commit()

# Show to manager (they must share with staff)
flash(f"Temporary password: {temp_password}")
```

#### Password Reset Token
```python
import secrets
import hashlib
from datetime import datetime, timedelta

# Generate token
reset_token = secrets.token_urlsafe(32)
token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
expires_at = datetime.utcnow() + timedelta(hours=24)

# Store hash (not raw token)
user.reset_token = token_hash
user.reset_token_expires = expires_at
db.session.commit()

# Send reset_token in email link
reset_link = url_for('auth.reset_password', token=reset_token, _external=True)
```

---

## Troubleshooting

### "Current password is incorrect"
- Check Caps Lock is off
- Verify you're using the correct password
- If forgotten, use "Forgot Password" or ask manager to reset

### "New password must be different"
- You cannot reuse your current password
- Choose a completely new password

### "Passwords do not match"
- The "New Password" and "Confirm Password" fields must be identical
- Copy/paste carefully or type both fields again

### Manager Cannot Reset Password
- Verify you have Manager or Super Admin role
- Check that staff member is in your hotel
- Super Admin passwords can only be reset by other Super Admins

### Reset Link Expired
- Reset tokens expire after 24 hours
- Request a new reset link
- Old tokens are automatically invalidated

---

## Audit Trail

All password changes are logged:

| Action | Logged Data |
|--------|-------------|
| Password Change | User ID, Timestamp, IP Address |
| Password Reset | Reset by (Manager), User ID, Timestamp |
| Failed Login | Email, Timestamp, IP Address |

Managers can review login activity in **Settings → Users → Last Login** column.

---

## Quick Reference

### URLs

| Action | URL | Method |
|--------|-----|--------|
| Change Password | `/auth/change-password` | GET/POST |
| Forgot Password | `/auth/forgot-password` | GET/POST |
| Reset Password (Token) | `/auth/reset-password/<token>` | GET/POST |
| Manager Reset Staff | `/settings/user/<id>/reset-password` | POST |

### Default Credentials (Change These!)

| Role | Email | Default Password |
|------|-------|------------------|
| Super Admin | admin@hotel.com | admin123 |
| Manager | manager@demo.com | manager123 |
| Receptionist | receptionist@demo.com | receptionist123 |
| Housekeeping | housekeeping@demo.com | housekeeping123 |
| Kitchen | kitchen@demo.com | kitchen123 |

**⚠️ IMPORTANT:** Change all default passwords immediately after first login!

---

**Last Updated:** 2026-02-16
**System:** Ngenda Hotel PMS
