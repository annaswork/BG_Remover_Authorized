from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class APIKey(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    app_name: str = Field(..., description="Application name associated with this key")
    api_key: str = Field(..., description="Unique API key")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True, description="Whether the key is active")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
