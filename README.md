# SwiftOrder

A restaurant ordering app I'm building to practise Python and web development.
The idea is simple: scan the QR code at your table, choose something from the
menu and send the order to the staff.

The backend uses FastAPI, SQLAlchemy and SQLite. The frontend is plain HTML,
CSS and JavaScript. The interface is in Romanian.

## What it does

- Customers can browse categories, search for products and place orders without an account.
- The cart stays saved if the page is refreshed.
- Waiters can see orders and mark them as preparing or delivered.
- Managers can edit the menu, create tables, download QR codes and manage staff accounts.
- Delivered orders stay in the history.

It works on desktop and mobile, with a light and dark theme. There are no online
payments. For now, I'm using it locally.

## Running it

You'll need Python 3.10 or newer. I tested it with Python 3.13.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python create_manager.py
python -m uvicorn main:app --reload
```

`create_manager.py` asks for a username and password. The password needs at least
10 characters. You only need to create the account once.

Open http://127.0.0.1:8000/login and sign in. From there you can add products and
tables. Each table has its own menu link and QR code.

If you want some sample products and five tables on a new database, run:

```bash
python seed_demo.py
```

This won't add anything if you already have products or tables.
You can also view the menu at http://127.0.0.1:8000/menu, but you need a table's
link to actually order. The API docs are at http://127.0.0.1:8000/docs.

## Testing on a phone

Connect the phone and laptop to the same Wi-Fi. Replace the IP below with your
laptop's local IP, then start the server:

```bash
export PUBLIC_BASE_URL="http://192.168.1.100:8000"
python -m uvicorn main:app --host 0.0.0.0
```

Open that address on the laptop too, log in and download the table QR codes.
Using `localhost` in a QR code won't work on the phone. If the laptop's IP changes,
the QR codes need to be downloaded again.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

There's also a browser test for the main ordering and staff flows:

```bash
pip install -r requirements-browser.txt
python -m playwright install chromium
python tests/browser_smoke.py
```

The tests use separate databases, so they don't change your saved orders.

## A few notes

The database is created automatically and saved as `tableflow.db`. The name is
left over from an earlier version of the project. It's not uploaded to GitHub.

You can change the restaurant name with `RESTAURANT_NAME`. The other settings
are listed in `.env.example`; they need to be exported in the terminal, since
the app doesn't load that file automatically.

Passwords are stored as hashes. Products that have been ordered can't be deleted,
but they can be marked unavailable. Retrying an order after a connection problem
uses the same order reference to avoid sending it twice.

I haven't deployed it online yet. That would need HTTPS and some extra setup.
