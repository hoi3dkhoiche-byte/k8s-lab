import os
import logging
from typing import Optional, List, Dict, Any
import httpx

logger = logging.getLogger("OrderDbApiClient")

DATABASE_API_URL = os.environ.get("DATABASE_API_URL", "http://data-api-service:8000")

class OrderDbClient:
    def __init__(self, base_url: str = DATABASE_API_URL):
        self.base_url = base_url.rstrip("/")

    async def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{self.base_url}/api/db/orders", json=order_data)
            resp.raise_for_status()
            return resp.json()

    async def list_orders(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        params = {}
        if user_id is not None:
            params["user_id"] = user_id
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/api/db/orders", params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/api/db/orders/{order_id}")
            if resp.status_code == 200:
                return resp.json()
            return None

    async def update_order_status(self, order_id: int, status: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(f"{self.base_url}/api/db/orders/{order_id}/status", json={"status": status})
            resp.raise_for_status()
            return resp.json()

    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{self.base_url}/api/db/payments", json=payment_data)
            resp.raise_for_status()
            return resp.json()

order_db_client = OrderDbClient()
