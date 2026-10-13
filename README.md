# SwiftOrder

A work-in-progress café ordering application built with Python, FastAPI,
SQLAlchemy and SQLite, with a vanilla JavaScript, HTML and CSS frontend.
Some internal labels still use the earlier name ScanServe.

## Implemented

- Table-specific tokens and a customer menu with a shopping cart.
- Product listing and manager-only product creation, updates and deletion.
- Order submission with quantity and availability validation and saved item prices.
- Staff order dashboard and validated NEW → PREPARING → DELIVERED transitions.
- Staff login/logout, Argon2 password hashing and expiring cookie sessions.
- Manager-only permissions for product changes; authenticated staff access to orders.

## Run locally

Use Python 3.12 or newer. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -c 'from database import engine; from models import Base; Base.metadata.create_all(engine)'
python create_manager.py
uvicorn main:app --reload
```

Choose your own manager username and password when prompted. The SQLite database
is created locally and is excluded from Git.

- API documentation: http://127.0.0.1:8000/docs
- Staff login: http://127.0.0.1:8000/login
- Staff dashboard: http://127.0.0.1:8000/admin

Create a table using `POST /tables` in the API documentation, then open
`http://127.0.0.1:8000/menu?token=TOKEN` with the returned `qr_token`.
Sign in through `/login` to add products in the dashboard.

## Project structure

- `main.py`: application and frontend pages
- `routes/`: products, tables, orders and authentication
- `models.py`, `schemas.py`: database models and request validation
- `security.py`, `dependencies.py`: password hashing and staff permissions
- `frontend/`: customer menu, login and staff interface

## Development status

This is a student portfolio project in development, intended for local review.
Table creation and listing are currently public API operations. Session cookies
use `secure=False` for local HTTP development. Deployment hardening, further
permission checks and automated regression tests remain future work.
No real customer data, staff accounts or database files are included.
