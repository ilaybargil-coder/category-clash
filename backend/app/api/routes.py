from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import TokenUser, create_access_token, get_current_user, verify_password
from ..db import get_session
from ..game.manager import room_manager
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


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class DemoSession(BaseModel):
    token: str
    user: UserOut


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
    users = (await session.execute(select(User).order_by(User.id).limit(2))).scalars().all()
    return [
        DemoSession(
            token=create_access_token(user.id, user.username, user.display_name),
            user=UserOut(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                coins=user.coins,
                wins=user.wins,
                losses=user.losses,
            ),
        )
        for user in users
    ]


@router.post("/auth/demo-login", response_model=LoginResponse)
async def demo_login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    user = (
        await session.execute(select(User).where(User.username == body.username))
    ).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Bad username or password")
    return LoginResponse(
        token=create_access_token(user.id, user.username, user.display_name),
        user=UserOut(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            coins=user.coins,
            wins=user.wins,
            losses=user.losses,
        ),
    )


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
