import logging
import os
from datetime import datetime
import httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from db import engine, Base, get_db
from models import Order, OrderItem, Payment, Inventory, OrderStatus
from schemas import OrderCreate, OrderResponse, PaymentCheckout, PaymentResponse, InventorySync
from security import get_current_user_claims
from kafka_producer import connect_to_kafka, close_kafka_connection, send_order_event

CART_SERVICE_URL = os.getenv(CART_SERVICE_URL, http://cart-service:8003)
CATALOG_SERVICE_URL = os.getenv(CATALOG_SERVICE_URL, http://catalog-service:8002)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(Order Service: Khởi tạo bảng MySQL thành công)
    except Exception as e:
        logger.error(fLỗi khởi tạo DB MySQL: {e})
    await connect_to_kafka()
    yield
    await close_kafka_connection()

app = FastAPI(title=Order & Payment Service, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[*],
    allow_credentials=True,
    allow_methods=[*],
    allow_headers=[*],
)

@app.post(/api/orders, response_model=OrderResponse)
@app.post(/api/orders/, response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    user_claims: dict = Depends(get_current_user_claims),
    mysql_db: Session = Depends(get_db)
):
    user_id = user_claims.get(user_id)
    
    # 1. Gọi sang Cart Service để lấy giỏ hàng của user
    raw_cart = {}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f{CART_SERVICE_URL}/internal/cart/{user_id}, timeout=5.0)
            if resp.status_code == 200:
                raw_cart = resp.json()
        except Exception as e:
            raise HTTPException(status_code=503, detail=fKhông thể kết nối tới Cart Service: {e})

    if not raw_cart:
        raise HTTPException(status_code=400, detail=Giỏ hàng trống)

    total_amount = 0.0
    items_to_create = []

    # 2. Kiểm tra thông tin sản phẩm từ Catalog Service và check kho MySQL
    async with httpx.AsyncClient() as client:
        for product_id_str, qty_str in raw_cart.items():
            qty = int(qty_str)
            try:
                resp = await client.get(f{CATALOG_SERVICE_URL}/api/catalog/products/{product_id_str}, timeout=4.0)
                if resp.status_code != 200:
                    raise HTTPException(status_code=404, detail=fSản phẩm {product_id_str} không tồn tại)
                product = resp.json()
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=503, detail=fKhông thể xác thực sản phẩm: {e})

            inv = mysql_db.query(Inventory).filter(Inventory.product_id == product_id_str).with_for_update().first()
            if not inv or (inv.quantity - inv.reserved) < qty:
                raise HTTPException(status_code=400, detail=fSản phẩm {product.get('name')} không đủ số lượng tồn kho)

            price = float(product.get(price, 0))
            total_amount += price * qty
            items_to_create.append({
                product_id: product_id_str,
                product_name: product.get(name),
                quantity: qty,
                unit_price: price,
                inv: inv
            })

    # 3. Tạo Order trong MySQL
    try:
        new_order = Order(
            user_id=user_id,
            status=OrderStatus.pending,
            total_amount=total_amount,
            shipping_address=order_data.shipping_address,
            shipping_name=order_data.shipping_name,
            shipping_phone=order_data.shipping_phone,
            note=order_data.note
        )
        mysql_db.add(new_order)
        mysql_db.flush()

        for item in items_to_create:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item[product_id],
                product_name=item[product_name],
                quantity=item[quantity],
                unit_price=item[unit_price]
            )
            mysql_db.add(order_item)
            item[inv].reserved += item[quantity]

        mysql_db.commit()
        mysql_db.refresh(new_order)

        # 4. Xóa giỏ hàng qua Cart Service
        async with httpx.AsyncClient() as client:
            await client.delete(f{CART_SERVICE_URL}/internal/cart/{user_id}, timeout=3.0)

        return new_order
    except Exception as e:
        mysql_db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get(/api/orders, response_model=list[OrderResponse])
@app.get(/api/orders/, response_model=list[OrderResponse])
def get_my_orders(
    user_claims: dict = Depends(get_current_user_claims),
    mysql_db: Session = Depends(get_db)
):
    user_id = user_claims.get(user_id)
    orders = mysql_db.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).all()
    return orders

@app.get(/api/orders/{order_id}, response_model=OrderResponse)
def get_order_detail(
    order_id: int, 
    user_claims: dict = Depends(get_current_user_claims), 
    mysql_db: Session = Depends(get_db)
):
    user_id = user_claims.get(user_id)
    role = user_claims.get(role)
    order = mysql_db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=Không tìm thấy đơn hàng)
    if order.user_id != user_id and role != admin:
        raise HTTPException(status_code=403, detail=Không có quyền truy cập đơn hàng này)
    return order

@app.post(/api/payments/checkout, response_model=PaymentResponse)
async def checkout(
    payment_data: PaymentCheckout,
    user_claims: dict = Depends(get_current_user_claims),
    mysql_db: Session = Depends(get_db)
):
    user_id = user_claims.get(user_id)
    order = mysql_db.query(Order).filter(Order.id == payment_data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=Không tìm thấy đơn hàng)
    if order.user_id != user_id:
        raise HTTPException(status_code=403, detail=Không có quyền thanh toán đơn hàng này)
    if order.status != OrderStatus.pending:
        raise HTTPException(status_code=400, detail=Đơn hàng không ở trạng thái chờ thanh toán)

    transaction_id = fTXN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{order.id}
    
    new_payment = Payment(
        order_id=order.id,
        method=payment_data.method,
        status=success,
        amount=order.total_amount,
        transaction_id=transaction_id,
        paid_at=datetime.utcnow()
    )
    mysql_db.add(new_payment)
    order.status = OrderStatus.paid
    mysql_db.commit()
    mysql_db.refresh(new_payment)

    await send_order_event(
        order_id=order.id,
        status=PAID,
        user_id=user_id
    )

    return new_payment

# Internal API để Catalog Service đồng bộ stock
@app.post(/internal/inventory)
def sync_inventory(inv_data: InventorySync, mysql_db: Session = Depends(get_db)):
    inv = mysql_db.query(Inventory).filter(Inventory.product_id == inv_data.product_id).first()
    if not inv:
        inv = Inventory(
            product_id=inv_data.product_id,
            quantity=inv_data.quantity,
            reserved=inv_data.reserved
        )
        mysql_db.add(inv)
    else:
        inv.quantity = inv_data.quantity
        inv.reserved = inv_data.reserved
    mysql_db.commit()
    return {status: synced}

@app.get(/healthz)
def health_check():
    return {status: ok, service: order-service}
