import asyncio
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
async def presence_users():
    prefix = f"pr{uuid.uuid4().hex[:8]}"
    async with SessionLocal() as session:
        current, friend, stranger = [
            User(
                username=f"{prefix}{index}",
                display_name=f"Presence {index}",
                password_hash=None,
                coins=0,
            )
            for index in range(3)
        ]
        session.add_all([current, friend, stranger])
        await session.flush()
        session.add(
            Friendship(
                user_a_id=min(current.id, friend.id),
                user_b_id=max(current.id, friend.id),
            )
        )
        await session.commit()

    user_ids = [current.id, friend.id, stranger.id]
    yield current, friend, stranger

    client = await get_redis()
    await client.delete(*(f"presence:{user_id}" for user_id in user_ids))
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
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as http_client:
        yield http_client


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.username, user.display_name)
    return {"Authorization": f"Bearer {token}"}


async def test_heartbeat_reports_only_online_friends(client, presence_users) -> None:
    current, friend, stranger = presence_users

    marked_online = await client.post("/api/presence/heartbeat", headers=auth_headers(friend))
    assert marked_online.status_code == 200

    redis = await get_redis()
    await redis.set(f"presence:{stranger.id}", "1", ex=settings.presence_ttl_seconds)
    response = await client.post("/api/presence/heartbeat", headers=auth_headers(current))
    assert response.status_code == 200
    assert response.json() == {"online_friend_ids": [friend.id]}

    await redis.set(f"presence:{friend.id}", "1", px=1)
    await asyncio.sleep(0.02)
    expired = await client.post("/api/presence/heartbeat", headers=auth_headers(current))
    assert expired.status_code == 200
    assert expired.json() == {"online_friend_ids": []}
