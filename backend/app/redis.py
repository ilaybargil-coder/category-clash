"""Shared asynchronous Redis client."""

import asyncio
import fnmatch
import logging
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

import redis.asyncio as redis
from redis.exceptions import (
    ConnectionError,
    RedisError,
)
from redis.exceptions import (
    TimeoutError as RedisTimeoutError,
)

from .config import settings

logger = logging.getLogger(__name__)


class InMemoryRedis:
    """Small in-process Redis replacement for single-worker deployments."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._values: dict[str, tuple[str, float | None]] = {}
        self._lock = asyncio.Lock()

    def _purge_expired(self) -> None:
        now = self._clock()
        expired = [
            key
            for key, (_, expires_at) in self._values.items()
            if expires_at is not None and expires_at <= now
        ]
        for key in expired:
            del self._values[key]

    async def set(
        self, name: str, value: Any, ex: int | float | None = None, nx: bool = False
    ) -> bool | None:
        async with self._lock:
            self._purge_expired()
            if nx and name in self._values:
                return None
            if isinstance(value, bytes):
                stored = value.decode()
            else:
                stored = str(value)
            expires_at = None if ex is None else self._clock() + ex
            self._values[name] = (stored, expires_at)
            return True

    async def get(self, name: str) -> str | None:
        async with self._lock:
            self._purge_expired()
            item = self._values.get(name)
            return None if item is None else item[0]

    async def mget(self, keys: list[str] | tuple[str, ...]) -> list[str | None]:
        async with self._lock:
            self._purge_expired()
            return [
                None if (item := self._values.get(key)) is None else item[0]
                for key in keys
            ]

    async def ttl(self, name: str) -> int:
        async with self._lock:
            self._purge_expired()
            item = self._values.get(name)
            if item is None:
                return -2
            if item[1] is None:
                return -1
            return int(item[1] - self._clock())

    async def getdel(self, name: str) -> str | None:
        async with self._lock:
            self._purge_expired()
            item = self._values.pop(name, None)
            return None if item is None else item[0]

    async def delete(self, *names: str) -> int:
        async with self._lock:
            self._purge_expired()
            deleted = 0
            for name in names:
                if name in self._values:
                    del self._values[name]
                    deleted += 1
            return deleted

    async def scan_iter(self, match: str | None = None) -> AsyncIterator[str]:
        async with self._lock:
            self._purge_expired()
            keys = [
                key
                for key in self._values
                if match is None or fnmatch.fnmatchcase(key, match)
            ]
        for key in keys:
            yield key

    async def aclose(self) -> None:
        pass


_redis: redis.Redis | InMemoryRedis | None = None


async def get_redis() -> redis.Redis | InMemoryRedis:
    global _redis
    if _redis is None:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        try:
            await asyncio.wait_for(client.ping(), timeout=1.0)
        except (ConnectionError, RedisTimeoutError, RedisError, asyncio.TimeoutError):
            logger.warning(
                "Redis unavailable at %s; falling back to in-process store "
                "(single-worker only)",
                settings.redis_url,
            )
            try:
                await client.aclose()
            except Exception:
                pass
            _redis = InMemoryRedis()
        else:
            _redis = client
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
