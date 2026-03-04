#!/bin/bash
# PRODUCTION SAFE: Fix Admin Password Reset Issue
# Run each step carefully and confirm before proceeding

set -e

echo "=========================================="
echo "Admin Password Reset Fix - Production"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Add 'admin' role to the database"
echo "  2. Update admin user to use the new role"
echo ""
echo "Both steps require confirmation before making changes."
echo ""
echo "⚠️  Press Ctrl+C to cancel, or Enter to continue..."
read

# Check if running in correct directory
if [ ! -f "run.py" ] && [ ! -d "app" ]; then
    echo "❌ Error: Not in the application directory"
    echo "   Please run: cd /var/www/booking-hms"
    exit 1
fi

# Check if virtualenv is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated"
    echo "   Please run: source venv/bin/activate"
    exit 1
fi

echo ""
echo "=========================================="
echo "Step 1: Add Admin Role"
echo "=========================================="
echo ""
python scripts/add_admin_role.py

echo ""
echo "=========================================="
echo "Step 2: Update Admin User"
echo "=========================================="
echo ""
python scripts/update_admin_role.py

echo ""
echo "=========================================="
echo "✅ Fix Applied Successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Restart the service:"
echo "     sudo systemctl restart booking-hms"
echo ""
echo "  2. Test in browser:"
echo "     - Go to Settings → Users"
echo "     - Edit the admin user"
echo "     - Set a new password"
echo ""
