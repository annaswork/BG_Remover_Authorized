from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Optional

async def get_animal_profile(db: AsyncIOMotorDatabase, name: str, animal_type: str) -> Optional[dict]:
    """Get animal profile by name (case-insensitive) and type"""
    collection = db["animal_profiles"]
    return await collection.find_one({
        "name": {"$regex": f"^{name}$", "$options": "i"},
        "type": animal_type
    })

async def create_animal_profile(
    db: AsyncIOMotorDatabase,
    name: str,
    animal_type: str,
    info: str,
    images: list = []
) -> dict:
    """Create or update (upsert) an animal profile"""
    collection = db["animal_profiles"]
    
    profile_data = {
        "name": name,
        "type": animal_type,
        "info": info,
        "images": images,
        "updated_at": datetime.utcnow()
    }
    
    await collection.update_one(
        {"name": {"$regex": f"^{name}$", "$options": "i"}, "type": animal_type},
        {"$set": profile_data, "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True
    )
    
    return await collection.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}, "type": animal_type})
