import json
import logging
import math
import os
import httpx
from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from contextlib import asynccontextmanager

from db import connect_to_mongo, close_mongo_connection, get_database
from cache import connect_to_redis, close_redis_connection, get_redis
from security import get_current_user_claims
from schemas import ProductCreate, ProductResponse

ORDER_SERVICE_URL = os.getenv('ORDER_SERVICE_URL', 'http://order-service:8004')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    await connect_to_redis()
    logger.info('Catalog Service: Đã kết nối MongoDB và Redis')
    yield
    await close_mongo_connection()
    await close_redis_connection()

app = FastAPI(title='Catalog Service', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get('/api/catalog/products')
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
        query['category'] = category
    if search:
        query['name'] = {'$regex': search, '$options': 'i'}
    if featured is not None:
        query['is_featured'] = featured

    cache_key = f'products:page:{page}:limit:{limit}'
    is_filterable = category or search or featured is not None
    if not is_filterable and redis_client:
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception:
            pass

    skip = (page - 1) * limit
    cursor = db.products.find(query).skip(skip).limit(limit)
    products = []
    async for doc in cursor:
        doc['id'] = str(doc.pop('_id'))
        products.append(doc)


    total = await db.products.count_documents(query)
    
    result = {
        'items': products,
        'total': total,
        'page': page,
        'limit': limit,
        'total_pages': math.ceil(total / limit)
    }

    if not is_filterable and redis_client:
        try:
            await redis_client.setex(cache_key, 300, json.dumps(result, default=str))
        except Exception:
            pass

    return result

@app.get('/api/catalog/products/{product_id}')
async def get_product(product_id: str):
    db = get_database()
    try:
        doc = await db.products.find_one({'_id': ObjectId(product_id)})
    except Exception:
        raise HTTPException(status_code=400, detail='ID sản phẩm không hợp lệ')
    if not doc:
        raise HTTPException(status_code=404, detail='Không tìm thấy sản phẩm')
    doc['id'] = str(doc.pop('_id'))
    return doc

@app.post('/api/catalog/products')
async def create_product(
    product: ProductCreate, 
    user_claims: dict = Depends(get_current_user_claims)
):
    if user_claims.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Yêu cầu quyền admin')
        
    db = get_database()
    doc = product.model_dump()
    doc['created_at'] = datetime.utcnow()
    doc['images'] = []
    doc['is_featured'] = False

    result = await db.products.insert_one(doc)
    product_id = str(result.inserted_id)

    try:
        async with httpkx.AsyncClient() as client:
            await client.post(
                f'{ORDER_SERVICE_URL}/internal/inventory',
                json={'product_id': product_id, 'quantity': product.stock, 'reserved': 0},
                timeout=5.0
            )
    except Exception as e:
        logger.warning(f'Không thể đồng bộ inventory sang Order Service: {e}')

    doc['id'] = product_id
    doc.pop('_id', None)
    return doc

@app.put('/api/catalog/products/{product_id}')
async def update_product(
    product_id: str, 
    product_data: ProductCreate,
    user_claims: dict = Depends(get_current_user_claims)
):
    if user_claims.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Yêu cầu quyền admin')
        
    db = get_database()
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail='ID sản phẩm không hợp lệ')

    update_data = product_data.model_dump(exclude_unset=True)
    result = await db.products.update_one({'_id': obj_id}, {'$set': update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail='Không tìm thấy sản phẩm')
    
    return {'message': 'Cập nhật sản phẩm thành công'}

@app.get('/api/catalog/categories')
async def get_categories():
    db = get_database()
    pipeline = [
        {'$group': {'_id': '$category', 'count': {'$sum': 1}}},
        {'$project': {'name': '$_id', 'count': 1, '_id': 0}}
    ]
    categories = []
    async for doc in db.products.aggregate(pipeline):
        categories.append(doc)
    return categories

@app.post('/api/catalog/products/upload-image')
async def upload_image(
    file: UploadFile = File(...),
    user_claims: dict = Depends(get_current_user_claims)
):
    if user_claims.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Yêu cầu quyền admin')
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

@app.get('/api/catalog/products/image/{image_id}')
async def serve_image(image_id: str):
    db = get_database()
    try:
        doc = await db.images.find_one({'_id': ObjectId(image_id)})
    except Exception:
        raise HTTPException(status_code=400, detail='ID hình ảnh không hợp lệ')
    if not doc:
        raise HTTPException(status_code=404, detail='Không tfim thấy hình ảnh')
    
    return Response(content=doc['data'], media_type=doc['content_type'])

@app.get('/healthz')
def health_check():
    return {'status': 'ok', 'service': 'catalog-service'}
