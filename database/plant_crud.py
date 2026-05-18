from motor.motor_asyncio import AsyncIOMotorDatabase
from database.plant_model import PlantProfile
from datetime import datetime
from typing import Optional

async def get_plant_by_scientific_name(db: AsyncIOMotorDatabase, scientific_name: str) -> Optional[dict]:
    """Get plant profile by scientific name"""
    collection = db["plant_profiles"]
    plant = await collection.find_one({"scientific_name": scientific_name})
    
    # Ensure image fields exist for backward compatibility
    if plant:
        if "image_urls" not in plant:
            plant["image_urls"] = []
        if "img_avail" not in plant:
            plant["img_avail"] = False
    
    return plant

async def get_plant_by_common_name(db: AsyncIOMotorDatabase, common_name: str) -> Optional[dict]:
    """Get plant profile by common name (case-insensitive)"""
    collection = db["plant_profiles"]
    plant = await collection.find_one({"common_name": {"$regex": f"^{common_name}$", "$options": "i"}})
    
    # Ensure image fields exist for backward compatibility
    if plant:
        if "image_urls" not in plant:
            plant["image_urls"] = []
        if "img_avail" not in plant:
            plant["img_avail"] = False
    
    return plant

async def create_plant_basic(
    db: AsyncIOMotorDatabase,
    scientific_name: str,
    common_name: str,
    family: str = "",
    genus: str = ""
) -> dict:
    """Create a basic plant profile with only names (all_info=False)"""
    collection = db["plant_profiles"]
    
    plant_data = {
        "scientific_name": scientific_name,
        "common_name": common_name,
        "family": family,
        "genus": genus,
        "all_info": False,
        "image_urls": [],
        "img_avail": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await collection.insert_one(plant_data)
    plant_data["_id"] = result.inserted_id
    return plant_data

async def update_plant_full_info(
    db: AsyncIOMotorDatabase,
    scientific_name: str,
    profile_data: dict
) -> bool:
    """Update plant profile with full information (set all_info=True)"""
    collection = db["plant_profiles"]
    
    update_data = {
        **profile_data,
        "all_info": True,
        "updated_at": datetime.utcnow()
    }
    
    result = await collection.update_one(
        {"scientific_name": scientific_name},
        {"$set": update_data}
    )
    
    return result.modified_count > 0

async def upsert_plant_full_info(
    db: AsyncIOMotorDatabase,
    scientific_name: str,
    common_name: str,
    profile_data: dict,
    family: str = "",
    genus: str = "",
    image_urls: list = [],
    img_avail: bool= False
) -> dict:
    """Create or update plant with full information"""
    collection = db["plant_profiles"]
    
    full_data = {
        "scientific_name": scientific_name,
        "common_name": common_name,
        "family": family,
        "genus": genus,
        **profile_data,
        "all_info": True,
        "updated_at": datetime.utcnow(),
        "image_urls": image_urls,
        "img_avail": img_avail
    }

    
    result = await collection.update_one(
        {"scientific_name": scientific_name},
        {"$set": full_data, "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True
    )
    
    # Fetch and return the updated document
    return await collection.find_one({"scientific_name": scientific_name})

async def update_plant_images(
    db: AsyncIOMotorDatabase,
    scientific_name: str,
    image_urls: list[str],
    img_avail: bool = False
) -> bool:
    """
    Update plant profile with image URLs.
    
    Args:
        db: Database instance
        scientific_name: Scientific name of the plant
        image_urls: List of image URLs
        img_avail: Whether images are permanently stored (default: False)
    
    Returns:
        True if update was successful
    """
    collection = db["plant_profiles"]
    
    result = await collection.update_one(
        {"scientific_name": scientific_name},
        {
            "$set": {
                "image_urls": image_urls,
                "img_avail": img_avail,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0

async def mark_images_available(
    db: AsyncIOMotorDatabase,
    scientific_name: str
) -> bool:
    """
    Mark images as permanently available (set img_avail=True).
    
    Args:
        db: Database instance
        scientific_name: Scientific name of the plant
    
    Returns:
        True if update was successful
    """
    collection = db["plant_profiles"]
    
    result = await collection.update_one(
        {"scientific_name": scientific_name},
        {
            "$set": {
                "img_avail": True,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0
