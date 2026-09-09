import json
from fastapi import APIRouter, Depends, HTTPException
from core.db_redis import get_redis
from core.db_mongo import get_database
from models.user_postgres import User
from models.schemas import CartItem, CartResponse, CartResponseItem
from core.security import get_current_user
from bson import ObjectId

router = APIRouter(prefix="/api/cart", tags=["cart"])

def get_cart_key(user_id: int):
    return f"cart:{user_id}"

@router.get("/", response_model=CartResponse)
async def get_cart(current_user: User = Depends(get_current_user), redis_client = Depends(get_redis)):
    if not redis_client:
        raise HTTPException(status_code=500, detail="Dịch vụ Redis không khả dụng")
    
    cart_key = get_cart_key(current_user.id)
    raw_cart = await redis_client.hgetall(cart_key)
    
    if not raw_cart:
        return {"items": [], "total": 0.0}

    db = get_database()
    items = []
    total = 0.0

    for product_id_str, qty_str in raw_cart.items():
        qty = int(qty_str)
        try:
            product = await db.products.find_one({"_id": ObjectId(product_id_str)})
            if product:
                price = float(product.get("price", 0))
                total_price = price * qty
                total += total_price
                image = product.get("images")[0] if product.get("images") else None
                items.append(CartResponseItem(
                    product_id=product_id_str,
                    product_name=product.get("name", "Unknown"),
                    quantity=qty,
                    unit_price=price,
                    total_price=total_price,
                    image=image
                ))
        except Exception:
            continue
            
    return {"items": items, "total": total}

@router.post("/add")
async def add_to_cart(
    item: CartItem, 
    current_user: User = Depends(get_current_user), 
    redis_client = Depends(get_redis)
):
    if not redis_client:
        raise HTTPException(status_code=500, detail="Dịch vụ Redis không khả dụng")
        
    db = get_database()
    try:
        product = await db.products.find_one({"_id": ObjectId(item.product_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID sản phẩm không hợp lệ")
        
    if not product:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")

    cart_key = get_cart_key(current_user.id)
    await redis_client.hincrby(cart_key, item.product_id, item.quantity)
    return {"message": "Đã thêm vào giỏ hàng"}

@router.put("/update")
async def update_cart_item(
    item: CartItem, 
    current_user: User = Depends(get_current_user), 
    redis_client = Depends(get_redis)
):
    if not redis_client:
        raise HTTPException(status_code=500, detail="Dịch vụ Redis không khả dụng")
        
    cart_key = get_cart_key(current_user.id)
    if item.quantity <= 0:
        await redis_client.hdel(cart_key, item.product_id)
    else:
        await redis_client.hset(cart_key, item.product_id, item.quantity)
    return {"message": "Cập nhật giỏ hàng thành công"}

@router.delete("/remove/{product_id}")
async def remove_from_cart(
    product_id: str, 
    current_user: User = Depends(get_current_user), 
    redis_client = Depends(get_redis)
):
    if not redis_client:
        raise HTTPException(status_code=500, detail="Dịch vụ Redis không khả dụng")
        
    cart_key = get_cart_key(current_user.id)
    await redis_client.hdel(cart_key, product_id)
    return {"message": "Đã xoá khỏi giỏ hàng"}

@router.delete("/clear")
async def clear_cart(
    current_user: User = Depends(get_current_user), 
    redis_client = Depends(get_redis)
):
    if not redis_client:
        raise HTTPException(status_code=500, detail="Dịch vụ Redis không khả dụng")
        
    cart_key = get_cart_key(current_user.id)
    await redis_client.delete(cart_key)
    return {"message": "Đã làm sạch giỏ hàng"}
