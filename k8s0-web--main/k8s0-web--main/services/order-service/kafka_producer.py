import os
import json
import logging
# pyrefly: ignore [missing-import]
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
        logger.info('Order Service: Kết nối Kafka thành công')
    except Exception as e:
        logger.warning(f'Order Service: Lỗi kết nối Kafka: {e}')
        producer = None

async def close_kafka_connection():
    global producer
    if producer:
        await producer.stop()

async def send_order_event(order_id, status, user_id):
    global producer
    if not producer:
        logger.warning('Kafka không khả dụng, bỏ qua gửi event')
        return
    
    event = {
        'order_id': order_id,
        'status': status,
        'user_id': user_id
    }
    try:
        await producer.send_and_wait('order-events', value=event)
        logger.info(f'Order Service: Đã gửi event cho order {order_id} trạng thái {status}')
    except Exception as e:
        logger.error(f'Order Service: Lỗi khi gửi sự kiện Kafka: {e}')
