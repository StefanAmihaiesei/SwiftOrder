from fastapi import APIRouter, HTTPException, Header
from hashlib import sha256
import json
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import Order, OrderItem, Product, RestaurantTable, OrderReceipt
from schemas import OrderCreate, OrderStatusUpdate
from fastapi import Depends
from dependencies import get_current_staff

router = APIRouter()

def order_result(db, order):
    table = db.get(RestaurantTable, order.table_id)
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    total = sum((Decimal(str(item.unit_price)) * item.quantity for item in items), Decimal(0))
    return {"order_id": order.id, "table_number": table.number, "status": order.status, "total": float(total.quantize(Decimal("0.01")))}


@router.post("/orders", status_code=201)
def create_order(data: OrderCreate, idempotency_key: str | None = Header(default=None, min_length=16, max_length=128)):
    fingerprint = sha256(json.dumps(data.model_dump(), sort_keys=True).encode()).hexdigest()
    with SessionLocal() as db:
        def previous_result():
            receipt = db.get(OrderReceipt, idempotency_key) if idempotency_key else None
            if receipt:
                if receipt.payload_hash != fingerprint:
                    raise HTTPException(409, "Aceeași cheie a fost folosită pentru altă comandă.")
                return order_result(db, db.get(Order, receipt.order_id))
        previous = previous_result()
        if previous:
            return previous
        table = db.query(RestaurantTable).filter(RestaurantTable.qr_token == data.qr_token).first()
        if table is None:
            raise HTTPException(404, "Masa nu a fost găsită. Scanează din nou QR-ul.")
        quantities = {}
        for item in data.items:
            quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
            if quantities[item.product_id] > 99:
                raise HTTPException(422, "Maximum 99 bucăți dintr-un produs.")
        checked = []
        for product_id, quantity in quantities.items():
            product = db.get(Product, product_id)
            if product is None:
                raise HTTPException(404, "Un produs nu mai există. Reîncarcă meniul.")
            if product.available != 1:
                raise HTTPException(409, f"{product.name} nu mai este disponibil. Actualizează coșul.")
            checked.append((product, quantity))
        order = Order(table_id=table.id)
        db.add(order)
        db.flush()
        for product, quantity in checked:
            db.add(OrderItem(order_id=order.id, product_id=product.id, product_name=product.name,
                             quantity=quantity, unit_price=product.price))
        if idempotency_key:
            db.add(OrderReceipt(key=idempotency_key, payload_hash=fingerprint, order_id=order.id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            previous = previous_result()
            if previous:
                return previous
            raise
        return order_result(db, order)

@router.get("/orders", dependencies=[Depends(get_current_staff)])
def get_order():
    db = SessionLocal()
    try:
        rows = db.query(Order, RestaurantTable.number).join(RestaurantTable, Order.table_id == RestaurantTable.id).order_by(Order.created_at.asc(), Order.id.asc()).all()
        orders_by_id = {}
        for order, table_number in rows:
            orders_by_id[order.id] = {
                "order_id": order.id,
                "table_number": table_number,
                "status": order.status,
                "created_at": order.created_at,
                "items": [],
                "total": 0,
            }
        if not orders_by_id:
            return []
        item_rows = (
            db.query(OrderItem, func.coalesce(OrderItem.product_name, Product.name))
            .join(Product, OrderItem.product_id == Product.id)
            .filter(OrderItem.order_id.in_(list(orders_by_id)))
            .order_by(OrderItem.id.asc())
            .all()
        )
        for item, product_name in item_rows:
            order_data = orders_by_id[item.order_id]
            subtotal = float(Decimal(str(item.unit_price)) * item.quantity)

            order_data["items"].append({
                "product_id": item.product_id,
                "name": product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": round(subtotal, 2),
            })
            order_data["total"] += subtotal
        for order_data in orders_by_id.values():
            order_data["total"] = round(order_data["total"], 2)
        return list(orders_by_id.values())
    finally:
        db.close()

        
@router.get("/orders/{order_id}", dependencies=[Depends(get_current_staff)])
def get_order_details(order_id: int):
    db = SessionLocal()
    try:
        order = db.get(Order, order_id)
        if order is None:
            raise HTTPException(status_code = 404, detail = "Order not found!")
        table = db.get(RestaurantTable, order.table_id)
        rows = (
            db.query(OrderItem, func.coalesce(OrderItem.product_name, Product.name)).join(Product, OrderItem.product_id == Product.id).filter(OrderItem.order_id == order.id).all()
        )
        items = []
        total = 0
        for item, product_name in rows:
            subtotal = float(Decimal(str(item.unit_price)) * item.quantity)
            total+=subtotal
            items.append({
                "product_id": item.product_id,
                "name": product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": round(subtotal, 2),
            })
        return {
            "order_id": order.id,
            "table_number": table.number,
            "status": order.status,
            "created_at": order.created_at,
            "items": items,
            "total": round(total, 2),
        }

    finally:
        db.close()

@router.patch("/orders/{order_id}/status", dependencies=[Depends(get_current_staff)])
def update_order_status(order_id: int, changes: OrderStatusUpdate):
    db = SessionLocal()
    try:
        order = db.get(Order, order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        result = {"order_id": order.id, "status": order.status}
        allowed_transitions = {"NEW": "PREPARING","PREPARING": "DELIVERED"}
        if changes.status != order.status:
            next_status = allowed_transitions.get(order.status)
            if changes.status != next_status:
                raise HTTPException(  status_code=409,detail="Invalid status transition")
            order.status = changes.status
            result["status"] = changes.status
            db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
