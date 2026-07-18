import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, update

from app.api.daily import _daily_sessions
from app.auth import create_access_token
from app.config import settings
from app.db import SessionLocal, engine
from app.main import app
from app.models import ApprovedAnswer, DailyResult, Question, User

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_INTEGRATION") != "1",
        reason="set RUN_DB_INTEGRATION=1 with local PostgreSQL running",
    ),
]


@pytest.fixture(autouse=True)
async def dispose_database_pool_after_test():
    """pytest uses separate event loops, so async clients cannot cross tests."""

    yield
    await engine.dispose()


@pytest.fixture
async def daily_data():
    prefix = f"daily{uuid.uuid4().hex[:8]}"
    async with SessionLocal() as session:
        previously_active_ids = set(
            (await session.execute(select(Question.id).where(Question.is_active.is_(True))))
            .scalars()
            .all()
        )
        if previously_active_ids:
            await session.execute(
                update(Question)
                .where(Question.id.in_(previously_active_ids))
                .values(is_active=False)
            )

        first_user = User(username=f"{prefix}a", display_name="Daily Alpha", coins=0)
        second_user = User(username=f"{prefix}b", display_name="Daily Beta", coins=0)
        questions = [
            Question(text=f"Daily integration question {prefix} {number}", is_active=True)
            for number in range(3)
        ]
        session.add_all([first_user, second_user, *questions])
        await session.flush()

        answers_by_question: dict[int, list[str]] = {}
        for number, question in enumerate(questions):
            canonicals = [f"תשובה {prefix} {number} א", f"תשובה {prefix} {number} ב"]
            answers_by_question[question.id] = canonicals
            session.add_all(
                [
                    ApprovedAnswer(
                        question_id=question.id,
                        canonical=canonical,
                        is_active=True,
                    )
                    for canonical in canonicals
                ]
            )
        await session.commit()

    yield first_user, second_user, questions, answers_by_question

    for key in [key for key in _daily_sessions if key[0] in {first_user.id, second_user.id}]:
        _daily_sessions.pop(key, None)
    async with SessionLocal() as session:
        await session.execute(
            delete(DailyResult).where(DailyResult.user_id.in_([first_user.id, second_user.id]))
        )
        await session.execute(delete(Question).where(Question.id.in_([q.id for q in questions])))
        await session.execute(delete(User).where(User.id.in_([first_user.id, second_user.id])))
        if previously_active_ids:
            await session.execute(
                update(Question)
                .where(Question.id.in_(previously_active_ids))
                .values(is_active=True)
            )
        await session.commit()


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "demo")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as http_client:
        yield http_client


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.username, user.display_name)
    return {"Authorization": f"Bearer {token}"}


async def test_category_of_day_is_deterministic_and_shared(client, daily_data) -> None:
    first_user, second_user, questions, _answers = daily_data

    first = await client.get("/api/daily/today", headers=auth_headers(first_user))
    repeated = await client.get("/api/daily/today", headers=auth_headers(first_user))
    second = await client.get("/api/daily/today", headers=auth_headers(second_user))

    assert first.status_code == repeated.status_code == second.status_code == 200
    assert first.json()["question_id"] == repeated.json()["question_id"]
    assert first.json()["question_id"] == second.json()["question_id"]
    assert first.json()["date"] == second.json()["date"]
    assert first.json()["question_id"] in {question.id for question in questions}


async def test_one_attempt_per_user_per_day_and_idempotent_finish(client, daily_data) -> None:
    first_user, _second_user, _questions, _answers = daily_data
    headers = auth_headers(first_user)

    started = await client.post("/api/daily/start", headers=headers)
    assert started.status_code == 200

    finished = await client.post("/api/daily/finish", headers=headers)
    retried = await client.post("/api/daily/finish", headers=headers)
    restarted = await client.post("/api/daily/start", headers=headers)

    assert finished.status_code == retried.status_code == 200
    assert retried.json() == finished.json()
    assert restarted.status_code == 409
    assert restarted.json()["detail"] == "Daily challenge already completed"


async def test_daily_scoring_counts_only_valid_answers(client, daily_data) -> None:
    first_user, _second_user, _questions, answers_by_question = daily_data
    headers = auth_headers(first_user)
    started = await client.post("/api/daily/start", headers=headers)
    question_answers = answers_by_question[started.json()["question_id"]]

    valid = await client.post(
        "/api/daily/answer", headers=headers, json={"text": question_answers[0]}
    )
    duplicate = await client.post(
        "/api/daily/answer", headers=headers, json={"text": question_answers[0]}
    )
    invalid = await client.post(
        "/api/daily/answer", headers=headers, json={"text": "לא תשובה מאושרת"}
    )
    second_valid = await client.post(
        "/api/daily/answer", headers=headers, json={"text": question_answers[1]}
    )
    finished = await client.post("/api/daily/finish", headers=headers)

    assert valid.json()["status"] == "VALID"
    assert duplicate.json()["status"] == "DUPLICATE"
    assert invalid.json()["status"] == "INVALID"
    assert second_valid.json()["status"] == "VALID"
    assert finished.json()["score"] == 2
    assert finished.json()["share_text"] == "עניתי 2 תשובות היום"


async def test_daily_leaderboard_orders_by_score(client, daily_data) -> None:
    first_user, second_user, _questions, answers_by_question = daily_data
    first_headers = auth_headers(first_user)
    second_headers = auth_headers(second_user)

    first_start = await client.post("/api/daily/start", headers=first_headers)
    question_answers = answers_by_question[first_start.json()["question_id"]]
    for answer in question_answers:
        await client.post("/api/daily/answer", headers=first_headers, json={"text": answer})
    await client.post("/api/daily/finish", headers=first_headers)

    second_start = await client.post("/api/daily/start", headers=second_headers)
    assert second_start.json()["question_id"] == first_start.json()["question_id"]
    await client.post(
        "/api/daily/answer", headers=second_headers, json={"text": question_answers[0]}
    )
    await client.post("/api/daily/finish", headers=second_headers)

    response = await client.get("/api/daily/leaderboard", headers=first_headers)
    assert response.status_code == 200
    entries = response.json()["entries"]
    first_index = next(i for i, entry in enumerate(entries) if entry["user_id"] == first_user.id)
    second_index = next(i for i, entry in enumerate(entries) if entry["user_id"] == second_user.id)
    assert first_index < second_index
    assert entries[first_index]["score"] == 2
    assert entries[second_index]["score"] == 1
