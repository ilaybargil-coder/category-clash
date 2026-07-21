import asyncio
import os
import uuid

import pytest
from sqlalchemy import delete, func, select, text, update

from app.db import SessionLocal, engine
from app.game.db_io import DbResultSink, make_question_provider
from app.game.engine import VIRTUAL_PLAYER_ID, GameConfig, GameRoom, RoomPhase
from app.game.validator import QuestionData, build_question_index
from app.models import (
    AnswerAlias,
    ApprovedAnswer,
    Match,
    Question,
    ServedQuestion,
    SubmittedAnswer,
    User,
)
from app.seed import seed


@pytest.fixture(autouse=True)
async def dispose_database_pool_after_test():
    """pytest uses separate event loops; pooled asyncpg connections cannot cross them."""

    yield
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="set RUN_DB_INTEGRATION=1 with local PostgreSQL running",
)
async def test_retried_command_persists_one_submitted_answer() -> None:
    async with SessionLocal() as session:
        user_ids = list(
            (await session.execute(select(User.id).order_by(User.id).limit(2))).scalars().all()
        )
        question_id = await session.scalar(select(Question.id).limit(1))
    assert len(user_ids) == 2 and question_id is not None

    async def provider(_exclude_ids: set[int], _player_ids: tuple[int, ...]) -> QuestionData:
        return QuestionData(
            id=question_id,
            text="integration question",
            index=build_question_index([]),
        )

    async def broadcast(_event: dict) -> None:
        return None

    code = f"IT{uuid.uuid4().hex[:10].upper()}"
    room = GameRoom(
        code,
        GameConfig(turn_seconds=30, preview_seconds=0.001),
        provider,
        broadcast,
        DbResultSink(SessionLocal),
    )

    try:
        await room.join(user_ids[0], "integration-a", "Integration A")
        await room.join(user_ids[1], "integration-b", "Integration B")
        for _ in range(100):
            if room.phase == RoomPhase.ROUND_ACTIVE:
                break
            await asyncio.sleep(0.005)
        assert room.phase == RoomPhase.ROUND_ACTIVE

        command_id = str(uuid.uuid4())
        await room.submit_answer(
            room.turn_user_id,
            "definitely-invalid",
            client_command_id=command_id,
        )
        await room.submit_answer(
            room.turn_user_id,
            "definitely-invalid",
            client_command_id=command_id,
        )
        submission_id = room.answers[0].submission_id

        async with SessionLocal() as session:
            by_submission = await session.scalar(
                select(func.count())
                .select_from(SubmittedAnswer)
                .where(SubmittedAnswer.submission_id == submission_id)
            )
            by_command = await session.scalar(
                select(func.count())
                .select_from(SubmittedAnswer)
                .where(SubmittedAnswer.client_command_id == command_id)
            )
        assert by_submission == by_command == 1
    finally:
        for task in list(room._tasks):
            task.cancel()
        async with SessionLocal() as session:
            await session.execute(delete(Match).where(Match.code == code))
            await session.commit()


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="set RUN_DB_INTEGRATION=1 with local PostgreSQL running",
)
async def test_practice_room_has_no_match_or_progression_writes(monkeypatch) -> None:
    async with SessionLocal() as session:
        creator = (await session.execute(select(User).order_by(User.id).limit(1))).scalar_one()
        original_progress = (creator.xp, creator.wins, creator.losses, creator.win_streak)
        served_id_before = int(await session.scalar(select(func.max(ServedQuestion.id))) or 0)

    async def broadcast(_event: dict) -> None:
        return None

    monkeypatch.setattr("app.game.engine.random.choice", lambda _order: VIRTUAL_PLAYER_ID)
    code = f"PR{uuid.uuid4().hex[:10].upper()}"
    room = GameRoom(
        code,
        GameConfig(
            turn_seconds=30,
            practice_dummy_turn_seconds=0.02,
            powerup_grace_ms=600,
            preview_seconds=0.001,
            intermission_seconds=0.001,
            rounds_to_win=1,
        ),
        make_question_provider(SessionLocal),
        broadcast,
        DbResultSink(SessionLocal, practice=True),
        practice=True,
        creator_user_id=creator.id,
    )

    try:
        assert await room.join(
            creator.id,
            creator.username,
            creator.display_name,
            creator.avatar,
        )
        assert room.players[VIRTUAL_PLAYER_ID].connected
        for _ in range(100):
            if room.phase == RoomPhase.MATCH_FINISHED:
                break
            await asyncio.sleep(0.005)
        assert room.phase == RoomPhase.MATCH_FINISHED
        assert room.match_winner_id == creator.id

        async with SessionLocal() as session:
            refreshed = await session.get(User, creator.id)
            assert refreshed is not None
            assert (
                refreshed.xp,
                refreshed.wins,
                refreshed.losses,
                refreshed.win_streak,
            ) == original_progress
            assert (
                await session.scalar(
                    select(func.count()).select_from(Match).where(Match.code == code)
                )
                == 0
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(ServedQuestion)
                    .where(ServedQuestion.user_id == VIRTUAL_PLAYER_ID)
                )
                == 0
            )
    finally:
        room.cancel_background_tasks()
        async with SessionLocal() as session:
            await session.execute(
                delete(ServedQuestion).where(
                    ServedQuestion.user_id == creator.id,
                    ServedQuestion.id > served_id_before,
                )
            )
            await session.commit()


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="set RUN_DB_INTEGRATION=1 with local PostgreSQL running",
)
async def test_1v1_question_provider_excludes_recent_union_and_falls_back() -> None:
    token = uuid.uuid4().hex
    user_ids: list[int] = []
    question_ids: list[int] = []
    original_active_ids: list[int] = []

    try:
        async with SessionLocal() as session:
            original_active_ids = list(
                (await session.execute(select(Question.id).where(Question.is_active.is_(True))))
                .scalars()
                .all()
            )
            await session.execute(update(Question).values(is_active=False))

            users = [
                User(username=f"recent-{token[:12]}-{suffix}", display_name=suffix)
                for suffix in ("a", "b")
            ]
            questions = [
                Question(text=f"recent-question-{token}-{number}", is_active=True)
                for number in range(3)
            ]
            session.add_all([*users, *questions])
            await session.flush()
            user_ids = [user.id for user in users]
            question_ids = [question.id for question in questions]
            session.add_all(
                [
                    ServedQuestion(user_id=user_ids[0], question_id=question_ids[0]),
                    ServedQuestion(user_id=user_ids[1], question_id=question_ids[1]),
                ]
            )
            await session.commit()

        provider = make_question_provider(SessionLocal)
        fresh = await provider(set(), tuple(user_ids))
        assert fresh is not None
        assert fresh.id == question_ids[2]

        async with SessionLocal() as session:
            recorded_for_fresh = await session.scalar(
                select(func.count())
                .select_from(ServedQuestion)
                .where(
                    ServedQuestion.question_id == fresh.id,
                    ServedQuestion.user_id.in_(user_ids),
                )
            )
        assert recorded_for_fresh == 2

        # All active questions are now recent for at least one player, so the
        # provider must relax recency and still return from the active pool.
        recent_fallback = await provider(set(), tuple(user_ids))
        assert recent_fallback is not None
        assert recent_fallback.id in question_ids

        # If same-game exclusions also cover the bank, the final full-active-
        # pool fallback must likewise keep the match alive.
        full_pool_fallback = await provider(set(question_ids), tuple(user_ids))
        assert full_pool_fallback is not None
        assert full_pool_fallback.id in question_ids
    finally:
        async with SessionLocal() as session:
            if question_ids:
                await session.execute(delete(Question).where(Question.id.in_(question_ids)))
            if user_ids:
                await session.execute(delete(User).where(User.id.in_(user_ids)))
            if original_active_ids:
                await session.execute(
                    update(Question)
                    .where(Question.id.in_(original_active_ids))
                    .values(is_active=True)
                )
            await session.commit()


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="set RUN_DB_INTEGRATION=1 with PostgreSQL running",
)
async def test_seed_is_idempotent_and_never_multiplies_reference_data() -> None:
    async def counts() -> tuple[int, int, int, int]:
        async with SessionLocal() as session:
            values = []
            for model in (User, Question, ApprovedAnswer, AnswerAlias):
                value = await session.scalar(select(func.count()).select_from(model))
                values.append(int(value or 0))
            return values[0], values[1], values[2], values[3]

    await seed()
    after_first = await counts()
    await seed()
    after_second = await counts()

    assert after_first == after_second
    assert after_second[0] >= 2
    assert after_second[1] >= 30
    assert after_second[2] >= 1_400


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="set RUN_DB_INTEGRATION=1 with PostgreSQL running",
)
async def test_seed_migrates_legacy_wrong_answers_and_aliases() -> None:
    await seed()
    async with SessionLocal() as session:
        tropical_id = await session.scalar(
            select(Question.id).where(Question.text == "כתבו שמות של פירות טרופיים")
        )
        dentist_id = await session.scalar(
            select(ApprovedAnswer.id)
            .join(Question, Question.id == ApprovedAnswer.question_id)
            .where(
                Question.text == "כתבו שמות של מקצועות",
                ApprovedAnswer.canonical == "רופא שיניים",
            )
        )
        assert tropical_id is not None and dentist_id is not None
        legacy_answer = ApprovedAnswer(question_id=tropical_id, canonical="סלק")
        session.add(legacy_answer)
        session.add(AnswerAlias(approved_answer_id=dentist_id, alias="שיננית"))
        await session.commit()
        legacy_id = legacy_answer.id

    await seed()

    async with SessionLocal() as session:
        legacy_is_active = await session.scalar(
            select(ApprovedAnswer.is_active).where(ApprovedAnswer.id == legacy_id)
        )
        salak_count = await session.scalar(
            select(func.count())
            .select_from(ApprovedAnswer)
            .join(Question, Question.id == ApprovedAnswer.question_id)
            .where(
                Question.text == "כתבו שמות של פירות טרופיים",
                ApprovedAnswer.canonical == "סאלאק",
                ApprovedAnswer.is_active.is_(True),
            )
        )
        wrong_alias_count = await session.scalar(
            select(func.count())
            .select_from(AnswerAlias)
            .where(
                AnswerAlias.approved_answer_id == dentist_id,
                AnswerAlias.alias == "שיננית",
            )
        )
        assert legacy_is_active is False
        assert salak_count == 1
        assert wrong_alias_count == 0

        await session.execute(delete(ApprovedAnswer).where(ApprovedAnswer.id == legacy_id))
        await session.commit()


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="set RUN_DB_INTEGRATION=1 with PostgreSQL running",
)
async def test_application_tables_have_row_level_security_enabled() -> None:
    async with SessionLocal() as session:
        protected_tables = await session.scalar(
            text(
                """
                SELECT count(*)
                FROM pg_class
                WHERE relnamespace = 'public'::regnamespace
                  AND relname = ANY(:tables)
                  AND relrowsecurity = true
                """
            ),
            {
                "tables": list(
                    (
                        "users",
                        "questions",
                        "approved_answers",
                        "answer_aliases",
                        "matches",
                        "rounds",
                        "submitted_answers",
                    )
                )
            },
        )
    assert protected_tables == 7


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="set RUN_DB_INTEGRATION=1 with PostgreSQL running",
)
async def test_supabase_profile_columns_are_ready() -> None:
    async with SessionLocal() as session:
        columns = {
            row.column_name: row.is_nullable
            for row in (
                await session.execute(
                    text(
                        """
                        SELECT column_name, is_nullable
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'users'
                          AND column_name IN ('auth_user_id', 'password_hash')
                        """
                    )
                )
            )
        }

    assert columns == {"auth_user_id": "YES", "password_hash": "YES"}
