import asyncio
import json
import time
from typing import Optional

import analytics.crud as analytics_db
import authorization.index as auth_db
from analytics.excluded_paths import EXCLUDE_PATHS
from database.analytics_model import Analytics
from starlette.types import ASGIApp, Message, Receive, Scope, Send


def _headers_scope(scope: Scope) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in scope.get("headers", []):
        try:
            out[k.decode("latin1").lower()] = v.decode("latin1")
        except Exception:
            continue
    return out


class AnalyticsMiddleware:
    """
    ASGI middleware — tracks API requests without BaseHTTPMiddleware so
    StreamingResponse and disconnect listeners work correctly.
    """

    def __init__(self, app: ASGIApp, exclude_paths: Optional[list] = None):
        self.app = app
        self.exclude_paths = exclude_paths or EXCLUDE_PATHS

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path == "/" or any(
            path.startswith(p) for p in self.exclude_paths if p != "/"
        ):
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        hdrs = _headers_scope(scope)

        client_ip = scope.get("client", (None,))[0]
        xff = hdrs.get("x-forwarded-for")
        if xff:
            client_ip = xff.split(",")[0].strip()
        user_agent = hdrs.get("user-agent")

        app_name = None
        api_key = hdrs.get("x-api-key")
        if api_key:
            key_doc = await auth_db.validate_api_key(api_key)
            if key_doc:
                app_name = key_doc.get("app_name")

        cl_raw = hdrs.get("content-length")
        has_request_cl = False
        request_size = 0
        if cl_raw:
            try:
                request_size = int(cl_raw)
                has_request_cl = True
            except ValueError:
                pass

        async def receive_counting() -> Message:
            nonlocal request_size
            msg = await receive()
            if not has_request_cl and msg["type"] == "http.request":
                request_size += len(msg.get("body") or b"")
            return msg

        recv: Receive = receive_counting if not has_request_cl else receive

        status_code: Optional[int] = None
        response_cl: Optional[int] = None
        response_size = 0
        error_body = bytearray()
        max_error_capture = 65536

        async def send_capture(message: Message) -> None:
            nonlocal status_code, response_cl, response_size
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_cl = None
                for hk, hv in message.get("headers", []):
                    try:
                        if hk.decode("latin1").lower() == "content-length":
                            response_cl = int(hv.decode("latin1"))
                            break
                    except Exception:
                        pass
            elif message["type"] == "http.response.body":
                chunk = message.get("body") or b""
                if response_cl is None:
                    response_size += len(chunk)
                if status_code is not None and status_code >= 400:
                    if len(error_body) < max_error_capture:
                        take = max_error_capture - len(error_body)
                        error_body.extend(chunk[:take])
            await send(message)

        await self.app(scope, recv, send_capture)

        if response_cl is not None:
            response_size = response_cl

        response_time = (time.time() - start_time) * 1000
        total_bandwidth = request_size + response_size

        error_reason = None
        if status_code is not None and status_code >= 400 and error_body:
            try:
                body_text = error_body.decode("utf-8", errors="replace")
                parsed = json.loads(body_text)
                if isinstance(parsed, dict):
                    error_reason = (
                        parsed.get("detail")
                        or parsed.get("message")
                        or body_text
                    )
                else:
                    error_reason = body_text
            except Exception:
                error_reason = error_body.decode("utf-8", errors="replace")

        analytics_record = Analytics(
            method=scope.get("method", ""),
            path=path,
            status_code=status_code or 0,
            request_size=request_size,
            response_size=response_size,
            total_bandwidth=total_bandwidth,
            client_ip=client_ip,
            user_agent=user_agent,
            response_time_ms=round(response_time, 2),
            app_name=app_name,
            error_reason=error_reason,
        )
        asyncio.create_task(analytics_db.create_analytics_record(analytics_record))
