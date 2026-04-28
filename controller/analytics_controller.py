from typing import List, Optional, Dict
from bson import ObjectId
from datetime import datetime, timedelta
from database.database_config import get_analytics_db
from database.analytics_model import Analytics
from config.index import ANALYTICS_COLLECTION_NAME

async def create_analytics_record(analytics: Analytics) -> dict:
    """Create a new analytics record"""
    db = get_analytics_db()
    collection = db[ANALYTICS_COLLECTION_NAME]
    
    analytics_dict = analytics.model_dump(exclude={"id"})
    result = await collection.insert_one(analytics_dict)
    created_record = await collection.find_one({"_id": result.inserted_id})
    if created_record:
        created_record["_id"] = str(created_record["_id"])
    return created_record

async def get_analytics_records(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    method: Optional[str] = None,
    path: Optional[str] = None,
    status_code: Optional[int] = None
) -> List[dict]:
    """Get analytics records with filters"""
    db = get_analytics_db()
    collection = db[ANALYTICS_COLLECTION_NAME]
    
    # Build query
    query = {}
    if start_date:
        query["timestamp"] = {"$gte": start_date}
    if end_date:
        if "timestamp" in query:
            query["timestamp"]["$lte"] = end_date
        else:
            query["timestamp"] = {"$lte": end_date}
    if method:
        query["method"] = method
    if path:
        query["path"] = {"$regex": path, "$options": "i"}
    if status_code:
        query["status_code"] = status_code
    
    records = []
    cursor = collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    async for record in cursor:
        record["_id"] = str(record["_id"])
        records.append(record)
    
    return records

async def count_analytics_records(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    method: Optional[str] = None,
    path: Optional[str] = None,
    status_code: Optional[int] = None
) -> int:
    """Count analytics records with filters"""
    db = get_analytics_db()
    collection = db[ANALYTICS_COLLECTION_NAME]
    
    # Build query
    query = {}
    if start_date:
        query["timestamp"] = {"$gte": start_date}
    if end_date:
        if "timestamp" in query:
            query["timestamp"]["$lte"] = end_date
        else:
            query["timestamp"] = {"$lte": end_date}
    if method:
        query["method"] = method
    if path:
        query["path"] = {"$regex": path, "$options": "i"}
    if status_code:
        query["status_code"] = status_code
    
    return await collection.count_documents(query)

async def get_analytics_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    path: Optional[str] = None
) -> dict:
    """Get analytics summary with aggregations"""
    db = get_analytics_db()
    collection = db[ANALYTICS_COLLECTION_NAME]
    
    # Build match query
    match_query = {}
    if start_date or end_date:
        match_query["timestamp"] = {}
        if start_date:
            match_query["timestamp"]["$gte"] = start_date
        if end_date:
            match_query["timestamp"]["$lte"] = end_date
    if path:
        match_query["path"] = {"$regex": path, "$options": "i"}
    
    # Aggregation pipeline
    pipeline = [
        {"$match": match_query} if match_query else {"$match": {}},
        {
            "$group": {
                "_id": None,
                "total_requests": {"$sum": 1},
                "total_bandwidth": {"$sum": "$total_bandwidth"},
                "avg_response_time": {"$avg": "$response_time_ms"},
                "requests_by_method": {
                    "$push": "$method"
                },
                "requests_by_status": {
                    "$push": "$status_code"
                },
                "requests_by_endpoint": {
                    "$push": "$path"
                }
            }
        }
    ]
    
    result = await collection.aggregate(pipeline).to_list(length=1)
    
    if not result:
        return {
            "total_requests": 0,
            "total_bandwidth": 0,
            "average_response_time_ms": None,
            "requests_by_method": {},
            "requests_by_status": {},
            "requests_by_endpoint": {}
        }
    
    data = result[0]
    
    # Count occurrences
    method_counts = {}
    for method in data.get("requests_by_method", []):
        method_counts[method] = method_counts.get(method, 0) + 1
    
    status_counts = {}
    for status in data.get("requests_by_status", []):
        status_counts[status] = status_counts.get(status, 0) + 1
    
    endpoint_counts = {}
    for endpoint in data.get("requests_by_endpoint", []):
        endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
    
    return {
        "total_requests": data.get("total_requests", 0),
        "total_bandwidth": data.get("total_bandwidth", 0),
        "average_response_time_ms": data.get("avg_response_time"),
        "requests_by_method": method_counts,
        "requests_by_status": status_counts,
        "requests_by_endpoint": endpoint_counts
    }

async def get_bandwidth_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    path: Optional[str] = None
) -> dict:
    """Get bandwidth statistics"""
    db = get_analytics_db()
    collection = db[ANALYTICS_COLLECTION_NAME]
    
    match_query = {}
    if start_date or end_date:
        match_query["timestamp"] = {}
        if start_date:
            match_query["timestamp"]["$gte"] = start_date
        if end_date:
            match_query["timestamp"]["$lte"] = end_date
    if path:
        match_query["path"] = {"$regex": path, "$options": "i"}
    
    pipeline = [
        {"$match": match_query} if match_query else {"$match": {}},
        {
            "$group": {
                "_id": None,
                "total_request_size": {"$sum": "$request_size"},
                "total_response_size": {"$sum": "$response_size"},
                "total_bandwidth": {"$sum": "$total_bandwidth"},
                "avg_request_size": {"$avg": "$request_size"},
                "avg_response_size": {"$avg": "$response_size"},
                "max_request_size": {"$max": "$request_size"},
                "max_response_size": {"$max": "$response_size"}
            }
        }
    ]
    
    result = await collection.aggregate(pipeline).to_list(length=1)
    
    if not result:
        return {
            "total_request_size": 0,
            "total_response_size": 0,
            "total_bandwidth": 0,
            "avg_request_size": 0,
            "avg_response_size": 0,
            "max_request_size": 0,
            "max_response_size": 0
        }
    
    return result[0]


async def get_ip_request_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    path: Optional[str] = None
) -> List[dict]:
    """Get request statistics grouped by client IP, day, and path"""
    db = get_analytics_db()
    collection = db[ANALYTICS_COLLECTION_NAME]
    
    # Build match query
    match_query = {}
    if start_date or end_date:
        match_query["timestamp"] = {}
        if start_date:
            match_query["timestamp"]["$gte"] = start_date
        if end_date:
            match_query["timestamp"]["$lte"] = end_date
    if path:
        match_query["path"] = {"$regex": path, "$options": "i"}
    
    # Filter out records without client_ip
    match_query["client_ip"] = {"$exists": True, "$ne": None}
    
    # Aggregation pipeline
    # Extract date (day) from timestamp
    pipeline = [
        {"$match": match_query},
        {
            "$project": {
                "client_ip": 1,
                "path": 1,
                "date": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$timestamp"
                    }
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "client_ip": "$client_ip",
                    "date": "$date",
                    "path": "$path"
                },
                "request_count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "client_ip": "$_id.client_ip",
                "date": "$_id.date",
                "path": "$_id.path",
                "request_count": 1
            }
        },
        {
            "$sort": {
                "date": -1,
                "request_count": -1
            }
        }
    ]
    
    results = []
    cursor = collection.aggregate(pipeline)
    async for record in cursor:
        results.append(record)
    
    return results

async def delete_old_analytics(days: int = 90) -> int:
    """Delete analytics records older than specified days"""
    db = get_analytics_db()
    collection = db[ANALYTICS_COLLECTION_NAME]
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    result = await collection.delete_many({"timestamp": {"$lt": cutoff_date}})
    return result.deleted_count

