from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

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
