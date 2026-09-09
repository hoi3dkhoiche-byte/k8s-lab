import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import create_engine, Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Enum as SQLEnum, select
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataApiService")

# DB Configuration
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://admin:admin123@mongo-db:27017/")
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://admin:admin123@postgres-db:5432/user_db")
MYSQL_URL = os.environ.get("MYSQL_URL", "mysql+pymysql://admin:admin123@mysql-db:3306/order_db")

# PostgreSQL setup for Users
PgBase = declarative_base()
class UserModel(PgBase):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)
    role = Column(String(20), default='user')
    created_at = Column(DateTime, default=datetime.utcnow)

# MySQL setup for Orders
MyBase = declarative_base()
class OrderStatusEnum(str, enum.Enum):
    pending = 'pending'
    confirmed = 'confirmed'
    paid = 'paid'
    shipped = 'shipped'
    delivered = 'delivered'
    cancelled = 'cancelled'

class OrderModel(MyBase):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    status = Column(SQLEnum(OrderStatusEnum), default=OrderStatusEnum.pending)
    total_amount = Column(Numeric(12, 2), nullable=False)
    shipping_address = Column(Text, nullable=False)
    shipping_name = Column(String(100), nullable=False)
    shipping_phone = Column(String(20), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = relationship('OrderItemModel', back_populates='order', cascade='all, delete-orphan')

class OrderItemModel(MyBase):
    __tablename__ = 'order_items'
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(String(100), nullable=False)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    order = relationship('OrderModel', back_populates='items')

class PaymentModel(MyBase):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    method = Column(String(50), nullable=False)
    status = Column(String(20), default='pending')
    amount = Column(Numeric(12, 2), nullable=False)
    transaction_id = Column(String(100), nullable=True)
    paid_at = Column(DateTime, nullable=True)

# Database clients
mongo_client: Optional[AsyncIOMotorClient] = None
pg_session_factory = None
mysql_session_factory = None

app = FastAPI(title="CMC Database REST API Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.on_event("startup")
async def startup():
    global mongo_client, pg_session_factory, mysql_session_factory
    try:
        mongo_client = AsyncIOMotorClient(MONGO_URL)
        logger.info("Connected to MongoDB for Products Data API")
    except Exception as e:
        logger.error(f"MongoDB connection error: {e}")

    try:
        pg_engine = create_engine(POSTGRES_URL, pool_pre_ping=True)
        PgBase.metadata.create_all(bind=pg_engine)
        pg_session_factory = sessionmaker(bind=pg_engine)
        logger.info("Postgres initialized for Users Data API")
    except Exception as e:
        logger.error(f"Postgres connection error: {e}")

    try:
        my_engine = create_engine(MYSQL_URL, pool_pre_ping=True)
        MyBase.metadata.create_all(bind=my_engine)
        mysql_session_factory = sessionmaker(bind=my_engine)
        logger.info("MySQL initialized for Orders Data API")
    except Exception as e:
        logger.error(f"MySQL connection error: {e}")

@app.on_event("shutdown")
async def shutdown():
    global mongo_client
    if mongo_client:
        mongo_client.close()

# Helper DB access
def get_pg():
    if not pg_session_factory:
        raise HTTPException(status_code=500, detail="User database connection unavailable")
    session = pg_session_factory()
    try:
        yield session
    finally:
        session.close()

def get_mysql():
    if not mysql_session_factory:
        raise HTTPException(status_code=500, detail="Order database connection unavailable")
    session = mysql_session_factory()
    try:
        yield session
    finally:
        session.close()

def get_mongo_db():
    if not mongo_client:
        raise HTTPException(status_code=500, detail="Catalog database connection unavailable")
    return mongo_client.catalog_db

# ==============================================================================
# 1. USER DATABASE API
# ==============================================================================
class UserCreateDTO(BaseModel):
    username: str
    email: Optional[str] = None
    password_hash: str
    full_name: Optional[str] = None
    role: str = 'user'

class UserUpdateDTO(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None

@app.get("/api/db/users/find")
def find_user(username: Optional[str] = None, email: Optional[str] = None):
    db = next(get_pg())
    query = db.query(UserModel)
    if username and email:
        user = query.filter((UserModel.username == username) | (UserModel.email == email)).first()
    elif username:
        user = query.filter(UserModel.username == username).first()
    elif email:
        user = query.filter(UserModel.email == email).first()
    else:
        raise HTTPException(status_code=400, detail="Specify username or email")
    
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "password_hash": user.password_hash,
        "full_name": user.full_name,
        "phone": user.phone,
        "address": user.address,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }

@app.get("/api/db/users/{user_id}")
def get_user_by_id(user_id: int):
    db = next(get_pg())
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "password_hash": user.password_hash,
        "full_name": user.full_name,
        "phone": user.phone,
        "address": user.address,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }

@app.post("/api/db/users")
def create_user(dto: UserCreateDTO):
    db = next(get_pg())
    user = UserModel(
        username=dto.username,
        email=dto.email,
        password_hash=dto.password_hash,
        full_name=dto.full_name,
        role=dto.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "address": user.address,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }

@app.put("/api/db/users/{user_id}")
def update_user(user_id: int, dto: UserUpdateDTO):
    db = next(get_pg())
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if dto.full_name is not None:
        user.full_name = dto.full_name
    if dto.phone is not None:
        user.phone = dto.phone
    if dto.address is not None:
        user.address = dto.address
    if dto.email is not None:
        user.email = dto.email
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "address": user.address,
        "role": user.role
    }

# ==============================================================================
# 2. PRODUCT DATABASE API
# ==============================================================================
class ProductDTO(BaseModel):
    name: str
    category: str
    price: float
    stock: int = 0
    img: Optional[str] = None
    images: List[str] = []
    desc: Optional[str] = None
    description: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    tags: List[str] = []
    is_featured: bool = False

@app.get("/api/db/products")
async def list_products_db(
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    featured: Optional[bool] = None
):
    db = get_mongo_db()
    query: Dict[str, Any] = {}
    if category and category != 'all':
        query['category'] = category
    if search:
        query['name'] = {'$regex': search, '$options': 'i'}
    if featured is not None:
        query['is_featured'] = featured

    total = await db.products.count_documents(query)
    skip = (page - 1) * limit
    cursor = db.products.find(query).skip(skip).limit(limit)

    items = []
    async for doc in cursor:
        doc['id'] = str(doc.pop('_id'))
        if doc.get('created_at') and isinstance(doc['created_at'], datetime):
            doc['created_at'] = doc['created_at'].isoformat()
        items.append(doc)

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit
    }

@app.get("/api/db/products/{product_id}")
async def get_product_db(product_id: str):
    db = get_mongo_db()
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")
    
    doc = await db.products.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    
    doc['id'] = str(doc.pop('_id'))
    if doc.get('created_at') and isinstance(doc['created_at'], datetime):
        doc['created_at'] = doc['created_at'].isoformat()
    return doc

@app.post("/api/db/products")
async def create_product_db(dto: ProductDTO):
    db = get_mongo_db()
    doc = dto.dict()
    doc['created_at'] = datetime.utcnow()
    doc['updated_at'] = datetime.utcnow()
    result = await db.products.insert_one(doc)
    doc['id'] = str(result.inserted_id)
    doc.pop('_id', None)
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    return doc

@app.put("/api/db/products/{product_id}")
async def update_product_db(product_id: str, dto: ProductDTO):
    db = get_mongo_db()
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    update_data = {k: v for k, v in dto.dict().items() if v is not None}
    update_data['updated_at'] = datetime.utcnow()

    res = await db.products.update_one({"_id": obj_id}, {"$set": update_data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    updated_doc = await db.products.find_one({"_id": obj_id})
    updated_doc['id'] = str(updated_doc.pop('_id'))
    if updated_doc.get('created_at') and isinstance(updated_doc['created_at'], datetime):
        updated_doc['created_at'] = updated_doc['created_at'].isoformat()
    if updated_doc.get('updated_at') and isinstance(updated_doc['updated_at'], datetime):
        updated_doc['updated_at'] = updated_doc['updated_at'].isoformat()
    return updated_doc

@app.delete("/api/db/products/{product_id}")
async def delete_product_db(product_id: str):
    db = get_mongo_db()
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    res = await db.products.delete_one({"_id": obj_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"status": "success", "message": "Product deleted"}

@app.get("/api/db/categories")
async def get_categories_db():
    db = get_mongo_db()
    pipeline = [
        {'$group': {'_id': '$category', 'count': {'$sum': 1}}},
        {'$project': {'name': '$_id', 'count': 1, '_id': 0}}
    ]
    categories = []
    async for doc in db.products.aggregate(pipeline):
        categories.append(doc)
    return categories

# ==============================================================================
# 3. ORDER DATABASE API
# ==============================================================================
class OrderItemDTO(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float

class OrderCreateDTO(BaseModel):
    user_id: int
    total_amount: float
    shipping_address: str
    shipping_name: str
    shipping_phone: str
    note: Optional[str] = None
    status: str = 'pending'
    items: List[OrderItemDTO] = []

class PaymentCreateDTO(BaseModel):
    order_id: int
    method: str
    amount: float
    status: str = 'success'
    transaction_id: str

@app.post("/api/db/orders")
def create_order_db(dto: OrderCreateDTO):
    db = next(get_mysql())
    new_order = OrderModel(
        user_id=dto.user_id,
        status=OrderStatusEnum(dto.status),
        total_amount=dto.total_amount,
        shipping_address=dto.shipping_address,
        shipping_name=dto.shipping_name,
        shipping_phone=dto.shipping_phone,
        note=dto.note
    )
    db.add(new_order)
    db.flush()

    for item in dto.items:
        order_item = OrderItemModel(
            order_id=new_order.id,
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price
        )
        db.add(order_item)

    db.commit()
    db.refresh(new_order)

    return {
        "id": new_order.id,
        "user_id": new_order.user_id,
        "status": new_order.status.value,
        "total_amount": float(new_order.total_amount),
        "created_at": new_order.created_at.isoformat(),
        "items": [
            {
                "product_id": it.product_id,
                "product_name": it.product_name,
                "quantity": it.quantity,
                "unit_price": float(it.unit_price)
            }
            for it in new_order.items
        ]
    }

@app.get("/api/db/orders")
def list_orders_db(user_id: Optional[int] = None):
    db = next(get_mysql())
    q = db.query(OrderModel)
    if user_id is not None:
        q = q.filter(OrderModel.user_id == user_id)
    orders = q.order_by(OrderModel.created_at.desc()).all()

    return [
        {
            "id": o.id,
            "user_id": o.user_id,
            "status": o.status.value,
            "total_amount": float(o.total_amount),
            "created_at": o.created_at.isoformat(),
            "items": [
                {
                    "product_id": it.product_id,
                    "product_name": it.product_name,
                    "quantity": it.quantity,
                    "unit_price": float(it.unit_price)
                }
                for it in o.items
            ]
        }
        for o in orders
    ]

@app.get("/api/db/orders/{order_id}")
def get_order_db(order_id: int):
    db = next(get_mysql())
    o = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "id": o.id,
        "user_id": o.user_id,
        "status": o.status.value,
        "total_amount": float(o.total_amount),
        "created_at": o.created_at.isoformat(),
        "items": [
            {
                "product_id": it.product_id,
                "product_name": it.product_name,
                "quantity": it.quantity,
                "unit_price": float(it.unit_price)
            }
            for it in o.items
        ]
    }

@app.put("/api/db/orders/{order_id}/status")
def update_order_status_db(order_id: int, status_update: Dict[str, str]):
    db = next(get_mysql())
    o = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    new_status = status_update.get("status")
    o.status = OrderStatusEnum(new_status)
    db.commit()
    return {"status": "success", "order_id": order_id, "new_status": new_status}

@app.post("/api/db/payments")
def create_payment_db(dto: PaymentCreateDTO):
    db = next(get_mysql())
    payment = PaymentModel(
        order_id=dto.order_id,
        method=dto.method,
        status=dto.status,
        amount=dto.amount,
        transaction_id=dto.transaction_id,
        paid_at=datetime.utcnow()
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "method": payment.method,
        "status": payment.status,
        "amount": float(payment.amount),
        "transaction_id": payment.transaction_id
    }

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "data-api-service"}
