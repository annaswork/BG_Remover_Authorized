from inits.server_init import app
from database.index import lifespan
from analytics.middleware import AnalyticsMiddleware
from analytics.excluded_paths import EXCLUDE_PATHS
from router.app_router import router as bg_router, page_router
from router.face_app_router import router as face_router
from router.analytics_router import router as analytics_router
from router.auth_router import router as auth_router
from router.plant_id_router import router as plant_router
from router.urdu_ai_router import router as urdu_ai_router


# ── Lifespan: DB connect / disconnect ────────────────────────────────────────
app.router.lifespan_context = lifespan

# ── Analytics middleware (records every non-excluded request) ─────────────────
app.add_middleware(AnalyticsMiddleware, exclude_paths=EXCLUDE_PATHS)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(page_router)         # / (UI)
app.include_router(bg_router)           # /api/bg-remover
app.include_router(face_router)         # /api/bg-remover/face-crop
app.include_router(analytics_router)    # /api/analytics
app.include_router(auth_router)         # /api/auth
app.include_router(plant_router)        # /api/plant-id
app.include_router(urdu_ai_router)    # /api/urdu-shayari
