# Production Deployment Checklist

## Quick Start Deployment

Follow these steps to deploy the Ngenda Hotel Booking HMS to production:

### 1. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your production values
nano .env
```

**Required changes in `.env`:**
- `SECRET_KEY` - Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
- `DATABASE_URL` - Your PostgreSQL connection string
- `FLASK_DEBUG=False` - Must be False in production

### 2. Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Install Gunicorn (production server)
pip install gunicorn
```

### 3. Set Up Database

```bash
# Create PostgreSQL database
sudo -u postgres psql
CREATE DATABASE hotel_pms_prod;
CREATE USER booking_app WITH PASSWORD 'your-strong-password';
GRANT ALL PRIVILEGES ON DATABASE hotel_pms_prod TO booking_app;
\q

# Update DATABASE_URL in .env
# Run migrations
flask db upgrade

# Create admin user
python create_admin_user.py
```

### 4. Run with Gunicorn

```bash
# Test run (foreground)
gunicorn -w 4 -b 0.0.0.0:8000 run:app

# Or set up as systemd service (recommended)
sudo nano /etc/systemd/system/booking-hms.service
```

**Systemd service configuration:**
```ini
[Unit]
Description=Ngenda Hotel Booking HMS
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/booking_hms
Environment="PATH=/var/www/booking_hms/venv/bin"
ExecStart=/var/www/booking_hms/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable booking-hms
sudo systemctl start booking-hms
sudo systemctl status booking-hms
```

### 5. Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/booking-hms
```

**Nginx configuration:**
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /static {
        alias /var/www/booking_hms/app/static;
        expires 30d;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/booking-hms /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Install SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## URLs After Deployment

| Service | URL |
|---------|-----|
| **Website** | `https://yourdomain.com/` |
| **HMS Admin** | `https://yourdomain.com/hms/` |
| **Login** | `https://yourdomain.com/hms/login` |

---

## Post-Deployment Verification

### Test Critical Flows
- [ ] Access website: `https://yourdomain.com/`
- [ ] Access HMS: `https://yourdomain.com/hms/`
- [ ] Login with admin credentials
- [ ] Create test user with different role
- [ ] Login as test user, verify role-based redirect
- [ ] Create test booking
- [ ] Upload test file (room image, etc.)
- [ ] Verify database backup script works

### Check Logs
```bash
# Application logs
tail -f /var/www/booking_hms/app.log

# Service logs
journalctl -u booking-hms -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## Detailed Pre-Deployment Checklist

### Environment Setup
- [ ] Copy `.env.example` to `.env`
- [ ] Generate strong SECRET_KEY
- [ ] Configure DATABASE_URL with production credentials
- [ ] Set FLASK_DEBUG=False
- [ ] Verify .env is in .gitignore

### Database Setup
- [ ] Install PostgreSQL
- [ ] Create database: `CREATE DATABASE hotel_pms_prod;`
- [ ] Create user with limited permissions
- [ ] Run migrations: `flask db upgrade`
- [ ] Create admin user: `python create_admin_user.py`

### Server Setup
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Install Gunicorn: `pip install gunicorn`
- [ ] Set up Nginx configuration
- [ ] Configure SSL certificate (Let's Encrypt)
- [ ] Set up systemd service

### Security
- [ ] Change all default passwords
- [ ] Remove test files from production
- [ ] Configure firewall (UFW)
- [ ] Set up fail2ban
- [ ] Verify HTTPS redirect works

### Static Files
- [ ] Ensure uploads folder exists: `app/static/uploads/`
- [ ] Set correct permissions: `chmod 777 app/static/uploads`
- [ ] Configure Nginx to serve static files

---

## Deployment Commands

```bash
# 1. Clone/pull code
cd /var/www/booking_hms
git pull origin main

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
pip install gunicorn

# 4. Run migrations
flask db upgrade

# 5. Restart service
sudo systemctl restart booking-hms

# 6. Check status
sudo systemctl status booking-hms
journalctl -u booking-hms -n 50 --no-pager
```

---

## Rollback Plan

If deployment fails:

```bash
# 1. Stop service
sudo systemctl stop booking-hms

# 2. Restore previous code
cd /var/www/booking_hms
git reset --hard <previous-commit>

# 3. Restore database (if needed)
pg_restore -U booking_app -d hotel_pms_prod /var/backups/booking_hms/latest.dump

# 4. Restart service
sudo systemctl start booking-hms
```

---

## Support Contacts

Document these before going live:

- **Developer:** [Your contact]
- **Server Admin:** [Admin contact]
- **Database Admin:** [DBA contact]

---

## Emergency Procedures

### Site Down
1. Check service: `sudo systemctl status booking-hms`
2. Check logs: `journalctl -u booking-hms -n 100`
3. Restart: `sudo systemctl restart booking-hms`
4. Check database: `pg_isready -h localhost`

### Database Issues
1. Check connection: `psql -U booking_app -d hotel_pms_prod -c "SELECT 1"`
2. Check disk space: `df -h`
3. Restore from backup if needed

### Security Incident
1. Enable maintenance mode
2. Review access logs
3. Change all passwords
4. Review user permissions
5. Update firewall rules

---

## The system is production-ready! 🚀
