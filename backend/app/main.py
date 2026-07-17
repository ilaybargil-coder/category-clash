import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .api.friends import router as friends_router
from .api.invites import router as invites_router
from .api.presence import router as presence_router
from .api.routes import router as api_router
from .api.solo import router as solo_router
from .config import settings
from .db import engine
from .redis import close_redis
from .ws import router as ws_router

logging.basicConfig(level=logging.INFO)

API_VERSION = "0.3.0"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await close_redis()


app = FastAPI(title="Category Clash API", version=API_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    """Cheap liveness probe used to wake a sleeping Render Free service."""

    return {"status": "ok", "version": API_VERSION}


async def database_is_ready() -> bool:
    try:
        async with asyncio.timeout(settings.readiness_timeout_seconds):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        logging.getLogger(__name__).warning("Database readiness check failed", exc_info=True)
        return False


def auth_is_ready() -> bool:
    if settings.auth_mode == "demo":
        return True
    return bool(settings.supabase_url and settings.supabase_publishable_key)


@app.get("/ready", include_in_schema=False)
async def ready() -> dict[str, str]:
    """Readiness probe: PostgreSQL and the selected auth mode are configured."""

    if not await database_is_ready():
        raise HTTPException(status_code=503, detail="Database is not ready")
    if not auth_is_ready():
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    return {"status": "ready"}


app.include_router(api_router)
app.include_router(friends_router)
app.include_router(presence_router)
app.include_router(invites_router)
app.include_router(solo_router)
app.include_router(ws_router)
