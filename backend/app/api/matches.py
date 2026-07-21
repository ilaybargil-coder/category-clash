"""Authenticated match history and result details."""

from datetime import datetime

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


class MatchHistoryOpponentOut(BaseModel):
    display_name: str
    username: str
    avatar: str | None


class MatchHistoryScoreOut(BaseModel):
    player: int
    opponent: int


class MatchHistoryOut(BaseModel):
    id: int
    opponent: MatchHistoryOpponentOut
    won: bool
    score: MatchHistoryScoreOut
    finished_at: datetime


@router.get("", response_model=list[MatchHistoryOut])
async def match_history(
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[MatchHistoryOut]:
    rows = (
        await session.execute(
            select(Match, User)
            .join(
                User,
                or_(
                    (Match.player1_id == current.id) & (User.id == Match.player2_id),
                    (Match.player2_id == current.id) & (User.id == Match.player1_id),
                ),
            )
            .where(
                or_(Match.player1_id == current.id, Match.player2_id == current.id),
                Match.status == "FINISHED",
                Match.finished_at.is_not(None),
            )
            .order_by(Match.finished_at.desc(), Match.id.desc())
            .limit(20)
        )
    ).all()

    history: list[MatchHistoryOut] = []
    for match, opponent in rows:
        current_is_player1 = match.player1_id == current.id
        history.append(
            MatchHistoryOut(
                id=match.id,
                opponent=MatchHistoryOpponentOut(
                    display_name=opponent.display_name,
                    username=opponent.username,
                    avatar=opponent.avatar,
                ),
                won=match.winner_id == current.id,
                score=MatchHistoryScoreOut(
                    player=match.score_p1 if current_is_player1 else match.score_p2,
                    opponent=match.score_p2 if current_is_player1 else match.score_p1,
                ),
                finished_at=match.finished_at,
            )
        )
    return history


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
