from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ProductCreate(BaseModel):
    name: str
    category: str
    price: float
    description: Optional[str] = ''
    desc: Optional[str] = None
    img: Optional[str] = None
    specs: Dict[str, Any] = {}
    tags: List[str] = []
    stock: int = 0
    images: List[str] = []
    is_featured: bool = False

class ProductResponse(BaseModel):
    id: str
    name: str
    category: str
    price: float
    description: Optional[str] = ''
    desc: Optional[str] = None
    img: Optional[str] = None
    specs: dict = {}
    tags: list = []
    stock: int = 0
    images: list = []
    is_featured: bool = False
    created_at: Optional[datetime] = None
