import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ['MONGO_URL']
client = None
db = None

async def connect_to_mongo():
    global client, db
    client = AsyncIOMotorClient(MONGO_URL)
    db = client['catalog_db']

async def close_mongo_connection():
    global client
    if client:
        client.close()

def get_database():
    return db
