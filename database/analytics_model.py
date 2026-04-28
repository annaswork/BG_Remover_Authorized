from pydantic import BaseModel, Field, field_serializer
from typing import Optional
from datetime import datetime
from bson import ObjectId

# Analytics Models
class Analytics(BaseModel):
    id: Optional[str] = Field(alias="_id", description="Analytics record ID", default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analytics timestamp")
    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="Analytics path")
    status_code: int = Field(..., description="Analytics status code")
    request_size: int = Field(0, description="Analytics request size in bytes")
    response_size: int = Field(0, description="Analytics response size in bytes")
    total_bandwidth: int = Field(0, description="Analytics total bandwidth (request + response) in bytes")
    client_ip: Optional[str] = Field(None, description="Analytics client IP address")
    user_agent: Optional[str] = Field(None, description="Analytics user agent")
    response_time_ms: Optional[float] = Field(None, description="Analytics response time in milliseconds")
    app_name: Optional[str] = Field(None, description="App name associated with the API key")

    @field_serializer('id')
    def serialize_id(self, value: ObjectId, _info):
        if value is None:
            return None
        return str(value) if isinstance(value, ObjectId) else value

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

class AnalyticsSummary(BaseModel):
    total_requests: int = Field(..., description="Total number of requests")
    total_bandwidth: int = Field(..., description="Total bandwidth in bytes")
    average_response_time_ms: Optional[float] = Field(None, description="Average response time in milliseconds")
    requests_by_method: dict = Field(default_factory=dict, description="Requests grouped by HTTP method")
    requests_by_status: dict = Field(default_factory=dict, description="Requests grouped by status code")
    requests_by_endpoint: dict = Field(default_factory=dict, description="Requests grouped by endpoint")

