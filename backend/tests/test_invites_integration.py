import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, or_

from app.auth import create_access_token
from app.config import settings
from app.db import SessionLocal, engine
from app.main import app
from app.models import Friendship, User
from app.redis import close_redis, get_redis

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_INTEGRATION") != "1",
        reason="set RUN_DB_INTEGRATION=1 with local PostgreSQL and Redis running",
    ),
]


@pytest.fixture(autouse=True)
async def dispose_clients_after_test():
    """pytest uses separate event loops, so async clients cannot cross tests."""

    yield
    await close_redis()
    await engine.dispose()


@pytest.fixture
async def invite_users():
    prefix = f"iv{uuid.uuid4().hex[:8]}"
    async with SessionLocal() as session:
        sender, friend, stranger = [
            User(
                username=f"{prefix}{index}",
                display_name=f"Invite {index}",
                password_hash=None,
                coins=0,
            )
            for index in range(3)
        ]
        session.add_all([sender, friend, stranger])
        await session.flush()
        session.add(
            Friendship(
                user_a_id=min(sender.id, friend.id),
                user_b_id=max(sender.id, friend.id),
            )
        )
        await session.commit()

    user_ids = [sender.id, friend.id, stranger.id]
    yield sender, friend, stranger

    redis = await get_redis()
    keys = []
    async for key in redis.scan_iter(match="invite:to:*:from:*"):
        parts = key.split(":")
        if int(parts[2]) in user_ids or int(parts[4]) in user_ids:
            keys.append(key)
    if keys:
        await redis.delete(*keys)
    async with SessionLocal() as session:
        await session.execute(
            delete(Friendship).where(
                or_(
                    Friendship.user_a_id.in_(user_ids),
                    Friendship.user_b_id.in_(user_ids),
                )
            )
        )
        await session.execute(delete(User).where(User.id.in_(user_ids)))
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


async def test_cannot_invite_non_friend(client, invite_users) -> None:
    sender, _, stranger = invite_users
    response = await client.post(
        "/api/invites",
        headers=auth_headers(sender),
        json={"username": stranger.username},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Can only invite friends"


async def test_invite_list_and_single_accept(client, invite_users) -> None:
    sender, friend, _ = invite_users
    created = await client.post(
        "/api/invites",
        headers=auth_headers(sender),
        json={"username": friend.username.upper()},
    )
    assert created.status_code == 200
    room_code = created.json()["room_code"]

    incoming = await client.get("/api/invites", headers=auth_headers(friend))
    assert incoming.status_code == 200
    assert incoming.json() == [
        {
            "sender": {
                "id": sender.id,
                "username": sender.username,
                "display_name": sender.display_name,
            },
            "room_code": room_code,
            "expires_in_seconds": incoming.json()[0]["expires_in_seconds"],
        }
    ]
    assert 0 < incoming.json()[0]["expires_in_seconds"] <= 90

    accepted = await client.post(f"/api/invites/{sender.id}/accept", headers=auth_headers(friend))
    assert accepted.status_code == 200
    assert accepted.json() == {"room_code": room_code}
    expired = await client.post(f"/api/invites/{sender.id}/accept", headers=auth_headers(friend))
    assert expired.status_code == 410


async def test_decline_removes_invite(client, invite_users) -> None:
    sender, friend, _ = invite_users
    created = await client.post(
        "/api/invites",
        headers=auth_headers(sender),
        json={"username": friend.username},
    )
    assert created.status_code == 200
    declined = await client.post(f"/api/invites/{sender.id}/decline", headers=auth_headers(friend))
    assert declined.status_code == 200
    assert declined.json() == {"declined": True}
    incoming = await client.get("/api/invites", headers=auth_headers(friend))
    assert incoming.json() == []


async def test_duplicate_pending_invite_is_rejected(client, invite_users) -> None:
    sender, friend, _ = invite_users
    first = await client.post(
        "/api/invites",
        headers=auth_headers(sender),
        json={"username": friend.username},
    )
    duplicate = await client.post(
        "/api/invites",
        headers=auth_headers(sender),
        json={"username": friend.username},
    )
    assert first.status_code == 200
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Invite already pending"
