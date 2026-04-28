from inits.server_init import app
from database.database_funcs import connect_to_mongo, close_mongo_connection
from analytics.middleware import AnalyticsMiddleware
from analytics.excluded_paths import EXCLUDE_PATHS
from router.app_router import router as bg_router, page_router
from router.analytics_router import router as analytics_router
from router.auth_router import router as auth_router


# ── Lifespan: DB connect / disconnect ────────────────────────────────────────
from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app.router.lifespan_context = lifespan

# ── Analytics middleware (records every non-excluded request) ─────────────────
app.add_middleware(AnalyticsMiddleware, exclude_paths=EXCLUDE_PATHS)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(page_router)         # / (UI)
app.include_router(bg_router)           # /api/bg-remover
app.include_router(analytics_router)    # /api/analytics
app.include_router(auth_router)         # /api/auth
