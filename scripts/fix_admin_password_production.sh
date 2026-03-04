#!/bin/bash
# =============================================================================
# Fix Admin Password Reset - Automated Production Script
# =============================================================================
# This script automates the entire fix process with safety confirmations
# 
# What it does:
#   1. Checks current admin status (SAFE - read only)
#   2. Adds admin role to database (requires confirmation)
#   3. Updates admin user (requires confirmation)
#   4. Restarts the service
#
# Safety features:
#   - Shows what will change before making changes
#   - Requires explicit confirmation for each step
#   - Can be cancelled anytime with Ctrl+C
#   - Makes minimal database changes
# =============================================================================

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}Fix Admin Password Reset - Production${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""

# Check if running in correct directory
if [ ! -f "run.py" ] && [ ! -d "app" ]; then
    echo -e "${RED}❌ Error: Not in the application directory${NC}"
    echo "   Please run: cd /var/www/booking-hms"
    exit 1
fi

# Check if virtualenv is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}❌ Error: Virtual environment not activated${NC}"
    echo "   Please run: source venv/bin/activate"
    exit 1
fi

# Check if running as root (needed for systemctl)
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Warning: Not running as root${NC}"
    echo "   You may need sudo for the final restart step"
    echo ""
fi

echo -e "${YELLOW}Step 1: Pre-Check (SAFE - Read Only)${NC}"
echo "-----------------------------------------------------------"
python scripts/check_admin_status.py
echo ""

echo -e "${YELLOW}Step 2: Add Admin Role to Database${NC}"
echo "-----------------------------------------------------------"
echo "This adds a new 'admin' role to the database."
echo "It is SAFE and will NOT affect existing data."
echo ""
echo -e "${YELLOW}Proceed? (YES to continue): ${NC}"
read -r CONFIRM1
if [ "$CONFIRM1" != "YES" ]; then
    echo -e "${RED}❌ Cancelled by user${NC}"
    exit 1
fi

python scripts/add_admin_role.py
echo ""

echo -e "${YELLOW}Step 3: Update Admin User${NC}"
echo "-----------------------------------------------------------"
echo "This updates the admin user to use the new admin role."
echo ""
echo -e "${YELLOW}Proceed? (YES to continue): ${NC}"
read -r CONFIRM2
if [ "$CONFIRM2" != "YES" ]; then
    echo -e "${RED}❌ Cancelled by user${NC}"
    exit 1
fi

python scripts/update_admin_role.py
echo ""

echo -e "${YELLOW}Step 4: Restart Service${NC}"
echo "-----------------------------------------------------------"
echo "This will restart the booking-hms service."
echo "Expected downtime: ~5 seconds"
echo ""
echo -e "${YELLOW}Proceed? (YES to continue): ${NC}"
read -r CONFIRM3
if [ "$CONFIRM3" != "YES" ]; then
    echo -e "${RED}❌ Cancelled by user${NC}"
    echo ""
    echo -e "${YELLOW}Note: You must restart the service manually for changes to take effect:${NC}"
    echo "   sudo systemctl restart booking-hms"
    exit 1
fi

sudo systemctl restart booking-hms

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ Fix Applied Successfully!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "${YELLOW}Verification Steps:${NC}"
echo "1. Check service status: sudo systemctl status booking-hms"
echo "2. Open browser: http://your-server/hms/"
echo "3. Login as admin"
echo "4. Go to Settings → Users"
echo "5. Click 'Edit' on admin user"
echo "6. Verify 'admin' appears in Role dropdown"
echo "7. Set a new password and save"
echo ""
echo -e "${GREEN}🎉 Done!${NC}"
