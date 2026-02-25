# User Roles and Credentials

## All Login Credentials

### Administrative Roles

| Role | Email | Password | Access Level |
|------|-------|----------|--------------|
| **Super Admin** | admin@hotel.com | admin123 | Full system access, all hotels |
| **Hotel Manager** | manager@demo.com | manager123 | Full hotel access |

### Staff Roles

| Role | Email | Password | Department |
|------|-------|----------|------------|
| **Receptionist** | receptionist@demo.com | receptionist123 | Front Desk |
| **Housekeeping Staff** | housekeeping@demo.com | housekeeping123 | Housekeeping |
| **Kitchen Staff** | kitchen@demo.com | kitchen123 | Kitchen/Restaurant |
| **Housekeeping Manager** | housekeeping.manager@demo.com | housekeeping_manager123 | Housekeeping Management |
| **Restaurant Manager** | restaurant.manager@demo.com | restaurant_manager123 | Restaurant Management |

---

## Role Permissions Matrix

### Super Admin
- ✅ All hotels and properties
- ✅ All features and modules
- ✅ User management
- ✅ System settings
- ✅ Full reporting

### Hotel Manager
- ✅ Full hotel access
- ✅ All departments
- ✅ Staff management
- ✅ Financial reports
- ✅ Settings for their hotel

### Receptionist
**Primary Duties:** Check-in/out, bookings, guest management

| Module | Permissions |
|--------|-------------|
| Dashboard | View |
| Bookings | View, Create, Edit |
| Guests | View, Create, Edit |
| Rooms | View |
| Restaurant | View, Create orders |
| Accounting | View invoices |

**Can:**
- Create and modify bookings
- Check guests in/out
- Manage guest information
- View room availability
- Create restaurant orders
- View invoices

**Cannot:**
- Delete bookings
- Modify room rates
- Access financial reports
- Manage staff

---

### Housekeeping Staff
**Primary Duties:** Room cleaning, status updates

| Module | Permissions |
|--------|-------------|
| Dashboard | View |
| Housekeeping | View, Edit tasks |
| Rooms | View, Update status |
| Inventory | View (cleaning supplies) |

**Can:**
- View assigned cleaning tasks
- Update room status (Clean/Dirty)
- View cleaning supply inventory
- Report maintenance issues

**Cannot:**
- Create bookings
- Access guest information
- Modify rates
- Access financial data

---

### Kitchen Staff
**Primary Duties:** Prepare food orders, room service

| Module | Permissions |
|--------|-------------|
| Dashboard | View |
| Restaurant | View, Kitchen view |
| Room Service | View, Prepare orders |

**Can:**
- View restaurant orders
- Access kitchen display
- Update order status (Preparing → Ready)
- View room service orders

**Cannot:**
- Modify menu
- Access bookings
- View financial data
- Manage staff

---

### Housekeeping Manager
**Primary Duties:** Manage housekeeping operations

| Module | Permissions |
|--------|-------------|
| Dashboard | View |
| Housekeeping | Full (Create, Edit, Delete) |
| Rooms | View, Update status |
| Staff | View housekeeping staff |
| Inventory | View, Edit |

**Can:**
- All housekeeping staff permissions PLUS:
- Create and assign cleaning tasks
- Manage housekeeping schedule
- View/edit cleaning supply inventory
- View housekeeping staff

**Cannot:**
- Access bookings
- Modify room rates
- Access financial reports

---

### Restaurant Manager
**Primary Duties:** Manage restaurant operations

| Module | Permissions |
|--------|-------------|
| Dashboard | View |
| Restaurant | Full (Create, Edit, Delete) |
| Room Service | Full access |
| Menu | Full (Create, Edit, Delete) |
| Accounting | View restaurant revenue |

**Can:**
- All kitchen staff permissions PLUS:
- Manage menu items and prices
- View restaurant orders
- Manage restaurant staff
- View restaurant revenue reports

**Cannot:**
- Access hotel bookings
- Modify room rates
- Manage housekeeping

---

## Role Assignment

### Add New Staff Member

1. Login as **Hotel Manager** or **Super Admin**
2. Go to **Settings → Users**
3. Click **Add User**
4. Fill in details:
   - Name
   - Email (will be username)
   - Password
   - Role (select from dropdown)
5. Save

### Change User Role

1. Go to **Settings → Users**
2. Click on user
3. Change role dropdown
4. Save changes

---

## Security Best Practices

1. **Change Default Passwords**: All staff should change passwords on first login
2. **Role Principle**: Assign minimum required permissions
3. **Regular Audits**: Review user access quarterly
4. **Inactive Users**: Deactivate accounts for departed staff
5. **Password Policy**: Minimum 8 characters, mix of letters/numbers

---

## Technical Details

### Role Implementation

- Roles stored in `roles` table
- User role in `users.role_id` (foreign key)
- Permissions stored as JSON in `roles.permissions`
- Access control via `@role_required()` decorator

### Adding Custom Roles

```python
from app.models.role import Role

role = Role(
    name='concierge',
    description='Guest services and recommendations',
    permissions={
        'guests': ['view', 'edit'],
        'bookings': ['view'],
        'restaurant': ['view', 'create'],
    }
)
db.session.add(role)
db.session.commit()
```

---

## Quick Reference

### Front Desk Common Tasks
- New Booking: Bookings → New Booking
- Check In: Bookings → Find booking → Check In
- Check Out: Bookings → Find booking → Check Out
- Guest Search: Guests → Search

### Housekeeping Common Tasks
- View Tasks: Housekeeping → My Tasks
- Update Room Status: Housekeeping → Rooms → Update Status
- Report Issue: Maintenance → New Issue

### Kitchen Common Tasks
- View Orders: Restaurant → Kitchen Display
- Update Order: Click order → Mark Ready
- Room Service: Room Service → Orders

---

**Last Updated:** 2026-02-16
**System:** Ngenda Hotel PMS
