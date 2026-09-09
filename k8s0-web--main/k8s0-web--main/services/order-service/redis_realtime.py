import os
import json
import logging
from typing import List, Dict, Any, Optional
import redis.asyncio as aioredis

logger = logging.getLogger("RedisRealtime")

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis-db:6379/0")

# Atomic Lua Scripts for Concurrency Safety
RESERVE_STOCK_SCRIPT = """
local stock_key = KEYS[1]
local reserved_key = KEYS[2]
local qty = tonumber(ARGV[1])

local stock = tonumber(redis.call('get', stock_key) or '0')
local reserved = tonumber(redis.call('get', reserved_key) or '0')
local available = stock - reserved

if available >= qty then
    redis.call('incrby', reserved_key, qty)
    return 1
else
    return 0
end
"""

DEDUCT_STOCK_SCRIPT = """
local stock_key = KEYS[1]
local reserved_key = KEYS[2]
local qty = tonumber(ARGV[1])

local stock = tonumber(redis.call('get', stock_key) or '0')
local reserved = tonumber(redis.call('get', reserved_key) or '0')

if stock >= qty then
    redis.call('decrby', stock_key, qty)
else
    redis.call('set', stock_key, '0')
end

if reserved >= qty then
    redis.call('decrby', reserved_key, qty)
else
    redis.call('set', reserved_key, '0')
end

return 1
"""

RELEASE_STOCK_SCRIPT = """
local reserved_key = KEYS[1]
local qty = tonumber(ARGV[1])

local reserved = tonumber(redis.call('get', reserved_key) or '0')
if reserved >= qty then
    redis.call('decrby', reserved_key, qty)
else
    redis.call('set', reserved_key, '0')
end

return 1
"""

class RedisRealtimeEngine:
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_url = redis_url
        self.client: Optional[aioredis.Redis] = None

    async def connect(self):
        try:
            self.client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.client.ping()
            logger.info("Connected to Redis for Real-time Trading & Inventory Engine")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")

    async def close(self):
        if self.client:
            await self.client.close()

    def _get_keys(self, product_id: str):
        return f"stock:{product_id}", f"reserved:{product_id}"

    async def set_initial_stock(self, product_id: str, quantity: int, reserved: int = 0):
        stock_key, res_key = self._get_keys(product_id)
        await self.client.set(stock_key, str(quantity))
        await self.client.set(res_key, str(reserved))

    async def get_stock(self, product_id: str) -> Dict[str, int]:
        stock_key, res_key = self._get_keys(product_id)
        pipe = self.client.pipeline()
        pipe.get(stock_key)
        pipe.get(res_key)
        results = await pipe.execute()
        
        stock = int(results[0] or 0)
        reserved = int(results[1] or 0)
        return {
            "quantity": stock,
            "reserved": reserved,
            "available": max(0, stock - reserved)
        }

    async def reserve_order_items(self, items: List[Dict[str, Any]]) -> bool:
        """
        Atomically checks and reserves stock for all items in an order.
        If any item fails, rolls back previously reserved items in the list.
        """
        reserved_so_far = []
        for item in items:
            p_id = str(item['product_id'])
            qty = int(item['quantity'])
            stock_key, res_key = self._get_keys(p_id)

            success = await self.client.eval(RESERVE_STOCK_SCRIPT, 2, stock_key, res_key, str(qty))
            if success == 1:
                reserved_so_far.append((p_id, qty))
            else:
                # Rollback previously reserved
                for roll_pid, roll_qty in reserved_so_far:
                    _, r_key = self._get_keys(roll_pid)
                    await self.client.eval(RELEASE_STOCK_SCRIPT, 1, r_key, str(roll_qty))
                return False
        return True

    async def deduct_order_items(self, items: List[Dict[str, Any]]):
        """
        Deducts real-time stock and clears reservation when payment succeeds.
        """
        for item in items:
            p_id = str(item['product_id'])
            qty = int(item['quantity'])
            stock_key, res_key = self._get_keys(p_id)
            await self.client.eval(DEDUCT_STOCK_SCRIPT, 2, stock_key, res_key, str(qty))

    async def release_order_items(self, items: List[Dict[str, Any]]):
        """
        Releases reserved stock back to available pool when order is cancelled.
        """
        for item in items:
            p_id = str(item['product_id'])
            qty = int(item['quantity'])
            _, res_key = self._get_keys(p_id)
            await self.client.eval(RELEASE_STOCK_SCRIPT, 1, res_key, str(qty))

realtime_engine = RedisRealtimeEngine()
