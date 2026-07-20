from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import (
    SupabaseIdentity,
    TokenUser,
    create_access_token,
    get_current_user,
    get_supabase_identity,
    verify_password,
)
from ..config import settings
from ..db import get_session
from ..game.manager import room_manager
from ..leveling import rank_for_level, xp_progress
from ..models import User

router = APIRouter(prefix="/api")


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    coins: int
    wins: int
    losses: int
    xp: int
    level: int
    xp_into_level: int
    xp_for_next_level: int
    rank: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class DemoSession(BaseModel):
    token: str
    user: UserOut


class ProfileRequest(BaseModel):
    username: str = Field(min_length=3, max_length=24, pattern=r"^[A-Za-z0-9_]+$")
    display_name: str = Field(min_length=2, max_length=64)


def user_out(user: User) -> UserOut:
    xp = getattr(user, "xp", 0)
    level, xp_into_level, xp_for_next_level = xp_progress(xp)
    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        coins=user.coins,
        wins=user.wins,
        losses=user.losses,
        xp=xp,
        level=level,
        xp_into_level=xp_into_level,
        xp_for_next_level=xp_for_next_level,
        rank=rank_for_level(level),
    )


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/users/demo", response_model=list[DemoSession])
async def demo_users(session: AsyncSession = Depends(get_session)):
    """Preload signed sessions for the public Phase 1 demo accounts.

    The demo password is already shipped in the browser bundle, so making the
    equivalent short-lived sessions available with the picker grants no new
    privilege. It does make selecting a player instant instead of running an
    expensive bcrypt check on a Render Free CPU for every click.
    """
    if settings.auth_mode != "demo":
        raise HTTPException(status_code=404, detail="Demo accounts are disabled")
    users = (await session.execute(select(User).order_by(User.id).limit(2))).scalars().all()
    return [
        DemoSession(
            token=create_access_token(user.id, user.username, user.display_name),
            user=user_out(user),
        )
        for user in users
    ]


@router.post("/auth/demo-login", response_model=LoginResponse)
async def demo_login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    if settings.auth_mode != "demo":
        raise HTTPException(status_code=404, detail="Demo accounts are disabled")
    user = (
        await session.execute(select(User).where(User.username == body.username))
    ).scalar_one_or_none()
    if (
        user is None
        or user.password_hash is None
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Bad username or password")
    return LoginResponse(
        token=create_access_token(user.id, user.username, user.display_name),
        user=user_out(user),
    )


@router.post("/profile", response_model=UserOut)
async def create_profile(
    body: ProfileRequest,
    identity: SupabaseIdentity = Depends(get_supabase_identity),
    session: AsyncSession = Depends(get_session),
):
    existing = (
        await session.execute(select(User).where(User.auth_user_id == identity.auth_user_id))
    ).scalar_one_or_none()
    if existing is not None:
        return user_out(existing)

    display_name = body.display_name.strip()
    if len(display_name) < 2:
        raise HTTPException(status_code=422, detail="Display name is too short")
    profile = User(
        auth_user_id=identity.auth_user_id,
        username=body.username.lower(),
        display_name=display_name,
        password_hash=None,
        coins=100,
    )
    session.add(profile)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Username is already taken") from exc
    await session.refresh(profile)
    return user_out(profile)


@router.get("/profile", response_model=UserOut)
async def supabase_profile(
    identity: SupabaseIdentity = Depends(get_supabase_identity),
    session: AsyncSession = Depends(get_session),
):
    profile = (
        await session.execute(select(User).where(User.auth_user_id == identity.auth_user_id))
    ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile required")
    return user_out(profile)


@router.get("/me", response_model=UserOut)
async def current_profile(
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return user_out(user)


@router.post("/rooms")
async def create_room(current: TokenUser = Depends(get_current_user)):
    room = room_manager.create_room()
    return {"code": room.code}


@router.get("/rooms/{code}")
async def get_room(code: str, current: TokenUser = Depends(get_current_user)):
    room = room_manager.get(code)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return {
        "code": room.code,
        "phase": room.phase.value,
        "players": [p.display_name for p in room.players.values()],
        "joinable": len(room.players) < 2 or current.id in room.players,
    }
