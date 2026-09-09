import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.getenv('MONGO_URL', 'mongodb://admin:admin123@mongo-db:27017/')

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
