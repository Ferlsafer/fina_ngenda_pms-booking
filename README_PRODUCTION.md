# Ngenda Hotel Booking & Management System

**Version:** 1.0.0  
**Type:** Hotel Property Management System (PMS)  
**Status:** Production Ready

---

## Quick Overview

This is a complete hotel management system with:
- Public website for room bookings
- Admin panel for hotel operations
- Role-based access control
- Restaurant POS integration
- Housekeeping management
- Inventory tracking
- Accounting integration

---

## Deployment Instructions

**For the person deploying this system:**

### Step 1: Clone This Repository

```bash
git clone https://github.com/YOUR_USERNAME/booking-hms.git
cd booking-hms
```

### Step 2: Run the Deployment Script

```bash
# Make script executable
chmod +x deploy.sh

# Run deployment (automates everything)
sudo ./deploy.sh
```

**OR** follow manual steps in `DEPLOYMENT_CHECKLIST.md`

### Step 3: Access the System

After deployment:
- **Website:** http://localhost:8000/
- **HMS Admin:** http://localhost:8000/hms/
- **Login:** http://localhost:8000/hms/login

Default admin credentials (CHANGE IMMEDIATELY):
- Email: admin@ngendahotel.com
- Password: (set during deployment)

---

## Project Structure

```
booking-hms/
├── app/                      # Main application
│   ├── __init__.py          # App factory
│   ├── models.py            # Database models
│   ├── hms/                 # Admin panel routes
│   ├── booking/             # Website routes
│   ├── templates/           # HTML templates
│   └── static/              # CSS, JS, images
├── migrations/               # Database migrations
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
├── deploy.sh                # Automated deployment
├── DEPLOYMENT_CHECKLIST.md  # Detailed deployment guide
└── PRODUCTION_READY.md      # Production audit report
```

---

## Technology Stack

- **Backend:** Flask (Python 3.12+)
- **Database:** PostgreSQL 14+
- **Frontend:** Tabler UI (Bootstrap 5)
- **Server:** Gunicorn + Nginx
- **Authentication:** Flask-Login

---

## User Roles

| Role | Access |
|------|--------|
| **Superadmin** | Full system access |
| **Manager** | Dashboard, all operations, user management |
| **Owner** | Dashboard, reports, financial data |
| **Receptionist** | Bookings, rooms, check-in/out |
| **Housekeeping** | Room status, cleaning tasks |
| **Kitchen** | Room service, restaurant orders |
| **Restaurant** | POS, table management |

---

## Key Features

### Public Website
- Room browsing and booking
- Dual currency (TZS/USD)
- Email confirmations
- Payment processing (manual/integration ready)

### Admin Panel (HMS)
- Dashboard with statistics
- Booking management
- Room management
- User management with role assignment
- Restaurant POS
- Housekeeping tasks
- Inventory tracking
- Accounting integration
- Reports

---

## Security Features

- ✅ Password hashing (scrypt)
- ✅ CSRF protection
- ✅ Rate limiting on login
- ✅ Role-based access control
- ✅ Session management
- ✅ SQL injection prevention (SQLAlchemy ORM)

---

## Requirements

- **OS:** Ubuntu 20.04+ (recommended)
- **Python:** 3.12+
- **PostgreSQL:** 14+
- **Nginx:** 1.18+
- **Disk:** 10GB minimum
- **RAM:** 2GB minimum (4GB recommended)

---

## Support

For deployment issues, refer to:
1. `DEPLOYMENT_CHECKLIST.md` - Step-by-step guide
2. `PRODUCTION_READY.md` - Technical details
3. `deploy.sh` - Automated deployment script

---

## License

Proprietary - Ngenda Hotel & Apartments

---

## Changelog

### Version 1.0.0 (February 2026)
- Initial production release
- Complete booking system
- Role-based access control
- Restaurant integration
- Housekeeping module
- Accounting integration
