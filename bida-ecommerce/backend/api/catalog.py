import json
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import Response
from typing import Optional
from bson import ObjectId
from datetime import datetime
from core.db_mongo import get_database
from core.db_mysql import get_db as get_mysql_db
from core.db_redis import get_redis
from models.user_postgres import User
from models.order_mysql import Inventory
from models.schemas import ProductCreate, ProductResponse
from core.security import get_current_user, get_optional_user
from sqlalchemy.orm import Session
import math

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

@router.get("/products")
async def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    featured: Optional[bool] = None,
    redis_client = Depends(get_redis)
):
    db = get_database()
    query = {}
    if category:
        query["category"] = category
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    if featured is not None:
        query["is_featured"] = featured

    # Try cache if no filters
    cache_key = f"products:page:{page}:limit:{limit}"
    is_filterable = category or search or featured is not None
    if not is_filterable and redis_client:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

    skip = (page - 1) * limit
    cursor = db.products.find(query).skip(skip).limit(limit)
    products = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        products.append(doc)

    total = await db.products.count_documents(query)
    
    result = {
        "items": products,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(total / limit)
    }

    if not is_filterable and redis_client:
        await redis_client.setex(cache_key, 300, json.dumps(result, default=str))

    return result

@router.get("/products/{product_id}")
async def get_product(product_id: str):
    db = get_database()
    try:
        doc = await db.products.find_one({"_id": ObjectId(product_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID sản phẩm không hợp lệ")
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    doc["id"] = str(doc.pop("_id"))
    return doc

@router.post("/products")
async def create_product(
    product: ProductCreate, 
    current_user: User = Depends(get_current_user),
    mysql_db: Session = Depends(get_mysql_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yêu cầu quyền admin")
        
    db = get_database()
    doc = product.model_dump()
    doc["created_at"] = datetime.utcnow()
    doc["images"] = []
    doc["is_featured"] = False

    result = await db.products.insert_one(doc)
    product_id = str(result.inserted_id)

    # Create inventory in MySQL
    new_inventory = Inventory(product_id=product_id, quantity=product.stock, reserved=0)
    mysql_db.add(new_inventory)
    mysql_db.commit()

    doc["id"] = product_id
    doc.pop("_id", None)
    return doc

@router.put("/products/{product_id}")
async def update_product(
    product_id: str, 
    product_data: ProductCreate,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yêu cầu quyền admin")
        
    db = get_database()
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID sản phẩm không hợp lệ")

    update_data = product_data.model_dump(exclude_unset=True)
    result = await db.products.update_one({"_id": obj_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    
    return {"message": "Cập nhật sản phẩm thành công"}

@router.get("/categories")
async def get_categories():
    db = get_database()
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$project": {"name": "$_id", "count": 1, "_id": 0}}
    ]
    categories = []
    async for doc in db.products.aggregate(pipeline):
        categories.append(doc)
    return categories

@router.post("/products/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yêu cầu quyền admin")
    db = get_database()
    content = await file.read()
    
    image_doc = {
        "filename": file.filename,
        "content_type": file.content_type,
        "data": content,
        "uploaded_at": datetime.utcnow()
    }
    result = await db.images.insert_one(image_doc)
    return {"image_id": str(result.inserted_id)}

@router.get("/products/image/{image_id}")
async def serve_image(image_id: str):
    db = get_database()
    try:
        doc = await db.images.find_one({"_id": ObjectId(image_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID hình ảnh không hợp lệ")
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy hình ảnh")
    
    return Response(content=doc["data"], media_type=doc["content_type"])
