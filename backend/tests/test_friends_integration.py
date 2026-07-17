import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, or_, select

from app.auth import create_access_token
from app.config import settings
from app.db import SessionLocal, engine
from app.main import app
from app.models import FriendRequest, Friendship, User

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_INTEGRATION") != "1",
        reason="set RUN_DB_INTEGRATION=1 with local PostgreSQL running",
    ),
]


@pytest.fixture(autouse=True)
async def dispose_database_pool_after_test():
    """pytest uses separate event loops; pooled asyncpg connections cannot cross them."""

    yield
    await engine.dispose()


@pytest.fixture
async def friend_users():
    prefix = f"fr{uuid.uuid4().hex[:8]}"
    async with SessionLocal() as session:
        users = [
            User(
                username=f"{prefix}{index}",
                display_name=f"Friend {index}",
                password_hash=None,
                coins=0,
                wins=index,
                losses=index + 1,
            )
            for index in range(5)
        ]
        session.add_all(users)
        await session.commit()
        for user in users:
            await session.refresh(user)

    yield users

    user_ids = [user.id for user in users]
    async with SessionLocal() as session:
        await session.execute(
            delete(FriendRequest).where(
                or_(
                    FriendRequest.sender_id.in_(user_ids),
                    FriendRequest.recipient_id.in_(user_ids),
                )
            )
        )
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


async def send_request(client: AsyncClient, sender: User, recipient: User):
    return await client.post(
        "/api/friends/requests",
        headers=auth_headers(sender),
        json={"username": recipient.username},
    )


async def test_send_request_appears_for_both_users(client, friend_users) -> None:
    sender, recipient = friend_users[:2]

    response = await send_request(client, sender, recipient)

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING"
    request_id = response.json()["request_id"]

    incoming = await client.get(
        "/api/friends/requests", headers=auth_headers(recipient)
    )
    outgoing = await client.get("/api/friends/requests", headers=auth_headers(sender))
    assert incoming.json()["incoming"][0]["id"] == request_id
    assert incoming.json()["incoming"][0]["user"]["id"] == sender.id
    assert outgoing.json()["outgoing"][0]["user"]["id"] == recipient.id


async def test_reverse_request_auto_accepts(client, friend_users) -> None:
    first, second = friend_users[:2]
    assert (await send_request(client, first, second)).status_code == 200

    response = await send_request(client, second, first)

    assert response.status_code == 200
    assert response.json()["status"] == "FRIENDS"
    async with SessionLocal() as session:
        request = await session.scalar(
            select(FriendRequest).where(
                FriendRequest.sender_id == first.id,
                FriendRequest.recipient_id == second.id,
            )
        )
        friendship = await session.scalar(
            select(Friendship).where(
                Friendship.user_a_id == min(first.id, second.id),
                Friendship.user_b_id == max(first.id, second.id),
            )
        )
    assert request is not None
    assert request.status == "ACCEPTED"
    assert request.responded_at is not None
    assert friendship is not None


async def test_accept_creates_friendship(client, friend_users) -> None:
    sender, recipient = friend_users[:2]
    sent = await send_request(client, sender, recipient)

    accepted = await client.post(
        f"/api/friends/requests/{sent.json()['request_id']}/accept",
        headers=auth_headers(recipient),
    )

    assert accepted.status_code == 200
    assert accepted.json()["status"] == "FRIENDS"
    listed = await client.get("/api/friends", headers=auth_headers(recipient))
    assert [friend["id"] for friend in listed.json()] == [sender.id]
    async with SessionLocal() as session:
        friendship = await session.scalar(
            select(Friendship).where(
                Friendship.user_a_id == min(sender.id, recipient.id),
                Friendship.user_b_id == max(sender.id, recipient.id),
            )
        )
    assert friendship is not None


async def test_decline_marks_request_without_creating_friendship(client, friend_users) -> None:
    sender, recipient = friend_users[:2]
    sent = await send_request(client, sender, recipient)

    declined = await client.post(
        f"/api/friends/requests/{sent.json()['request_id']}/decline",
        headers=auth_headers(recipient),
    )

    assert declined.status_code == 200
    assert declined.json()["status"] == "DECLINED"
    async with SessionLocal() as session:
        request = await session.get(FriendRequest, sent.json()["request_id"])
        friendship = await session.scalar(
            select(Friendship).where(
                Friendship.user_a_id == min(sender.id, recipient.id),
                Friendship.user_b_id == max(sender.id, recipient.id),
            )
        )
    assert request is not None
    assert request.status == "DECLINED"
    assert request.responded_at is not None
    assert friendship is None


async def test_cannot_accept_someone_elses_request(client, friend_users) -> None:
    sender, recipient, other = friend_users[:3]
    sent = await send_request(client, sender, recipient)

    response = await client.post(
        f"/api/friends/requests/{sent.json()['request_id']}/accept",
        headers=auth_headers(other),
    )

    assert response.status_code == 404
    async with SessionLocal() as session:
        request = await session.get(FriendRequest, sent.json()["request_id"])
    assert request is not None and request.status == "PENDING"


async def test_duplicate_pending_request_returns_409(client, friend_users) -> None:
    sender, recipient = friend_users[:2]
    assert (await send_request(client, sender, recipient)).status_code == 200

    duplicate = await send_request(client, sender, recipient)

    assert duplicate.status_code == 409


async def test_unfriend_removes_only_friendship(client, friend_users) -> None:
    sender, recipient = friend_users[:2]
    sent = await send_request(client, sender, recipient)
    request_id = sent.json()["request_id"]
    assert (
        await client.post(
            f"/api/friends/requests/{request_id}/accept",
            headers=auth_headers(recipient),
        )
    ).status_code == 200

    removed = await client.delete(f"/api/friends/{recipient.id}", headers=auth_headers(sender))

    assert removed.status_code == 200
    assert removed.json() == {"removed": True}
    async with SessionLocal() as session:
        request = await session.get(FriendRequest, request_id)
        friendship = await session.scalar(
            select(Friendship).where(
                Friendship.user_a_id == min(sender.id, recipient.id),
                Friendship.user_b_id == max(sender.id, recipient.id),
            )
        )
    assert request is not None and request.status == "ACCEPTED"
    assert friendship is None


async def test_search_reports_each_relation(client, friend_users) -> None:
    current, friend, outgoing, incoming, unrelated = friend_users
    friendship_request = await send_request(client, current, friend)
    assert (
        await client.post(
            f"/api/friends/requests/{friendship_request.json()['request_id']}/accept",
            headers=auth_headers(friend),
        )
    ).status_code == 200
    assert (await send_request(client, current, outgoing)).status_code == 200
    assert (await send_request(client, incoming, current)).status_code == 200

    response = await client.get(
        "/api/users/search",
        params={"q": current.username[:-1]},
        headers=auth_headers(current),
    )

    assert response.status_code == 200
    relations = {user["id"]: user["relation"] for user in response.json()}
    assert relations == {
        friend.id: "friends",
        outgoing.id: "outgoing_pending",
        incoming.id: "incoming_pending",
        unrelated.id: "none",
    }
