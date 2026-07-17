import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, update

from app.auth import create_access_token
from app.config import settings
from app.db import SessionLocal, engine
from app.main import app
from app.models import AnswerAlias, ApprovedAnswer, Question, User

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
async def solo_data():
    prefix = f"solo{uuid.uuid4().hex[:8]}"
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

        owner = User(username=f"{prefix}a", display_name="Solo Owner", coins=0)
        stranger = User(username=f"{prefix}b", display_name="Solo Stranger", coins=0)
        question = Question(text=f"Integration solo question {prefix}", is_active=True)
        session.add_all([owner, stranger, question])
        await session.flush()
        first = ApprovedAnswer(
            question_id=question.id,
            canonical="תשובה ראשונה",
            semantic_group="קבוצה משותפת",
            is_active=True,
        )
        grouped = ApprovedAnswer(
            question_id=question.id,
            canonical="תשובה שנייה",
            semantic_group="קבוצה משותפת",
            is_active=True,
        )
        aliased = ApprovedAnswer(
            question_id=question.id,
            canonical="תשובה שלישית",
            is_active=True,
        )
        session.add_all([first, grouped, aliased])
        await session.flush()
        session.add(AnswerAlias(approved_answer_id=aliased.id, alias="כינוי שלישי"))
        await session.commit()

    yield owner, stranger, question, first, grouped, aliased

    async with SessionLocal() as session:
        await session.execute(delete(Question).where(Question.id == question.id))
        await session.execute(delete(User).where(User.id.in_([owner.id, stranger.id])))
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


async def test_solo_question_flow(client, solo_data) -> None:
    owner, stranger, question, first, grouped, aliased = solo_data
    owner_headers = auth_headers(owner)

    started = await client.post("/api/solo/start", headers=owner_headers)
    assert started.status_code == 200
    assert started.json()["question_id"] == question.id
    assert started.json()["question_text"] == question.text
    assert started.json()["total_answers"] == 4
    solo_id = started.json()["solo_id"]

    accepted = await client.post(
        f"/api/solo/{solo_id}/answer",
        headers=owner_headers,
        json={"text": first.canonical},
    )
    assert accepted.json() == {
        "status": "VALID",
        "canonical": first.canonical,
        "found_count": 1,
        "total_answers": 4,
    }

    duplicate = await client.post(
        f"/api/solo/{solo_id}/answer",
        headers=owner_headers,
        json={"text": first.canonical},
    )
    assert duplicate.json()["status"] == "DUPLICATE"
    assert duplicate.json()["found_count"] == 1

    semantic_duplicate = await client.post(
        f"/api/solo/{solo_id}/answer",
        headers=owner_headers,
        json={"text": grouped.canonical},
    )
    assert semantic_duplicate.json()["status"] == "TOO_SIMILAR"
    assert semantic_duplicate.json()["found_count"] == 1

    reveal = await client.post(f"/api/solo/{solo_id}/reveal", headers=owner_headers)
    assert reveal.status_code == 200
    by_canonical = {answer["canonical"]: answer for answer in reveal.json()["answers"]}
    assert by_canonical[first.canonical]["found"] is True
    assert by_canonical[first.canonical]["semantic_group"] == "קבוצה משותפת"
    assert by_canonical[grouped.canonical]["found"] is False
    assert by_canonical[aliased.canonical]["found"] is False

    hidden = await client.post(
        f"/api/solo/{solo_id}/answer",
        headers=auth_headers(stranger),
        json={"text": first.canonical},
    )
    assert hidden.status_code == 404

    exhausted = await client.post(f"/api/solo/{solo_id}/next", headers=owner_headers)
    assert exhausted.status_code == 409
    assert exhausted.json()["detail"] == "No more questions"
