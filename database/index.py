from fastapi import FastAPI
from contextlib import asynccontextmanager
from database.database_config import connect_to_mongo, close_mongo_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    #Startup
    await connect_to_mongo()
    yield

    #Shutdown
    await close_mongo_connection()

