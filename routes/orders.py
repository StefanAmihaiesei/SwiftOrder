from fastapi import APIRouter, HTTPException

from database import SessionLocal
from models import Order, OrderItem, Product, RestaurantTable
from schemas import OrderCreate, OrderStatusUpdate
from fastapi import Depends
from dependencies import get_current_staff

router = APIRouter()

@router.post("/orders", status_code=201)
def create_order(data: OrderCreate):
    db = SessionLocal()
    try:
        table =db.query(RestaurantTable).filter(RestaurantTable.qr_token == data.qr_token).first() 
        if table is None:
            raise HTTPException(status_code = 404, detail="Table not found!")
        checked_items = []
        for item in data.items:
            product = db.get(Product, item.product_id)
            if product is None:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
            if product.available != 1:
                raise HTTPException(status_code=409, detail=f"Product {item.product_id} is unavailable")
            checked_items.append((item, product))
        new_order =  Order(table_id=table.id)
        db.add(new_order)
        db.flush()
        total = 0
        for item, product in checked_items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.price,
            )
            db.add(order_item)
            total += item.quantity * product.price
        db.commit()
        db.refresh(new_order)
        return {
            "order_id": new_order.id,
            "table_number": table.number,
            "status": new_order.status,
            "total": round(total, 2),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

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
            db.query(OrderItem, Product.name)
            .join(Product, OrderItem.product_id == Product.id)
            .filter(OrderItem.order_id.in_(list(orders_by_id)))
            .order_by(OrderItem.id.asc())
            .all()
        )
        for item, product_name in item_rows:
            order_data = orders_by_id[item.order_id]
            subtotal = item.quantity * item.unit_price

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
            db.query(OrderItem, Product.name).join(Product, OrderItem.product_id == Product.id).filter(OrderItem.order_id == order.id).all()
        )
        items = []
        total = 0
        for item, product_name in rows:
            subtotal = item.quantity * item.unit_price
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
