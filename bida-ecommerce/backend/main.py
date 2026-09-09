import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.db_postgres import engine as pg_engine, Base as PgBase
from core.db_mysql import engine as my_engine, Base as MyBase
from core.db_mongo import connect_to_mongo, close_mongo_connection
from core.db_redis import connect_to_redis, close_redis_connection
from core.kafka_producer import connect_to_kafka, close_kafka_connection

from api import auth, catalog, cart, orders, payments

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo DB
    try:
        PgBase.metadata.create_all(bind=pg_engine)
        logger.info("Tạo bảng PostgreSQL thành công")
    except Exception as e:
        logger.error(f"Lỗi tạo bảng PostgreSQL: {e}")

    try:
        MyBase.metadata.create_all(bind=my_engine)
        logger.info("Tạo bảng MySQL thành công")
    except Exception as e:
        logger.error(f"Lỗi tạo bảng MySQL: {e}")

    await connect_to_mongo()
    logger.info("Kết nối MongoDB thành công")

    await connect_to_redis()
    logger.info("Kết nối Redis thành công")

    await connect_to_kafka()

    yield

    # Cleanup
    await close_mongo_connection()
    await close_redis_connection()
    await close_kafka_connection()

app = FastAPI(title="Bida Cao Cap E-commerce", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(payments.router)

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

@app.get("/")
def read_root():
    return {"message": "Chào mừng đến với API Bida Cao Cấp!"}
