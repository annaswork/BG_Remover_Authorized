from typing import List, Optional
from datetime import datetime, timedelta
from database.database_funcs import get_analytics_db
from database.analytics_model import Analytics
from config.index import ANALYTICS_COLLECTION_NAME


async def create_analytics_record(analytics: Analytics) -> dict:
    db = get_analytics_db()
    collection = db[ANALYTICS_COLLECTION_NAME]
    analytics_dict = analytics.model_dump(exclude={"id"})
    result = await collection.insert_one(analytics_dict)
    created = await collection.find_one({"_id": result.inserted_id})
    if created:
        created["_id"] = str(created["_id"])
    return created


async def get_analytics_records(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    method: Optional[str] = None,
    path: Optional[str] = None,
    status_code: Optional[int] = None,
    app_name: Optional[str] = None,
) -> List[dict]:
    db = get_analytics_db()
    collection = db[ANALYTICS_COLLECTION_NAME]

    query = {}
    if start_date or end_date:
        query["timestamp"] = {}
        if start_date:
            query["timestamp"]["$gte"] = start_date
        if end_date:
            query["timestamp"]["$lte"] = end_date
    if method:
        query["method"] = method
    if path:
        query["path"] = {"$regex": path, "$options": "i"}
    if status_code:
        query["status_code"] = status_code
    if app_name:
        query["app_name"] = {"$regex": app_name, "$options": "i"}

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
    status_code: Optional[int] = None,
    app_name: Optional[str] = None,
) -> int:
    db = get_analytics_db()
    collection = db[ANALYTICS_COLLECTION_NAME]

    query = {}
    if start_date or end_date:
        query["timestamp"] = {}
        if start_date:
            query["timestamp"]["$gte"] = start_date
        if end_date:
            query["timestamp"]["$lte"] = end_date
    if method:
        query["method"] = method
    if path:
        query["path"] = {"$regex": path, "$options": "i"}
    if status_code:
        query["status_code"] = status_code
    if app_name:
        query["app_name"] = {"$regex": app_name, "$options": "i"}

    return await collection.count_documents(query)


async def get_analytics_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    path: Optional[str] = None,
    app_name: Optional[str] = None,
) -> dict:
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
    if app_name:
        match_query["app_name"] = {"$regex": app_name, "$options": "i"}

    pipeline = [
        {"$match": match_query if match_query else {}},
        {
            "$group": {
                "_id": None,
                "total_requests": {"$sum": 1},
                "total_bandwidth": {"$sum": "$total_bandwidth"},
                "avg_response_time": {"$avg": "$response_time_ms"},
                "requests_by_method": {"$push": "$method"},
                "requests_by_status": {"$push": "$status_code"},
                "requests_by_endpoint": {"$push": "$path"},
            }
        },
    ]

    result = await collection.aggregate(pipeline).to_list(length=1)
    if not result:
        return {
            "total_requests": 0,
            "total_bandwidth": 0,
            "average_response_time_ms": None,
            "requests_by_method": {},
            "requests_by_status": {},
            "requests_by_endpoint": {},
        }

    data = result[0]

    def count_list(lst):
        counts = {}
        for item in lst:
            counts[item] = counts.get(item, 0) + 1
        return counts

    return {
        "total_requests": data.get("total_requests", 0),
        "total_bandwidth": data.get("total_bandwidth", 0),
        "average_response_time_ms": data.get("avg_response_time"),
        "requests_by_method": count_list(data.get("requests_by_method", [])),
        "requests_by_status": count_list(data.get("requests_by_status", [])),
        "requests_by_endpoint": count_list(data.get("requests_by_endpoint", [])),
    }


async def get_bandwidth_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    path: Optional[str] = None,
    app_name: Optional[str] = None,
) -> dict:
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
    if app_name:
        match_query["app_name"] = {"$regex": app_name, "$options": "i"}

    pipeline = [
        {"$match": match_query if match_query else {}},
        {
            "$group": {
                "_id": None,
                "total_request_size": {"$sum": "$request_size"},
                "total_response_size": {"$sum": "$response_size"},
                "total_bandwidth": {"$sum": "$total_bandwidth"},
                "avg_request_size": {"$avg": "$request_size"},
                "avg_response_size": {"$avg": "$response_size"},
                "max_request_size": {"$max": "$request_size"},
                "max_response_size": {"$max": "$response_size"},
            }
        },
    ]

    result = await collection.aggregate(pipeline).to_list(length=1)
    if not result:
        return {k: 0 for k in [
            "total_request_size", "total_response_size", "total_bandwidth",
            "avg_request_size", "avg_response_size", "max_request_size", "max_response_size",
        ]}
    return result[0]


async def get_ip_request_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    path: Optional[str] = None,
    app_name: Optional[str] = None,
) -> List[dict]:
    db = get_analytics_db()
    collection = db[ANALYTICS_COLLECTION_NAME]

    match_query = {"client_ip": {"$exists": True, "$ne": None}}
    if start_date or end_date:
        match_query["timestamp"] = {}
        if start_date:
            match_query["timestamp"]["$gte"] = start_date
        if end_date:
            match_query["timestamp"]["$lte"] = end_date
    if path:
        match_query["path"] = {"$regex": path, "$options": "i"}
    if app_name:
        match_query["app_name"] = {"$regex": app_name, "$options": "i"}

    pipeline = [
        {"$match": match_query},
        {"$project": {
            "client_ip": 1, "path": 1,
            "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
        }},
        {"$group": {
            "_id": {"client_ip": "$client_ip", "date": "$date", "path": "$path"},
            "request_count": {"$sum": 1},
        }},
        {"$project": {
            "_id": 0,
            "client_ip": "$_id.client_ip",
            "date": "$_id.date",
            "path": "$_id.path",
            "request_count": 1,
        }},
        {"$sort": {"date": -1, "request_count": -1}},
    ]

    results = []
    async for record in collection.aggregate(pipeline):
        results.append(record)
    return results


async def delete_old_analytics(days: int = 90) -> int:
    db = get_analytics_db()
    collection = db[ANALYTICS_COLLECTION_NAME]
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await collection.delete_many({"timestamp": {"$lt": cutoff}})
    return result.deleted_count


async def get_distinct_app_names() -> List[str]:
    db = get_analytics_db()
    collection = db[ANALYTICS_COLLECTION_NAME]
    values = await collection.distinct("app_name", {"app_name": {"$ne": None}})
    return sorted([v for v in values if v])


async def get_distinct_status_codes() -> List[int]:
    db = get_analytics_db()
    collection = db[ANALYTICS_COLLECTION_NAME]
    values = await collection.distinct("status_code")
    return sorted([v for v in values if v])
