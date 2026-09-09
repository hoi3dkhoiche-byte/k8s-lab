from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

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

class InventorySync(BaseModel):
    product_id: str
    quantity: int = 0
    reserved: int = 0
