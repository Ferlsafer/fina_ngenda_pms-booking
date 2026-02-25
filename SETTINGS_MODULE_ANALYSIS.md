# Settings Module Analysis & Multi-Hotel Management

**Date:** February 21, 2026  
**Status:** ⚠️ **PARTIALLY IMPLEMENTED - NEEDS IMPROVEMENTS**

---

## Executive Summary

The Settings module has **basic multi-hotel support** but lacks critical features for true multi-tenant isolation and self-service hotel management. Password recovery infrastructure exists in the database but no UI or email functionality is implemented.

---

## Current Implementation

### ✅ What's Working

#### 1. Multi-Hotel Data Model
```python
class User:
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=True)
    is_superadmin = Column(Boolean, default=False)
```

- Users are associated with specific hotels
- Superadmins can access all hotels
- Hotel-level filtering in queries

#### 2. Settings Routes
| Route | Purpose | Status |
|-------|---------|--------|
| `/settings` | Settings dashboard | ✅ Working |
| `/settings/users` | User management (CRUD) | ✅ Working |
| `/settings/users/<id>/reset-password` | Admin password reset | ✅ Working |
| `/settings/users/<id>/delete` | Delete user | ✅ Working |
| `/settings/hotel` | Hotel settings | ✅ Working |
| `/settings/roles` | Role management | ✅ Working |

#### 3. User Management Features
- Create staff/managers per hotel
- Assign roles (Manager, Receptionist, Housekeeping, etc.)
- Reset passwords (admin-generated temporary password)
- Delete users
- Activate/deactivate users

#### 4. Password Reset Infrastructure (Database Only)
```python
class User:
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
```

**Migration exists:** `9a0b1c2d3e4f_add_password_reset_fields.py`

---

## ❌ Critical Gaps

### 1. No Self-Service Password Recovery

**Current State:**
- Database columns exist (`reset_token`, `reset_token_expires`)
- No "Forgot Password" link on login page
- No email sending functionality
- No password reset request form
- Admin must manually reset passwords

**Impact:**
- Users can't recover forgotten passwords
- Admin burden for password resets
- No audit trail for reset requests

---

### 2. Incomplete Multi-Hotel Isolation

**Current State:**
```python
# Settings users route shows:
users = User.query.filter_by(hotel_id=hotel_id).all()

# But no check for:
# - Can this manager create other managers?
# - Can this hotel manager delete users?
# - Role hierarchy enforcement
```

**Issues:**
1. **Role Hierarchy Not Enforced**
   - A regular manager can create another manager
   - No restriction on creating users with same/higher role
   - Should prevent: Receptionist creating Manager

2. **Hotel Isolation Gaps**
   - No validation that user can only manage their hotel
   - Superadmin bypass is good, but regular hotel staff checks are weak

3. **No Hotel Creation in Settings**
   - Only superadmins can create hotels (via separate route)
   - Hotel owners can't create new hotel properties
   - No hotel transfer workflow

---

### 3. No Email Configuration

**Current State:**
- No SMTP configuration in `.env`
- No email sending service
- No email templates

**Missing:**
```python
# No implementation of:
- send_password_reset_email()
- send_welcome_email()
- send_user_invitation_email()
```

---

### 4. Missing Role-Based Permissions in Settings

**Current Access Control:**
```python
# In routes.py line 256
'settings': ['manager', 'owner', 'superadmin', 'restaurant_manager', 'housekeeping_manager']
```

**Problem:**
- All these roles have SAME access level
- No granular permissions (view vs create vs delete)
- Manager and Receptionist have different permissions in other modules, but not in settings

---

## Multi-Hotel Management Analysis

### Current Flow

```
Superadmin
├── Can create hotels
├── Can create owners
├── Can create managers for any hotel
└── Can access all hotels

Owner
├── Owns multiple hotels? (owner_id link exists)
├── Can view financial reports
└── Cannot create managers (gap!)

Manager
├── Assigned to ONE hotel (hotel_id)
├── Can create staff for that hotel
├── Can manage hotel settings
└── Cannot access other hotels

Staff (Receptionist, Housekeeping, etc.)
├── Assigned to ONE hotel
├── Limited dashboard access
└── Cannot manage users
```

### Desired Flow (Gaps Identified)

```
Superadmin
├── Create hotels ✅
├── Create owners ✅
├── Assign managers to hotels ✅
└── System-wide oversight ✅

Owner
├── View owned hotels ⚠️ (partial)
├── Create managers for owned hotels ❌ (MISSING)
├── View financial reports ✅
└── Transfer hotel management ❌ (MISSING)

Hotel Manager
├── Create staff (NOT managers) ❌ (NEEDS RESTRICTION)
├── Create receptionists ✅
├── Create housekeeping ✅
├── Manage hotel operations ✅
└── View hotel-only data ✅

Department Managers (Restaurant, Housekeeping)
├── Create department staff only ❌ (NEEDS IMPLEMENTATION)
├── View department data ✅
└── Limited settings access ⚠️
```

---

## Password Recovery Analysis

### Current Implementation (Admin Reset Only)

**Flow:**
1. Manager goes to Settings → Users
2. Clicks "Reset" button next to user
3. System generates random 8-character password
4. Displays temporary password on screen
5. Manager must communicate password to user (in person, phone, etc.)

**Code:**
```python
@hms_bp.route('/settings/users/<int:user_id>/reset-password', methods=['POST'])
def settings_users_reset_password(user_id):
    # Generate temporary password
    import secrets
    temp_password = secrets.token_urlsafe(8)
    
    user.password_hash = generate_password_hash(temp_password)
    db.session.commit()
    
    # Show in flash message (INSECURE - visible to anyone with admin access)
    flash(f"Password reset for {user.name}. Temporary password: {temp_password}", "warning")
```

**Security Issues:**
1. Temporary password shown in plain text
2. No expiration on temporary password
3. No email notification to user
4. No audit log of who requested reset
5. No rate limiting on reset requests

---

### Desired Implementation (Self-Service)

**Flow:**
1. User clicks "Forgot Password" on login page
2. Enters email address
3. System sends reset link via email (not password!)
4. User clicks link (expires in 1 hour)
5. User sets new password
6. Reset token invalidated

**Missing Components:**
```python
# 1. Forgot password route
@hms_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    # Show form, accept email
    # Generate reset token
    # Send email with reset link
    pass

# 2. Reset password route
@hms_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Validate token
    # Show password change form
    # Update password
    # Invalidate token
    pass

# 3. Email service
def send_password_reset_email(user_email, reset_token):
    # SMTP configuration
    # Send email with reset link
    pass
```

---

## Recommendations

### Phase 1: Critical Security Fixes (1-2 hours)

#### 1.1 Add Password Expiration
```python
# In settings_users_reset_password()
from datetime import datetime, timedelta

user.reset_token = secrets.token_urlsafe(32)
user.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
# Don't set password yet - wait for user to reset
```

#### 1.2 Add Audit Logging
```python
# Log password reset requests
audit_log = PasswordResetAudit(
    user_id=user_id,
    requested_by=current_user.id,
    requested_at=datetime.utcnow(),
    ip_address=request.remote_addr
)
db.session.add(audit_log)
```

#### 1.3 Role Hierarchy Enforcement
```python
# Prevent creating users with higher role
def can_create_role(current_user_role, target_role):
    hierarchy = {
        'superadmin': 100,
        'owner': 90,
        'manager': 80,
        'restaurant_manager': 70,
        'housekeeping_manager': 70,
        'receptionist': 60,
        'housekeeping': 50,
        'kitchen': 50,
    }
    return hierarchy.get(current_user_role, 0) > hierarchy.get(target_role, 0)
```

---

### Phase 2: Self-Service Password Recovery (2-3 hours)

#### 2.1 Add Email Configuration
```python
# .env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-password
MAIL_DEFAULT_SENDER=Ngenda Hotel <noreply@ngendahotel.com>
```

#### 2.2 Create Email Service
```python
# app/utils/email.py
from flask_mail import Mail, Message

mail = Mail()

def send_password_reset_email(user, token):
    msg = Message(
        'Password Reset Request - Ngenda Hotel PMS',
        recipients=[user.email],
        html=f'''
        <p>Hello {user.name},</p>
        <p>You requested a password reset.</p>
        <p>Click <a href="{{ url_for('hms.reset_password', token=token, _external=True) }}">here</a> to reset your password.</p>
        <p>This link expires in 1 hour.</p>
        <p>If you didn't request this, ignore this email.</p>
        '''
    )
    mail.send(msg)
```

#### 2.3 Create Forgot Password Routes
```python
@hms_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            send_password_reset_email(user, token)
        
        # Always show same message to prevent email enumeration
        flash('If an account exists with that email, a reset link has been sent.', 'info')
        return redirect(url_for('hms.login'))
    
    return render_template('hms/auth/forgot_password.html')


@hms_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or user.reset_token_expires < datetime.utcnow():
        flash('Invalid or expired reset token.', 'danger')
        return redirect(url_for('hms.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return redirect(url_for('hms.reset_password', token=token))
        
        user.password_hash = generate_password_hash(password)
        user.reset_token = None  # Invalidate token
        user.reset_token_expires = None
        db.session.commit()
        
        flash('Password updated successfully. You can now login.', 'success')
        return redirect(url_for('hms.login'))
    
    return render_template('hms/auth/reset_password.html', token=token)
```

---

### Phase 3: Enhanced Multi-Hotel Management (3-4 hours)

#### 3.1 Owner Hotel Management
```python
@hms_bp.route('/settings/owners/hotels')
@login_required
def owner_hotels():
    """Owner can view their hotels"""
    if current_user.role != 'owner':
        flash('Access denied.', 'danger')
        return redirect(url_for('hms.dashboard'))
    
    hotels = Hotel.query.filter_by(owner_id=current_user.owner_id).all()
    return render_template('hms/settings/owner_hotels.html', hotels=hotels)


@hms_bp.route('/settings/owners/<int:hotel_id>/manager', methods=['POST'])
@login_required
def assign_hotel_manager(hotel_id):
    """Owner can assign manager to their hotel"""
    hotel = Hotel.query.get_or_404(hotel_id)
    
    if hotel.owner_id != current_user.owner_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('hms.dashboard'))
    
    user_id = request.form.get('user_id')
    user = User.query.get_or_404(user_id)
    
    user.hotel_id = hotel_id
    user.role = 'manager'
    user.role_id = get_role_id('manager')
    db.session.commit()
    
    return redirect(url_for('hms.owner_hotels'))
```

#### 3.2 Hotel Creation for Owners
```python
@hms_bp.route('/settings/hotels/create', methods=['GET', 'POST'])
@login_required
def create_hotel():
    """Owner can create new hotel"""
    if current_user.role != 'owner':
        flash('Access denied.', 'danger')
        return redirect(url_for('hms.dashboard'))
    
    if request.method == 'POST':
        hotel = Hotel(
            owner_id=current_user.owner_id,
            name=request.form.get('name'),
            location=request.form.get('location'),
            # ... other fields
        )
        db.session.add(hotel)
        db.session.commit()
        
        return redirect(url_for('hms.owner_hotels'))
    
    return render_template('hms/settings/create_hotel.html')
```

---

## Implementation Priority

### Week 1: Security
1. ✅ Add password expiration (30 min)
2. ✅ Add audit logging (1 hour)
3. ✅ Role hierarchy enforcement (1 hour)
4. ⏳ Email configuration (30 min)

### Week 2: Password Recovery
5. ⏳ Forgot password UI (1 hour)
6. ⏳ Reset password flow (2 hours)
7. ⏳ Email templates (1 hour)

### Week 3: Multi-Hotel
8. ⏳ Owner hotel management (2 hours)
9. ⏳ Hotel creation for owners (2 hours)
10. ⏳ Manager assignment (1 hour)

---

## Security Considerations

### Password Requirements
```python
def is_valid_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain a number"
    return True, ""
```

### Rate Limiting
```python
from flask_limiter import limiter

@hms_bp.route('/forgot-password', methods=['POST'])
@limiter.limit("3 per hour")  # Prevent abuse
def forgot_password():
    # ...
```

### Token Security
```python
# Use secure token generation
token = secrets.token_urlsafe(32)  # 256-bit token

# Set short expiration
expires_in = timedelta(hours=1)

# Invalidate after use
user.reset_token = None
```

---

## Conclusion

The Settings module has a **solid foundation** for multi-hotel management but needs:

1. **Immediate:** Password expiration and audit logging
2. **Short-term:** Self-service password recovery with email
3. **Medium-term:** Enhanced owner hotel management
4. **Long-term:** Full multi-tenant isolation with role hierarchy

**Estimated Implementation Time:** 8-12 hours total

---

**Generated:** 2026-02-21  
**Analyst:** Automated Code Review
