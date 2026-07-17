import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from redis.exceptions import RedisError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import TokenUser, get_current_user
from ..config import settings
from ..db import get_session
from ..game.manager import room_manager
from ..models import User
from ..redis import get_redis
from .friends import FriendUserOut, find_friendship, friend_user_out

router = APIRouter(prefix="/api")


class CreateInviteRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)


class CreatedInviteOut(BaseModel):
    room_code: str
    expires_in_seconds: int


class IncomingInviteOut(BaseModel):
    sender: FriendUserOut
    room_code: str
    expires_in_seconds: int


class AcceptedInviteOut(BaseModel):
    room_code: str


class DeclinedInviteOut(BaseModel):
    declined: bool = True


def invite_key(target_id: int, sender_id: int) -> str:
    return f"invite:to:{target_id}:from:{sender_id}"


def redis_unavailable(exc: RedisError) -> HTTPException:
    return HTTPException(status_code=503, detail="Invite service is unavailable")


@router.post("/invites", response_model=CreatedInviteOut)
async def create_invite(
    body: CreateInviteRequest,
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CreatedInviteOut:
    target = (
        await session.execute(
            select(User).where(
                func.lower(User.username) == body.username.strip().lower()
            )
        )
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == current.id:
        raise HTTPException(status_code=409, detail="Cannot invite yourself")
    if await find_friendship(session, current.id, target.id) is None:
        raise HTTPException(status_code=403, detail="Can only invite friends")

    client = await get_redis()
    key = invite_key(target.id, current.id)
    room = room_manager.create_room()
    value = json.dumps({"room_code": room.code, "sender_id": current.id})
    try:
        stored = await client.set(
            key, value, ex=settings.invite_ttl_seconds, nx=True
        )
    except RedisError as exc:
        room_manager.rooms.pop(room.code, None)
        raise redis_unavailable(exc) from exc
    if not stored:
        room_manager.rooms.pop(room.code, None)
        raise HTTPException(status_code=409, detail="Invite already pending")
    return CreatedInviteOut(
        room_code=room.code, expires_in_seconds=settings.invite_ttl_seconds
    )


@router.get("/invites", response_model=list[IncomingInviteOut])
async def list_invites(
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[IncomingInviteOut]:
    client = await get_redis()
    pending: list[tuple[int, str, int]] = []
    try:
        async for key in client.scan_iter(
            match=f"invite:to:{current.id}:from:*"
        ):
            value, ttl = await client.get(key), await client.ttl(key)
            if value is None or ttl <= 0:
                continue
            data = json.loads(value)
            pending.append((int(data["sender_id"]), str(data["room_code"]), ttl))
    except RedisError as exc:
        raise redis_unavailable(exc) from exc

    if not pending:
        return []
    sender_ids = {sender_id for sender_id, _, _ in pending}
    senders = {
        user.id: user
        for user in (
            (await session.execute(select(User).where(User.id.in_(sender_ids))))
            .scalars()
            .all()
        )
    }
    result = [
        IncomingInviteOut(
            sender=friend_user_out(senders[sender_id]),
            room_code=room_code,
            expires_in_seconds=ttl,
        )
        for sender_id, room_code, ttl in pending
        if sender_id in senders
    ]
    return sorted(result, key=lambda invite: invite.expires_in_seconds)


@router.post("/invites/{sender_id}/accept", response_model=AcceptedInviteOut)
async def accept_invite(
    sender_id: int,
    current: TokenUser = Depends(get_current_user),
) -> AcceptedInviteOut:
    client = await get_redis()
    try:
        value = await client.getdel(invite_key(current.id, sender_id))
    except RedisError as exc:
        raise redis_unavailable(exc) from exc
    if value is None:
        raise HTTPException(status_code=410, detail="Invite expired")
    data = json.loads(value)
    return AcceptedInviteOut(room_code=str(data["room_code"]))


@router.post("/invites/{sender_id}/decline", response_model=DeclinedInviteOut)
async def decline_invite(
    sender_id: int,
    current: TokenUser = Depends(get_current_user),
) -> DeclinedInviteOut:
    client = await get_redis()
    try:
        await client.delete(invite_key(current.id, sender_id))
    except RedisError as exc:
        raise redis_unavailable(exc) from exc
    return DeclinedInviteOut()
