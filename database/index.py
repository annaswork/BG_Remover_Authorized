from fastapi import FastAPI
from contextlib import asynccontextmanager
from database.database_config import connect_to_mongo, close_mongo_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events for database and optional services.
    """
    # ── Startup ───────────────────────────────────────────────────────────────
    print("[Lifespan] Starting up...")
    
    # Connect to MongoDB
    await connect_to_mongo()
    
    # Initialize PlantProfiler if available
    from inits.models_init import plant_profiler
    if plant_profiler:
        try:
            await plant_profiler.startup()
            print("[Lifespan] PlantProfiler started successfully")
        except Exception as e:
            print(f"[Lifespan] Warning: PlantProfiler startup failed: {e}")
    
    print("[Lifespan] Startup complete")
    
    yield
    
    # ── Shutdown ──────────────────────────────────────────────────────────────
    print("[Lifespan] Shutting down...")
    
    # Shutdown PlantProfiler if available
    if plant_profiler:
        try:
            await plant_profiler.shutdown()
            print("[Lifespan] PlantProfiler shutdown successfully")
        except Exception as e:
            print(f"[Lifespan] Warning: PlantProfiler shutdown failed: {e}")
    
    # Close MongoDB connection
    await close_mongo_connection()
    
    print("[Lifespan] Shutdown complete")

