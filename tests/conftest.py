import os
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_test_dir = tempfile.TemporaryDirectory(prefix="swiftorder-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_test_dir.name) / "test.db")
os.environ["COOKIE_SECURE"] = "false"
os.environ.pop("PUBLIC_BASE_URL", None)

import pytest
from fastapi.testclient import TestClient
from database import engine, SessionLocal
from models import Base, StaffUser
from main import app
from routes.auth import login_attempts
from security import hash_password


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    login_attempts.clear()
    with SessionLocal() as db:
        for username, role in [("manager", "MANAGER"), ("waiter", "WAITER")]:
            db.add(StaffUser(username=username, role=role, password_hash=hash_password("test-password-123"), is_active=True))
        db.commit()
    with TestClient(app) as client:
        yield client


def sign_in(client, username="manager"):
    response = client.post("/auth/login", json={"username": username, "password": "test-password-123"})
    assert response.status_code == 200
    return response


@pytest.fixture
def manager(client):
    sign_in(client)
    return client


@pytest.fixture
def menu(manager):
    product = manager.post("/products", json={"name": "Espresso", "price": 12.35, "available": 1, "category": "Băuturi calde"}).json()
    table = manager.post("/tables", json={"number": 5}).json()
    return product, table
