#!/bin/bash
# Quick Production Setup Script
# Run with: bash scripts/quick_production_setup.sh

set -e

echo "======================================"
echo "Ngenda Hotel PMS - Production Setup"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}Please do not run as root${NC}"
    exit 1
fi

cd /home/bytehustla/Projects/hotel2/hotel_pms

echo -e "${YELLOW}Step 1: Generating secure keys...${NC}"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

echo -e "${YELLOW}Step 2: Creating .env file...${NC}"
cat > .env << EOF
# Production Configuration
FLASK_ENV=production
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=postgresql://hotel_user:hotel_secure_pass_2026@localhost/hotel_pms_prod
WEBSITE_API_KEY=${API_KEY}
NGENDA_HOTEL_ID=1
TZS_TO_USD=2500
EOF

chmod 600 .env
echo -e "${GREEN}✓ .env file created${NC}"

echo ""
echo -e "${YELLOW}Step 3: Re-enabling rate limiter...${NC}"
sed -i 's/# @limiter.limit("5 per minute")/@limiter.limit("5 per minute")/' app/auth/routes.py
echo -e "${GREEN}✓ Rate limiter enabled${NC}"

echo ""
echo -e "${YELLOW}Step 4: Installing production dependencies...${NC}"
source venv/bin/activate
pip install gunicorn psycopg2-binary --quiet
echo -e "${GREEN}✓ Dependencies installed${NC}"

echo ""
echo -e "${YELLOW}Step 5: Creating wsgi.py...${NC}"
cat > wsgi.py << 'EOF'
from app import create_app
app = create_app('production')
EOF
echo -e "${GREEN}✓ wsgi.py created${NC}"

echo ""
echo -e "${YELLOW}Step 6: Creating directories...${NC}"
mkdir -p /var/log/hotel_pms
mkdir -p /home/bytehustla/backups
chmod 755 /var/log/hotel_pms
chmod 700 /home/bytehustla/backups
echo -e "${GREEN}✓ Directories created${NC}"

echo ""
echo -e "${YELLOW}Step 7: Creating backup script...${NC}"
cat > scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/bytehustla/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="hotel_pms_prod"
DB_USER="hotel_user"

mkdir -p $BACKUP_DIR
pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/db_${DATE}.sql.gz
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete
echo "Backup completed: db_${DATE}.sql.gz"
EOF
chmod +x scripts/backup.sh
echo -e "${GREEN}✓ Backup script created${NC}"

echo ""
echo -e "${YELLOW}Step 8: Testing configuration...${NC}"
if python3 -c "from app import create_app; app = create_app('production')" 2>/dev/null; then
    echo -e "${GREEN}✓ Configuration valid${NC}"
else
    echo -e "${RED}✗ Configuration error${NC}"
    exit 1
fi

echo ""
echo "======================================"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "======================================"
echo ""
echo "IMPORTANT - Save these credentials:"
echo "-----------------------------------"
echo "SECRET_KEY: ${SECRET_KEY}"
echo "API_KEY: ${API_KEY}"
echo ""
echo "Next Steps:"
echo "1. Change all default user passwords"
echo "2. Configure supervisor (see PRODUCTION_DEPLOYMENT.md)"
echo "3. Configure nginx (see PRODUCTION_DEPLOYMENT.md)"
echo "4. Set up SSL certificate"
echo "5. Enable firewall"
echo ""
echo "Default credentials (CHANGE THESE):"
echo "  Super Admin: admin@hotel.com / admin123"
echo "  Manager: manager@demo.com / manager123"
echo ""
