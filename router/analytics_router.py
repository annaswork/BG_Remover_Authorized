from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from database.analytics_model import AnalyticsSummary
import analytics.crud as analytics_db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/filters-meta", response_model=dict)
async def get_filters_meta():
    """Return distinct app names and status codes for filter dropdowns."""
    try:
        app_names = await analytics_db.get_distinct_app_names()
        status_codes = await analytics_db.get_distinct_status_codes()
        return {"app_names": app_names, "status_codes": status_codes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=dict)
async def get_analytics(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    path: Optional[str] = Query(None, description="Filter by path (partial match)"),
    status_code: Optional[int] = Query(None, description="Filter by status code"),
    app_name: Optional[str] = Query(None, description="Filter by app name (partial match)"),
):
    """Get analytics records with optional filters"""
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD or ISO format")
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    # Set to end of day
                    end_dt = end_dt.replace(hour=23, minute=59, second=59)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD or ISO format")
        
        records = await analytics_db.get_analytics_records(
            skip=skip,
            limit=limit,
            start_date=start_dt,
            end_date=end_dt,
            method=method,
            path=path,
            status_code=status_code,
            app_name=app_name,
        )
        
        total = await analytics_db.count_analytics_records(
            start_date=start_dt,
            end_date=end_dt,
            method=method,
            path=path,
            status_code=status_code,
            app_name=app_name,
        )
        
        return {
            "message": "Analytics records retrieved successfully",
            "data": records,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics: {str(e)}")

@router.get("/summary", response_model=dict)
async def get_analytics_summary(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    days: Optional[int] = Query(None, description="Number of days to look back (alternative to start_date/end_date)"),
    path: Optional[str] = Query(None, description="Filter by endpoint path (partial match)"),
    app_name: Optional[str] = Query(None, description="Filter by app name (partial match)"),
):
    """Get analytics summary with aggregations"""
    try:
        start_dt = None
        end_dt = None
        
        if days:
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(days=days)
        else:
            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid start_date format")
            
            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                        end_dt = end_dt.replace(hour=23, minute=59, second=59)
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid end_date format")
        
        summary = await analytics_db.get_analytics_summary(
            start_date=start_dt,
            end_date=end_dt,
            path=path,
            app_name=app_name,
        )
        
        return {
            "message": "Analytics summary retrieved successfully",
            "data": summary
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics summary: {str(e)}")

@router.get("/bandwidth", response_model=dict)
async def get_bandwidth_stats(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    days: Optional[int] = Query(None, description="Number of days to look back"),
    path: Optional[str] = Query(None, description="Filter by endpoint path (partial match)"),
    app_name: Optional[str] = Query(None, description="Filter by app name (partial match)"),
):
    """Get bandwidth statistics"""
    try:
        start_dt = None
        end_dt = None
        
        if days:
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(days=days)
        else:
            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid start_date format")
            
            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                        end_dt = end_dt.replace(hour=23, minute=59, second=59)
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid end_date format")
        
        stats = await analytics_db.get_bandwidth_stats(
            start_date=start_dt,
            end_date=end_dt,
            path=path,
            app_name=app_name,
        )
        
        # Format bytes to human-readable format
        def format_bytes(bytes_val):
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_val < 1024.0:
                    return f"{bytes_val:.2f} {unit}"
                bytes_val /= 1024.0
            return f"{bytes_val:.2f} PB"
        
        formatted_stats = {
            **stats,
            "total_request_size_formatted": format_bytes(stats.get("total_request_size", 0)),
            "total_response_size_formatted": format_bytes(stats.get("total_response_size", 0)),
            "total_bandwidth_formatted": format_bytes(stats.get("total_bandwidth", 0)),
            "avg_request_size_formatted": format_bytes(stats.get("avg_request_size", 0)),
            "avg_response_size_formatted": format_bytes(stats.get("avg_response_size", 0)),
            "max_request_size_formatted": format_bytes(stats.get("max_request_size", 0)),
            "max_response_size_formatted": format_bytes(stats.get("max_response_size", 0))
        }
        
        return {
            "message": "Bandwidth statistics retrieved successfully",
            "data": formatted_stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving bandwidth stats: {str(e)}")

@router.get("/ip-stats", response_model=dict)
async def get_ip_request_stats(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    days: Optional[int] = Query(None, description="Number of days to look back (alternative to start_date/end_date)"),
    path: Optional[str] = Query(None, description="Filter by endpoint path (partial match)"),
    app_name: Optional[str] = Query(None, description="Filter by app name (partial match)"),
):
    """Get request statistics grouped by client IP, day, and path"""
    try:
        start_dt = None
        end_dt = None
        
        if days:
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(days=days)
        else:
            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD or ISO format")
            
            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                        end_dt = end_dt.replace(hour=23, minute=59, second=59)
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD or ISO format")
        
        stats = await analytics_db.get_ip_request_stats(
            start_date=start_dt,
            end_date=end_dt,
            path=path,
            app_name=app_name,
        )
        
        # Group results by IP for easier consumption
        ip_summary = {}
        for record in stats:
            ip = record["client_ip"]
            if ip not in ip_summary:
                ip_summary[ip] = {
                    "client_ip": ip,
                    "total_requests": 0,
                    "by_day_and_path": []
                }
            ip_summary[ip]["total_requests"] += record["request_count"]
            ip_summary[ip]["by_day_and_path"].append({
                "date": record["date"],
                "path": record["path"],
                "request_count": record["request_count"]
            })
        
        # Convert to list and sort by total requests
        ip_summary_list = list(ip_summary.values())
        ip_summary_list.sort(key=lambda x: x["total_requests"], reverse=True)
        
        return {
            "message": "IP request statistics retrieved successfully",
            "data": {
                "total_unique_ips": len(ip_summary_list),
                "ip_statistics": ip_summary_list,
                "raw_data": stats  # Include raw data for detailed analysis
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving IP request stats: {str(e)}")

@router.delete("/cleanup", response_model=dict)
async def cleanup_old_analytics(
    days: int = Query(90, ge=1, description="Delete records older than this many days")
):
    """Delete old analytics records"""
    try:
        deleted_count = await analytics_db.delete_old_analytics(days=days)
        return {
            "message": f"Deleted {deleted_count} old analytics records",
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up analytics: {str(e)}")

