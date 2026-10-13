from fastapi import FastAPI, HTTPException, Request
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


app = FastAPI()

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
    return {"message": "ScanServe API is running"}

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
