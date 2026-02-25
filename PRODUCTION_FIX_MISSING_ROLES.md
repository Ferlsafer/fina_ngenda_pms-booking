# 🔧 Production Fix: Missing Staff Roles

## Problem Summary

**Issue:** When editing staff in Settings → Users, the role dropdown is empty on production.

**Root Cause:** The database `roles` table exists but contains no data. The deployment script creates the admin user but doesn't populate the default roles (Manager, Receptionist, Housekeeping, Kitchen, etc.).

---

## ✅ Solution: Run the Role Seeder

### Step-by-Step Instructions

**1. SSH into the production server**
```bash
ssh your-server-ip
```

**2. Navigate to the application directory**
```bash
cd /var/www/booking-hms
```

**3. Activate the Python virtual environment**
```bash
source venv/bin/activate
```

**4. Run the staff roles seeder script**
```bash
python -m scripts.seed_staff_roles
```

**Expected Output:**
```
=== Seeding Staff Roles and Users ===

Using hotel: Ngenda Hotel (ID: 1)

✓ Created role: receptionist
✓ Created role: housekeeping
✓ Created role: kitchen
✓ Created role: housekeeping_manager
✓ Created role: restaurant_manager

✓ Created user: Sarah Johnson (receptionist@demo.com) - Front desk receptionist
✓ Created user: Maria Garcia (housekeeping@demo.com) - Housekeeping staff
✓ Created user: John Chef (kitchen@demo.com) - Kitchen staff
✓ Created user: Linda Smith (housekeeping.manager@demo.com) - Housekeeping manager
✓ Created user: Robert Brown (restaurant.manager@demo.com) - Restaurant manager

=== Staff Credentials ===

Role                  | Email                              | Password
--------------------------------------------------------------------------------
receptionist          | receptionist@demo.com              | receptionist123
housekeeping          | housekeeping@demo.com              | housekeeping123
kitchen               | kitchen@demo.com                   | kitchen123
housekeeping_manager  | housekeeping.manager@demo.com      | hkmanager123
restaurant_manager    | restaurant.manager@demo.com        | restmanager123

=== Complete ===
```

**5. Verify the fix**
```bash
# Optional: Check roles in database
python -c "from app import create_app; from app.extensions import db; from app.models import Role; app = create_app(); app.app_context().push(); roles = Role.query.all(); print(f'Roles in database: {len(roles)}'); [print(f'  - {r.name}') for r in roles]"
```

Expected output should show 5+ roles.

**6. Test in the browser**
- Go to: `http://your-server-ip/hms/settings/users`
- Click "Add user" or "Edit" on any user
- The role dropdown should now show all available roles

---

## 📋 For Future Deployments

### Update the Deployment Script

Add this step to `deploy.sh` after "Step 6: Creating Admin User":

```bash
echo -e "${YELLOW}Step 7: Creating Default Roles...${NC}"
source venv/bin/activate
python -m scripts.seed_staff_roles || echo -e "${YELLOW}⚠ Role seeding skipped (roles may already exist)${NC}"
echo -e "${GREEN}✓ Default roles created${NC}"
```

### OR Create a One-Line Setup Command

For quick production setup, run all post-deployment tasks:

```bash
cd /var/www/booking-hms && source venv/bin/activate && python -m scripts.seed_staff_roles
```

---

## 🔒 Security Note

The seeder script creates sample staff users with default passwords. **After running this script:**

1. **Change all default passwords** immediately
2. **Or delete the sample users** if not needed:
   ```bash
   python -c "
   from app import create_app, db
   from app.models import User
   app = create_app()
   with app.app_context():
       sample_emails = ['receptionist@demo.com', 'housekeeping@demo.com', 'kitchen@demo.com', 
                       'housekeeping.manager@demo.com', 'restaurant.manager@demo.com']
       for email in sample_emails:
           user = User.query.filter_by(email=email).first()
           if user:
               db.session.delete(user)
               print(f'Deleted: {email}')
       db.session.commit()
       print('Sample users deleted.')
   "
   ```

The **roles will remain** in the database even if you delete the sample users.

---

## 📞 Troubleshooting

### Error: "No module named 'scripts.seed_staff_roles'"
**Fix:** Make sure you're in the correct directory:
```bash
cd /var/www/booking-hms
python -m scripts.seed_staff_roles
```

### Error: "DATABASE_URL must be set"
**Fix:** The `.env` file should already exist from deployment. Verify:
```bash
ls -la .env
cat .env | grep DATABASE_URL
```

### Error: "No hotel found"
**Fix:** The seeder needs a hotel to exist first. Check if hotel exists:
```bash
python -c "from app import create_app, db; from app.models import Hotel; app = create_app(); app.app_context().push(); print(f'Hotels: {Hotel.query.count()}')"
```

If no hotel exists, the deployment may have failed. Re-run `deploy.sh` or create a hotel manually.

### Roles still not showing after running seeder
**Fix:** Restart the application:
```bash
sudo systemctl restart booking-hms
```

---

## ✅ Checklist for Deployer

After every deployment, verify:

- [ ] Database migrations completed: `flask db upgrade`
- [ ] Admin user created
- [ ] **Roles seeded:** `python -m scripts.seed_staff_roles`
- [ ] Service is running: `sudo systemctl status booking-hms`
- [ ] Can access HMS: `http://server-ip/hms/`
- [ ] **Role dropdown works** in Settings → Users

---

## 📧 Contact

If issues persist, check application logs:
```bash
sudo journalctl -u booking-hms -f --no-pager
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-25  
**Applies To:** All production deployments after initial setup
