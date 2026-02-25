# Quick Reference Card - Ngenda Hotel PMS

## 🚀 Quick Start

### Access the Application
```
URL: http://127.0.0.1:5000
```

### Default Login Credentials
| Role | Email | Password | Change Required |
|------|-------|----------|-----------------|
| Super Admin | admin@hotel.com | admin123 | ⚠️ YES |
| Manager | manager@demo.com | manager123 | ⚠️ YES |
| Receptionist | receptionist@demo.com | receptionist123 | ⚠️ YES |
| Housekeeping | housekeeping@demo.com | housekeeping123 | ⚠️ YES |
| Kitchen | kitchen@demo.com | kitchen123 | ⚠️ YES |

---

## 🔧 Common Commands

### Start Application
```bash
cd /home/bytehustla/Projects/hotel2/hotel_pms
source venv/bin/activate
python run.py
```

### Production Start
```bash
sudo supervisorctl start hotel_pms
sudo systemctl reload nginx
```

### Database Backup
```bash
pg_dump -U hotel_user hotel_pms_prod | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Database Restore
```bash
gunzip < backup_YYYYMMDD.sql.gz | psql -U hotel_user hotel_pms_prod
```

### View Logs
```bash
# Application logs
tail -f /var/log/hotel_pms/out.log
tail -f /var/log/hotel_pms/err.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Check Service Status
```bash
# Application
sudo supervisorctl status hotel_pms

# Database
sudo systemctl status postgresql

# Web Server
sudo systemctl status nginx
```

### Restart Services
```bash
sudo supervisorctl restart hotel_pms
sudo systemctl restart postgresql
sudo systemctl restart nginx
```

---

## 👥 User Management

### Add New User
1. Login as Manager or Super Admin
2. Go to Settings → Users
3. Click "Add User"
4. Fill in details and select role
5. Save

### Reset User Password
1. Login as Manager
2. Go to Settings → Users
3. Click "Reset Password" on user
4. Copy temporary password
5. Share with user securely

### Change Own Password
1. Click your name (top-right)
2. Select "Change Password"
3. Enter current and new password
4. Save

---

## 🏨 Daily Operations

### Receptionist Tasks

**Check-in Guest:**
1. Bookings → Find booking
2. Click "Check In"
3. Verify guest details
4. Confirm

**Create New Booking:**
1. Bookings → New Booking
2. Search existing guest or create new
3. Select room and dates
4. Save

**Check-out Guest:**
1. Bookings → Find booking
2. Click "Check Out"
3. Process payment
4. Confirm

### Housekeeping Tasks

**View Assigned Rooms:**
1. Housekeeping → My Tasks
2. See room list and status
3. Clean rooms
4. Update status to "Clean"

**Report Maintenance Issue:**
1. Housekeeping → Maintenance
2. Click "Report Issue"
3. Describe problem
4. Submit

### Kitchen Tasks

**View Orders:**
1. Restaurant → Kitchen Display
2. See pending orders
3. Prepare food
4. Mark as "Ready"

---

## 📊 Reports

### Financial Reports
1. Accounting → Financial Reports
2. Select date range
3. View revenue, expenses, profit
4. Export if needed

### Occupancy Report
1. Dashboard → View stats
2. See occupancy rate
3. Check arrivals/departures

### User Activity
1. Settings → Users
2. View last login times
3. Monitor active users

---

## 🚨 Troubleshooting

### "No hotel assigned" error
**Solution:** Logout and login again. Hotel should auto-select.

### Can't access module
**Solution:** Check if your role has permission for that module.

### Login not working
**Solution:** 
1. Verify credentials
2. Check Caps Lock
3. Try password reset

### Slow performance
**Solution:**
1. Check database connections
2. Review error logs
3. Run database optimization: `psql -U hotel_user -d hotel_pms_prod -c "VACUUM ANALYZE;"`

### Backup failed
**Solution:**
1. Check disk space: `df -h`
2. Verify PostgreSQL is running
3. Check backup script permissions

---

## 📞 Emergency Contacts

### Technical Support
- System Admin: [Your contact]
- Database Admin: [Your contact]
- Developer: [Your contact]

### Service Providers
- Hosting: [Provider contact]
- Domain: [Registrar contact]
- SSL: [Certificate provider]

---

## 🔐 Security Reminders

- ✅ Change passwords every 90 days
- ✅ Never share passwords
- ✅ Log out when leaving workstation
- ✅ Report suspicious activity
- ✅ Lock computer when away
- ✅ Use strong passwords

---

## 📅 Maintenance Schedule

### Daily
- [ ] Check error logs
- [ ] Verify backups
- [ ] Monitor disk space

### Weekly
- [ ] Review slow queries
- [ ] Check for updates
- [ ] Review user access

### Monthly
- [ ] Apply security patches
- [ ] Optimize database
- [ ] Test backup restoration
- [ ] Review audit logs

---

## 📚 Documentation

Full documentation available at:
- `PRODUCTION_DEPLOYMENT.md` - Deployment guide
- `SECURITY_CHECKLIST.md` - Security requirements
- `USER_ROLES_CREDENTIALS.md` - User roles
- `DATABASE_INDEXING.md` - Database optimization
- `PASSWORD_MANAGEMENT.md` - Password policies

---

**Quick Reference Card v1.0**  
**Last Updated:** 2026-02-16  
**Print and keep at reception desk**
