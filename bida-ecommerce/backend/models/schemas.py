from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ProductCreate(BaseModel):
    name: str
    category: str
    price: float
    description: str
    specs: Dict[str, Any] = {}
    tags: List[str] = []
    stock: int = 0

class ProductResponse(BaseModel):
    id: str
    name: str
    category: str
    price: float
    description: str
    specs: dict
    tags: list
    stock: int
    images: list = []
    is_featured: bool = False
    created_at: datetime

class CartItem(BaseModel):
    product_id: str
    quantity: int

class CartResponseItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float
    image: Optional[str] = None

class CartResponse(BaseModel):
    items: List[CartResponseItem]
    total: float

class OrderCreate(BaseModel):
    shipping_address: str
    shipping_name: str
    shipping_phone: str
    note: Optional[str] = None
    payment_method: str = 'cod'

class OrderItemResponse(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    user_id: int
    status: str
    total_amount: float
    items: List[OrderItemResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True

class PaymentCheckout(BaseModel):
    order_id: int
    method: str

class PaymentResponse(BaseModel):
    id: int
    order_id: int
    status: str
    amount: float
    method: str

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
