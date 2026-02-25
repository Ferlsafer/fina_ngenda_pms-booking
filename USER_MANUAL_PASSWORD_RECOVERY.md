# User Management - Manual Password Recovery

**Date:** February 21, 2026  
**Status:** ✅ **COMPLETE - NO EMAIL REQUIRED**

---

## Overview

Since email recovery is not configured, managers and superadmins can now directly manage user passwords through the Settings interface. This is perfect for internal hotel management systems where IT staff can manually reset passwords.

---

## Features Implemented

### 1. Edit User Details ✅
- **Access:** Settings → Users → Edit button
- **What Can Be Edited:**
  - Name
  - Email
  - Role (within hierarchy limits)
  - Active/Inactive status
  - Password (optional - leave blank to keep current)

### 2. Set Password Directly ✅
- **Access:** Settings → Users → "Set Password" button (yellow)
- **Features:**
  - Set custom password for any user
  - Password confirmation required
  - Minimum 8 characters
  - Respects role hierarchy
  - Instant password update

### 3. Generate Temporary Password ✅
- **Access:** Settings → Users → "Reset" button (outline yellow)
- **Features:**
  - Generates random 8-character password
  - Shows temporary password in flash message
  - Admin copies and shares with user
  - User can change after login

### 4. Delete User ✅
- **Access:** Settings → Users → "Delete" button (red)
- **Features:**
  - Permanent deletion
  - Cannot delete yourself
  - Confirmation dialog
  - Respects role hierarchy

---

## User Management Interface

### Action Buttons

| Button | Color | Purpose |
|--------|-------|---------|
| **Edit** | Blue | Modify user details |
| **Set Password** | Yellow | Set custom password |
| **Reset** | Outline Yellow | Generate temp password |
| **Delete** | Outline Red | Remove user account |

---

## How to Use

### Scenario 1: User Forgot Password

**Steps:**
1. Go to **Settings → Users**
2. Find the user in the list
3. Click **"Set Password"** (yellow button)
4. Enter new password (min 8 chars)
5. Confirm password
6. Click **"Set Password"**
7. Share new password with user securely

**Result:** User can login immediately with new password.

---

### Scenario 2: Create User for New Employee

**Steps:**
1. Go to **Settings → Users**
2. Click **"Add User"**
3. Fill in:
   - Name: John Doe
   - Email: john@hotel.com
   - Password: Welcome123!
   - Role: Receptionist
   - Active: ✓
4. Click **"Create"**

**Result:** New user created and can login immediately.

---

### Scenario 3: Promote Employee

**Steps:**
1. Go to **Settings → Users**
2. Find user (e.g., Receptionist)
3. Click **"Edit"**
4. Change Role to "Manager" (if you have permission)
5. Optionally update password
6. Click **"Update"**

**Result:** User now has manager privileges.

---

### Scenario 4: Reset Password for User Who Forgot

**Steps:**
1. Go to **Settings → Users**
2. Find user
3. Click **"Reset"** button
4. System generates temporary password (e.g., `aB3xK9mP`)
5. Copy the temporary password
6. Tell user: "Your temporary password is: aB3xK9mP"
7. User logs in and changes password

**Result:** User has temporary access, should change password.

---

## Role Hierarchy

### Who Can Do What

| Your Role | Can Create | Can Edit | Can Set Password | Can Delete |
|-----------|-----------|----------|------------------|------------|
| **Superadmin** | Anyone | Anyone | Anyone | Anyone |
| **Owner** | Staff, Receptionist | Staff, Receptionist | Staff, Receptionist | Staff, Receptionist |
| **Manager** | Staff, Receptionist | Staff, Receptionist | Staff, Receptionist | Staff, Receptionist |
| **Receptionist** | Nobody | Nobody | Nobody | Nobody |

### Protection Rules

1. **Can't edit your own role** - Prevents privilege escalation
2. **Can't delete yourself** - Prevents accidental self-deletion
3. **Can't promote above your level** - Maintains hierarchy
4. **Hotel isolation** - Managers only see their hotel users

---

## Security Features

### Password Requirements
- Minimum 8 characters
- Confirmation required
- Secure hashing (werkzeug)
- No plain text storage

### Access Control
- Login required
- Hotel-level filtering
- Role hierarchy enforcement
- CSRF protection on all forms

### Audit Trail
- Password changes logged via flash messages
- User creation/update timestamps in database
- Last login tracking

---

## Best Practices

### For Managers

1. **Use Strong Passwords**
   - Mix of uppercase, lowercase, numbers
   - Example: `Hotel2026!Mbeya`
   - Avoid: `password123`, `admin123`

2. **Share Passwords Securely**
   - In person or via phone
   - Don't email passwords
   - Use secure messaging if remote

3. **Regular Password Reviews**
   - Reset passwords quarterly
   - Remove access for departed employees immediately
   - Review active users monthly

4. **Principle of Least Privilege**
   - Give minimum required permissions
   - Promote gradually as needed
   - Don't make everyone a manager

### For Users

1. **Change Temporary Passwords Immediately**
   - Go to Settings after first login
   - Choose strong personal password
   - Don't share with colleagues

2. **Use Password Manager**
   - Remember complex passwords
   - Generate strong passwords
   - Sync across devices

---

## Troubleshooting

### "Access Denied" When Trying to Set Password

**Cause:** Trying to set password for user with higher/equal role

**Solution:**
- Check your role vs target user's role
- Only superadmins can set passwords for managers
- Ask superadmin to help

---

### "You cannot delete your own account"

**Cause:** Trying to delete yourself

**Solution:**
- This is intentional for safety
- Ask another manager to delete your account if needed

---

### Password Not Working After Reset

**Possible Causes:**
1. User typing wrong password
2. Caps Lock is on
3. Browser auto-fill using old password

**Solutions:**
1. Copy-paste the temporary password
2. Check Caps Lock
3. Clear browser cache/cookies
4. Use incognito mode to test

---

## Comparison: Email vs Manual Recovery

| Feature | Email Recovery | Manual Recovery |
|---------|---------------|-----------------|
| **Setup** | Requires SMTP config | Works immediately |
| **Speed** | User self-service | Requires admin |
| **Security** | Token-based | Admin verification |
| **Audit Trail** | Email logs | Flash messages |
| **Best For** | Large organizations | Small/medium hotels |

**Current System:** Manual (no email configured)  
**Recommendation:** Keep manual for now, add email when needed

---

## API Endpoints

### Set Password (Manual)
```
POST /hms/settings/users/set-password
Body:
  - user_id: int
  - password: string (min 8 chars)
  - confirm_password: string
```

### Reset Password (Generate Temp)
```
POST /hms/settings/users/{user_id}/reset-password
Response: Flash message with temp password
```

### Edit User
```
POST /hms/settings/users
Body:
  - user_id: int (optional for create)
  - name: string
  - email: string
  - password: string (optional for edit)
  - role_id: int
  - active: boolean
```

### Delete User
```
POST /hms/settings/users/{user_id}/delete
```

---

## Future Enhancements

### Planned Features
1. **Bulk Password Reset** - Reset multiple users at once
2. **Password Expiry** - Force password change every 90 days
3. **Login History** - See when users last logged in
4. **Failed Login Alerts** - Notify admin of suspicious activity
5. **Two-Factor Auth** - Optional 2FA for users

### Not Planned (For Now)
1. Self-service password reset (no email)
2. Security questions
3. SMS recovery
4. Biometric authentication

---

## Summary

**Manual password management is now fully functional!**

✅ Managers can set user passwords directly  
✅ Temporary password generation works  
✅ Edit user details (name, email, role)  
✅ Delete users with confirmation  
✅ Role hierarchy enforced  
✅ Hotel-level isolation maintained  

**No email configuration required!**

---

**Generated:** 2026-02-21 10:30 UTC  
**Status:** Production Ready ✅
