from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from xml.etree import ElementTree
import pytest
from conftest import sign_in
from database import SessionLocal, engine, initialize_database
from models import StaffSession, StaffUser, Order, OrderItem
from sqlalchemy import text, inspect


def payload(menu):
    product, table = menu
    return {"qr_token": table["qr_token"], "items": [{"product_id": product["id"], "quantity": 2}]}


def test_pages_and_no_public_tokens(client):
    assert client.get("/", follow_redirects=False).headers["location"] == "/menu"
    for url in ["/menu", "/login", "/settings", "/health"]:
        assert client.get(url).status_code == 200
    for url in ["/orders", "/tables", "/staff", "/tables/1/qr"]:
        assert client.get(url).status_code == 401
    assert client.post("/tables", json={"number": 1}).status_code == 401
    for url in ["/admin", "/static/admin.html"]:
        assert client.get(url, follow_redirects=False).status_code == 303


def test_login_logout_roles(client):
    bad = client.post("/auth/login", json={"username": "manager", "password": "wrong"})
    assert bad.status_code == 401
    response = sign_in(client, "waiter")
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert client.get("/admin").status_code == 200
    assert client.get("/orders").status_code == 200
    for url in ["/tables", "/staff"]:
        assert client.get(url).status_code == 403
    assert client.post("/products", json={"name": "X", "price": 1, "available": 1}).status_code == 403
    assert client.post("/auth/logout").status_code == 200
    assert client.get("/auth/me").status_code == 401


def test_order_flow_and_snapshots(manager, menu):
    data = payload(menu)
    manager.cookies.clear()  # Customers order without accounts.
    response = manager.post("/orders", json=data)
    assert response.status_code == 201
    order = response.json()
    assert order["total"] == 24.7
    sign_in(manager)
    product, table = menu
    assert manager.patch(f'/products/{product["id"]}', json={"price": 99, "name": "Renamed"}).status_code == 200
    details = manager.get(f'/orders/{order["order_id"]}').json()
    assert details["items"][0]["name"] == "Espresso"
    assert details["total"] == 24.7
    assert manager.get("/orders").json()[0] == details
    assert manager.delete(f'/products/{product["id"]}').status_code == 409
    assert manager.delete(f'/tables/{table["id"]}').status_code == 409
    sign_in(manager, "waiter")
    url = f'/orders/{order["order_id"]}/status'
    assert manager.patch(url, json={"status": "DELIVERED"}).status_code == 409
    for status in ["PREPARING", "PREPARING", "DELIVERED"]:
        assert manager.patch(url, json={"status": status}).status_code == 200
    assert manager.patch(url, json={"status": "NEW"}).status_code == 409
    assert manager.get("/orders").json()[0]["status"] == "DELIVERED"


def test_retry_is_idempotent(manager, menu):
    headers = {"Idempotency-Key": "random-order-key-for-test"}
    data = payload(menu)
    first = manager.post("/orders", json=data, headers=headers)
    second = manager.post("/orders", json=data, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    data["items"][0]["quantity"] = 3
    assert manager.post("/orders", json=data, headers=headers).status_code == 409
    with SessionLocal() as db:
        assert db.query(Order).count() == 1


def test_concurrent_retry(manager, menu):
    data = payload(menu)
    def send(_):
        return manager.post("/orders", json=data, headers={"Idempotency-Key": "concurrent-order-key-1234"})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(send, range(2)))
    assert [response.status_code for response in responses] == [201, 201]
    assert responses[0].json()["order_id"] == responses[1].json()["order_id"]
    with SessionLocal() as db:
        assert db.query(Order).count() == 1


def test_invalid_order_rolls_back(manager, menu):
    data = payload(menu)
    data["items"].append({"product_id": 99999, "quantity": 1})
    assert manager.post("/orders", json=data).status_code == 404
    with SessionLocal() as db:
        assert db.query(Order).count() == db.query(OrderItem).count() == 0
    product, table = menu
    manager.patch(f'/products/{product["id"]}', json={"available": 0})
    assert manager.post("/orders", json=payload(menu)).status_code == 409
    data = payload(menu)
    data["qr_token"] = "invalid"
    assert manager.post("/orders", json=data).status_code == 404


@pytest.mark.parametrize("changes", [{"quantity": 0}, {"quantity": -1}, {"quantity": 100}, {"product_id": 0}])
def test_order_validation(manager, menu, changes):
    data = payload(menu)
    data["items"][0].update(changes)
    assert manager.post("/orders", json=data).status_code == 422


def test_products_validation_and_delete(manager):
    for data in [{"name": " ", "price": 1, "available": 1}, {"name": "X", "price": -1, "available": 1}]:
        assert manager.post("/products", json=data).status_code == 422
    product = manager.post("/products", json={"name": "X", "price": 0, "available": 1, "category": "Speciale"}).json()
    assert manager.patch(f'/products/{product["id"]}', json={"name": None}).status_code == 400
    assert manager.delete(f'/products/{product["id"]}').status_code == 200
    assert manager.get(f'/products/{product["id"]}').status_code == 404


def test_tables_qr(manager):
    assert manager.post("/tables", json={"number": 0}).status_code == 422
    table = manager.post("/tables", json={"number": 12}).json()
    assert manager.post("/tables", json={"number": 12}).status_code == 409
    assert table["menu_url"].endswith("/menu?token=" + table["qr_token"])
    qr = manager.get(f'/tables/{table["id"]}/qr')
    assert qr.status_code == 200
    assert "svg" in ElementTree.fromstring(qr.content).tag
    assert "attachment" in qr.headers["content-disposition"]
    public = manager.get("/tables/by-token/" + table["qr_token"]).json()
    assert public == {"id": table["id"], "number": 12}
    assert manager.delete(f'/tables/{table["id"]}').status_code == 200


def test_staff_deactivation_revokes_sessions(manager):
    created = manager.post("/staff", json={"username": "new-waiter", "password": "long-password-123", "role": "WAITER"})
    assert created.status_code == 201
    user = created.json()
    assert "password_hash" not in user
    assert manager.post("/staff", json={"username": "new-waiter", "password": "long-password-123"}).status_code == 409
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as waiter:
        assert waiter.post("/auth/login", json={"username": "new-waiter", "password": "long-password-123"}).status_code == 200
        assert manager.patch(f'/staff/{user["id"]}', json={"is_active": False}).status_code == 200
        assert waiter.get("/orders").status_code == 401
    own = next(user for user in manager.get("/staff").json() if user["username"] == "manager")
    assert manager.patch(f'/staff/{own["id"]}', json={"is_active": False}).status_code == 409


def test_expired_session(client):
    sign_in(client)
    with SessionLocal() as db:
        session = db.query(StaffSession).first()
        session.expires_at = datetime.now() - timedelta(days=1)
        db.commit()
    assert client.get("/orders").status_code == 401


def test_csrf_and_rate_limit(client):
    assert client.post("/auth/login", json={"username": "x", "password": "x"}, headers={"Origin": "https://evil.example"}).status_code == 403
    for _ in range(10):
        assert client.post("/auth/login", json={"username": "x", "password": "x"}).status_code == 401
    assert client.post("/auth/login", json={"username": "x", "password": "x"}).status_code == 429
    assert client.get("/menu").headers["x-content-type-options"] == "nosniff"


def test_upgrade_preserves_legacy_data(manager, menu):
    order = manager.post("/orders", json=payload(menu)).json()
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE order_items DROP COLUMN product_name"))
    initialize_database()
    initialize_database()  # Repeat startup is safe.
    assert "product_name" in {c["name"] for c in inspect(engine).get_columns("order_items")}
    assert manager.get(f'/orders/{order["order_id"]}').json()["total"] == 24.7
