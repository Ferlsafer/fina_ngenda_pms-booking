
# Hotel PMS — Deployment Guide (Contabo VPS)

## What you need before starting
- A Contabo VPS running **Ubuntu 22.04**
- SSH access as `root`
- The project files (zip or git clone)
- Your email/SMTP credentials

---

## Step 1 — Upload the project to the server

**Option A — Git (recommended)**
```bash
# on the server
git clone https://github.com/YOUR_ORG/hms.git /tmp/hms
```

**Option B — Upload a zip**
```bash
# from your local machine
scp hms_finale-main.zip root@YOUR_SERVER_IP:/tmp/
# on the server
unzip /tmp/hms_finale-main.zip -d /tmp/hms
```

---

## Step 2 — Create the .env file

```bash
cd /tmp/hms
cp .env.example .env
nano .env
```

Fill in these values:

| Variable | What to put |
|---|---|
| `SECRET_KEY` | Any long random string, e.g. run `openssl rand -hex 32` |
| `DATABASE_URL` | `postgresql://hms_user:YOUR_DB_PASS@localhost/hms_db` (pick any password) |
| `MAIL_PASSWORD` | Your SMTP password |
| Everything else | Leave defaults or adjust as needed |

Save and close (`Ctrl+X`, `Y`, `Enter`).

---

## Step 3 — Edit the Nginx config with your domain/IP

```bash
nano /tmp/hms/deploy/hms.nginx
```

Change `YOUR_DOMAIN_OR_IP` on line 3 to either:
- Your server's IP address (e.g. `85.215.xxx.xxx`), or
- Your domain name (e.g. `pms.ngendagroup.africa`)

---

## Step 4 — Run the deploy script

```bash
bash /tmp/hms/deploy/deploy.sh
```

The script will automatically:
1. Install Python 3.12, PostgreSQL, Nginx
2. Create the database and database user
3. Copy the app to `/var/www/hms`
4. Create a Python virtual environment and install packages
5. Run database migrations
6. Create the superadmin account
7. Start the app as a background service (systemd)
8. Configure Nginx as the reverse proxy

**This takes about 3–5 minutes.**

---

## Step 5 — Open the app

Visit `http://YOUR_SERVER_IP` in a browser.

Log in at `http://YOUR_SERVER_IP/hms/login`:
- Email: `admin@hotel.com`
- Password: `admin123`

**Change this password immediately** after first login.

---

## Step 6 — Set up HTTPS (optional but recommended)

If you have a domain name pointed to the server:

```bash
certbot --nginx -d YOUR_DOMAIN
```

Follow the prompts. Certbot handles everything automatically.

---

## Useful commands after deployment

```bash
# Check app status
systemctl status hms

# View live logs
journalctl -u hms -f

# Restart the app (e.g. after changing .env)
systemctl restart hms

# View Nginx logs
tail -f /var/log/nginx/error.log
tail -f /var/log/hms/error.log
```

---

## Updating the app later

```bash
# Copy new files
rsync -a --exclude='.git' --exclude='venv' /tmp/hms_new/ /var/www/hms/

# Install any new packages
/var/www/hms/venv/bin/pip install -r /var/www/hms/requirements.txt

# Apply DB migrations
cd /var/www/hms && /var/www/hms/venv/bin/flask --app wsgi:app db upgrade

# Restart
systemctl restart hms
```

---

## Architecture overview

```
Internet → Nginx (port 80/443) → Gunicorn (port 8000) → Flask app
                                                        ↓
                                                   PostgreSQL
```

- **Nginx** handles SSL, static files, and forwards requests to Gunicorn
- **Gunicorn** runs 4 worker processes of the Flask app
- **Systemd** keeps Gunicorn running and restarts it on crash
- **PostgreSQL** stores all data
