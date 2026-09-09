import json
import logging
import os
import httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from cache import connect_to_redis, close_redis_connection, get_redis
from security import get_current_user_claims
from schemas import CartItem, CartResponse, CartResponseItem

CATALOG_SERVICE_URL = os.getenv(CATALOG_SERVICE_URL, http://catalog-service:8002)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_redis()
    logger.info(Cart Service: Kết nối Redis thành công)
    yield
    await close_redis_connection()

app = FastAPI(title=Cart Service, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[*],
    allow_credentials=True,
    allow_methods=[*],
    allow_headers=[*],
)

def get_cart_key(user_id: int):
    return fcart:{user_id}

@app.get(/api/cart, response_model=CartResponse)
@app.get(/api/cart/, response_model=CartResponse)
async def get_cart(
    user_claims: dict = Depends(get_current_user_claims),
    redis_client = Depends(get_redis)
):
    if not redis_client:
        raise HTTPException(status_code=500, detail=Dịch vụ Redis không khả dụng)
    
    user_id = user_claims.get(user_id)
    cart_key = get_cart_key(user_id)
    raw_cart = await redis_client.hgetall(cart_key)
    
    if not raw_cart:
        return {items: [], total: 0.0}

    items = []
    total = 0.0

    async with httpx.AsyncClient() as client:
        for product_id_str, qty_str in raw_cart.items():
            qty = int(qty_str)
            try:
                resp = await client.get(f{CATALOG_SERVICE_URL}/api/catalog/products/{product_id_str}, timeout=3.0)
                if resp.status_code == 200:
                    product = resp.json()
                    price = float(product.get(price, 0))
                    total_price = price * qty
                    total += total_price
                    image = product.get(images)[0] if product.get(images) else None
                    items.append(CartResponseItem(
                        product_id=product_id_str,
                        product_name=product.get(name, Unknown),
                        quantity=qty,
                        unit_price=price,
                        total_price=total_price,
                        image=image
                    ))
            except Exception as e:
                logger.warning(fLỗi lấy thông tin sản phẩm {product_id_str}: {e})
                continue
            
    return {items: items, total: total}

@app.post(/api/cart/add)
async def add_to_cart(
    item: CartItem, 
    user_claims: dict = Depends(get_current_user_claims), 
    redis_client = Depends(get_redis)
):
    if not redis_client:
        raise HTTPException(status_code=500, detail=Dịch vụ Redis không khả dụng)
        
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f{CATALOG_SERVICE_URL}/api/catalog/products/{item.product_id}, timeout=3.0)
            if resp.status_code != 200:
                raise HTTPException(status_code=404, detail=Sản phẩm không tồn tại)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=503, detail=Không thể kiểm tra sản phẩm với Catalog Service)

    user_id = user_claims.get(user_id)
    cart_key = get_cart_key(user_id)
    await redis_client.hincrby(cart_key, item.product_id, item.quantity)
    return {message: Đã thêm vào giỏ hàng}

@app.put(/api/cart/update)
async def update_cart_item(
    item: CartItem, 
    user_claims: dict = Depends(get_current_user_claims), 
    redis_client = Depends(get_redis)
):
    if not redis_client:
        raise HTTPException(status_code=500, detail=Dịch vụ Redis không khả dụng)
        
    user_id = user_claims.get(user_id)
    cart_key = get_cart_key(user_id)
    if item.quantity <= 0:
        await redis_client.hdel(cart_key, item.product_id)
    else:
        await redis_client.hset(cart_key, item.product_id, item.quantity)
    return {message: Cập nhật giỏ hàng thành công}

@app.delete(/api/cart/remove/{product_id})
async def remove_from_cart(
    product_id: str, 
    user_claims: dict = Depends(get_current_user_claims), 
    redis_client = Depends(get_redis)
):
    if not redis_client:
        raise HTTPException(status_code=500, detail=Dịch vụ Redis không khả dụng)
        
    user_id = user_claims.get(user_id)
    cart_key = get_cart_key(user_id)
    await redis_client.hdel(cart_key, product_id)
    return {message: Đã xoá khỏi giỏ hàng}

@app.delete(/api/cart/clear)
async def clear_cart(
    user_claims: dict = Depends(get_current_user_claims), 
    redis_client = Depends(get_redis)
):
    if not redis_client:
        raise HTTPException(status_code=500, detail=Dịch vụ Redis không khả dụng)
        
    user_id = user_claims.get(user_id)
    cart_key = get_cart_key(user_id)
    await redis_client.delete(cart_key)
    return {message: Đã làm sạch giỏ hàng}

@app.get(/internal/cart/{user_id})
async def get_raw_cart(user_id: int, redis_client = Depends(get_redis)):
    if not redis_client:
        raise HTTPException(status_code=500, detail=Redis không khả dụng)
    cart_key = get_cart_key(user_id)
    return await redis_client.hgetall(cart_key)

@app.delete(/internal/cart/{user_id})
async def clear_user_cart(user_id: int, redis_client = Depends(get_redis)):
    if not redis_client:
        raise HTTPException(status_code=500, detail=Redis không khả dụng)
    cart_key = get_cart_key(user_id)
    await redis_client.delete(cart_key)
    return {status: cleared}

@app.get(/healthz)
def health_check():
    return {status: ok, service: cart-service}
