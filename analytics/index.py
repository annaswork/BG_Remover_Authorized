from fastapi import FastAPI
from contextlib import asynccontextmanager
from analytics.routes import router as analytics_router
from database.database_funcs import connect_to_mongo, close_mongo_connection
from analytics.middleware import AnalyticsMiddleware
from analytics.excluded_paths import EXCLUDE_PATHS


@asynccontextmanager
async def lifespan(app: FastAPI):
    #Startup
    await connect_to_mongo()
    yield

    #Shutdown
    await close_mongo_connection()

