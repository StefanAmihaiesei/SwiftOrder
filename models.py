from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone
from sqlalchemy import (Column, Integer, String, Float, DateTime, ForeignKey, Boolean)

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    available = Column(Integer, nullable=False)
    category = Column(String, nullable=False, default="Altele")

class RestaurantTable(Base):
    __tablename__ = "restaurant_tables"

    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False, unique=True)
    qr_token = Column(String, nullable=False, unique=True)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    table_id = Column(Integer, ForeignKey("restaurant_tables.id"), nullable=False)
    status = Column(String, nullable=False, default="NEW")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

class StaffUser(Base):
    __tablename__ = "staff_users";

    id = Column(Integer, primary_key = True)
    username = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

class StaffSession(Base):
    __tablename__ = "staff_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("staff_users.id"), nullable=False
    )
    token_hash = Column(String, nullable=False, unique=True)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = Column(DateTime, nullable=False)