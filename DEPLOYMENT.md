# Ngenda Hotel PMS - Deployment Guide

## ⚠️ PostgreSQL Database Required

This application **requires PostgreSQL** database. SQLite is not supported.

## Quick Start Deployment

### 1. Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. Create Database & User

```bash
sudo -u postgres psql

CREATE DATABASE hotel_pms_prod;
CREATE USER hotel_user WITH PASSWORD 'YourSecurePassword123!';
GRANT ALL PRIVILEGES ON DATABASE hotel_pms_prod TO hotel_user;
\c hotel_pms_prod
GRANT ALL ON SCHEMA public TO hotel_user;
\q
```

### 3. Create `.env` File

```bash
cp .env.example .env
nano .env
```

**Edit `.env` with your credentials:**
```env
FLASK_ENV=production
SECRET_KEY=generate-with-python-c-import-secrets-print-secrets.token-hex-32
DATABASE_URL=postgresql://hotel_user:YourSecurePassword123!@localhost/hotel_pms_prod
TZS_TO_USD=2500
```

**Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Initialize Database

```bash
export $(cat .env | xargs)
flask db upgrade
```

### 6. Create Admin User

```bash
python create_admin_user.py
```

### 7. Start Application

**Development:**
```bash
python run.py
```

**Production (Gunicorn):**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

---

## Default Login

- **URL:** http://localhost:5000/hms/login
- **Email:** admin@ngendahotel.com
- **Password:** Admin123!

**⚠️ Change password after first login!**
