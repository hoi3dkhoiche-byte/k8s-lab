import logging
import os
from datetime import datetime
import httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from schemas import OrderCreate, OrderResponse, PaymentCheckout, PaymentResponse, InventorySync
from security import get_current_user_claims
from kafka_producer import connect_to_kafka, close_kafka_connection, send_order_event
from redis_realtime import realtime_engine
from db_api_client import order_db_client

CART_SERVICE_URL = os.environ.get('CART_SERVICE_URL', 'http://cart-service:8000')
CATALOG_SERVICE_URL = os.environ.get('CATALOG_SERVICE_URL', 'http://catalog-service:8000')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OrderService")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_kafka()
    await realtime_engine.connect()
    logger.info('Order Service: Khởi động thành công với Redis Real-Time Engine & Database API')
    yield
    await realtime_engine.close()
    await close_kafka_connection()

app = FastAPI(title='Order & Payment Service (Redis Real-Time Engine)', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.post('/api/orders', response_model=OrderResponse)
@app.post('/api/orders/', response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    user_claims: dict = Depends(get_current_user_claims)
):
    user_id = user_claims.get('user_id')
    
    # 1. Lấy giỏ hàng từ Cart Service
    raw_cart = {}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f'{CART_SERVICE_URL}/internal/cart/{user_id}', timeout=5.0)
            if resp.status_code == 200:
                raw_cart = resp.json()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f'Không thể kết nối tới Cart Service: {e}')

    if not raw_cart:
        raise HTTPException(status_code=400, detail='Giỏ hàng trống')

    total_amount = 0.0
    items_to_create = []

    # 2. Lấy thông tin sản phẩm từ Catalog Service
    async with httpx.AsyncClient() as client:
        for product_id_str, qty_str in raw_cart.items():
            qty = int(qty_str)
            try:
                resp = await client.get(f'{CATALOG_SERVICE_URL}/api/catalog/products/{product_id_str}', timeout=4.0)
                if resp.status_code != 200:
                    raise HTTPException(status_code=404, detail=f'Sản phẩm {product_id_str} không tồn tại')
                product = resp.json()
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=503, detail=f'Không thể xác thực sản phẩm: {e}')

            price = float(product.get('price', 0))
            total_amount += price * qty
            items_to_create.append({
                'product_id': product_id_str,
                'product_name': product.get('name', 'Sản phẩm'),
                'quantity': qty,
                'unit_price': price
            })

    # 3. Kiểm tra và khóa giữ chỗ tồn kho REAL-TIME trên Redis (Atomic Lua Script)
    reserved_success = await realtime_engine.reserve_order_items(items_to_create)
    if not reserved_success:
        raise HTTPException(status_code=400, detail='Rất tiếc, một số sản phẩm trong giỏ hàng không đủ số lượng tồn kho khả dụng')

    # 4. Lưu đơn hàng vĩnh viễn qua Database API
    try:
        new_order = await order_db_client.create_order({
            'user_id': user_id,
            'total_amount': total_amount,
            'shipping_address': order_data.shipping_address,
            'shipping_name': order_data.shipping_name,
            'shipping_phone': order_data.shipping_phone,
            'note': order_data.note,
            'status': 'pending',
            'items': items_to_create
        })

        # 5. Xóa giỏ hàng qua Cart Service
        async with httpx.AsyncClient() as client:
            await client.delete(f'{CART_SERVICE_URL}/internal/cart/{user_id}', timeout=3.0)

        return new_order
    except Exception as e:
        # Nếu lưu Database API lỗi, hoàn trả tồn kho trên Redis
        await realtime_engine.release_order_items(items_to_create)
        logger.error(f"Failed to persist order to Database API: {e}")
        raise HTTPException(status_code=500, detail=f'Lỗi lưu trữ đơn hàng: {str(e)}')

@app.get('/api/orders', response_model=list[OrderResponse])
@app.get('/api/orders/', response_model=list[OrderResponse])
async def get_my_orders(user_claims: dict = Depends(get_current_user_claims)):
    user_id = user_claims.get('user_id')
    return await order_db_client.list_orders(user_id=user_id)

@app.get('/api/orders/all', response_model=list[OrderResponse])
async def get_all_orders(user_claims: dict = Depends(get_current_user_claims)):
    if user_claims.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Yêu cầu quyền admin')
    return await order_db_client.list_orders()

@app.get('/api/orders/{order_id}', response_model=OrderResponse)
async def get_order_detail(order_id: int, user_claims: dict = Depends(get_current_user_claims)):
    user_id = user_claims.get('user_id')
    role = user_claims.get('role')
    order = await order_db_client.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail='Không tìm thấy đơn hàng')
    if order['user_id'] != user_id and role != 'admin':
        raise HTTPException(status_code=403, detail='Không có quyền truy cập đơn hàng này')
    return order

@app.put('/api/orders/{order_id}/cancel')
async def cancel_order(order_id: int, user_claims: dict = Depends(get_current_user_claims)):
    user_id = user_claims.get('user_id')
    role = user_claims.get('role')

    order = await order_db_client.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail='Không tìm thấy đơn hàng')
    if order['user_id'] != user_id and role != 'admin':
        raise HTTPException(status_code=403, detail='Không có quyền hủy đơn hàng này')
    if order['status'] not in ('pending', 'confirmed'):
        raise HTTPException(status_code=400, detail='Không thể hủy đơn hàng ở trạng thái này')

    # Giải phóng tồn kho trên Redis Real-time Engine
    await realtime_engine.release_order_items(order.get('items', []))

    # Cập nhật trạng thái trong Database API
    await order_db_client.update_order_status(order_id, 'cancelled')
    return {'message': 'Đã hủy đơn hàng thành công và hoàn trả tồn kho', 'order_id': order_id}

@app.put('/api/orders/{order_id}/status')
async def update_order_status(
    order_id: int,
    body: dict,
    user_claims: dict = Depends(get_current_user_claims)
):
    if user_claims.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Yêu cầu quyền admin')

    order = await order_db_client.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail='Không tìm thấy đơn hàng')

    new_status = body.get('status')
    old_status = order['status']

    # Nếu chuyển sang cancelled → giải phóng reserved tồn kho trên Redis
    if new_status == 'cancelled' and old_status in ('pending', 'confirmed'):
        await realtime_engine.release_order_items(order.get('items', []))

    await order_db_client.update_order_status(order_id, new_status)
    return {'message': f'Đã cập nhật trạng thái thành {new_status}', 'order_id': order_id}

@app.post('/api/payments/checkout', response_model=PaymentResponse)
async def checkout(
    payment_data: PaymentCheckout,
    user_claims: dict = Depends(get_current_user_claims)
):
    user_id = user_claims.get('user_id')
    order = await order_db_client.get_order(payment_data.order_id)
    if not order:
        raise HTTPException(status_code=404, detail='Không tìm thấy đơn hàng')
    if order['user_id'] != user_id:
        raise HTTPException(status_code=403, detail='Không có quyền thanh toán đơn hàng này')
    if order['status'] != 'pending':
        raise HTTPException(status_code=400, detail='Đơn hàng không ở trạng thái chờ thanh toán')

    # 1. Trừ tồn kho thực tế trên REDIS Real-time Engine (Atomic)
    await realtime_engine.deduct_order_items(order.get('items', []))

    # 2. Lưu payment và cập nhật trạng thái PAID qua Database API
    transaction_id = f"TXN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{order['id']}"
    payment = await order_db_client.create_payment({
        'order_id': order['id'],
        'method': payment_data.method,
        'amount': order['total_amount'],
        'status': 'success',
        'transaction_id': transaction_id
    })

    await order_db_client.update_order_status(order['id'], 'paid')

    # 3. Bắn event Kafka bất đồng bộ
    await send_order_event(
        order_id=order['id'],
        status='PAID',
        user_id=user_id
    )

    return payment

# Internal API để nạp/đồng bộ tồn kho vào Redis Real-time Engine
@app.post('/internal/inventory')
async def sync_inventory(inv_data: InventorySync):
    await realtime_engine.set_initial_stock(
        product_id=inv_data.product_id,
        quantity=inv_data.quantity,
        reserved=inv_data.reserved
    )
    return {'status': 'synced', 'engine': 'redis-realtime'}

@app.get('/api/orders/realtime/stock/{product_id}')
async def get_product_realtime_stock(product_id: str):
    return await realtime_engine.get_stock(product_id)

@app.get('/healthz')
def health_check():
    return {'status': 'ok', 'service': 'order-service'}
