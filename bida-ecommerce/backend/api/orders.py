from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.db_mysql import get_db as get_mysql_db
from core.db_redis import get_redis
from core.db_mongo import get_database
from models.user_postgres import User
from models.order_mysql import Order, OrderItem, Inventory, OrderStatus
from models.schemas import OrderCreate, OrderResponse
from core.security import get_current_user
from bson import ObjectId

router = APIRouter(prefix="/api/orders", tags=["orders"])

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    mysql_db: Session = Depends(get_mysql_db),
    redis_client = Depends(get_redis)
):
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis không khả dụng")
        
    cart_key = f"cart:{current_user.id}"
    raw_cart = await redis_client.hgetall(cart_key)
    if not raw_cart:
        raise HTTPException(status_code=400, detail="Giỏ hàng trống")

    db_mongo = get_database()
    total_amount = 0.0
    items_to_create = []
    
    # Validation and Inventory Check
    for product_id_str, qty_str in raw_cart.items():
        qty = int(qty_str)
        try:
            product = await db_mongo.products.find_one({"_id": ObjectId(product_id_str)})
        except Exception:
            continue
            
        if not product:
            raise HTTPException(status_code=404, detail=f"Sản phẩm {product_id_str} không tồn tại")
            
        # Check inventory
        inv = mysql_db.query(Inventory).filter(Inventory.product_id == product_id_str).with_for_update().first()
        if not inv or (inv.quantity - inv.reserved) < qty:
            raise HTTPException(status_code=400, detail=f"Sản phẩm {product.get('name')} không đủ số lượng")
            
        price = float(product.get("price", 0))
        total_amount += price * qty
        items_to_create.append({
            "product_id": product_id_str,
            "product_name": product.get("name"),
            "quantity": qty,
            "unit_price": price,
            "inv": inv
        })

    try:
        # Create Order
        new_order = Order(
            user_id=current_user.id,
            status=OrderStatus.pending,
            total_amount=total_amount,
            shipping_address=order_data.shipping_address,
            shipping_name=order_data.shipping_name,
            shipping_phone=order_data.shipping_phone,
            note=order_data.note
        )
        mysql_db.add(new_order)
        mysql_db.flush()

        # Create Order Items and update inventory
        for item in items_to_create:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item["product_id"],
                product_name=item["product_name"],
                quantity=item["quantity"],
                unit_price=item["unit_price"]
            )
            mysql_db.add(order_item)
            item["inv"].reserved += item["quantity"]

        mysql_db.commit()
        mysql_db.refresh(new_order)
        
        # Clear Cart
        await redis_client.delete(cart_key)
        
        return new_order
    except Exception as e:
        mysql_db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=list[OrderResponse])
def get_my_orders(current_user: User = Depends(get_current_user), mysql_db: Session = Depends(get_mysql_db)):
    orders = mysql_db.query(Order).filter(Order.user_id == current_user.id).order_by(Order.created_at.desc()).all()
    return orders

@router.get("/{order_id}", response_model=OrderResponse)
def get_order_detail(order_id: int, current_user: User = Depends(get_current_user), mysql_db: Session = Depends(get_mysql_db)):
    order = mysql_db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    if order.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền truy cập đơn hàng này")
    return order
