"""Authenticated match result details."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import TokenUser, get_current_user
from ..db import get_session
from ..leveling import LOSS_XP, WIN_XP, level_for_xp, rank_for_level, win_streak_bonus
from ..models import Match, User

router = APIRouter(prefix="/api/matches", tags=["matches"])


class MatchXpResultOut(BaseModel):
    xp_awarded: int
    new_xp: int
    new_level: int
    rank: str


@router.get("/{match_id}/xp-result", response_model=MatchXpResultOut)
async def match_xp_result(
    match_id: str,
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MatchXpResultOut:
    identifiers = [Match.code == match_id.upper()]
    if match_id.isdigit():
        identifiers.append(Match.id == int(match_id))
    match = (
        await session.execute(
            select(Match)
            .where(
                or_(*identifiers),
                or_(Match.player1_id == current.id, Match.player2_id == current.id),
                Match.status.in_(("FINISHED", "FORFEITED")),
            )
            .order_by(Match.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=404, detail="Finished match not found")

    user = await session.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    won = match.winner_id == current.id
    xp_awarded = LOSS_XP
    if won:
        previous_winners = (
            await session.execute(
                select(Match.winner_id)
                .where(
                    Match.id <= match.id,
                    or_(Match.player1_id == current.id, Match.player2_id == current.id),
                    Match.status.in_(("FINISHED", "FORFEITED")),
                )
                .order_by(Match.id.desc())
            )
        ).scalars()
        streak_at_match = 0
        for winner_id in previous_winners:
            if winner_id != current.id:
                break
            streak_at_match += 1
        xp_awarded = WIN_XP + win_streak_bonus(streak_at_match)
    level = level_for_xp(user.xp)
    return MatchXpResultOut(
        xp_awarded=xp_awarded,
        new_xp=user.xp,
        new_level=level,
        rank=rank_for_level(level),
    )
