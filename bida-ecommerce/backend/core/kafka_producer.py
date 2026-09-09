import os
import json
import logging
from aiokafka import AIOKafkaProducer

KAFKA_BOOTSTRAP = os.getenv('KAFKA_BOOTSTRAP', 'kafka:9092')
logger = logging.getLogger(__name__)
producer = None

async def connect_to_kafka():
    global producer
    try:
        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await producer.start()
        logger.info("Kết nối Kafka thành công")
    except Exception as e:
        logger.warning(f"Lỗi kết nối Kafka: {e}. Sẽ thử lại sau hoặc bỏ qua nếu không cần thiết.")
        producer = None

async def close_kafka_connection():
    global producer
    if producer:
        await producer.stop()

async def send_order_event(order_id, status, user_id):
    global producer
    if not producer:
        logger.warning("Kafka không khả dụng, bỏ qua việc gửi event")
        return
    
    event = {
        "order_id": order_id,
        "status": status,
        "user_id": user_id
    }
    try:
        await producer.send_and_wait('order-events', value=event)
        logger.info(f"Đã gửi event cho order {order_id} với trạng thái {status}")
    except Exception as e:
        logger.error(f"Lỗi khi gửi sự kiện Kafka: {e}")
