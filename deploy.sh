#!/bin/bash
# Ngenda Hotel Booking HMS - Automated Deployment Script
# This script automates the entire deployment process

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Ngenda Hotel HMS - Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Please run as root (sudo ./deploy.sh)${NC}"
    exit 1
fi

# Configuration
APP_NAME="booking-hms"
APP_DIR="/var/www/booking-hms"
DB_NAME="hotel_pms_prod"
DB_USER="booking_app"
SYSTEMD_SERVICE="booking-hms"

echo -e "${YELLOW}Step 1: Installing System Dependencies...${NC}"
apt update
apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx supervisor
echo -e "${GREEN}✓ System dependencies installed${NC}"
echo ""

echo -e "${YELLOW}Step 2: Setting Up Python Virtual Environment...${NC}"
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
echo -e "${GREEN}✓ Python environment set up${NC}"
echo ""

echo -e "${YELLOW}Step 3: Configuring PostgreSQL...${NC}"
# Generate random password
DB_PASSWORD=$(openssl rand -base64 16)

sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" || true
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" || true
sudo -u postgres psql -c "ALTER DATABASE $DB_NAME OWNER TO $DB_USER;" || true

# Save database credentials to file
cat > .db_credentials << EOF
Database: $DB_NAME
Username: $DB_USER
Password: $DB_PASSWORD
EOF
chmod 600 .db_credentials

echo -e "${GREEN}✓ Database configured${NC}"
echo -e "${YELLOW}Database credentials saved to .db_credentials (keep this safe!)${NC}"
echo ""

echo -e "${YELLOW}Step 4: Creating Environment File...${NC}"
# Generate secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Create .env file
cat > .env << EOF
# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_HOST=0.0.0.0
PORT=8000

# Security
SECRET_KEY=$SECRET_KEY

# Database
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME

# Exchange Rate
TZS_TO_USD=2500

# File Upload
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=app/static/uploads

# Session
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
EOF

chmod 600 .env
echo -e "${GREEN}✓ Environment file created${NC}"
echo ""

echo -e "${YELLOW}Step 5: Running Database Migrations...${NC}"
source venv/bin/activate
flask db upgrade
echo -e "${GREEN}✓ Database migrations completed${NC}"
echo ""

echo -e "${YELLOW}Step 6: Creating Admin User...${NC}"
echo ""
echo -e "${YELLOW}Please enter admin user details:${NC}"
read -p "Admin email: " ADMIN_EMAIL
read -sp "Admin password: " ADMIN_PASSWORD
echo ""

python3 << EOF
from app import create_app, db
from app.models import User, Hotel
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    # Create hotel if not exists
    hotel = Hotel.query.first()
    if not hotel:
        hotel = Hotel(name="Ngenda Hotel", code="NGENDA")
        db.session.add(hotel)
        db.session.flush()
    
    # Create admin user
    admin = User(
        email="$ADMIN_EMAIL",
        name="Admin User",
        password_hash=generate_password_hash("$ADMIN_PASSWORD"),
        role="manager",
        hotel_id=hotel.id,
        is_superadmin=True,
        active=True
    )
    db.session.add(admin)
    db.session.commit()
    print(f"✓ Admin user created: $ADMIN_EMAIL")
EOF

echo -e "${GREEN}✓ Admin user created${NC}"
echo ""

echo -e "${YELLOW}Step 7: Creating Default Roles...${NC}"
source venv/bin/activate
python -m scripts.seed_staff_roles 2>/dev/null || echo -e "${YELLOW}⚠ Note: Roles may already exist${NC}"
echo -e "${GREEN}✓ Default roles created${NC}"
echo ""

echo -e "${YELLOW}Step 8: Setting Up Permissions...${NC}"
chown -R www-data:www-data $APP_DIR
chmod -R 755 $APP_DIR
chmod -R 777 $APP_DIR/app/static/uploads
echo -e "${GREEN}✓ Permissions configured${NC}"
echo ""

echo -e "${YELLOW}Step 9: Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/$APP_NAME << EOF
server {
    listen 80;
    server_name _;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Static files
    location /static {
        alias $APP_DIR/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Uploads
    location /static/uploads {
        alias $APP_DIR/app/static/uploads;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # Application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Deny access to sensitive files
    location ~ /\. {
        deny all;
    }
}
EOF

ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
echo -e "${GREEN}✓ Nginx configured${NC}"
echo ""

echo -e "${YELLOW}Step 10: Creating Systemd Service...${NC}"
cat > /etc/systemd/system/$SYSTEMD_SERVICE.service << EOF
[Unit]
Description=Ngenda Hotel Booking HMS
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 run:app
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SYSTEMD_SERVICE
systemctl start $SYSTEMD_SERVICE
echo -e "${GREEN}✓ Systemd service created and started${NC}"
echo ""

echo -e "${YELLOW}Step 11: Final Checks...${NC}"
sleep 3

# Check if service is running
if systemctl is-active --quiet $SYSTEMD_SERVICE; then
    echo -e "${GREEN}✓ Service is running${NC}"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    exit 1
fi

# Check if Nginx is running
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx is running${NC}"
else
    echo -e "${RED}✗ Nginx failed to start${NC}"
    exit 1
fi

# Check if PostgreSQL is running
if systemctl is-active --quiet postgresql; then
    echo -e "${GREEN}✓ PostgreSQL is running${NC}"
else
    echo -e "${RED}✗ PostgreSQL failed to start${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Completed Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Access URLs:${NC}"
echo "  Website: http://$(hostname -I | awk '{print $1}')/"
echo "  HMS Admin: http://$(hostname -I | awk '{print $1}')/hms/"
echo "  Login: http://$(hostname -I | awk '{print $1}')/hms/login"
echo ""
echo -e "${YELLOW}Important Files:${NC}"
echo "  Database credentials: $APP_DIR/.db_credentials"
echo "  Environment config: $APP_DIR/.env"
echo "  Application logs: journalctl -u $SYSTEMD_SERVICE -f"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Change admin password immediately after first login"
echo "  2. Configure SSL certificate: sudo certbot --nginx"
echo "  3. Set up database backups (see DEPLOYMENT_CHECKLIST.md)"
echo "  4. Configure firewall: sudo ufw enable"
echo ""
echo -e "${GREEN}The system is production-ready! 🚀${NC}"
