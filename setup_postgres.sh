#!/bin/bash
# PostgreSQL Setup Script for Hotel PMS
# Run this script with: bash setup_postgres.sh

set -e

echo "=== PostgreSQL Setup for Hotel PMS ==="

# Generate secure passwords
DB_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -hex 32)

echo "Creating PostgreSQL user and database..."

# Create database user and database
sudo -u postgres psql << EOF
-- Create user with secure password
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'hotel_user') THEN
      CREATE ROLE hotel_user WITH LOGIN PASSWORD '${DB_PASSWORD}';
   END IF;
END
\$\$;

-- Create database
SELECT 'CREATE DATABASE hotel_pms_prod OWNER hotel_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'hotel_pms_prod')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE hotel_pms_prod TO hotel_user;
\c hotel_pms_prod
GRANT ALL ON SCHEMA public TO hotel_user;
EOF

echo "Installing Python PostgreSQL driver..."
source venv/bin/activate
pip install psycopg2-binary

echo "Creating .env file..."
cat > .env << EOF
FLASK_ENV=production
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=postgresql://hotel_user:${DB_PASSWORD}@localhost/hotel_pms_prod
TZS_TO_USD=2500
EOF

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Database credentials (SAVE THESE):"
echo "  Username: hotel_user"
echo "  Password: ${DB_PASSWORD}"
echo "  Database: hotel_pms_prod"
echo ""
echo "Running database migrations..."
FLASK_APP=run.py flask db upgrade

echo ""
echo "=== Migration Complete ==="
echo ""
echo "Your .env file has been created with production settings."
echo "Restart your application to use PostgreSQL."
echo ""
