from pydantic import BaseModel
from typing import Optional, List

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
