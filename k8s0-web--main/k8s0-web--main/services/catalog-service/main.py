import json
import logging
import math
import os
import httpx
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from cache import connect_to_redis, close_redis_connection, get_redis
from security import get_current_user_claims
from schemas import ProductCreate, ProductResponse
from db_api_client import catalog_db_client
from s3_client import s3_storage

ORDER_SERVICE_URL = os.environ.get('ORDER_SERVICE_URL', 'http://order-service:8000')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CatalogService")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_redis()
    logger.info('Catalog Service: Đã kết nối Redis (giao tiếp qua Database API & S3 Storage)')
    yield
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
    cache_key = f'products:page:{page}:limit:{limit}'
    is_filterable = category or search or (featured is not None)
    if not is_filterable and redis_client:
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception:
            pass

    try:
        data = await catalog_db_client.list_products(
            category=category,
            search=search,
            page=page,
            limit=limit,
            featured=featured
        )
    except Exception as e:
        logger.error(f"Error calling Database API: {e}")
        raise HTTPException(status_code=502, detail=f"Lỗi kết nối tới Database API: {str(e)}")

    products = []
    for doc in data.get('items', []):
        if not doc.get('img') and doc.get('images'):
            doc['img'] = doc['images'][0]
        if not doc.get('desc') and doc.get('description'):
            doc['desc'] = doc['description']
        elif not doc.get('description') and doc.get('desc'):
            doc['description'] = doc['desc']
        products.append(doc)

    total = data.get('total', len(products))
    result = {
        'items': products,
        'total': total,
        'page': page,
        'limit': limit,
        'pages': math.ceil(total / limit) if limit > 0 else 1
    }

    if not is_filterable and redis_client:
        try:
            await redis_client.setex(cache_key, 60, json.dumps(result))
        except Exception:
            pass

    return result

@app.get('/api/catalog/products/{product_id}', response_model=ProductResponse)
async def get_product(product_id: str):
    doc = await catalog_db_client.get_product(product_id)
    if not doc:
        raise HTTPException(status_code=404, detail='Không tìm thấy sản phẩm')
    
    if not doc.get('img') and doc.get('images'):
        doc['img'] = doc['images'][0]
    if not doc.get('desc') and doc.get('description'):
        doc['desc'] = doc['description']
    elif not doc.get('description') and doc.get('desc'):
        doc['description'] = doc['desc']
    return doc

@app.post('/api/catalog/products', response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    user_claims: dict = Depends(get_current_user_claims),
    redis_client = Depends(get_redis)
):
    if user_claims.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Yêu cầu quyền admin')
    
    product_dict = product_data.dict()
    if product_dict.get('img') and not product_dict.get('images'):
        product_dict['images'] = [product_dict['img']]
    elif product_dict.get('images') and not product_dict.get('img'):
        product_dict['img'] = product_dict['images'][0]

    created_product = await catalog_db_client.create_product(product_dict)
    
    # Invalidate cache
    if redis_client:
        try:
            keys = await redis_client.keys('products:*')
            if keys:
                await redis_client.delete(*keys)
        except Exception:
            pass

    # Đồng bộ tồn kho sang Order Service (nạp vào Redis realtime)
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f'{ORDER_SERVICE_URL}/internal/inventory',
                json={
                    'product_id': created_product['id'],
                    'quantity': product_data.stock or 0,
                    'reserved': 0
                },
                timeout=2.0
            )
    except Exception as e:
        logger.warning(f'Không thể đồng bộ stock sang order-service: {e}')

    return created_product

@app.put('/api/catalog/products/{product_id}', response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductCreate,
    user_claims: dict = Depends(get_current_user_claims),
    redis_client = Depends(get_redis)
):
    if user_claims.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Yêu cầu quyền admin')
    
    product_dict = {k: v for k, v in product_data.dict().items() if v is not None}
    if product_dict.get('img') and not product_dict.get('images'):
        product_dict['images'] = [product_dict['img']]
    elif product_dict.get('images') and not product_dict.get('img'):
        product_dict['img'] = product_dict['images'][0]

    updated_product = await catalog_db_client.update_product(product_id, product_dict)
    
    if redis_client:
        try:
            keys = await redis_client.keys('products:*')
            if keys:
                await redis_client.delete(*keys)
        except Exception:
            pass

    return updated_product

@app.delete('/api/catalog/products/{product_id}')
async def delete_product(
    product_id: str,
    user_claims: dict = Depends(get_current_user_claims),
    redis_client = Depends(get_redis)
):
    if user_claims.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Yêu cầu quyền admin')

    await catalog_db_client.delete_product(product_id)

    if redis_client:
        try:
            keys = await redis_client.keys('products:*')
            if keys:
                await redis_client.delete(*keys)
        except Exception:
            pass

    return {'message': 'Xoá sản phẩm thành công'}

@app.get('/api/catalog/categories')
async def get_categories():
    return await catalog_db_client.get_categories()

# ==============================================================================
# S3 IMAGE UPLOAD (CMC CLOUD S3)
# ==============================================================================
@app.post('/api/catalog/products/upload-image')
async def upload_image(
    file: UploadFile = File(...),
    user_claims: dict = Depends(get_current_user_claims)
):
    if user_claims.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Yêu cầu quyền admin')

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File rỗng")

    # Tải trực tiếp lên S3 Object Storage
    try:
        image_url = s3_storage.upload_image(
            file_content=content,
            original_filename=file.filename or "product_image.jpg",
            content_type=file.content_type or "image/jpeg"
        )
        return {
            "image_url": image_url,
            "image_id": image_url, # Backward compatibility
            "filename": file.filename
        }
    except Exception as e:
        logger.error(f"S3 Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi tải ảnh lên S3 CMC Cloud: {str(e)}")

@app.get('/healthz')
def health_check():
    return {'status': 'ok', 'service': 'catalog-service'}
