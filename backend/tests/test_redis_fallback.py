from unittest.mock import AsyncMock

import pytest
from redis.exceptions import ConnectionError

import app.redis as redis_module
from app.redis import InMemoryRedis, close_redis, get_redis


@pytest.fixture(autouse=True)
async def reset_cached_client():
    redis_module._redis = None
    yield
    await close_redis()


async def test_round_trips() -> None:
    client = InMemoryRedis()

    assert await client.set("one", "1") is True
    assert await client.set("two", b"2") is True
    assert await client.get("one") == "1"
    assert await client.mget(["one", "missing", "two"]) == ["1", None, "2"]
    assert await client.getdel("one") == "1"
    assert await client.get("one") is None
    assert await client.delete("two", "missing") == 1
    assert await client.get("two") is None


async def test_set_nx_blocks_existing_key() -> None:
    client = InMemoryRedis()

    assert await client.set("key", "first", nx=True) is True
    assert await client.set("key", "second", nx=True) is None
    assert await client.get("key") == "first"


async def test_expiry_uses_injected_clock() -> None:
    now = [100.0]
    client = InMemoryRedis(clock=lambda: now[0])

    await client.set("key", "value", ex=5)
    now[0] = 105.01

    assert await client.get("key") is None
    assert await client.ttl("key") == -2


async def test_ttl_reports_remaining_whole_seconds() -> None:
    now = [10.0]
    client = InMemoryRedis(clock=lambda: now[0])

    await client.set("expiring", "value", ex=10)
    await client.set("persistent", "value")
    now[0] = 13.2

    assert await client.ttl("expiring") == 6
    assert await client.ttl("persistent") == -1
    assert await client.ttl("missing") == -2


async def test_scan_iter_matches_pattern_and_purges_expired_keys() -> None:
    now = [0.0]
    client = InMemoryRedis(clock=lambda: now[0])
    await client.set("invite:one", "1")
    await client.set("invite:expired", "2", ex=1)
    await client.set("presence:one", "3")
    now[0] = 2.0

    keys = [key async for key in client.scan_iter(match="invite:*")]

    assert keys == ["invite:one"]


async def test_get_redis_falls_back_when_ping_fails(monkeypatch) -> None:
    failed_client = AsyncMock()
    failed_client.ping.side_effect = ConnectionError("unavailable")
    from_url = lambda *args, **kwargs: failed_client
    monkeypatch.setattr(redis_module.redis, "from_url", from_url)

    client = await get_redis()

    assert isinstance(client, InMemoryRedis)
    assert await get_redis() is client
    failed_client.aclose.assert_awaited_once()


async def test_get_redis_returns_real_client_when_ping_succeeds(monkeypatch) -> None:
    real_client = AsyncMock()
    real_client.ping.return_value = True
    from_url = lambda *args, **kwargs: real_client
    monkeypatch.setattr(redis_module.redis, "from_url", from_url)

    client = await get_redis()

    assert client is real_client
    assert await get_redis() is real_client
    real_client.ping.assert_awaited_once()
