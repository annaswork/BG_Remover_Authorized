from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from database.analytics_model import AnalyticsSummary, PKT
import analytics.crud as analytics_db
from controller.auth_controller import require_admin_session

router = APIRouter(
    prefix="/api/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_admin_session)],
)


def _parse_query_datetime(value: str, *, end_of_day: bool = False) -> datetime:
    """Parse filter dates as PKT (UTC+5)."""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD or ISO format",
            )
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=PKT)
    else:
        dt = dt.astimezone(PKT)
    if end_of_day and "T" not in value and " " not in value:
        dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    return dt

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
            start_dt = _parse_query_datetime(start_date)
        if end_date:
            end_dt = _parse_query_datetime(end_date, end_of_day=True)
        
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
            end_dt = analytics_db._now_pkt()
            start_dt = end_dt - timedelta(days=days)
        else:
            if start_date:
                start_dt = _parse_query_datetime(start_date)
            if end_date:
                end_dt = _parse_query_datetime(end_date, end_of_day=True)
        
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
            end_dt = analytics_db._now_pkt()
            start_dt = end_dt - timedelta(days=days)
        else:
            if start_date:
                start_dt = _parse_query_datetime(start_date)
            if end_date:
                end_dt = _parse_query_datetime(end_date, end_of_day=True)
        
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
            end_dt = analytics_db._now_pkt()
            start_dt = end_dt - timedelta(days=days)
        else:
            if start_date:
                start_dt = _parse_query_datetime(start_date)
            if end_date:
                end_dt = _parse_query_datetime(end_date, end_of_day=True)
        
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


@router.delete("/delete-by-filter", response_model=dict)
async def delete_analytics_by_filter(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    path: Optional[str] = Query(None, description="Filter by path (partial match)"),
    status_code: Optional[int] = Query(None, description="Filter by status code"),
    app_name: Optional[str] = Query(None, description="Filter by app name (partial match)"),
):
    """
    Delete analytics records matching the given filters.
    At least one filter parameter must be provided.
    This allows deleting recent records (e.g., bot traffic, test requests).
    """
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = _parse_query_datetime(start_date)
        if end_date:
            end_dt = _parse_query_datetime(end_date, end_of_day=True)
        
        deleted_count = await analytics_db.delete_analytics_by_filter(
            start_date=start_dt,
            end_date=end_dt,
            method=method,
            path=path,
            status_code=status_code,
            app_name=app_name,
        )
        
        return {
            "message": f"Deleted {deleted_count} analytics records matching the filters",
            "deleted_count": deleted_count
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting analytics: {str(e)}")


@router.delete("/delete-all", response_model=dict)
async def delete_all_analytics(
    confirm: str = Query(..., description="Type 'DELETE_ALL' to confirm deletion of all analytics records")
):
    """
    Delete ALL analytics records. Use with extreme caution!
    Requires confirmation parameter to prevent accidental deletion.
    """
    try:
        if confirm != "DELETE_ALL":
            raise HTTPException(
                status_code=400,
                detail="Confirmation failed. Set confirm='DELETE_ALL' to proceed with deletion of all records."
            )
        
        deleted_count = await analytics_db.delete_all_analytics()
        return {
            "message": f"Deleted all {deleted_count} analytics records",
            "deleted_count": deleted_count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting all analytics: {str(e)}")

