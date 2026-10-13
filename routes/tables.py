from uuid import uuid4
from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError
from database import SessionLocal
from models import RestaurantTable
from schemas import TableCreate

router = APIRouter()

@router.post("/tables", status_code=201)
def create_table(table: TableCreate):
    db = SessionLocal()
    try:
        new_table = RestaurantTable(number=table.number, qr_token=str(uuid4()))
        db.add(new_table)
        db.commit()
        db.refresh(new_table)
        return new_table
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Table number or QR Token already exists")
    finally:
        db.close()

@router.get("/tables")
def get_tables():
    db = SessionLocal()
    tables = db.query(RestaurantTable).all()
    db.close()
    return tables

@router.get("/tables/by-token/{qr_token}")
def get_table_by_token(qr_token: str):
    db = SessionLocal()
    try:
        table = db.query(RestaurantTable).filter(RestaurantTable.qr_token == qr_token).first()
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
        return table
    finally:
        db.close()

