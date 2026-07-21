import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.auth import create_access_token
from app.config import settings
from app.db import SessionLocal, engine
from app.game.validator import AnswerStatus, RoundValidator, build_question_index
from app.main import app
from app.models import AnswerAlias, AnswerReport, ApprovedAnswer, Question, User

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
async def moderation_context(monkeypatch):
    suffix = uuid.uuid4().hex[:8]
    async with SessionLocal() as session:
        admin = User(
            username=f"admin{suffix}",
            display_name="Report Admin",
            password_hash=None,
            coins=0,
        )
        reporter_one = User(
            username=f"reporter1{suffix}",
            display_name="First Reporter",
            password_hash=None,
            coins=0,
        )
        reporter_two = User(
            username=f"reporter2{suffix}",
            display_name="Second Reporter",
            password_hash=None,
            coins=0,
        )
        question = Question(text=f"Moderation integration question {suffix}")
        session.add_all([admin, reporter_one, reporter_two, question])
        await session.flush()
        existing_answer = ApprovedAnswer(
            question_id=question.id,
            canonical="תשובה קיימת",
            is_active=True,
        )
        session.add(existing_answer)
        await session.commit()
        for item in (admin, reporter_one, reporter_two, question, existing_answer):
            await session.refresh(item)

    monkeypatch.setattr(settings, "admin_usernames", admin.username)
    yield admin, reporter_one, reporter_two, question, existing_answer

    async with SessionLocal() as session:
        await session.execute(delete(Question).where(Question.id == question.id))
        await session.execute(
            delete(User).where(User.id.in_([admin.id, reporter_one.id, reporter_two.id]))
        )
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


@pytest.mark.integration
@requires_database
async def test_admin_pending_reports_are_grouped(client, moderation_context) -> None:
    admin, reporter_one, reporter_two, question, existing_answer = moderation_context
    first = await client.post(
        "/api/reports",
        headers=auth_headers(reporter_one),
        json={"question_id": question.id, "raw_text": "תשובה-חדשה"},
    )
    second = await client.post(
        "/api/reports",
        headers=auth_headers(reporter_two),
        json={"question_id": question.id, "raw_text": "תשובה חדשה"},
    )
    single = await client.post(
        "/api/reports",
        headers=auth_headers(reporter_one),
        json={"question_id": question.id, "raw_text": "תשובה בודדת"},
    )
    assert first.status_code == second.status_code == single.status_code == 200

    response = await client.get("/api/reports/pending", headers=auth_headers(admin))

    assert response.status_code == 200
    payload = response.json()
    group = next(
        item
        for item in payload
        if item["question_id"] == question.id and item["normalized"] == "תשובה חדשה"
    )
    assert group["question_text"] == question.text
    assert group["sample_raw_text"] in {"תשובה-חדשה", "תשובה חדשה"}
    assert group["occurrence_count"] == 2
    assert group["distinct_reporter_count"] == 2
    assert group["newest_created_at"]
    grouped_position = payload.index(group)
    single_position = next(
        index
        for index, item in enumerate(payload)
        if item["question_id"] == question.id and item["normalized"] == "תשובה בודדת"
    )
    assert grouped_position < single_position

    context = await client.get(f"/api/reports/context/{question.id}", headers=auth_headers(admin))
    assert context.status_code == 200
    assert context.json() == {
        "question_id": question.id,
        "question_text": question.text,
        "answers": [{"id": existing_answer.id, "canonical": "תשובה קיימת"}],
    }


@pytest.mark.integration
@requires_database
async def test_admin_approves_report_as_new_answer(client, moderation_context) -> None:
    admin, reporter, _other_reporter, question, _existing_answer = moderation_context
    created = await client.post(
        "/api/reports",
        headers=auth_headers(reporter),
        json={"question_id": question.id, "raw_text": "תשובה לא נקייה"},
    )
    assert created.status_code == 200

    response = await client.post(
        "/api/reports/approve",
        headers=auth_headers(admin),
        json={
            "question_id": question.id,
            "normalized": created.json()["normalized"],
            "mode": "new_answer",
            "canonical": "  תשובה נקייה  ",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "approved", "updated_reports": 1}
    async with SessionLocal() as session:
        report = await session.get(AnswerReport, created.json()["id"])
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
    assert report is not None and report.status == "approved"
    index = build_question_index(
        [
            (
                answer.id,
                answer.canonical,
                answer.semantic_group,
                [alias.alias for alias in answer.aliases],
            )
            for answer in answers
        ]
    )
    result = RoundValidator(index).check("תשובה נקייה")
    assert result.status == AnswerStatus.VALID
    assert result.entry is not None and result.entry.canonical == "תשובה נקייה"


@pytest.mark.integration
@requires_database
async def test_admin_approves_report_as_alias(client, moderation_context) -> None:
    admin, reporter, _other_reporter, question, existing_answer = moderation_context
    created = await client.post(
        "/api/reports",
        headers=auth_headers(reporter),
        json={"question_id": question.id, "raw_text": "כינוי חדש"},
    )
    assert created.status_code == 200

    response = await client.post(
        "/api/reports/approve",
        headers=auth_headers(admin),
        json={
            "question_id": question.id,
            "normalized": created.json()["normalized"],
            "mode": "alias",
            "canonical": "כינוי חדש",
            "target_answer_id": existing_answer.id,
        },
    )

    assert response.status_code == 200
    async with SessionLocal() as session:
        alias = await session.scalar(
            select(AnswerAlias).where(
                AnswerAlias.approved_answer_id == existing_answer.id,
                AnswerAlias.alias == "כינוי חדש",
            )
        )
        report = await session.get(AnswerReport, created.json()["id"])
    assert alias is not None
    assert report is not None and report.status == "approved"
    index = build_question_index(
        [(existing_answer.id, existing_answer.canonical, None, [alias.alias])]
    )
    result = RoundValidator(index).check("כינוי חדש")
    assert result.status == AnswerStatus.VALID
    assert result.entry is not None and result.entry.answer_id == existing_answer.id


@pytest.mark.integration
@requires_database
async def test_admin_rejects_pending_report(client, moderation_context) -> None:
    admin, reporter, _other_reporter, question, _existing_answer = moderation_context
    created = await client.post(
        "/api/reports",
        headers=auth_headers(reporter),
        json={"question_id": question.id, "raw_text": "לא מתאים"},
    )
    assert created.status_code == 200

    response = await client.post(
        "/api/reports/reject",
        headers=auth_headers(admin),
        json={
            "question_id": question.id,
            "normalized": created.json()["normalized"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "rejected", "updated_reports": 1}
    async with SessionLocal() as session:
        report = await session.get(AnswerReport, created.json()["id"])
    assert report is not None and report.status == "rejected"


@pytest.mark.integration
@requires_database
async def test_non_admin_cannot_access_review_endpoints(client, moderation_context) -> None:
    _admin, reporter, _other_reporter, question, existing_answer = moderation_context
    headers = auth_headers(reporter)
    requests = [
        client.get("/api/reports/pending", headers=headers),
        client.get(f"/api/reports/context/{question.id}", headers=headers),
        client.post(
            "/api/reports/approve",
            headers=headers,
            json={
                "question_id": question.id,
                "normalized": "blocked",
                "mode": "alias",
                "canonical": "blocked",
                "target_answer_id": existing_answer.id,
            },
        ),
        client.post(
            "/api/reports/reject",
            headers=headers,
            json={"question_id": question.id, "normalized": "blocked"},
        ),
    ]

    for request in requests:
        response = await request
        assert response.status_code == 403
        assert response.json() == {"detail": "Admin access required"}
