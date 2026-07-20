"""DB-backed question provider and result sink for the game engine."""

from __future__ import annotations

import logging

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from ..leveling import LOSS_XP, WIN_XP, win_streak_bonus
from ..models import ApprovedAnswer, Match, Question, Round, SubmittedAnswer, User
from .engine import ResultSink
from .validator import QuestionData, build_question_index

logger = logging.getLogger(__name__)


def make_question_provider(session_factory: async_sessionmaker):
    async def provider(exclude_ids: set[int]) -> QuestionData | None:
        async with session_factory() as session:
            stmt = (
                select(Question)
                .where(Question.is_active.is_(True))
                .order_by(func.random())
                .limit(1)
            )
            if exclude_ids:
                stmt = stmt.where(Question.id.not_in(exclude_ids))
            question = (await session.execute(stmt)).scalar_one_or_none()
            if question is None:
                return None

            answers = (
                (
                    await session.execute(
                        select(ApprovedAnswer)
                        .where(
                            ApprovedAnswer.question_id == question.id,
                            ApprovedAnswer.is_active.is_(True),
                        )
                        .options(selectinload(ApprovedAnswer.aliases))
                    )
                )
                .scalars()
                .all()
            )
            index = build_question_index(
                [
                    (a.id, a.canonical, a.semantic_group, [al.alias for al in a.aliases])
                    for a in answers
                ]
            )
            return QuestionData(id=question.id, text=question.text, index=index)

    return provider


class DbResultSink(ResultSink):
    """Persists match history and every submitted answer (the raw log later
    feeds the admin's rejected-answers review screen)."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._sf = session_factory
        self._match_ids: dict[str, int] = {}
        self._round_ids: dict[tuple[str, int], int] = {}

    async def on_match_start(self, code: str, p1_id: int, p2_id: int) -> None:
        async with self._sf() as session:
            match = Match(code=code, player1_id=p1_id, player2_id=p2_id)
            session.add(match)
            await session.commit()
            self._match_ids[code] = match.id

    async def on_round_start(
        self, code: str, round_no: int, question_id: int, starter_id: int
    ) -> None:
        match_id = self._match_ids.get(code)
        if match_id is None:
            return
        async with self._sf() as session:
            round_row = Round(
                match_id=match_id,
                round_no=round_no,
                question_id=question_id,
                starter_user_id=starter_id,
            )
            session.add(round_row)
            await session.commit()
            self._round_ids[(code, round_no)] = round_row.id

    async def on_answer(
        self,
        code: str,
        round_no: int,
        submission_id: str,
        client_command_id: str | None,
        user_id: int,
        raw_text: str,
        normalized: str,
        status: str,
        matched_answer_id: int | None,
    ) -> None:
        round_id = self._round_ids.get((code, round_no))
        if round_id is None:
            return
        async with self._sf() as session:
            session.add(
                SubmittedAnswer(
                    submission_id=submission_id,
                    client_command_id=client_command_id,
                    round_id=round_id,
                    user_id=user_id,
                    raw_text=raw_text,
                    normalized_text=normalized,
                    status=status,
                    matched_answer_id=matched_answer_id,
                )
            )
            await session.commit()

    async def on_question_swap(self, code: str, round_no: int, question_id: int) -> None:
        round_id = self._round_ids.get((code, round_no))
        if round_id is None:
            return
        async with self._sf() as session:
            await session.execute(
                update(Round).where(Round.id == round_id).values(question_id=question_id)
            )
            await session.commit()

    async def on_round_end(self, code: str, round_no: int, winner_id: int, reason: str) -> None:
        round_id = self._round_ids.get((code, round_no))
        if round_id is None:
            return
        async with self._sf() as session:
            await session.execute(
                update(Round)
                .where(Round.id == round_id)
                .values(winner_user_id=winner_id, end_reason=reason)
            )
            await session.commit()

    async def on_match_end(
        self, code: str, winner_id: int, score: dict[int, int], reason: str
    ) -> None:
        match_id = self._match_ids.pop(code, None)
        self._round_ids = {k: v for k, v in self._round_ids.items() if k[0] != code}
        if match_id is None:
            return
        async with self._sf() as session:
            match = await session.get(Match, match_id)
            if match is None:
                return
            match.winner_id = winner_id
            match.score_p1 = score.get(match.player1_id, 0)
            match.score_p2 = score.get(match.player2_id, 0)
            match.status = "FINISHED" if reason == "SCORE" else "FORFEITED"
            match.finished_at = func.now()
            loser_id = match.player2_id if winner_id == match.player1_id else match.player1_id
            users = {
                user.id: user
                for user in (
                    (
                        await session.execute(
                            select(User)
                            .where(User.id.in_(sorted((winner_id, loser_id))))
                            .order_by(User.id)
                            .with_for_update()
                        )
                    )
                    .scalars()
                    .all()
                )
            }
            winner = users[winner_id]
            loser = users[loser_id]

            winner.wins += 1
            winner.win_streak += 1
            winner.xp += WIN_XP + win_streak_bonus(winner.win_streak)

            loser.losses += 1
            loser.xp += LOSS_XP
            loser.win_streak = 0
            await session.commit()
