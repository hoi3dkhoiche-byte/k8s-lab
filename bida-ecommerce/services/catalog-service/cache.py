import os
import redis.asyncio as aioredis

REDIS_URL = os.getenv('REDIS_URL', 'redis://redis-db:6379/0')
redis_client = None

async def connect_to_redis():
    global redis_client
    try:
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        redis_client = None

async def close_redis_connection():
    global redis_client
    if redis_client:
        await redis_client.close()

async def get_redis():
    return redis_client
