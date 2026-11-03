from pydantic import BaseModel, Field, StringConstraints
from typing import Annotated
from typing import Literal 

ProductName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
ProductCategory = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]

class ProductCreate(BaseModel):
    name: ProductName
    price: float = Field(ge=0, le=1000000, multiple_of=0.01, allow_inf_nan=False)
    available: Literal[0, 1]
    category: ProductCategory = 'Altele'


class ProductUpdate(BaseModel):
    name: ProductName | None = None
    price: float | None = Field(default=None, ge=0, le=1000000, multiple_of=0.01, allow_inf_nan=False)
    available: Literal[0, 1] | None = None
    category: ProductCategory | None = None

class TableCreate(BaseModel):
    number: int = Field(gt=0, le=9999)

class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=99)

class OrderCreate(BaseModel):
    qr_token: str = Field(min_length=1, max_length=128)
    items: list[OrderItemCreate] = Field(min_length=1, max_length=100)

class OrderStatusUpdate(BaseModel):
    status: Literal["NEW", "PREPARING", "DELIVERED"]

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class StaffCreate(BaseModel):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    password: str = Field(min_length=10, max_length=256)
    role: Literal["WAITER", "MANAGER"] = "WAITER"


class StaffUpdate(BaseModel):
    is_active: bool
