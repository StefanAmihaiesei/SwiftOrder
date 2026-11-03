"""Optional browser regression. Always uses a temporary SQLite database."""
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_test_dir = tempfile.TemporaryDirectory(prefix="swiftorder-browser-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_test_dir.name) / "browser.db")
os.environ["COOKIE_SECURE"] = "false"
os.environ.pop("PUBLIC_BASE_URL", None)
from database import initialize_database, SessionLocal
from models import StaffUser, Product, RestaurantTable
from security import hash_password
initialize_database()
with SessionLocal() as db:
    db.add(StaffUser(username="demo-manager", password_hash=hash_password("demo-password-123"), role="MANAGER", is_active=True))
    for name, price, category in [("Pizza Margherita", 35, "Pizza"), ("Espresso", 10, "Băuturi calde"), ("Specialitatea casei", 25, "Recomandări")]:
        db.add(Product(name=name, price=price, available=1, category=category))
    db.add(RestaurantTable(number=5, qr_token="ui-demo-table-token"))
    db.commit()
with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
BASE_URL = f"http://127.0.0.1:{port}"
server = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "error"], cwd=ROOT)
import atexit

def cleanup():
    server.terminate()
    try:
        server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait()
atexit.register(cleanup)
for attempt in range(100):
    try:
        if httpx.get(BASE_URL + "/health").status_code == 200:
            break
    except httpx.ConnectError:
        pass
    time.sleep(0.05)
else:
    raise RuntimeError("Test server did not start")

from pathlib import Path
from playwright.sync_api import sync_playwright, expect

out = Path(os.getenv('BROWSER_ARTIFACT_DIR', str(ROOT / 'artifacts')))
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.getenv('BROWSER_EXECUTABLE'), headless=True, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width': 390, 'height': 844})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(f'{BASE_URL}/menu?token=ui-demo-table-token')
    expect(page.locator('#table-info')).to_have_text('Masa 5')
    page.get_by_role('button', name='Adaugă Pizza Margherita în coș').click()
    expect(page.locator('#cart-count')).to_have_text('1')
    page.reload()
    expect(page.locator('#cart-count')).to_have_text('1')
    page.get_by_role('button', name='Recomandări', exact=True).click()
    expect(page.locator('#products')).to_contain_text('Specialitatea casei')
    page.locator('#menu-search').fill('Espresso')
    expect(page.locator('#products')).to_contain_text('Espresso')
    expect(page.locator('#products .product-card')).to_have_count(1)
    page.get_by_role('button', name='Adaugă Espresso în coș').click()
    page.locator('#menu-search').fill('')
    page.screenshot(path=str(out / 'menu-mobile.png'), full_page=True)
    page.locator('#open-cart').click()
    expect(page.locator('#cart-dialog')).to_be_visible()
    expect(page.locator('#cart-total')).to_contain_text('45')
    page.screenshot(path=str(out / 'cart-mobile.png'), full_page=True)
    # Drop first response after server has committed; retry must resolve same order.
    def drop_response(route):
        route.fetch()
        route.abort('failed')
    page.route('**/orders', drop_response, times=1)
    page.locator('#place-order').click()
    expect(page.locator('#order-message')).to_contain_text('Nu am putut confirma')
    page.reload()
    expect(page.locator('#order-message')).to_contain_text('așteaptă confirmare')
    page.locator('#open-cart').click()
    page.locator('#place-order').click()
    expect(page.locator('#order-message')).to_contain_text('Comanda #1 a fost plasată')
    expect(page.locator('#cart-count')).to_have_text('0')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.goto(f'{BASE_URL}/login')
    page.locator('#username').fill('demo-manager')
    page.locator('#password').fill('demo-password-123')
    page.get_by_role('button', name='Intră în cont').click()
    expect(page).to_have_url(f'{BASE_URL}/admin')
    expect(page.locator('#staff-info')).to_contain_text('Manager')
    expect(page.locator('#orders .order-card')).to_have_count(1)
    page.get_by_role('button', name='Gestionare meniu', exact=True).click()
    page.locator('#add-product').click()
    page.locator('#product-name').fill('Produs nou')
    page.locator('#product-category').fill('Categorie nouă')
    page.locator('#product-price').fill('19.90')
    page.locator('#save-product').click()
    expect(page.locator('#menu-message')).to_contain_text('salvat')
    expect(page.locator('#managed-products')).to_contain_text('Produs nou')
    page.get_by_role('button', name='Editează Produs nou', exact=True).click()
    page.locator('#product-name').fill('Produs editat')
    page.locator('#save-product').click()
    expect(page.locator('#managed-products')).to_contain_text('Produs editat')
    page.get_by_role('button', name='Șterge Produs editat', exact=True).click()
    page.locator('#save-product').click()
    expect(page.locator('#managed-products')).not_to_contain_text('Produs editat')
    page.get_by_role('button', name='Mese și QR', exact=True).click()
    page.locator('#table-number').fill('12')
    page.locator('#table-form button').click()
    expect(page.locator('#managed-tables')).to_contain_text('Masa 12')
    expect(page.locator('#managed-tables .qr-preview')).to_have_count(2)
    assert page.locator('.qr-preview').first.evaluate('(img) => img.complete && img.naturalWidth > 0')
    page.screenshot(path=str(out / 'tables-mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.get_by_role('button', name='Personal', exact=True).click()
    page.locator('#staff-username').fill('ui-waiter')
    page.locator('#staff-password').fill('waiter-password-123')
    page.locator('#staff-form button').click()
    expect(page.locator('#managed-staff')).to_contain_text('ui-waiter')
    page.locator('#logout-button').click()
    expect(page).to_have_url(f'{BASE_URL}/login')
    page.locator('#username').fill('ui-waiter')
    page.locator('#password').fill('waiter-password-123')
    page.get_by_role('button', name='Intră în cont').click()
    expect(page.locator('#staff-navigation')).to_be_hidden()
    expect(page.locator('#orders .order-card')).to_have_count(1)
    page.get_by_role('button', name='Începe prepararea').click()
    page.get_by_role('button', name='Marchează livrată').click()
    page.get_by_role('button', name='Istoric', exact=True).click()
    expect(page.locator('#orders')).to_contain_text('Livrată')
    page.set_viewport_size({'width': 1280, 'height': 900})
    page.screenshot(path=str(out / 'orders-desktop.png'), full_page=True)
    page.goto(f'{BASE_URL}/menu')
    expect(page.locator('#table-info')).to_contain_text('Scanează')
    expect(page.locator('#open-cart')).to_be_hidden()
    assert page.locator('.product-add:visible').count() == 0
    page.emulate_media(color_scheme='dark')
    page.screenshot(path=str(out / 'menu-dark.png'), full_page=True)
    assert errors == [], errors
    browser.close()
print('Browser flow passed: mobile cart persistence, custom categories, search, lost-response retry, product CRUD, tables/QR, staff creation, waiter delivery/history, desktop/dark, no JS errors.')
