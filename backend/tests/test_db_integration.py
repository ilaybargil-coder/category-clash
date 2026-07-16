import asyncio
import os
import uuid

import pytest
from sqlalchemy import delete, func, select, text

from app.db import SessionLocal, engine
from app.game.db_io import DbResultSink
from app.game.engine import GameConfig, GameRoom, RoomPhase
from app.game.validator import QuestionData, build_question_index
from app.models import AnswerAlias, ApprovedAnswer, Match, Question, SubmittedAnswer, User
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

    async def provider(_exclude_ids: set[int]) -> QuestionData:
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
    assert after_second[1] >= 10


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
