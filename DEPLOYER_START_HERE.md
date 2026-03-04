# 🚨 DEPLOYER: Start Here for Admin Password Fix

## Quick Start (Choose ONE method)

### Method A: Automated Script (Recommended - 3 commands)
```bash
cd /var/www/booking-hms
source venv/bin/activate
bash scripts/fix_admin_password_production.sh
```
**Then:** Type `YES` when prompted (3 times), service restarts automatically

### Method B: Manual Steps (4 commands)
```bash
cd /var/www/booking-hms
source venv/bin/activate
python scripts/add_admin_role.py    # Type YES to confirm
python scripts/update_admin_role.py  # Type YES to confirm
sudo systemctl restart booking-hms
```

---

## What This Fix Does

**Problem:** Admin can't reset password - role missing from dropdown

**Solution:** 
1. Adds 'admin' role to database (1 new row in roles table)
2. Updates admin user to use that role (1 user updated)
3. Restarts service (~5 seconds downtime)

**Impact:** Minimal - only affects admin user, no data loss

**Time:** 5-10 minutes

---

## Documentation Files

| File | Use When |
|------|----------|
| **FIX_ADMIN_QUICK_REFERENCE.txt** | You want a one-page cheat sheet |
| **DEPLOYER_FIX_ADMIN_PASSWORD.md** | You want detailed step-by-step instructions |
| **DEPLOYMENT_SUMMARY_ADMIN_FIX.md** | You want to understand what was created |

---

## Safety Features

✅ **Scripts show what will change BEFORE making changes**
✅ **Scripts require typing "YES" to confirm**
✅ **Can cancel anytime with Ctrl+C**
✅ **Pre-check script is 100% read-only**
✅ **Database transactions rollback on error**

---

## Verify Success

After running the script:

1. Check service: `sudo systemctl status booking-hms`
2. Open browser: `http://your-server/hms/`
3. Login as admin
4. Go to: **Settings → Users**
5. Click **Edit** on admin user
6. Verify "admin" appears in Role dropdown
7. Test: Set new password and save
8. Login with new password

---

## Emergency Rollback

If something goes wrong:

```bash
sudo -u postgres psql hotel_pms_prod
```

Then in PostgreSQL:
```sql
UPDATE users SET role = 'manager', role_id = NULL 
WHERE email = 'admin@ngendahotel.com';
DELETE FROM roles WHERE name = 'admin';
\q
```

Then: `sudo systemctl restart booking-hms`

---

## Need Help?

1. **Error during script:** Read the error message, usually missing venv or wrong directory
2. **Service won't start:** Check logs with `sudo journalctl -u booking-hms -f`
3. **Still stuck:** Refer to `DEPLOYER_FIX_ADMIN_PASSWORD.md` for detailed troubleshooting

---

## Files Uploaded

You should have these files in `/var/www/booking-hms/scripts/`:

- ✅ `check_admin_status.py` - Pre-check (SAFE)
- ✅ `add_admin_role.py` - Add admin role
- ✅ `update_admin_role.py` - Update admin user
- ✅ `fix_admin_password_production.sh` - Automated script

---

**Ready? Start with:** `bash scripts/fix_admin_password_production.sh`

Good luck! 🚀
