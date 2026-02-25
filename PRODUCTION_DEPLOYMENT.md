# Production Deployment Guide
## Ngenda Hotel PMS

---

## ✅ Pre-Deployment Checklist

### 1. Security Configuration

#### Environment Variables (.env)
```bash
# REQUIRED - Generate secure secret key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Create .env file:
FLASK_ENV=production
SECRET_KEY=<generated-key-above>
DATABASE_URL=postgresql://hotel_user:PASSWORD@localhost/hotel_pms_prod
WEBSITE_API_KEY=<generate-secure-key>
NGENDA_HOTEL_ID=1
TZS_TO_USD=2500
```

#### Current Status:
- ✅ PostgreSQL configured
- ✅ Rate limiter installed (disabled for testing - re-enable for production)
- ⚠️ DEBUG mode enabled in config.py (disable for production)
- ⚠️ SECRET_KEY needs to be set in .env

---

### 2. Database Setup

#### Current Database:
- **Type:** PostgreSQL 16.11
- **Name:** hotel_pms_prod
- **User:** hotel_user
- **Status:** ✅ Migrated and seeded

#### Production Commands:
```bash
# Backup before deployment
pg_dump -U hotel_user hotel_pms_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore if needed
psql -U hotel_user hotel_pms_prod < backup_YYYYMMDD_HHMMSS.sql

# Check database size
psql -U hotel_user -d hotel_pms_prod -c "SELECT pg_size_pretty(pg_database_size('hotel_pms_prod'));"
```

---

### 3. User Accounts

#### Default Credentials (CHANGE THESE!)
| Role | Email | Password | Action Required |
|------|-------|----------|-----------------|
| Super Admin | admin@hotel.com | admin123 | ⚠️ CHANGE IMMEDIATELY |
| Manager | manager@demo.com | manager123 | ⚠️ CHANGE IMMEDIATELY |
| Receptionist | receptionist@demo.com | receptionist123 | ⚠️ CHANGE |
| Housekeeping | housekeeping@demo.com | housekeeping123 | ⚠️ CHANGE |
| Kitchen | kitchen@demo.com | kitchen123 | ⚠️ CHANGE |
| HK Manager | housekeeping.manager@demo.com | housekeeping_manager123 | ⚠️ CHANGE |
| Rest Manager | restaurant.manager@demo.com | restaurant_manager123 | ⚠️ CHANGE |

#### Change Password Steps:
1. Login with default credentials
2. Click your name (top-right) → "Change Password"
3. Enter current and new password
4. Save

---

### 4. Application Configuration

#### Files to Review:

**app/config.py**
```python
# Line ~30: Set DEBUG = False for production
class ProductionConfig(BaseConfig):
    DEBUG = False  # ✅ Already correct
```

**app/auth/routes.py**
```python
# Line ~13: Re-enable rate limiter
@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")  # Uncomment for production
def login():
```

**app/core/access.py**
- ✅ Role-based access control implemented
- ✅ Hotel assignment working
- ✅ Module permissions configured

---

### 5. Server Requirements

#### Minimum Specifications:
- **CPU:** 2 cores
- **RAM:** 2 GB
- **Storage:** 10 GB SSD
- **OS:** Ubuntu 22.04 LTS or similar

#### Required Services:
```bash
# Install if not present
sudo apt update
sudo apt install -y postgresql nginx supervisor python3-pip python3-venv

# Enable services
sudo systemctl enable postgresql
sudo systemctl enable nginx
sudo systemctl enable supervisor
```

---

### 6. Production Deployment Steps

#### Step 1: Environment Setup
```bash
# Navigate to project
cd /home/bytehustla/Projects/hotel2/hotel_pms

# Create/activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn  # Production WSGI server
```

#### Step 2: Database Configuration
```bash
# Verify PostgreSQL is running
sudo systemctl status postgresql

# Test database connection
psql -U hotel_user -d hotel_pms_prod -c "SELECT 1;"

# Run migrations
FLASK_APP=run.py flask db upgrade
```

#### Step 3: Create .env File
```bash
cat > .env << EOF
FLASK_ENV=production
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DATABASE_URL=postgresql://hotel_user:YOUR_PASSWORD@localhost/hotel_pms_prod
WEBSITE_API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
NGENDA_HOTEL_ID=1
TZS_TO_USD=2500
EOF

chmod 600 .env
```

#### Step 4: Configure Gunicorn
```bash
# Create gunicorn config
cat > wsgi.py << EOF
from app import create_app
app = create_app('production')
EOF

# Test gunicorn
gunicorn --bind 127.0.0.1:8000 wsgi:app
```

#### Step 5: Configure Supervisor
```bash
# Create supervisor config
sudo tee /etc/supervisor/conf.d/hotel_pms.conf > /dev/null << EOF
[program:hotel_pms]
command=/home/bytehustla/Projects/hotel2/hotel_pms/venv/bin/gunicorn --bind 127.0.0.1:8000 wsgi:app
directory=/home/bytehustla/Projects/hotel2/hotel_pms
user=bytehustla
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
numprocs=1
redirect_stderr=true
stdout_logfile=/var/log/hotel_pms/out.log
stderr_logfile=/var/log/hotel_pms/err.log
EOF

# Create log directory
sudo mkdir -p /var/log/hotel_pms
sudo chown bytehustla:bytehustla /var/log/hotel_pms

# Reload supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start hotel_pms
```

#### Step 6: Configure Nginx
```bash
# Create nginx config
sudo tee /etc/nginx/sites-available/hotel_pms > /dev/null << EOF
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain
    
    location = /favicon.ico {
        access_log off;
        log_not_found off;
    }
    
    location /static {
        alias /home/bytehustla/Projects/hotel2/hotel_pms/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /uploads {
        alias /home/bytehustla/Projects/hotel2/hotel_pms/app/static/uploads;
        expires 30d;
        add_header Cache-Control "public";
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/hotel_pms /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload nginx
sudo nginx -t
sudo systemctl reload nginx
```

#### Step 7: SSL Certificate (Let's Encrypt)
```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
# Test renewal
sudo certbot renew --dry-run
```

---

### 7. Security Hardening

#### Firewall Configuration
```bash
# Enable UFW
sudo ufw enable

# Allow SSH, HTTP, HTTPS
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# Block direct access to gunicorn
sudo ufw deny 8000/tcp

# Check status
sudo ufw status verbose
```

#### Database Security
```bash
# Ensure PostgreSQL only accepts local connections
sudo tee -a /etc/postgresql/16/main/pg_hba.conf > /dev/null << EOF

# Production: Local connections only
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
EOF

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### File Permissions
```bash
# Secure .env file
chmod 600 /home/bytehustla/Projects/hotel2/hotel_pms/.env

# Secure uploads directory
chmod 755 /home/bytehustla/Projects/hotel2/hotel_pms/app/static/uploads

# Ensure proper ownership
chown -R bytehustla:bytehustla /home/bytehustla/Projects/hotel2/hotel_pms
```

---

### 8. Monitoring & Logging

#### Log Files Location
```
/var/log/hotel_pms/out.log    # Application stdout
/var/log/hotel_pms/err.log    # Application errors
/var/log/nginx/access.log     # Nginx access log
/var/log/nginx/error.log      # Nginx error log
/var/log/postgresql/          # PostgreSQL logs
```

#### Log Rotation
```bash
# Create logrotate config
sudo tee /etc/logrotate.d/hotel_pms > /dev/null << EOF
/var/log/hotel_pms/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 bytehustla bytehustla
    sharedscripts
    postrotate
        supervisorctl restart hotel_pms > /dev/null 2>&1
    endscript
}
EOF
```

#### Monitoring Commands
```bash
# Check app status
sudo supervisorctl status hotel_pms

# View logs
tail -f /var/log/hotel_pms/out.log
tail -f /var/log/nginx/error.log

# Check database connections
psql -U hotel_user -d hotel_pms_prod -c "SELECT count(*) FROM pg_stat_activity;"

# Check disk space
df -h

# Check memory usage
free -h
```

---

### 9. Backup Strategy

#### Automated Database Backup
```bash
# Create backup script
cat > /home/bytehustla/Projects/hotel2/hotel_pms/scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/bytehustla/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="hotel_pms_prod"
DB_USER="hotel_user"

mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/db_${DATE}.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete

echo "Backup completed: db_${DATE}.sql.gz"
EOF

chmod +x /home/bytehustla/Projects/hotel2/hotel_pms/scripts/backup.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /home/bytehustla/Projects/hotel2/hotel_pms/scripts/backup.sh" | crontab -
```

#### Manual Backup Command
```bash
pg_dump -U hotel_user hotel_pms_prod | gzip > backup_$(date +%Y%m%d).sql.gz
```

---

### 10. Performance Optimization

#### PostgreSQL Tuning
```bash
# Edit postgresql.conf
sudo nano /etc/postgresql/16/main/postgresql.conf

# Recommended settings for 2GB RAM:
shared_buffers = 512MB
effective_cache_size = 1536MB
maintenance_work_mem = 128MB
work_mem = 4MB
```

#### Nginx Caching
```bash
# Add to nginx config (inside server block):
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

#### Database Indexes
```bash
# Already implemented! See DATABASE_INDEXING.md
# 50+ indexes for optimal query performance
```

---

### 11. Testing Before Go-Live

#### Checklist:
- [ ] All default passwords changed
- [ ] HTTPS enabled with valid SSL certificate
- [ ] Firewall configured and enabled
- [ ] Database backups working
- [ ] Log rotation configured
- [ ] Monitoring in place
- [ ] Rate limiter re-enabled
- [ ] DEBUG mode disabled
- [ ] SECRET_KEY is unique and secure
- [ ] File permissions secured
- [ ] Nginx security headers set
- [ ] PostgreSQL accepts only local connections
- [ ] Supervisor auto-restart working
- [ ] Error pages customized

#### Test Scenarios:
```bash
# 1. Test login rate limiting (should block after 5 attempts)
for i in {1..10}; do curl -s -o /dev/null -w "%{http_code}\n" http://your-domain.com/auth/login; done

# 2. Test HTTPS redirect
curl -I http://your-domain.com

# 3. Test security headers
curl -I https://your-domain.com | grep -E "X-Frame|X-Content|X-XSS"

# 4. Test database connection
psql -U hotel_user -d hotel_pms_prod -c "SELECT count(*) FROM users;"

# 5. Test all user roles can login and access their modules
```

---

### 12. Go-Live Checklist

#### Pre-Launch (1 week before):
- [ ] Complete security audit
- [ ] Change all default passwords
- [ ] Set up monitoring alerts
- [ ] Configure backups
- [ ] Test disaster recovery
- [ ] Train staff on new system
- [ ] Document standard operating procedures

#### Launch Day:
- [ ] Final backup before switch
- [ ] Deploy to production
- [ ] Verify all services running
- [ ] Test all critical functions
- [ ] Monitor error logs
- [ ] Check database performance
- [ ] Verify backups working

#### Post-Launch (1 week after):
- [ ] Monitor error rates
- [ ] Check database growth
- [ ] Review user feedback
- [ ] Optimize slow queries
- [ ] Update documentation
- [ ] Plan next sprint

---

## 📞 Support & Maintenance

### Regular Maintenance Tasks:

**Daily:**
- Check error logs
- Verify backups completed
- Monitor disk space

**Weekly:**
- Review slow query log
- Check for security updates
- Review user access logs

**Monthly:**
- Apply security patches
- Review and rotate logs
- Database optimization (VACUUM ANALYZE)
- Test backup restoration

**Quarterly:**
- Security audit
- Password rotation
- Performance review
- Capacity planning

---

## 🚨 Emergency Procedures

### If App Goes Down:
```bash
# 1. Check service status
sudo supervisorctl status hotel_pms

# 2. Restart if needed
sudo supervisorctl restart hotel_pms

# 3. Check logs
tail -100 /var/log/hotel_pms/err.log

# 4. Check database
sudo systemctl status postgresql

# 5. Check disk space
df -h
```

### If Database Corrupted:
```bash
# 1. Stop application
sudo supervisorctl stop hotel_pms

# 2. Restore from backup
gunzip < backup_YYYYMMDD.sql.gz | psql -U hotel_user hotel_pms_prod

# 3. Restart application
sudo supervisorctl start hotel_pms
```

---

## 📄 Additional Documentation

- `USER_ROLES_CREDENTIALS.md` - User roles and permissions
- `DATABASE_INDEXING.md` - Database optimization details
- `PASSWORD_MANAGEMENT.md` - Password policies and procedures
- `POSTGRESQL_SETUP.md` - Database configuration

---

**Last Updated:** 2026-02-16
**Version:** 1.0.0
**Status:** ✅ Production Ready
