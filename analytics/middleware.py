from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
from typing import Callable
from database.analytics_model import Analytics
import analytics.crud as analytics_db
import asyncio
from analytics.excluded_paths import EXCLUDE_PATHS
import authorization.index as auth_db

class AnalyticsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API requests and bandwidth usage.
    Records request count, request/response sizes, and response times.
    """
    
    def __init__(self, app: ASGIApp, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or EXCLUDE_PATHS
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip analytics for excluded paths — exact match for "/" prefix match for others
        path = request.url.path
        if path == "/" or any(path.startswith(p) for p in self.exclude_paths if p != "/"):
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Get client IP
        client_ip = request.client.host if request.client else None
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        
        # Get user agent
        user_agent = request.headers.get("user-agent")

        # Resolve app_name from API key header
        app_name = None
        api_key = request.headers.get("x-api-key")
        if api_key:
            key_doc = await auth_db.validate_api_key(api_key)
            if key_doc:
                app_name = key_doc.get("app_name")
        
        # Calculate request size
        request_size = 0
        if "content-length" in request.headers:
            try:
                request_size = int(request.headers["content-length"])
            except ValueError:
                pass
        else:
            body_bytes = await request.body()
            request_size = len(body_bytes)
            
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000
        
        # Calculate response size
        response_size = 0
        if "content-length" in response.headers:
            try:
                response_size = int(response.headers["content-length"])
            except ValueError:
                pass
        
        if response_size == 0:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            response_size = len(response_body)
            
            from starlette.responses import Response as StarletteResponse
            response = StarletteResponse(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        
        total_bandwidth = request_size + response_size
        
        analytics_record = Analytics(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            request_size=request_size,
            response_size=response_size,
            total_bandwidth=total_bandwidth,
            client_ip=client_ip,
            user_agent=user_agent,
            response_time_ms=round(response_time, 2),
            app_name=app_name
        )
        
        asyncio.create_task(analytics_db.create_analytics_record(analytics_record))
        
        return response

