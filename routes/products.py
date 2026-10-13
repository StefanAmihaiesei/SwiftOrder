from fastapi import APIRouter, Depends, HTTPException
from database import SessionLocal
from dependencies import require_manager
from models import OrderItem, Product
from sqlalchemy.exc import IntegrityError
from schemas import ProductCreate, ProductUpdate

router = APIRouter()

@router.get("/products")
def get_products():
    db = SessionLocal()
    products = db.query(Product).all()
    db.close()
    return products

@router.post("/products", dependencies=[Depends(require_manager)])
def create_product(product: ProductCreate):
    db = SessionLocal()
    new_product = Product(name = product.name, price=product.price, available=product.available, category=product.category)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    db.close()
    return new_product

@router.get("/products/{product_id}")
def get_product(product_id: int):
    db = SessionLocal()
    product = db.get(Product, product_id)
    db.close()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.patch("/products/{product_id}", dependencies=[Depends(require_manager)])
def update_product(product_id: int, changes: ProductUpdate):
    updates = changes.model_dump(exclude_unset=True)
    if any(value is None for value in updates.values()):
        raise HTTPException(status_code=400, detail="Invalid update data")
    db = SessionLocal()
    try:
        product = db.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        for key, value in updates.items():
            setattr(product, key, value)
        db.commit()
        db.refresh(product)
        return product
    finally:
        db.close()

@router.delete("/products/{product_id}", dependencies=[Depends(require_manager)])
def delete_product(product_id: int):
    db = SessionLocal()
    try:
        product = db.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        if db.query(OrderItem.id).filter(OrderItem.product_id == product_id).first():
            raise HTTPException(
                status_code=409,
                detail="Produsul apare în comenzi și nu poate fi șters. Editează-l și debifează disponibilitatea.",
            )
        db.delete(product)
        db.commit()
        return {"message": "Product deleted successfully"}
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Produsul este folosit în comenzi și nu poate fi șters. Marchează-l indisponibil.",
        )
    finally:
        db.close()
        
    
