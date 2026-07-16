import asyncio
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .api.routes import router as api_router
from .config import settings
from .db import engine
from .ws import router as ws_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Category Clash API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    """Cheap liveness probe used to wake a sleeping Render Free service."""

    return {"status": "ok"}


async def database_is_ready() -> bool:
    try:
        async with asyncio.timeout(settings.readiness_timeout_seconds):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        logging.getLogger(__name__).warning("Database readiness check failed", exc_info=True)
        return False


@app.get("/ready", include_in_schema=False)
async def ready() -> dict[str, str]:
    """Readiness probe: the process is useful only when PostgreSQL responds."""

    if not await database_is_ready():
        raise HTTPException(status_code=503, detail="Database is not ready")
    return {"status": "ready"}


app.include_router(api_router)
app.include_router(ws_router)
