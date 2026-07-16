from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import app.main as main_module
from app.api.routes import demo_users
from app.auth import create_access_token, decode_token
from app.config import Settings, settings
from app.main import app


def token_for(user_id: int = 1) -> str:
    return create_access_token(user_id, f"user{user_id}", f"User {user_id}")


def test_supabase_postgres_url_is_normalized_for_async_sqlalchemy():
    configured = Settings(database_url="postgresql://user:password@db.example/postgres")
    assert configured.async_database_url == (
        "postgresql+asyncpg://user:password@db.example/postgres"
    )


def test_explicit_asyncpg_url_is_unchanged():
    url = "postgresql+asyncpg://user:password@db.example/postgres"
    assert Settings(database_url=url).async_database_url == url


def test_supabase_sslmode_is_translated_for_asyncpg():
    configured = Settings(
        database_url="postgresql://user:password@db.example/postgres?sslmode=require"
    )
    assert configured.async_database_url.endswith("?ssl=require")


def test_health_is_a_database_independent_liveness_probe():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_503_when_database_is_unavailable(monkeypatch):
    async def unavailable() -> bool:
        return False

    monkeypatch.setattr(main_module, "database_is_ready", unavailable)
    response = TestClient(app).get("/ready")
    assert response.status_code == 503


def test_ready_returns_success_when_database_responds(monkeypatch):
    async def available() -> bool:
        return True

    monkeypatch.setattr(main_module, "database_is_ready", available)
    response = TestClient(app).get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_cors_preflight_allows_only_configured_frontend_origin():
    client = TestClient(app)
    allowed = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"

    rejected = client.options(
        "/health",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in rejected.headers


def test_websocket_rejects_origin_outside_allowlist(monkeypatch):
    monkeypatch.setattr(settings, "websocket_origins", "https://game.example")
    client = TestClient(app)
    with client.websocket_connect(
        f"/ws/rooms/NOPE1?token={token_for()}",
        headers={"origin": "https://evil.example"},
    ) as websocket:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_json()
    assert exc_info.value.code == 4403


def test_websocket_allows_configured_origin_and_continues_auth_flow(monkeypatch):
    monkeypatch.setattr(settings, "websocket_origins", "https://game.example")
    client = TestClient(app)
    with client.websocket_connect(
        f"/ws/rooms/NOPE1?token={token_for()}",
        headers={"origin": "https://game.example"},
    ) as websocket:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_json()
    assert exc_info.value.code == 4404


async def test_demo_picker_preloads_signed_sessions_for_instant_selection():
    users = [
        SimpleNamespace(
            id=1,
            username="dana",
            display_name="דנה",
            coins=0,
            wins=0,
            losses=0,
        ),
        SimpleNamespace(
            id=2,
            username="omer",
            display_name="עומר",
            coins=0,
            wins=0,
            losses=0,
        ),
    ]

    class Result:
        def scalars(self):
            return self

        def all(self):
            return users

    class Session:
        async def execute(self, _statement):
            return Result()

    sessions = await demo_users(Session())

    assert [item.user.username for item in sessions] == ["dana", "omer"]
    decoded = [decode_token(item.token) for item in sessions]
    assert all(item is not None for item in decoded)
    assert [item.username for item in decoded if item is not None] == ["dana", "omer"]
