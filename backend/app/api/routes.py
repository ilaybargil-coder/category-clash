from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import (
    SupabaseIdentity,
    TokenUser,
    create_access_token,
    decode_token,
    get_current_user,
    get_supabase_identity,
    verify_password,
    verify_supabase_identity,
)
from ..config import settings
from ..db import get_session
from ..game.manager import room_manager
from ..leveling import rank_for_level, xp_progress
from ..models import User

router = APIRouter(prefix="/api")
_profile_bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    avatar: str | None
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
    username: str | None = Field(
        default=None, min_length=3, max_length=24, pattern=r"^[A-Za-z0-9_]+$"
    )
    display_name: str | None = Field(default=None, min_length=2, max_length=64)
    avatar: str | None = Field(default=None, pattern=r"^avatar-(0[1-9]|[12]\d|3\d|40)$")


class CreateRoomRequest(BaseModel):
    practice: bool = False


def user_out(user: User) -> UserOut:
    xp = getattr(user, "xp", 0)
    level, xp_into_level, xp_for_next_level = xp_progress(xp)
    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar=getattr(user, "avatar", None),
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
            token=create_access_token(
                user.id,
                user.username,
                user.display_name,
                getattr(user, "avatar", None),
            ),
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
        token=create_access_token(user.id, user.username, user.display_name, user.avatar),
        user=user_out(user),
    )


@router.post("/profile", response_model=UserOut)
async def create_profile(
    body: ProfileRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(_profile_bearer),
    session: AsyncSession = Depends(get_session),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing credentials")

    identity = None
    if settings.auth_mode == "demo":
        current = decode_token(credentials.credentials)
        if current is None:
            raise HTTPException(status_code=401, detail="Invalid token or missing profile")
        existing = await session.get(User, current.id)
    else:
        identity = await verify_supabase_identity(credentials.credentials)
        if identity is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        existing = (
            await session.execute(select(User).where(User.auth_user_id == identity.auth_user_id))
        ).scalar_one_or_none()
    if existing is not None:
        if body.display_name is not None:
            display_name = body.display_name.strip()
            if len(display_name) < 2:
                raise HTTPException(status_code=422, detail="Display name is too short")
            existing.display_name = display_name
        if "avatar" in body.model_fields_set:
            existing.avatar = body.avatar
        await session.commit()
        await session.refresh(existing)
        return user_out(existing)

    if body.username is None or body.display_name is None:
        raise HTTPException(status_code=422, detail="Username and display name are required")
    if identity is None:
        raise HTTPException(status_code=404, detail="Profile required")
    display_name = body.display_name.strip()
    if len(display_name) < 2:
        raise HTTPException(status_code=422, detail="Display name is too short")
    profile = User(
        auth_user_id=identity.auth_user_id,
        username=body.username.lower(),
        display_name=display_name,
        avatar=body.avatar,
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


@router.delete("/account")
async def delete_account(
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    params = {"user_id": current.id}
    statements = (
        "DELETE FROM answer_reports WHERE reporter_user_id = :user_id",
        "DELETE FROM daily_results WHERE user_id = :user_id",
        """
        DELETE FROM friend_requests
        WHERE sender_id = :user_id OR recipient_id = :user_id
        """,
        """
        DELETE FROM friendships
        WHERE user_a_id = :user_id OR user_b_id = :user_id
        """,
        """
        DELETE FROM submitted_answers
        WHERE user_id = :user_id
           OR round_id IN (
                SELECT rounds.id
                FROM rounds
                WHERE rounds.starter_user_id = :user_id
                   OR rounds.winner_user_id = :user_id
                   OR rounds.match_id IN (
                        SELECT matches.id
                        FROM matches
                        WHERE matches.player1_id = :user_id
                           OR matches.player2_id = :user_id
                           OR matches.winner_id = :user_id
                   )
           )
        """,
        """
        DELETE FROM rounds
        WHERE starter_user_id = :user_id
           OR winner_user_id = :user_id
           OR match_id IN (
                SELECT matches.id
                FROM matches
                WHERE matches.player1_id = :user_id
                   OR matches.player2_id = :user_id
                   OR matches.winner_id = :user_id
           )
        """,
        """
        DELETE FROM matches
        WHERE player1_id = :user_id
           OR player2_id = :user_id
           OR winner_id = :user_id
        """,
    )
    for statement in statements:
        await session.execute(text(statement), params)

    # Some deployments may have extra user-owned tables (for example,
    # served_questions) that are not part of this checkout's ORM models. Remove
    # rows from every remaining direct users.id FK before deleting the profile.
    foreign_keys = (
        await session.execute(
            text(
                """
                SELECT DISTINCT tc.table_schema, tc.table_name, kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_catalog = kcu.constraint_catalog
                 AND tc.constraint_schema = kcu.constraint_schema
                 AND tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON tc.constraint_catalog = ccu.constraint_catalog
                 AND tc.constraint_schema = ccu.constraint_schema
                 AND tc.constraint_name = ccu.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND ccu.table_schema = current_schema()
                  AND ccu.table_name = 'users'
                  AND ccu.column_name = 'id'
                """
            )
        )
    ).all()

    def quoted(identifier: str) -> str:
        return f'"{identifier.replace(chr(34), chr(34) * 2)}"'

    for table_schema, table_name, column_name in foreign_keys:
        await session.execute(
            text(
                f"DELETE FROM {quoted(table_schema)}.{quoted(table_name)} "
                f"WHERE {quoted(column_name)} = :user_id"
            ),
            params,
        )

    await session.execute(text("DELETE FROM users WHERE id = :user_id"), params)
    await session.commit()
    return {"deleted": True}


@router.post("/rooms")
async def create_room(
    payload: CreateRoomRequest | None = None,
    current: TokenUser = Depends(get_current_user),
):
    practice = payload.practice if payload is not None else False
    room = room_manager.create_room(practice=practice, creator_user_id=current.id)
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
