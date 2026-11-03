# SwiftOrder

SwiftOrder is a complete local MVP for café and restaurant table ordering.
Customers scan a table QR code, browse the menu and place an order without an
account. Waiters manage preparation and delivery; managers also manage products,
tables, QR codes and staff accounts. Built with FastAPI, SQLAlchemy, SQLite and
plain HTML/CSS/JavaScript. The interface is in Romanian; prices are in RON.

## Start locally

Requires Python 3.10+ (verified with Python 3.13).

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python create_manager.py
# Optional on a NEW database only:
.venv/bin/python seed_demo.py
.venv/bin/python -m uvicorn main:app --reload
```

The manager script asks for your own username and password (10–256 characters).
There are no default production credentials. Tables are created automatically on
startup; the sample data script refuses to modify an existing menu or tables.

Open [staff login](http://127.0.0.1:8000/login), sign in and use:

1. **Gestionare meniu:** add products with a name, category, price and availability.
   Categories can be typed freely. Existing drink categories appear under Băuturi;
   other categories appear under Mâncare. Customer search covers all categories.
2. **Mese și QR:** create numbered tables, open each table's menu or download its
   printable SVG QR code. A table with order history cannot be deleted.
3. **Personal:** create waiter or manager accounts; deactivate/reactivate other
   accounts. Deactivation immediately revokes their sessions.
4. **Comenzi:** orders move from Nouă → În preparare → Livrată. Delivered orders stay
   in history; “Încarcă mai multe” expands the list. Polling refreshes every 5 seconds.

The [menu preview](http://127.0.0.1:8000/menu) is readable without a table token.
Ordering requires the table-specific link. The [API docs](http://127.0.0.1:8000/docs)
use the same staff session after login. `/health` checks database connectivity.

## Try it on a phone

Use the laptop's current LAN IP; phone and laptop must share a reachable network.
For example, replace `192.168.1.100` below with your actual IP:

```bash
export PUBLIC_BASE_URL="http://192.168.1.100:8000"
export RESTAURANT_NAME="Restaurant Demo"
.venv/bin/python -m uvicorn main:app --host 0.0.0.0
```

Open that same address on the laptop, log in, then download the QR codes from
**Mese și QR**. A QR containing `127.0.0.1` points to the phone itself and will not
reach the laptop. Regenerate/reprint QR codes when the public address changes.
Use a permanent address for permanent prints.

## Configuration and data

Settings come from exported environment variables; `.env.example` documents them.
The application does **not** automatically load `.env` files.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | SQLite `tableflow.db` beside the code | Absolute SQLite path is recommended for overrides |
| `PUBLIC_BASE_URL` | Current request origin | Public URL used for QR links and same-origin checks |
| `RESTAURANT_NAME` | Restaurant Demo | Name displayed in the menu and staff header |
| `COOKIE_SECURE` | false | Set true when served over HTTPS |

The legacy database filename is retained to preserve existing installations.
Startup creates missing tables and adds the nullable `order_items.product_name`
column if needed. Existing orders, products, staff and table tokens are preserved.
Historical rows fall back to the current product name; new orders keep a name and
price snapshot. Products referenced in orders can be made unavailable rather
than deleted. All order history is retained.

Back up SQLite while the server is stopped, or use SQLite's online backup API
while it is running. Database files, credentials, virtual environments and browser
artifacts are excluded from Git.

## Behavior and security

- The server validates table tokens, availability, quantities (1–99), prices
  (nonnegative, at most two decimal places) and order status transitions.
- The cart is stored per table in browser local storage and reconciled with the
  current menu on reload. Storage failures do not prevent ordering.
- The client persists an idempotency key before sending. After an uncertain
  network result, it retries the original order and receives its existing receipt.
  Cart editing is locked until that pending order is resolved. The API supports
  the same behavior through the optional `Idempotency-Key` header.
- Staff passwords use Argon2. Eight-hour sessions store token hashes server-side;
  cookies are HttpOnly and SameSite=Strict. Staff-only data and writes enforce
  roles server-side. Table token lists and QR downloads require a manager.
- Cross-origin writes are rejected. Security headers and a same-origin Content
  Security Policy are included. Login is limited to 10 attempts/minute/IP.

This release targets a local demo and portfolio presentation. Internet hosting
requires HTTPS, `COOKIE_SECURE=true`, a correct `PUBLIC_BASE_URL`, persistent
storage and backups. The login limiter is in memory and intended for one process;
use a shared/edge limiter for multiple workers. A table QR is a bearer link: anyone
with that link can submit orders; it does not prove physical presence.
Payments, customer accounts, product photos, multi-restaurant tenancy and
production hosting are outside this MVP.

## Verification

API tests use temporary databases and never alter your restaurant data:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

Optional browser regression (starts/stops its own server and temporary database):

```bash
.venv/bin/python -m pip install -r requirements-browser.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python tests/browser_smoke.py
# Or use an installed Chromium/Brave executable:
# BROWSER_EXECUTABLE=/path/to/browser .venv/bin/python tests/browser_smoke.py
```

Screenshots are written to ignored `artifacts/` (override with
`BROWSER_ARTIFACT_DIR`). The browser check covers mobile cart persistence,
custom categories/search, a committed order with a lost response and safe retry,
product create/edit/delete, tables/QR, staff creation, waiter delivery/history,
desktop/dark mode, layout overflow and JavaScript errors.

## Source map

- `main.py`, `config.py`, `database.py`: app startup, settings and SQLite setup.
- `models.py`, `schemas.py`: persisted records and request validation.
- `routes/`: products, tables/QR, orders, authentication and staff administration.
- `frontend/`: responsive menu, login and staff dashboard, with no build step.
- `create_manager.py`, `seed_demo.py`: interactive bootstrap and optional samples.
- `tests/`: isolated API tests and optional browser regression.
