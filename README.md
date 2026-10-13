# SwiftOrder

A café ordering app I'm building with Python, FastAPI and SQLite.
The frontend uses HTML, CSS and JavaScript. It's still in development.

Customers can open the menu using a table link and place an order.
Staff can log in, view orders and update their status. Managers can also
add, edit and remove products.

## Run it locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -c 'from database import engine; from models import Base; Base.metadata.create_all(engine)'
python create_manager.py
uvicorn main:app --reload
```

The manager script asks you to choose a username and password.

Open http://127.0.0.1:8000/login to sign in and add products.
To try the customer menu, create a table with `POST /tables` at
http://127.0.0.1:8000/docs, then use its `qr_token` in this link:

```text
http://127.0.0.1:8000/menu?token=YOUR_TABLE_TOKEN
```

For now, the app is meant to run locally. Some files still use the old name,
ScanServe.
