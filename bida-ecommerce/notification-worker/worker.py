"""
Notification Worker Service - Bida Cao Cap E-commerce
Consume order events from Apache Kafka and persist/process notifications in MongoDB.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from motor.motor_asyncio import AsyncIOMotorClient

# ==============================================================================
# Logging Configuration
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("NotificationWorker")

# ==============================================================================
# Environment Configuration
# ==============================================================================
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "order-events")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "bida-notification-group")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://admin:admin123@mongo-db:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "notification_db")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "notifications")

# Retries configuration
MAX_CONNECT_RETRIES = int(os.getenv("MAX_CONNECT_RETRIES", "30"))
RETRY_INTERVAL_SECONDS = int(os.getenv("RETRY_INTERVAL_SECONDS", "5"))


class NotificationWorker:
    """
    Kafka Consumer Worker xử lý thông báo đơn hàng (Order Notifications)
    """

    def __init__(self):
        self.running = False
        self.shutdown_event = asyncio.Event()
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.collection = None

    def init_mongo(self) -> None:
        """Khởi tạo kết nối tới MongoDB"""
        logger.info(f"Connecting to MongoDB at: {MONGO_URL}")
        self.mongo_client = AsyncIOMotorClient(
            MONGO_URL,
            serverSelectionTimeoutMS=5000,
        )
        self.db = self.mongo_client[MONGO_DB_NAME]
        self.collection = self.db[MONGO_COLLECTION]
        logger.info(f"MongoDB initialized. Database: {MONGO_DB_NAME}, Collection: {MONGO_COLLECTION}")

    async def save_notification_to_mongo(self, order_data: Dict[str, Any], raw_payload: Dict[str, Any]) -> Optional[str]:
        """
        Lưu bản ghi thông báo vào MongoDB
        """
        if self.collection is None:
            logger.warning("MongoDB collection is not initialized. Skipping save.")
            return None

        try:
            order_id = str(order_data.get("order_id") or order_data.get("id") or "UNKNOWN")
            user_id = str(order_data.get("user_id") or order_data.get("customer_id") or "")
            customer_email = order_data.get("customer_email") or order_data.get("email") or ""
            customer_name = order_data.get("customer_name") or order_data.get("name") or "Khách hàng"
            total_amount = order_data.get("total_amount") or order_data.get("total") or 0

            notification_doc = {
                "order_id": order_id,
                "user_id": user_id,
                "customer_email": customer_email,
                "customer_name": customer_name,
                "total_amount": total_amount,
                "currency": "VND",
                "notification_type": "ORDER_CONFIRMATION",
                "channel": "EMAIL_AND_INAPP",
                "status": "SENT",
                "subject": f"Xác nhận thanh toán thành công đơn hàng #{order_id}",
                "message": (
                    f"Chào {customer_name}, đơn hàng #{order_id} với giá trị "
                    f"{total_amount:,.0f} VND đã được thanh toán thành công. "
                    "Bida Cao Cấp đang tiến hành chuẩn bị đơn hàng cho bạn."
                ),
                "event_payload": raw_payload,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            result = await self.collection.insert_one(notification_doc)
            inserted_id = str(result.inserted_id)
            logger.info(f"✅ Notification saved to MongoDB with _id: {inserted_id} for order #{order_id}")
            return inserted_id
        except Exception as e:
            logger.error(f"❌ Error saving notification to MongoDB: {e}", exc_info=True)
            return None

    async def process_message(self, message_value: Dict[str, Any]) -> None:
        """
        Xử lý nội dung message nhận được từ Kafka topic order-events
        """
        try:
            # Hỗ trợ payload dạng lồng nhau hoặc phẳng
            event_type = (
                message_value.get("event")
                or message_value.get("event_type")
                or message_value.get("type")
                or ""
            )
            order_data = message_value.get("data") or message_value.get("order") or message_value
            status = str(
                order_data.get("status")
                or message_value.get("status")
                or event_type
            ).upper()

            order_id = order_data.get("order_id") or order_data.get("id") or "N/A"
            user_id = order_data.get("user_id") or order_data.get("customer_id") or "N/A"
            customer_email = order_data.get("customer_email") or order_data.get("email") or "N/A"
            customer_name = order_data.get("customer_name") or order_data.get("name") or "Khách hàng"
            total_amount = order_data.get("total_amount") or order_data.get("total") or 0
            payment_method = order_data.get("payment_method") or "VNPAY/COD"
            items = order_data.get("items") or []

            logger.info(f"📥 Received event: [status='{status}'] for Order ID: #{order_id}")

            # Kiểm tra trạng thái PAID
            if status == "PAID" or "PAID" in event_type.upper():
                logger.info("=" * 60)
                logger.info(f"🎱 [BIDA CAO CẤP] XÁC NHẬN ĐƠN HÀNG ĐÃ THANH TOÁN THÀNH CÔNG")
                logger.info(f"   Mã đơn hàng       : #{order_id}")
                logger.info(f"   Mã người dùng     : {user_id}")
                logger.info(f"   Tên khách hàng    : {customer_name}")
                logger.info(f"   Email nhận thông báo: {customer_email}")
                logger.info(f"   Phương thức TT    : {payment_method}")
                logger.info(f"   Tổng số tiền      : {total_amount:,.0f} VND")
                if items:
                    logger.info(f"   Số lượng sản phẩm : {len(items)} món")
                logger.info(f"   Thời gian ghi nhận: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info("=" * 60)

                # Lưu thông báo vào MongoDB
                await self.save_notification_to_mongo(order_data, message_value)
            else:
                logger.info(f"ℹ️ Order #{order_id} status is '{status}' (Non-PAID event). Notification skipped.")

        except Exception as e:
            logger.error(f"❌ Error processing message: {e}", exc_info=True)

    async def connect_kafka_with_retry(self) -> AIOKafkaConsumer:
        """
        Thực hiện kết nối tới Kafka với cơ chế retry lặp lại khi Kafka đang khởi động
        """
        retry_count = 0
        while not self.shutdown_event.is_set():
            retry_count += 1
            try:
                logger.info(
                    f"Attempting to connect to Kafka at '{KAFKA_BOOTSTRAP}' "
                    f"(Attempt {retry_count}/{MAX_CONNECT_RETRIES})..."
                )
                consumer = AIOKafkaConsumer(
                    KAFKA_TOPIC,
                    bootstrap_servers=KAFKA_BOOTSTRAP,
                    group_id=KAFKA_GROUP_ID,
                    auto_offset_reset="earliest",
                    enable_auto_commit=True,
                    auto_commit_interval_ms=1000,
                    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                )
                await consumer.start()
                logger.info(
                    f"✅ Successfully connected to Kafka! "
                    f"Subscribed to topic: '{KAFKA_TOPIC}', group: '{KAFKA_GROUP_ID}'"
                )
                return consumer
            except (KafkaConnectionError, Exception) as e:
                logger.warning(
                    f"⚠️ Kafka connection failed: {e}. "
                    f"Retrying in {RETRY_INTERVAL_SECONDS}s..."
                )
                if retry_count >= MAX_CONNECT_RETRIES:
                    logger.error(f"❌ Exceeded maximum connection attempts ({MAX_CONNECT_RETRIES}).")
                    raise e
                try:
                    await asyncio.wait_for(self.shutdown_event.wait(), timeout=RETRY_INTERVAL_SECONDS)
                    if self.shutdown_event.is_set():
                        raise asyncio.CancelledError("Shutdown requested during retry")
                except asyncio.TimeoutError:
                    pass

        raise asyncio.CancelledError("Worker shutdown before Kafka connected")

    async def start(self) -> None:
        """Khởi chạy Worker và vòng lặp nhận tin nhắn"""
        self.running = True
        logger.info("🚀 Starting Notification Worker Service...")

        # 1. Khởi tạo kết nối MongoDB
        self.init_mongo()

        # 2. Kết nối tới Kafka
        try:
            self.consumer = await self.connect_kafka_with_retry()
        except Exception as e:
            logger.critical(f"❌ Could not establish Kafka connection: {e}")
            return

        # 3. Vòng lặp tiêu thụ tin nhắn
        logger.info(f"🎧 Listening for order events on topic '{KAFKA_TOPIC}'...")
        try:
            async for msg in self.consumer:
                if self.shutdown_event.is_set():
                    break
                try:
                    logger.debug(
                        f"Offset: {msg.offset}, Partition: {msg.partition}, Key: {msg.key}"
                    )
                    await self.process_message(msg.value)
                except Exception as err:
                    logger.error(f"Error handling message at offset {msg.offset}: {err}", exc_info=True)
        except asyncio.CancelledError:
            logger.info("Consumption loop cancelled.")
        except Exception as e:
            logger.error(f"Unexpected error in consumer loop: {e}", exc_info=True)
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Dừng Worker một cách an toàn (Graceful Shutdown)"""
        if not self.running:
            return
        self.running = False
        self.shutdown_event.set()
        logger.info("🛑 Stopping Notification Worker Service...")

        if self.consumer:
            try:
                await self.consumer.stop()
                logger.info("Kafka consumer stopped successfully.")
            except Exception as e:
                logger.error(f"Error stopping Kafka consumer: {e}")

        if self.mongo_client:
            try:
                self.mongo_client.close()
                logger.info("MongoDB connection closed.")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")

        logger.info("👋 Notification Worker Service stopped cleanly.")


def handle_signals(worker: NotificationWorker, loop: asyncio.AbstractEventLoop):
    """Đăng ký signal handlers cho SIGINT và SIGTERM"""
    def _shutdown():
        logger.info("Received termination signal. Initiating graceful shutdown...")
        worker.shutdown_event.set()

    # Unix signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except (NotImplementedError, AttributeError):
            # Windows fallback
            signal.signal(sig, lambda s, f: _shutdown())


async def main():
    worker = NotificationWorker()
    loop = asyncio.get_running_loop()
    handle_signals(worker, loop)

    try:
        await worker.start()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.critical(f"Fatal error in main: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker process exited.")
