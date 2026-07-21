"""Global XP leaderboard endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import TokenUser, get_current_user
from ..db import get_session
from ..leveling import level_for_xp
from ..models import User

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])
_LEADERBOARD_LIMIT = 20


class XpLeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    display_name: str
    username: str
    avatar: str | None
    level: int
    xp: int


class CurrentXpStanding(BaseModel):
    rank: int
    level: int
    xp: int


class XpLeaderboardOut(BaseModel):
    entries: list[XpLeaderboardEntry]
    you: CurrentXpStanding


@router.get("/xp", response_model=XpLeaderboardOut)
async def xp_leaderboard(
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> XpLeaderboardOut:
    current_user = await session.get(User, current.id)
    if current_user is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    users = (
        (
            await session.execute(
                select(User).order_by(User.xp.desc(), User.id.asc()).limit(_LEADERBOARD_LIMIT)
            )
        )
        .scalars()
        .all()
    )
    users_ahead = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(
            or_(
                User.xp > current_user.xp,
                (User.xp == current_user.xp) & (User.id < current_user.id),
            )
        )
    )
    return XpLeaderboardOut(
        entries=[
            XpLeaderboardEntry(
                rank=rank,
                user_id=user.id,
                display_name=user.display_name,
                username=user.username,
                avatar=user.avatar,
                level=level_for_xp(user.xp),
                xp=user.xp,
            )
            for rank, user in enumerate(users, start=1)
        ],
        you=CurrentXpStanding(
            rank=int(users_ahead or 0) + 1,
            level=level_for_xp(current_user.xp),
            xp=current_user.xp,
        ),
    )
