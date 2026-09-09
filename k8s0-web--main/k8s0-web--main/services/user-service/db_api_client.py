import os
import logging
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger("UserDbApiClient")

DATABASE_API_URL = os.environ.get("DATABASE_API_URL", "http://data-api-service:8000")

class UserDbClient:
    def __init__(self, base_url: str = DATABASE_API_URL):
        self.base_url = base_url.rstrip("/")

    async def find_user(self, username: Optional[str] = None, email: Optional[str] = None) -> Optional[Dict[str, Any]]:
        params = {}
        if username:
            params["username"] = username
        if email:
            params["email"] = email
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/api/db/users/find", params=params)
            if resp.status_code == 200:
                return resp.json()
            return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/api/db/users/{user_id}")
            if resp.status_code == 200:
                return resp.json()
            return None

    async def create_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{self.base_url}/api/db/users", json=data)
            resp.raise_for_status()
            return resp.json()

    async def update_user(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(f"{self.base_url}/api/db/users/{user_id}", json=data)
            resp.raise_for_status()
            return resp.json()

user_db_client = UserDbClient()
