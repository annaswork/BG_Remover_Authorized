import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from config.index import MONGODB_URL, ANALYTICS_DATABASE, AUTHORIZATION_DATABASE

load_dotenv()

class MongoDB:
    client: AsyncIOMotorClient = None

db = MongoDB()

async def connect_to_mongo():
    """Create database connection"""
    try:
        db.client = AsyncIOMotorClient(MONGODB_URL)
        # Test the connection
        await db.client.admin.command('ping')
        print(f"Connected to MongoDB at {MONGODB_URL}")
        print(f"Using database: {ANALYTICS_DATABASE}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()

# Existing Analytics DB Getter
def get_analytics_db():
    if db.client is None:
        db.client = AsyncIOMotorClient(MONGODB_URL)
    return db.client[ANALYTICS_DATABASE]

# New Assets DB Getter
def get_authorization_db():
    if db.client is None:
        db.client = AsyncIOMotorClient(MONGODB_URL)
    return db.client[AUTHORIZATION_DATABASE]