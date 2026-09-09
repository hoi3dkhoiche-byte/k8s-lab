import os
import logging
from typing import Optional, List, Dict, Any
import httpx

logger = logging.getLogger("CatalogDbApiClient")

DATABASE_API_URL = os.environ.get("DATABASE_API_URL", "http://data-api-service:8000")

class CatalogDbClient:
    def __init__(self, base_url: str = DATABASE_API_URL):
        self.base_url = base_url.rstrip("/")

    async def list_products(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 12,
        featured: Optional[bool] = None
    ) -> Dict[str, Any]:
        params = {"page": page, "limit": limit}
        if category:
            params["category"] = category
        if search:
            params["search"] = search
        if featured is not None:
            params["featured"] = featured

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/api/db/products", params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/api/db/products/{product_id}")
            if resp.status_code == 200:
                return resp.json()
            return None

    async def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{self.base_url}/api/db/products", json=data)
            resp.raise_for_status()
            return resp.json()

    async def update_product(self, product_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(f"{self.base_url}/api/db/products/{product_id}", json=data)
            resp.raise_for_status()
            return resp.json()

    async def delete_product(self, product_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(f"{self.base_url}/api/db/products/{product_id}")
            resp.raise_for_status()
            return resp.json()

    async def get_categories(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/api/db/categories")
            if resp.status_code == 200:
                return resp.json()
            return []

catalog_db_client = CatalogDbClient()
