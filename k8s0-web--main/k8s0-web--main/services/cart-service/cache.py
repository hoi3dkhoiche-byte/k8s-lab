import os
import redis.asyncio as aioredis

REDIS_URL = os.environ['REDIS_URL']
redis_client = None

async def connect_to_redis():
    global redis_client
    extra_kwargs = {}
    if REDIS_URL.startswith("rediss://"):
        extra_kwargs["ssl_cert_reqs"] = None
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True, **extra_kwargs)

async def close_redis_connection():
    global redis_client
    if redis_client:
        await redis_client.close()

async def get_redis():
    return redis_client
