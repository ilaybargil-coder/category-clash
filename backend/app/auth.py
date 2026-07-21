from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import monotonic, time
from typing import Any
from uuid import UUID

import bcrypt
import httpx
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_session
from .models import User


@dataclass
class TokenUser:
    id: int
    username: str
    display_name: str
    avatar: str | None = None


@dataclass(frozen=True)
class SupabaseIdentity:
    auth_user_id: str
    email: str | None
    metadata: dict[str, Any]


_identity_cache: dict[str, tuple[float, SupabaseIdentity]] = {}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_access_token(
    user_id: int,
    username: str,
    display_name: str,
    avatar: str | None = None,
) -> str:
    """Create a legacy demo token for local development and automated tests."""
    payload = {
        "sub": str(user_id),
        "username": username,
        "display_name": display_name,
        "avatar": avatar,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenUser | None:
    """Decode a legacy demo token. Production uses Supabase access tokens."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenUser(
            id=int(payload["sub"]),
            username=payload["username"],
            display_name=payload["display_name"],
            avatar=payload.get("avatar"),
        )
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


async def verify_supabase_identity(token: str) -> SupabaseIdentity | None:
    """Validate a Supabase access token with the project's Auth server.

    This supports legacy HS256 projects and asymmetric signing keys alike.
    Successful validations are cached briefly so a REST request followed by a
    WebSocket connection does not add repeated regional network round-trips.
    """

    if not settings.supabase_url or not settings.supabase_publishable_key:
        return None

    now = monotonic()
    cached = _identity_cache.get(token)
    if cached and cached[0] > now:
        return cached[1]
    if cached:
        _identity_cache.pop(token, None)

    try:
        async with httpx.AsyncClient(timeout=settings.supabase_auth_timeout_seconds) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "apikey": settings.supabase_publishable_key,
                    "Authorization": f"Bearer {token}",
                },
            )
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None

    payload = response.json()
    try:
        auth_user_id = str(UUID(payload["id"]))
    except (KeyError, TypeError, ValueError):
        return None
    metadata = payload.get("user_metadata")
    identity = SupabaseIdentity(
        auth_user_id=auth_user_id,
        email=payload.get("email") if isinstance(payload.get("email"), str) else None,
        metadata=metadata if isinstance(metadata, dict) else {},
    )

    if len(_identity_cache) >= 1024:
        _identity_cache.clear()
    cache_seconds = max(0, settings.auth_identity_cache_seconds)
    try:
        unverified = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False},
        )
        if isinstance(unverified.get("exp"), (int, float)):
            cache_seconds = min(cache_seconds, max(0, int(unverified["exp"] - time())))
    except jwt.PyJWTError:
        cache_seconds = 0
    _identity_cache[token] = (now + cache_seconds, identity)
    return identity


async def resolve_profile(identity: SupabaseIdentity, session: AsyncSession) -> TokenUser | None:
    user = (
        await session.execute(select(User).where(User.auth_user_id == identity.auth_user_id))
    ).scalar_one_or_none()
    if user is None:
        return None
    return TokenUser(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar=user.avatar,
    )


async def authenticate_token(token: str, session: AsyncSession) -> TokenUser | None:
    if settings.auth_mode == "demo":
        return decode_token(token)
    identity = await verify_supabase_identity(token)
    if identity is None:
        return None
    return await resolve_profile(identity, session)


_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> TokenUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing credentials")
    user = await authenticate_token(credentials.credentials, session)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token or missing profile")
    return user


async def get_supabase_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> SupabaseIdentity:
    if settings.auth_mode != "supabase":
        raise HTTPException(status_code=404, detail="Supabase Auth is not enabled")
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing credentials")
    identity = await verify_supabase_identity(credentials.credentials)
    if identity is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return identity
