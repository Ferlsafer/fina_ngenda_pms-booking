# Backend Security Audit Report — Multi-Property Hotel PMS

**Scope:** Flask application under `hotel_pms/app/` (routes, models, access control, accounting, auth, config).  
**Method:** Static analysis of all routes, queries, access checks, transactions, and configuration.

---

## Risk Level Summary

| Area | Level |
|------|--------|
| Multi-tenant isolation | **Low** |
| Access control & RBAC | **Low** |
| Transaction safety | **Medium** |
| Accounting integrity | **Medium** |
| Night audit lock | **Medium** |
| Input validation | **Medium** |
| SQL injection & ORM | **Low** |
| CSRF & session | **High** |
| Password security | **Low** |
| Production readiness | **Medium** |

**Overall risk level: Medium** (driven by missing CSRF, non-atomic booking/accounting, and open redirects).

---

## 1. MULTI-TENANT ISOLATION

### Verified safe

- **Operational queries are filtered by `hotel_id` or allowed set:**
  - `app/bookings/routes.py`: All `Booking`, `Room`, `Guest`, `Invoice`, `Payment` usage is scoped by `get_allowed_hotel_ids()` or `require_hotel_access(booking.hotel_id)` / `hid`.
  - `app/rooms/routes.py`: `Room`, `RoomType`, `RoomStatusHistory` use `hotel_ids` or `require_hotel_access(hid)` / `require_hotel_access(room.hotel_id)`.
  - `app/accounting/routes.py`: `JournalEntry`, `ChartOfAccount` use `hotel_ids` and `require_hotel_access(hid)`.
  - `app/dashboard/routes.py`: `Room`, `Booking`, `Payment`, `Hotel` use `hotel_ids` and `active_hotel_id`.
  - `app/night_audit/routes.py`: `BusinessDate` and `hotel_id` from form are gated by `require_hotel_access(hid)`.
- **IDOR-style access:** All `get_or_404(id)` on booking/room/invoice are followed by `require_hotel_access(resource.hotel_id)` before any mutation or sensitive render.
- **`hotel_id` from URL:** `app/core/routes.py` line 21–24: `set_hotel(hotel_id)` receives `hotel_id` from path; access is validated with `require_hotel_access(hotel_id)` before setting session.
- **`hotel_id` from form:** `app/night_audit/routes.py` line 29: `hid = request.form.get("hotel_id", type=int)` is validated with `require_hotel_access(hid)` before use.
- **Superadmin bypass:** `app/core/access.py` lines 13–14: `Hotel.query.all()` is used only when `current_user.is_superadmin` is True. Role and flag come from DB (no user-controlled role/flag in requests).

### Potential cross-hotel / isolation issues

- **None identified.** No route reads or writes operational data without either `hotel_id.in_(hotel_ids)` or a `require_hotel_access(resource.hotel_id)` check after load.

### Exact references (for audit trail)

- List/index flows: `bookings/routes.py` 21–23, `rooms/routes.py` 62–64, 23–25, `accounting/routes.py` 17–19, `dashboard/routes.py` 21–25, 30–46.
- Create/mutate flows: `bookings/routes.py` 49, 66–68, 79–91, 108–109, 125–126, 142–143; `rooms/routes.py` 86, 102–103; `night_audit/routes.py` 29–30, 33; `core/routes.py` 23–24.
- Access helper: `core/access.py` 6–18 (allowed list), 44–49 (`require_hotel_access`).

---

## 2. ACCESS CONTROL & RBAC

### Verified

- **Server-side role usage:** All scoping uses `get_allowed_hotel_ids()` and `require_hotel_access()` (backend); no reliance on frontend for “current hotel” or “role”.
- **Route protection:** Every operational route (dashboard, rooms, bookings, accounting, night audit, core `set_hotel`/`clear_hotel`/`hotels`) is decorated with `@login_required`.
- **Sensitive routes:** Login/logout are the only ones without `@login_required`; root `/` only redirects and does not expose data.
- **Owner vs other owners:** Owner’s allowed set is `Hotel.query.filter_by(owner_id=current_user.owner_id)`; `owner_id` is from DB, not request. No way for one owner to see another’s hotels through current routes.

### Gaps / notes

- **Logout:** `app/auth/routes.py` line 26: `/auth/logout` has no `@login_required`. Not a privilege issue (logout is safe when unauthenticated) but inconsistent with “all non-auth routes protected” if that is policy.
- **No role-based decorator:** There is no `@role_required('manager')` etc.; authorization is entirely “can access this hotel_id.” That is consistent and safe for current design.

### Exact references

- `@login_required`: `bookings/routes.py` 14, 29, 106, 123, 140; `rooms/routes.py` 16, 30, 55, 70, 100; `dashboard/routes.py` 14; `accounting/routes.py` 10, 25; `night_audit/routes.py` 11, 27; `core/routes.py` 10, 22, 35.
- Auth routes (intentionally unprotected): `auth/routes.py` 9, 26.

---

## 3. TRANSACTION SAFETY

### Issues

- **Booking create vs accounting not atomic:**  
  `app/bookings/routes.py` lines 92–94: `db.session.commit()` is called for guest, booking, room status, and invoice. Then **after** commit, `post_booking_revenue(hid, booking.id, total, check_in_d)` is called (line 94).  
  If `post_booking_revenue` fails or is never run (e.g. deploy between commit and post), the ledger will be missing the booking revenue entry while the booking and invoice exist.  
  **File:** `app/bookings/routes.py` — commit at 92; accounting call at 94.

- **Payment vs accounting not atomic:**  
  `app/bookings/routes.py` lines 162–165: Payment is committed (162–163), then `post_payment(...)` is called (165).  
  Same pattern: payment can be persisted without the corresponding Cash/AR journal entry.  
  **File:** `app/bookings/routes.py` — commit at 163; accounting call at 165.

- **Scattered commits:**  
  - Booking flow: one commit for booking+invoice (92); accounting in a separate transaction (`accounting/service.py` 39, 54).  
  - Payment flow: one commit for payment (163); accounting in another transaction (54).  
  No single transaction wraps “business event + double-entry post.”

### What is atomic

- Booking creation itself (guest + booking + room status + invoice) is in one transaction with rollback on exception (97–98).
- Payment record + invoice status update are in one commit (161–163).
- Accounting service internally uses one transaction per `post_booking_revenue` and `post_payment` (single commit per post).

### Exact references

- `app/bookings/routes.py`: 80–98 (booking block), 161–165 (payment block).
- `app/accounting/service.py`: 20, 39, 54 (`db.session.commit()`).

---

## 4. ACCOUNTING INTEGRITY

### Verified

- **Double-entry in code:** `post_booking_revenue` and `post_payment` each create two lines with equal debit and credit; no single-sided entries.
- **No UI for arbitrary entries:** There are no routes that accept user-supplied journal lines; the only writes are via the two service functions.
- **Chart of accounts:** Created per hotel and referenced by `hotel_id`; no cross-hotel account use.

### Gaps / risks

- **No explicit balance check:** There is no shared validation that `sum(debit) == sum(credit)` before commit. If a future route or service adds manual journal entries without that check, unbalanced entries could be saved.  
  **File:** `app/accounting/service.py` — no validation function; balance is ensured only by construction in the two posting functions.

- **Immutability not enforced:** There are no routes to edit or delete `JournalEntry` / `JournalLine`. Deletion/update is still possible via ORM/shell; there is no `deleted_at` or “locked” flag.  
  **Spec called for:** “financial records are not hard-deletable” and “no journal entry lines can be altered after creation” — not enforced in model or app logic.

- **Overpayment allowed:** `app/bookings/routes.py` 156–161: Payment is accepted even when `paid + amount > inv.total`; invoice is set to “Paid” and extra is not rejected. Business/audit impact rather than isolation, but affects correctness.

### Exact references

- `app/accounting/service.py`: 27–39 (post_booking_revenue), 42–54 (post_payment); no balance validator.
- Models: `app/models/accounting.py` — no soft-delete or immutable flag.

---

## 5. NIGHT AUDIT LOCK ENFORCEMENT

### Implemented

- **Close and advance:** `app/night_audit/routes.py` 38–42: When run, `is_closed` is set True and `current_business_date` is advanced; second run on same record is blocked by `if biz.is_closed` (38–39).
- **Hotel scoping:** `hid` is validated with `require_hotel_access(hid)` (30).

### Gaps

- **No lock used on bookings/payments:** No code checks `BusinessDate` or `is_closed` before creating or updating bookings, payments, or journal entries. Transactions for past or “closed” business dates can still be created or modified after night audit has been run.  
  **Files:** `app/bookings/routes.py` (new booking, check-in, check-out, payment) and `app/accounting/service.py` do not reference `BusinessDate` or `is_closed`.

- **Room charges not posted:** Night audit only advances the business date and closes the day; it does not post daily room charges or generate a revenue summary. Lock semantics (e.g. “no edits for closed date”) are not enforced for existing modules.

### Exact references

- `app/night_audit/routes.py`: 33–42 (run logic); no use of `BusinessDate` / `is_closed` elsewhere in app.

---

## 6. INPUT VALIDATION

### Missing or weak validation

- **Room type base price:** `app/rooms/routes.py` 42: `base_price = request.form.get("base_price", type=float)`. No check for `base_price < 0` or for unreasonably large values. Negative base price is accepted.  
  **File:** `app/rooms/routes.py` line 42.

- **Booking dates:** `app/bookings/routes.py` 56–62: Only `check_out_d > check_in_d` is enforced. No check that check-in/check-out are not in the past if required by policy, or that the range is within a max stay.

- **Payment amount:** `app/bookings/routes.py` 151–155: `amount <= 0` is rejected. No explicit check for negative (type=float could in theory accept negative in some setups); no max or “overpayment allowed vs not” policy.

- **Guest/room form fields:** Name/room_number are stripped but not length-limited (DB has String(255)/String(20)); no sanitization beyond strip. Risk is mostly DoS or noisy data, not injection (ORM parameterized).

- **`room_id` / `room_type_id`:** Validated by “exists and belongs to current hotel” (e.g. 49, 86); no further range check.

### What is validated

- Non-empty required fields (name, room_number, room_type_id, check_in, check_out, amount).
- Room availability and overlap (66–73).
- Room status for new booking (52–54).
- Status change in allowed set (108).

### Exact references

- `app/rooms/routes.py`: 41–44 (type_add), 81–84 (add room).
- `app/bookings/routes.py`: 40–64, 151–155.

---

## 7. SQL INJECTION & ORM SAFETY

### Verified

- **No raw SQL:** No use of `db.session.execute(text(...))`, `execute("...")`, or string-concatenated queries in application code.
- **All access via ORM:** Queries use SQLAlchemy (e.g. `Model.query.filter`, `filter_by`, `db.session.query`) with column objects and parameters.  
- **No concatenation of user input into SQL.**

### Note

- Flask-Migrate/Alembic generate migrations; those are part of the toolchain, not user-driven.

---

## 8. CSRF & SESSION SECURITY

### Critical issues

- **CSRF protection not enabled:** Flask-WTF is in `requirements.txt` but `CSRFProtect` is never initialized in the app. No `csrf_token()` in forms and no global CSRF check.  
  All state-changing POST requests (booking create, check-in, check-out, payment, room add, room type add, room status change, night audit run) are vulnerable to CSRF from a malicious site.  
  **File:** `app/__init__.py` — no CSRFProtect or equivalent; templates do not include CSRF tokens.

- **Session cookie security:** No `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, or `SESSION_COOKIE_SAMESITE` in `app/config.py`. In production over HTTPS, cookies should be Secure and HttpOnly; SameSite helps against CSRF.

- **SECRET_KEY default:** `app/config.py` line 8: `SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")`. If `SECRET_KEY` is not set in production, session and any signed data are predictable. Production could run with default key.

### Exact references

- `app/__init__.py`: no CSRF.
- `app/config.py`: BaseConfig lines 8–9; no session cookie options; ProductionConfig does not override session/secret.

---

## 9. PASSWORD SECURITY

### Verified

- **Hashing:** `app/auth/routes.py` and seed scripts use `werkzeug.security.generate_password_hash` and `check_password_hash`. No plain-text storage in code paths observed.
- **Login:** Password is not logged or reflected in responses.

### Gaps

- **No brute-force protection:** No rate limiting, lockout, or CAPTCHA on `auth/routes.py` login. Credentials can be brute-forced.
- **Hash method:** Default for `generate_password_hash` is currently secure (e.g. pbkdf2:sha256); no explicit method or round count in code — acceptable but could be pinned for consistency.

### Exact references

- `app/auth/routes.py`: 17–18 (lookup and check_password_hash).
- Seed scripts: hashing used when creating users.

---

## 10. PRODUCTION READINESS

### Issues

- **Debug mode:** `run.py` line 8: `app.run(debug=True, port=5000)`. If production is started with `python run.py`, debug is on (stack traces, reloader).  
  **File:** `run.py` line 8.

- **Error handling:** No registered `@app.errorhandler(500)` (or 404). In debug mode, 500s can expose tracebacks.  
  **File:** `app/__init__.py` — no error handlers.

- **Exception message to user:** `app/bookings/routes.py` 99: `flash(f"Error: {e}", "danger")` exposes the raw exception message (e.g. DB/constraint errors) to the client.  
  **File:** `app/bookings/routes.py` line 99.

- **Config separation:** Development and production configs exist (`DevelopmentConfig`, `ProductionConfig`). Production does not set `SESSION_COOKIE_SECURE` or similar; `DATABASE_URL` must be set or app fails.

- **User loader robustness:** `app/__init__.py` line 21: `User.query.get(int(uid))` can raise `ValueError` if `uid` is not numeric (e.g. tampered cookie). No try/except; could result in 500 and possible information leakage in debug.

### Exact references

- `run.py`: 8.
- `app/__init__.py`: 21 (user_loader); no error handlers.
- `app/config.py`: BaseConfig, ProductionConfig.
- `app/bookings/routes.py`: 99.

---

## CRITICAL ISSUES (fix before production)

1. **CSRF disabled** — Enable Flask-WTF CSRF (e.g. `CSRFProtect(app)`) and add CSRF tokens to all state-changing forms (or equivalent protection).
2. **SECRET_KEY default** — Fail startup or refuse to run in production if `SECRET_KEY` is missing or equals `"change-me-in-production"`.
3. **Session cookies** — In production config, set `SESSION_COOKIE_SECURE = True`, `SESSION_COOKIE_HTTPONLY = True`, and `SESSION_COOKIE_SAMESITE = 'Lax'` (or stricter).

---

## MEDIUM ISSUES (should fix)

4. **Booking + accounting not atomic** — Wrap booking create + `post_booking_revenue` in one transaction (or use a single commit after both); same for payment + `post_payment`.
5. **Night audit not enforced on edits** — Before creating/updating bookings or payments, check that the transaction date is not after the hotel’s current business date and that the business date is not closed for that date (or document that lock is out of scope for MVP).
6. **Open redirect** — Validate `request.args.get("next")` and `request.referrer` in `core/routes.py` (set_hotel) and `auth/routes.py` (login) so redirects are only to same-origin or an allowlist (e.g. `url_for`-generated paths).
7. **Negative room type price** — Reject `base_price < 0` (and optionally set a max) in `rooms/routes.py` type_add.
8. **Error message leakage** — Do not flash raw exception `str(e)` to the user; log it and show a generic message (e.g. “Booking could not be created”).
9. **Debug in run.py** — Do not hardcode `debug=True`; use `app.run(debug=app.config.get('DEBUG', False), ...)` or run via `flask run` with `FLASK_ENV=production`.
10. **User loader** — Wrap `User.query.get(int(uid))` in try/except; on invalid `uid` return None and optionally log.

---

## MINOR ISSUES (recommended)

11. **Accounting balance validation** — Add a helper that asserts `sum(debit)==sum(credit)` for a journal entry and call it from any future code that creates manual journal lines; consider using it in the existing posting functions for defense in depth.
12. **Financial immutability** — If spec is to be fully met, add soft delete and/or “locked” flag for financial records and block updates/deletes in routes (and consider DB constraints).
13. **Overpayment policy** — Explicitly allow or reject overpayment and enforce in payment route (e.g. cap amount at `inv.total - paid_total` or allow and document).
14. **Login rate limiting** — Add rate limiting or lockout for `/auth/login` to reduce brute-force risk.
15. **Logout** — Add `@login_required` to logout if the policy is that all non-public routes must be protected (optional).

---

## RECOMMENDED FIXES (summary)

- Enable CSRF and add tokens to all POST forms (or equivalent).
- Set SECRET_KEY from env and reject default in production.
- Harden session cookies in production (Secure, HttpOnly, SameSite).
- Make booking+revenue and payment+journal a single transaction each.
- Enforce night-audit lock on booking/payment by business date (or document scope).
- Sanitize redirect targets (next/referrer) to same-origin or allowlist.
- Validate base_price >= 0 (and optional max).
- Stop flashing raw exceptions; log and show generic messages.
- Avoid hardcoded debug=True; tie to config.
- Harden user_loader for invalid uid.
- Add optional accounting balance check and financial immutability if required by spec.
- Add login rate limiting and clarify overpayment and logout policy.

---

## Overall Architecture Stability Assessment

- **Multi-tenant isolation and access control** are implemented consistently: every operational route and query is scoped by `get_allowed_hotel_ids()` or `require_hotel_access()`. No cross-hotel data leak or IDOR was found. Superadmin logic is safe under the assumption that `is_superadmin` and role are only set in the DB.
- **Transaction and accounting design** are the main reliability risks: booking/payment can be committed without the corresponding journal entries, and there is no enforcement of night-audit lock on transactions. Fixing atomicity and (if required) lock enforcement will significantly improve correctness and auditability.
- **Security hardening** is incomplete: CSRF, session cookie settings, and SECRET_KEY handling must be fixed for production; open redirect and error message leakage should be addressed. With these addressed and the medium issues mitigated, the architecture is suitable for a production MVP from a security and isolation perspective.

**Conclusion:** The application is **not production-ready from a security standpoint** until CSRF is enabled, session and SECRET_KEY are correctly configured, and redirect/error handling are tightened. Multi-tenant isolation and RBAC are in good shape; transaction and accounting integrity need the changes above to meet a strict audit standard.
