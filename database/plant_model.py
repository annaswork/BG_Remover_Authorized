from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class PlantProfile(BaseModel):
    """MongoDB model for plant profiles"""
    scientific_name: str = Field(..., description="Scientific name of the plant")
    common_name: Optional[str] = Field(None, description="Common name of the plant")
    family: Optional[str] = Field(None, description="Plant family")
    genus: Optional[str] = Field(None, description="Plant genus")
    
    # Flag to indicate if full info is loaded
    all_info: bool = Field(False, description="Whether full profile information is loaded")
    
    # Image URLs and availability flag
    image_urls: List[str] = Field(default_factory=list, description="List of image URLs for the plant")
    img_avail: bool = Field(False, description="Whether images have been scraped and stored")
    
    # Full profile fields (populated when all_info=True)
    description: Optional[str] = None
    taxonomy: Optional[str] = None
    care_frequency: Optional[str] = None
    temperature_celsius: Optional[str] = None
    fertilizer: Optional[str] = None
    sunlight: Optional[str] = None
    watering: Optional[str] = None
    humidity: Optional[str] = None
    location: Optional[str] = None
    pruning: Optional[str] = None
    insects: Optional[str] = None
    soil_type: Optional[str] = None
    growth_rate: Optional[str] = None
    hardiness_zones: Optional[str] = None
    toxicity: Optional[str] = None
    allergies_hazards: Optional[str] = None
    companions: Optional[str] = None
    problems: Optional[List[str]] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "scientific_name": "Solanum tuberosum",
                "common_name": "Potato",
                "family": "Solanaceae",
                "genus": "Solanum",
                "all_info": False,
                "image_urls": [],
                "img_avail": False
            }
        }
