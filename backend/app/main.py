from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.database import create_db_and_tables
from app.api import sessions
import structlog

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database")
    create_db_and_tables()
    yield
    logger.info("Shutting down")

app = FastAPI(title="Lenny Growth Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok"}

@app.get("/api/config")
async def get_config():
    from app.core.config import settings
    return {
        "provider": settings.LLM_PROVIDER,
        "model": settings.OLLAMA_MODEL if settings.LLM_PROVIDER.lower() == "ollama" else settings.ANTHROPIC_MODEL,
        "mode": "local" if settings.LLM_PROVIDER.lower() == "ollama" else "cloud"
    }
