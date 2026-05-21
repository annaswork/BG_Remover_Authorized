from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class AnimalProfile(BaseModel):
    """MongoDB model for animal profiles (dogs, insects, spiders)"""
    name: str = Field(..., description="Name of the animal (breed, insect name, spider name)")
    type: str = Field(..., description="Type of animal: dog, insect, spider")
    info: str = Field(..., description="Rendered HTML info string for the animal")
    images: List[str] = Field(default_factory=list, description="List of image URLs")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Golden Retriever",
                "type": "dog",
                "info": "<table>...</table>",
                "images": ["/static/animals/Golden Retriever/1.jpg"]
            }
        }
