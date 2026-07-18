import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.auth import create_access_token
from app.config import settings
from app.db import SessionLocal, engine
from app.main import app
from app.models import AnswerReport, Question, User

requires_database = pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="set RUN_DB_INTEGRATION=1 with local PostgreSQL running",
)


@pytest.fixture(autouse=True)
async def dispose_database_pool_after_test():
    """pytest uses separate event loops; pooled asyncpg connections cannot cross them."""

    yield
    await engine.dispose()


@pytest.fixture
async def report_context():
    suffix = uuid.uuid4().hex[:8]
    async with SessionLocal() as session:
        user = User(
            username=f"report{suffix}",
            display_name="Answer Reporter",
            password_hash=None,
            coins=0,
        )
        question = Question(text=f"Integration report question {suffix}")
        session.add_all([user, question])
        await session.commit()
        await session.refresh(user)
        await session.refresh(question)

    yield user, question

    async with SessionLocal() as session:
        await session.execute(delete(AnswerReport).where(AnswerReport.reporter_user_id == user.id))
        await session.execute(delete(Question).where(Question.id == question.id))
        await session.execute(delete(User).where(User.id == user.id))
        await session.commit()


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "demo")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as http_client:
        yield http_client


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.username, user.display_name)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
@requires_database
async def test_create_report(client, report_context) -> None:
    user, question = report_context

    response = await client.post(
        "/api/reports",
        headers=auth_headers(user),
        json={"question_id": question.id, "raw_text": "  BMW  "},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["question_id"] == question.id
    assert payload["raw_text"] == "  BMW  "
    assert payload["normalized"] == "bmw"
    assert payload["reporter_user_id"] == user.id
    assert payload["status"] == "pending"
    async with SessionLocal() as session:
        persisted = await session.get(AnswerReport, payload["id"])
    assert persisted is not None
    assert persisted.normalized == "bmw"

    listed = await client.get("/api/reports", headers=auth_headers(user))
    assert listed.status_code == 200
    assert payload in listed.json()


@pytest.mark.integration
@requires_database
async def test_duplicate_normalized_report_returns_existing(client, report_context) -> None:
    user, question = report_context
    first = await client.post(
        "/api/reports",
        headers=auth_headers(user),
        json={"question_id": question.id, "raw_text": "סוסון-ים"},
    )
    duplicate = await client.post(
        "/api/reports",
        headers=auth_headers(user),
        json={"question_id": question.id, "raw_text": "סוסון ים"},
    )

    assert first.status_code == duplicate.status_code == 200
    assert duplicate.json() == first.json()
    async with SessionLocal() as session:
        reports = (
            (
                await session.execute(
                    select(AnswerReport).where(
                        AnswerReport.question_id == question.id,
                        AnswerReport.reporter_user_id == user.id,
                    )
                )
            )
            .scalars()
            .all()
        )
    assert len(reports) == 1


@pytest.mark.integration
@requires_database
async def test_unknown_question_returns_404(client, report_context) -> None:
    user, _question = report_context

    response = await client.post(
        "/api/reports",
        headers=auth_headers(user),
        json={"question_id": 2_147_483_647, "raw_text": "missing question"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Question not found"}


async def test_reports_require_authentication(client) -> None:
    created = await client.post(
        "/api/reports",
        json={"question_id": 1, "raw_text": "untrusted"},
    )
    listed = await client.get("/api/reports")

    assert created.status_code == 401
    assert listed.status_code == 401
