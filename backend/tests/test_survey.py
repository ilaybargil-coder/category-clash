import pytest
from fastapi.testclient import TestClient

from app.auth import TokenUser, get_current_user
from app.main import app
from app.survey_questions import SURVEY_QUESTIONS


@pytest.fixture
def authenticated_client():
    async def authenticated_user() -> TokenUser:
        return TokenUser(id=1, username="survey_player", display_name="Survey Player")

    app.dependency_overrides[get_current_user] = authenticated_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_each_survey_has_ranked_answers_worth_100_points():
    assert len(SURVEY_QUESTIONS) == 10

    for question in SURVEY_QUESTIONS:
        points = [answer["points"] for answer in question["answers"]]
        assert 6 <= len(points) <= 8
        assert sum(points) == 100
        assert points == sorted(points, reverse=True)


def test_canonical_guess_reveals_the_right_slot(authenticated_client):
    response = authenticated_client.post(
        "/api/survey/questions/q1/guess",
        json={"text": "מחפשים מטען או שקע", "revealed": []},
    )

    assert response.status_code == 200
    assert response.json() == {
        "matched": True,
        "slot_index": 0,
        "canonical": "מחפשים מטען או שקע",
        "points": 32,
        "already_revealed": False,
    }


def test_alias_guess_reveals_the_right_slot(authenticated_client):
    response = authenticated_client.post(
        "/api/survey/questions/q1/guess",
        json={"text": "מחפש מטען", "revealed": []},
    )

    assert response.status_code == 200
    assert response.json()["slot_index"] == 0
    assert response.json()["points"] == 32


def test_wrong_guess_does_not_match(authenticated_client):
    response = authenticated_client.post(
        "/api/survey/questions/q1/guess",
        json={"text": "זורקים אותו מהחלון", "revealed": []},
    )

    assert response.status_code == 200
    assert response.json() == {
        "matched": False,
        "slot_index": None,
        "canonical": None,
        "points": 0,
        "already_revealed": False,
    }


def test_duplicate_guess_returns_no_points(authenticated_client):
    response = authenticated_client.post(
        "/api/survey/questions/q1/guess",
        json={"text": "מחפשים מטען", "revealed": [0]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "matched": True,
        "slot_index": 0,
        "canonical": "מחפשים מטען או שקע",
        "points": 0,
        "already_revealed": True,
    }


def test_question_list_does_not_leak_answers(authenticated_client):
    response = authenticated_client.get("/api/survey/questions")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 10
    assert all(set(question) == {"id", "text", "slot_count", "max_points"} for question in payload)
    assert all(question["max_points"] == 100 for question in payload)
    assert "answers" not in response.text
    assert "canonical" not in response.text
    assert "aliases" not in response.text


def test_unauthenticated_guess_returns_401():
    response = TestClient(app).post(
        "/api/survey/questions/q1/guess",
        json={"text": "מחפשים מטען", "revealed": []},
    )

    assert response.status_code == 401
