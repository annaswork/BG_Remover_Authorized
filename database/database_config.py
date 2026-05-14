import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, MongoClient

from config.index import (
    ANALYTICS_DATABASE,
    AUTHORIZATION_DATABASE,
    MONGODB_URL,
    URDU_SHAYARI_DATABASE,
)

load_dotenv()


class MongoDB:
    client: AsyncIOMotorClient = None


db = MongoDB()


async def connect_to_mongo():
    """Create database connection"""
    try:
        db.client = AsyncIOMotorClient(MONGODB_URL)
        await db.client.admin.command("ping")
        print(f"Connected to MongoDB at {MONGODB_URL}")
        print(f"Using database: {ANALYTICS_DATABASE}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()


def get_analytics_db():
    if db.client is None:
        db.client = AsyncIOMotorClient(MONGODB_URL)
    return db.client[ANALYTICS_DATABASE]


def get_authorization_db():
    if db.client is None:
        db.client = AsyncIOMotorClient(MONGODB_URL)
    return db.client[AUTHORIZATION_DATABASE]


# ── Urdu Shayari (sync PyMongo; OpenAI chat persistence) ─────────────────────
urdu_sync_client = MongoClient(MONGODB_URL)
urdu_shayari_db = urdu_sync_client[URDU_SHAYARI_DATABASE]
collection_by_type = urdu_shayari_db["shayari_by_types"]
collection_by_topic = urdu_shayari_db["shayari_by_topics"]
collection_of_conversation = urdu_shayari_db["ai_conversation"]
sort_orders = [ASCENDING, DESCENDING]
