# Ngenda Hotel Booking & Management System

**Production Deployment Package**  
**Version:** 1.0.0  
**Last Updated:** February 2026

---

## 🚀 Quick Deployment (Automated)

**For the person deploying this system:**

### Prerequisites
- Ubuntu 20.04+ server (or similar Linux)
- Internet connection
- Root/sudo access

### Deployment Steps

```bash
# 1. Clone this repository
git clone https://github.com/YOUR_USERNAME/booking-hms.git
cd booking-hms

# 2. Make deployment script executable
chmod +x deploy.sh

# 3. Run automated deployment (takes 5-10 minutes)
sudo ./deploy.sh
```

That's it! The script will:
- ✅ Install all dependencies (Python, PostgreSQL, Nginx)
- ✅ Create database and user
- ✅ Set up Python virtual environment
- ✅ Install application dependencies
- ✅ Run database migrations
- ✅ Create admin user
- ✅ Configure Nginx web server
- ✅ Set up systemd service
- ✅ Start the application

### After Deployment

The script will display:
- Access URLs (website and admin panel)
- Database credentials (saved in `.db_credentials`)
- Log file location

**Default access:**
- Website: `http://your-server-ip/`
- HMS Admin: `http://your-server-ip/hms/`
- Login: `http://your-server-ip/hms/login`

---

## 📋 Manual Deployment

If you prefer manual deployment, follow:
- **`DEPLOYMENT_CHECKLIST.md`** - Step-by-step checklist
- **`PRODUCTION_READY.md`** - Technical details and configurations

---

## 📁 What's Included

| File/Folder | Purpose |
|-------------|---------|
| `app/` | Main application code |
| `migrations/` | Database schema migrations |
| `deploy.sh` | Automated deployment script ⭐ |
| `DEPLOYMENT_CHECKLIST.md` | Manual deployment guide |
| `PRODUCTION_READY.md` | Production audit report |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variables template |
| `README_PRODUCTION.md` | This file |

---

## 🔐 Security Notes

### What's Safe to Commit to GitHub
- ✅ All application code
- ✅ Database migrations (schema only)
- ✅ Templates and static files
- ✅ Configuration examples

### What's NOT in GitHub (Configured During Deployment)
- ❌ `.env` file (contains secrets)
- ❌ Database credentials
- ❌ SECRET_KEY
- ❌ Passwords

These are generated and configured by the deployment script.

---

## 🛠️ System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Ubuntu 20.04 | Ubuntu 22.04 LTS |
| **RAM** | 2 GB | 4 GB |
| **Disk** | 10 GB | 20 GB+ |
| **CPU** | 1 core | 2+ cores |

---

## 📊 User Roles

| Role | Dashboard | Access |
|------|-----------|--------|
| **Superadmin** | Main | Full system access |
| **Manager** | Main | All operations + user management |
| **Owner** | Main | Reports + financial data |
| **Receptionist** | Bookings | Front desk operations |
| **Housekeeping** | Housekeeping | Room status & tasks |
| **Kitchen** | Kitchen | Room service & restaurant |
| **Restaurant** | Restaurant | POS & table management |

---

## 🔧 Common Commands

```bash
# View application logs
sudo journalctl -u booking-hms -f

# Restart service
sudo systemctl restart booking-hms

# Check service status
sudo systemctl status booking-hms

# View database credentials
cat /var/www/booking-hms/.db_credentials

# Backup database
sudo -u postgres pg_dump hotel_pms_prod > backup.sql
```

---

## 🆘 Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u booking-hms -n 50

# Check database connection
sudo -u postgres psql -c "SELECT 1"

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Can't Access Website
```bash
# Check if Nginx is running
sudo systemctl status nginx

# Check firewall
sudo ufw status

# Check if app is listening
sudo netstat -tlnp | grep 8000
```

### Database Issues
```bash
# Connect to database
sudo -u postgres psql hotel_pms_prod

# Check tables
\dt

# Exit
\q
```

---

## 📞 Support

For issues during deployment:

1. Check logs: `sudo journalctl -u booking-hms -f`
2. Review `DEPLOYMENT_CHECKLIST.md` for detailed steps
3. Review `PRODUCTION_READY.md` for technical details

---

## ✅ Post-Deployment Checklist

After successful deployment:

- [ ] Access website and verify it loads
- [ ] Access HMS admin panel
- [ ] Login with admin credentials
- [ ] Change admin password immediately
- [ ] Create test user with different role
- [ ] Test role-based access
- [ ] Configure SSL certificate: `sudo certbot --nginx`
- [ ] Set up firewall: `sudo ufw enable`
- [ ] Configure database backups
- [ ] Document admin credentials securely

---

## 🎯 Next Steps After Deployment

1. **SSL Certificate (HTTPS)**
   ```bash
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```

2. **Firewall Configuration**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 22/tcp
   sudo ufw enable
   ```

3. **Database Backups**
   - See `DEPLOYMENT_CHECKLIST.md` for backup script

4. **Monitoring**
   - Set up log monitoring
   - Configure alerts (optional)

---

## 📝 Version History

### v1.0.0 (February 2026)
- Initial production release
- Complete booking system
- Role-based access control
- Restaurant POS integration
- Housekeeping module
- Inventory management
- Accounting integration
- Automated deployment script

---

## 📄 License

Proprietary - Ngenda Hotel & Apartments

**All rights reserved.**

---

## 🎉 Ready to Deploy!

The system is production-ready. Follow the Quick Deployment steps above.

**Need help?** Check `DEPLOYMENT_CHECKLIST.md` for detailed instructions.

**The deployment script automates everything - just run `sudo ./deploy.sh`!** 🚀
