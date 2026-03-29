#!/usr/bin/env bash
# =============================================================================
#  Hotel PMS — Contabo VPS Deployment Script
#  Run as root on a fresh Ubuntu 22.04 server:
#    bash deploy.sh
# =============================================================================
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
APP_USER="hms"
APP_DIR="/var/www/hms"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"   # parent of deploy/ folder
PYTHON="python3.12"
PG_DB="hms_db"
PG_USER="hms_user"
LOG_DIR="/var/log/hms"
# ─────────────────────────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
abort()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

[[ $EUID -ne 0 ]] && abort "Run this script as root (sudo bash deploy.sh)"

# ── Step 1: Check .env ────────────────────────────────────────────────────────
info "Checking .env …"
ENV_FILE="$REPO_DIR/.env"
[[ -f "$ENV_FILE" ]] || abort ".env not found in $REPO_DIR. Copy .env.example to .env and fill in the values."

source "$ENV_FILE"
[[ "${SECRET_KEY:-}" == "CHANGE_ME"* ]] && abort "Set a real SECRET_KEY in .env before deploying."
[[ "${DATABASE_URL:-}" == *"CHANGE_ME"* ]] && abort "Set the real DATABASE_URL in .env before deploying."

# Parse DB password from DATABASE_URL  postgresql://user:PASS@host/db
PG_PASS=$(echo "$DATABASE_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
[[ -z "$PG_PASS" ]] && abort "Could not parse DB password from DATABASE_URL."

# ── Step 2: System packages ───────────────────────────────────────────────────
info "Installing system packages …"
apt-get update -qq
apt-get install -y -qq \
    python3.12 python3.12-venv python3.12-dev \
    postgresql postgresql-contrib \
    nginx \
    git \
    build-essential libpq-dev \
    certbot python3-certbot-nginx

# ── Step 3: PostgreSQL ────────────────────────────────────────────────────────
info "Setting up PostgreSQL …"
systemctl enable --now postgresql

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$PG_USER'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER $PG_USER WITH PASSWORD '$PG_PASS';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$PG_DB'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE $PG_DB OWNER $PG_USER;"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $PG_DB TO $PG_USER;"

# ── Step 4: App user + directories ───────────────────────────────────────────
info "Creating app user and directories …"
id "$APP_USER" &>/dev/null || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
mkdir -p "$APP_DIR" "$LOG_DIR"

# ── Step 5: Copy application files ───────────────────────────────────────────
info "Copying application files to $APP_DIR …"
rsync -a --exclude='.git' --exclude='venv' --exclude='__pycache__' \
    "$REPO_DIR/" "$APP_DIR/"

cp "$ENV_FILE" "$APP_DIR/.env"

# ── Step 6: Python virtual environment ───────────────────────────────────────
info "Creating Python virtual environment …"
if [[ ! -d "$APP_DIR/venv" ]]; then
    $PYTHON -m venv "$APP_DIR/venv"
fi
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
"$APP_DIR/venv/bin/pip" install --quiet gunicorn

# ── Step 7: Database migrations ──────────────────────────────────────────────
info "Running database migrations …"
cd "$APP_DIR"
"$APP_DIR/venv/bin/flask" --app wsgi:app db upgrade

# ── Step 8: Create superadmin ────────────────────────────────────────────────
info "Creating superadmin account (skipped if already exists) …"
"$APP_DIR/venv/bin/python" -m scripts.seed_superadmin || true

# ── Step 9: Permissions ───────────────────────────────────────────────────────
info "Setting file permissions …"
chown -R "$APP_USER:$APP_USER" "$APP_DIR" "$LOG_DIR"
chmod 600 "$APP_DIR/.env"

# ── Step 10: Systemd service ──────────────────────────────────────────────────
info "Installing systemd service …"
cp "$APP_DIR/deploy/hms.service" /etc/systemd/system/hms.service
systemctl daemon-reload
systemctl enable hms
systemctl restart hms

# ── Step 11: Nginx ────────────────────────────────────────────────────────────
info "Configuring Nginx …"
cp "$APP_DIR/deploy/hms.nginx" /etc/nginx/sites-available/hms
ln -sf /etc/nginx/sites-available/hms /etc/nginx/sites-enabled/hms
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl restart nginx

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Deployment complete!                        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  App:          http://YOUR_SERVER_IP"
echo "  HMS login:    http://YOUR_SERVER_IP/hms/login"
echo "  Default user: admin@hotel.com  /  admin123"
echo ""
echo -e "${YELLOW}  IMPORTANT — do these after first login:${NC}"
echo "  1. Change the superadmin password immediately"
echo "  2. Create your first hotel, then set NGENDA_HOTEL_ID in .env"
echo "  3. Run: systemctl restart hms"
echo "  4. For HTTPS: certbot --nginx -d YOUR_DOMAIN"
echo ""
