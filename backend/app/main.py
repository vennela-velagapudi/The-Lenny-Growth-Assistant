from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.database import create_db_and_tables
import structlog

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database")
    create_db_and_tables()
    yield
    logger.info("Shutting down")

app = FastAPI(title="Lenny Growth Assistant", lifespan=lifespan)

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok"}
