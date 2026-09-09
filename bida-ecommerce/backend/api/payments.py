from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.db_mysql import get_db as get_mysql_db
from models.user_postgres import User
from models.order_mysql import Order, Payment, OrderStatus
from models.schemas import PaymentCheckout, PaymentResponse
from core.security import get_current_user
from core.kafka_producer import send_order_event
from datetime import datetime

router = APIRouter(prefix="/api/payments", tags=["payments"])

@router.post("/checkout", response_model=PaymentResponse)
async def checkout(
    payment_data: PaymentCheckout,
    current_user: User = Depends(get_current_user),
    mysql_db: Session = Depends(get_mysql_db)
):
    order = mysql_db.query(Order).filter(Order.id == payment_data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền thanh toán đơn hàng này")
    if order.status != OrderStatus.pending:
        raise HTTPException(status_code=400, detail="Đơn hàng không ở trạng thái chờ thanh toán")

    # Giả lập thanh toán thành công
    transaction_id = f"TXN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{order.id}"
    
    new_payment = Payment(
        order_id=order.id,
        method=payment_data.method,
        status="success",
        amount=order.total_amount,
        transaction_id=transaction_id,
        paid_at=datetime.utcnow()
    )
    mysql_db.add(new_payment)
    
    # Cập nhật trạng thái đơn hàng
    order.status = OrderStatus.paid
    mysql_db.commit()
    mysql_db.refresh(new_payment)

    # Gửi sự kiện Kafka
    await send_order_event(
        order_id=order.id,
        status="PAID",
        user_id=current_user.id
    )

    return new_payment
