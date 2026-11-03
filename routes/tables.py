from uuid import uuid4
from io import BytesIO
from urllib.parse import quote
import qrcode
from qrcode.image.svg import SvgPathImage
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from database import SessionLocal
from dependencies import require_manager
from models import RestaurantTable, Order
from schemas import TableCreate
from config import PUBLIC_BASE_URL

router = APIRouter(tags=["Mese"])


def table_data(table, request):
    base = PUBLIC_BASE_URL or str(request.base_url).rstrip("/")
    return {"id": table.id, "number": table.number, "qr_token": table.qr_token,
            "menu_url": f"{base}/menu?token={quote(table.qr_token)}"}


@router.post("/tables", status_code=201, dependencies=[Depends(require_manager)])
def create_table(table: TableCreate, request: Request):
    with SessionLocal() as db:
        new_table = RestaurantTable(number=table.number, qr_token=str(uuid4()))
        db.add(new_table)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Numărul mesei există deja.")
        return table_data(new_table, request)


@router.get("/tables", dependencies=[Depends(require_manager)])
def get_tables(request: Request):
    with SessionLocal() as db:
        return [table_data(table, request) for table in db.query(RestaurantTable).order_by(RestaurantTable.number)]


@router.get("/tables/by-token/{qr_token}")
def get_table_by_token(qr_token: str):
    with SessionLocal() as db:
        table = db.query(RestaurantTable).filter(RestaurantTable.qr_token == qr_token).first()
        if table is None:
            raise HTTPException(404, "Masa nu a fost găsită.")
        return {"id": table.id, "number": table.number}


@router.get("/tables/{table_id}/qr", dependencies=[Depends(require_manager)])
def get_qr(table_id: int, request: Request):
    with SessionLocal() as db:
        table = db.get(RestaurantTable, table_id)
        if table is None:
            raise HTTPException(404, "Masa nu a fost găsită.")
        image = qrcode.make(table_data(table, request)["menu_url"], image_factory=SvgPathImage, border=4)
        output = BytesIO()
        image.save(output)
        return Response(output.getvalue(), media_type="image/svg+xml", headers={
            "Content-Disposition": f'attachment; filename="swiftorder-masa-{table.number}.svg"',
        })


@router.delete("/tables/{table_id}", dependencies=[Depends(require_manager)])
def delete_table(table_id: int):
    with SessionLocal() as db:
        table = db.get(RestaurantTable, table_id)
        if table is None:
            raise HTTPException(404, "Masa nu a fost găsită.")
        if db.query(Order.id).filter(Order.table_id == table_id).first():
            raise HTTPException(409, "Masa are comenzi în istoric și trebuie păstrată.")
        db.delete(table)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Masa are comenzi și trebuie păstrată.")
        return {"message": "Masa a fost ștearsă."}
