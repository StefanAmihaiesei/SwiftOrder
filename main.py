from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
from database import initialize_database
from config import RESTAURANT_NAME, PUBLIC_BASE_URL
from routes.staff import router as staff_router
from routes.products import router as products_router
from routes.tables import router as tables_router
from routes.orders import router as orders_router
from pathlib import Path
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from routes.auth import router as auth_router
from dependencies import get_current_staff


BASE_DIR = Path(__file__).resolve().parent


class FrontendStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        if Path(path).name == "admin.html":
            return RedirectResponse(
                "/admin", status_code=303,
                headers={"Cache-Control": "no-store"},
            )
        return await super().get_response(path, scope)


@asynccontextmanager
async def lifespan(app):
    initialize_database()
    yield


app = FastAPI(title="SwiftOrder", version="1.0.0", lifespan=lifespan)
app.include_router(staff_router)


@app.middleware("http")
async def protect_requests(request: Request, call_next):
    # Browsers send Origin on cross-origin requests, including HTML forms.
    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
        origin = request.headers.get("origin")
        expected = PUBLIC_BASE_URL or str(request.base_url).rstrip("/")
        if origin and (urlsplit(origin).scheme, urlsplit(origin).netloc) != (urlsplit(expected).scheme, urlsplit(expected).netloc):
            return JSONResponse({"detail": "Origine nepermisă."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
    if request.url.path.startswith(("/auth", "/orders", "/staff", "/tables")):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/settings")
def settings():
    return {"restaurant_name": RESTAURANT_NAME}


@app.get("/health")
def health():
    from sqlalchemy import text
    from database import engine
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}


app.mount(
    "/static",
    FrontendStaticFiles(directory=BASE_DIR / "frontend"),
    name="static",
)

app.include_router(tables_router)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(auth_router)

@app.get("/")
def root():
    return RedirectResponse("/menu", status_code=303)

@app.get("/menu", response_class=FileResponse)
def menu_page():
    return FileResponse(
        BASE_DIR / "frontend" / "menu.html",
        media_type="text/html",
    )
@app.get("/admin", response_class=FileResponse)
def admin_page(request: Request):
    try:
        get_current_staff(request)
    except HTTPException as error:
        if error.status_code != 401:
            raise
        return RedirectResponse(
            "/login", status_code=303,
            headers={"Cache-Control": "no-store"},
        )
    return FileResponse(
        BASE_DIR / "frontend" / "admin.html",
        media_type="text/html",
        headers={"Cache-Control": "no-store"},
    )
@app.get("/login", response_class=FileResponse)
def login_page():
    return FileResponse(
        BASE_DIR / "frontend" / "login.html",
        media_type="text/html",
    )
