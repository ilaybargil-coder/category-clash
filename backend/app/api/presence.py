from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import TokenUser, get_current_user
from ..config import settings
from ..db import get_session
from ..redis import get_redis
from .friends import get_friend_ids

router = APIRouter(prefix="/api")


class PresenceOut(BaseModel):
    online_friend_ids: list[int]


@router.post("/presence/heartbeat", response_model=PresenceOut)
async def presence_heartbeat(
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PresenceOut:
    client = await get_redis()
    try:
        await client.set(
            f"presence:{current.id}",
            "1",
            ex=settings.presence_ttl_seconds,
        )
        friend_ids = await get_friend_ids(session, current.id)
        if not friend_ids:
            return PresenceOut(online_friend_ids=[])
        values = await client.mget([f"presence:{friend_id}" for friend_id in friend_ids])
    except RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail="Presence service is unavailable",
        ) from exc

    return PresenceOut(
        online_friend_ids=[
            friend_id
            for friend_id, value in zip(friend_ids, values, strict=True)
            if value is not None
        ]
    )
