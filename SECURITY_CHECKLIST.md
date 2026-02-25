# Security Checklist for Production

## 🔒 Critical Security Tasks

### IMMEDIATE (Before First Login)

- [ ] **Change ALL default passwords**
  - [ ] admin@hotel.com (Super Admin)
  - [ ] manager@demo.com (Manager)
  - [ ] receptionist@demo.com (Receptionist)
  - [ ] housekeeping@demo.com (Housekeeping)
  - [ ] kitchen@demo.com (Kitchen)
  - [ ] housekeeping.manager@demo.com (HK Manager)
  - [ ] restaurant.manager@demo.com (Rest Manager)

- [ ] **Secure .env file**
  ```bash
  chmod 600 /home/bytehustla/Projects/hotel2/hotel_pms/.env
  ls -la .env  # Should show: -rw------- 
  ```

- [ ] **Verify SECRET_KEY is unique**
  ```bash
  grep SECRET_KEY .env
  # Should be 64 character hex string, not "change-me" or similar
  ```

---

### HIGH PRIORITY (Day 1)

- [ ] **Enable HTTPS/SSL**
  ```bash
  sudo certbot --nginx -d your-domain.com
  ```

- [ ] **Configure Firewall**
  ```bash
  sudo ufw enable
  sudo ufw allow 22/tcp    # SSH
  sudo ufw allow 80/tcp    # HTTP
  sudo ufw allow 443/tcp   # HTTPS
  sudo ufw deny 8000/tcp   # Block direct app access
  ```

- [ ] **Re-enable Rate Limiter**
  - Edit: `app/auth/routes.py`
  - Uncomment: `@limiter.limit("5 per minute")`

- [ ] **Set DEBUG = False**
  - Verify in: `app/config.py`
  - Should be: `DEBUG = False`

- [ ] **Secure PostgreSQL**
  ```bash
  # Edit pg_hba.conf to allow only local connections
  sudo nano /etc/postgresql/16/main/pg_hba.conf
  ```

---

### MEDIUM PRIORITY (Week 1)

- [ ] **Set up automated backups**
  ```bash
  # Add to crontab
  0 2 * * * /home/bytehustla/Projects/hotel2/hotel_pms/scripts/backup.sh
  ```

- [ ] **Configure log rotation**
  ```bash
  sudo nano /etc/logrotate.d/hotel_pms
  ```

- [ ] **Set up monitoring**
  - [ ] Application monitoring (logs)
  - [ ] Database monitoring (connections, slow queries)
  - [ ] Disk space monitoring
  - [ ] Memory monitoring

- [ ] **Create admin user audit trail**
  - Document who has admin access
  - Set up regular access reviews

- [ ] **Configure email notifications**
  - Set up SMTP for password resets
  - Configure error alerts

---

### ONGOING (Monthly)

- [ ] **Review user access**
  - Check for inactive accounts
  - Remove departed employees
  - Review role assignments

- [ ] **Apply security updates**
  ```bash
  sudo apt update
  sudo apt upgrade
  source venv/bin/activate
  pip list --outdated
  ```

- [ ] **Review error logs**
  ```bash
  tail -1000 /var/log/hotel_pms/err.log | grep -i error
  ```

- [ ] **Test backup restoration**
  ```bash
  gunzip < backup_YYYYMMDD.sql.gz | psql -U hotel_user hotel_pms_prod
  ```

- [ ] **Database optimization**
  ```bash
  psql -U hotel_user -d hotel_pms_prod -c "VACUUM ANALYZE;"
  ```

---

## 🚨 Security Incident Response

### If You Suspect a Breach:

1. **Immediate Actions:**
   ```bash
   # Stop the application
   sudo supervisorctl stop hotel_pms
   
   # Change all admin passwords
   # Review recent login logs
   # Check for unauthorized users
   ```

2. **Investigate:**
   ```bash
   # Check recent logins
   psql -U hotel_user -d hotel_pms_prod -c "SELECT email, created_at, last_login_at FROM users ORDER BY created_at DESC LIMIT 20;"
   
   # Check error logs
   tail -500 /var/log/hotel_pms/err.log
   
   # Check nginx access logs
   tail -500 /var/log/nginx/access.log
   ```

3. **Recover:**
   ```bash
   # Restore from known-good backup
   # Change ALL passwords
   # Review and patch vulnerability
   # Restart services
   ```

---

## 📊 Security Audit Commands

### Quick Security Scan:
```bash
# Check for world-readable files
find /home/bytehustla/Projects/hotel2/hotel_pms -type f -perm -004 | wc -l

# Check for weak file permissions
find /home/bytehustla/Projects/hotel2/hotel_pms -type f -name "*.py" -perm -002

# Check .env permissions
ls -la /home/bytehustla/Projects/hotel2/hotel_pms/.env

# Check for hardcoded passwords
grep -r "password.*=" --include="*.py" . | grep -v "__pycache__" | grep -v "test"

# Check database users
psql -U postgres -c "\du"

# Check open ports
sudo netstat -tulpn | grep LISTEN
```

### User Access Review:
```bash
# List all users with roles
psql -U hotel_user -d hotel_pms_prod -c "SELECT email, role, hotel_id, created_at, active FROM users ORDER BY role, email;"

# Find inactive users (no login in 90 days)
psql -U hotel_user -d hotel_pms_prod -c "SELECT email, last_login_at FROM users WHERE last_login_at < NOW() - INTERVAL '90 days' AND active = true;"

# Find users with multiple failed logins (potential brute force)
# Check application logs for this
```

---

## 🔐 Password Policy

### Requirements:
- Minimum 8 characters
- Mix of uppercase and lowercase
- At least one number
- At least one special character
- Not based on dictionary words
- Changed every 90 days

### Implementation:
```python
# Add to user creation/edit forms
import re

def is_strong_password(password):
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True
```

---

## 📝 Compliance Notes

### Data Protection:
- [ ] Guest data encrypted at rest
- [ ] Payment data handled securely (PCI DSS)
- [ ] Personal data access logged
- [ ] Data retention policy implemented
- [ ] Right to deletion implemented

### Access Control:
- [ ] Role-based access control (RBAC) implemented
- [ ] Least privilege principle followed
- [ ] Access reviews scheduled quarterly
- [ ] Termination procedure documented

### Audit Trail:
- [ ] Login attempts logged
- [ ] Password changes logged
- [ ] Data modifications logged
- [ ] Admin actions logged
- [ ] Logs retained for 1 year

---

## ✅ Final Security Sign-Off

Before going live, confirm:

- [ ] All default passwords changed
- [ ] HTTPS enabled with valid certificate
- [ ] Firewall configured and active
- [ ] Rate limiting enabled
- [ ] DEBUG mode disabled
- [ ] SECRET_KEY is unique and secure
- [ ] Backups configured and tested
- [ ] Monitoring in place
- [ ] Security audit completed
- [ ] Incident response plan documented
- [ ] Staff trained on security procedures

**Signed by:** ___________________  
**Date:** ___________________  
**Role:** ___________________

---

**Last Updated:** 2026-02-16  
**Next Review:** 2026-03-16
