from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import TokenUser, get_current_user
from ..db import get_session
from ..models import FriendRequest, Friendship, User

router = APIRouter(prefix="/api")


class FriendUserOut(BaseModel):
    id: int
    username: str
    display_name: str


class UserSearchOut(FriendUserOut):
    wins: int
    losses: int
    relation: Literal["none", "friends", "outgoing_pending", "incoming_pending"]


class CreateFriendRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)


class PendingRequestResult(BaseModel):
    status: Literal["PENDING"] = "PENDING"
    request_id: int


class FriendshipResult(BaseModel):
    status: Literal["FRIENDS"] = "FRIENDS"
    friendship_id: int
    friend: FriendUserOut
    friends_since: datetime


class FriendRequestOut(BaseModel):
    id: int
    user: FriendUserOut
    created_at: datetime


class FriendRequestsOut(BaseModel):
    incoming: list[FriendRequestOut]
    outgoing: list[FriendRequestOut]


class RequestStatusOut(BaseModel):
    id: int
    status: Literal["DECLINED"]
    responded_at: datetime


class FriendOut(FriendUserOut):
    wins: int
    losses: int
    friends_since: datetime


class RemovedFriendshipOut(BaseModel):
    removed: bool = True


def friend_user_out(user: User) -> FriendUserOut:
    return FriendUserOut(id=user.id, username=user.username, display_name=user.display_name)


def friendship_result(friendship: Friendship, friend: User) -> FriendshipResult:
    return FriendshipResult(
        friendship_id=friendship.id,
        friend=friend_user_out(friend),
        friends_since=friendship.created_at,
    )


def normalized_pair(first_id: int, second_id: int) -> tuple[int, int]:
    return min(first_id, second_id), max(first_id, second_id)


async def find_friendship(
    session: AsyncSession, first_id: int, second_id: int
) -> Friendship | None:
    user_a_id, user_b_id = normalized_pair(first_id, second_id)
    return (
        await session.execute(
            select(Friendship).where(
                Friendship.user_a_id == user_a_id,
                Friendship.user_b_id == user_b_id,
            )
        )
    ).scalar_one_or_none()


async def get_friend_ids(session: AsyncSession, user_id: int) -> list[int]:
    rows = (
        (
            await session.execute(
                select(Friendship).where(
                    or_(
                        Friendship.user_a_id == user_id,
                        Friendship.user_b_id == user_id,
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    return [row.user_b_id if row.user_a_id == user_id else row.user_a_id for row in rows]


async def get_or_create_friendship(
    session: AsyncSession, first_id: int, second_id: int
) -> Friendship:
    existing = await find_friendship(session, first_id, second_id)
    if existing is not None:
        return existing

    user_a_id, user_b_id = normalized_pair(first_id, second_id)
    friendship = Friendship(user_a_id=user_a_id, user_b_id=user_b_id)
    try:
        async with session.begin_nested():
            session.add(friendship)
            await session.flush()
    except IntegrityError:
        existing = await find_friendship(session, first_id, second_id)
        if existing is None:
            raise
        return existing
    return friendship


@router.get("/users/search", response_model=list[UserSearchOut])
async def search_users(
    q: Annotated[str, Query(min_length=2)],
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(
            status_code=422, detail="Search query must contain at least 2 characters"
        )
    escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    users = (
        (
            await session.execute(
                select(User)
                .where(
                    User.id != current.id,
                    User.username.ilike(f"{escaped_query}%", escape="\\"),
                )
                .order_by(User.username)
                .limit(10)
            )
        )
        .scalars()
        .all()
    )
    if not users:
        return []

    result_ids = {user.id for user in users}
    friend_ids = set(await get_friend_ids(session, current.id)) & result_ids
    pending_rows = (
        (
            await session.execute(
                select(FriendRequest).where(
                    FriendRequest.status == "PENDING",
                    or_(
                        FriendRequest.sender_id == current.id,
                        FriendRequest.recipient_id == current.id,
                    ),
                )
            )
        )
        .scalars()
        .all()
    )
    outgoing_ids = {
        row.recipient_id for row in pending_rows if row.sender_id == current.id
    } & result_ids
    incoming_ids = {
        row.sender_id for row in pending_rows if row.recipient_id == current.id
    } & result_ids

    results = []
    for user in users:
        relation: Literal["none", "friends", "outgoing_pending", "incoming_pending"] = "none"
        if user.id in friend_ids:
            relation = "friends"
        elif user.id in outgoing_ids:
            relation = "outgoing_pending"
        elif user.id in incoming_ids:
            relation = "incoming_pending"
        results.append(
            UserSearchOut(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                wins=user.wins,
                losses=user.losses,
                relation=relation,
            )
        )
    return results


@router.post(
    "/friends/requests",
    response_model=PendingRequestResult | FriendshipResult,
)
async def create_friend_request(
    body: CreateFriendRequest,
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        target = (
            await session.execute(
                select(User).where(func.lower(User.username) == body.username.strip().lower())
            )
        ).scalar_one_or_none()
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")
        if target.id == current.id:
            raise HTTPException(status_code=409, detail="Cannot add yourself as a friend")
        if await find_friendship(session, current.id, target.id) is not None:
            raise HTTPException(status_code=409, detail="Already friends")

        outgoing = (
            await session.execute(
                select(FriendRequest).where(
                    FriendRequest.sender_id == current.id,
                    FriendRequest.recipient_id == target.id,
                    FriendRequest.status == "PENDING",
                )
            )
        ).scalar_one_or_none()
        if outgoing is not None:
            raise HTTPException(status_code=409, detail="Friend request already pending")

        reverse = (
            await session.execute(
                select(FriendRequest).where(
                    FriendRequest.sender_id == target.id,
                    FriendRequest.recipient_id == current.id,
                    FriendRequest.status == "PENDING",
                )
            )
        ).scalar_one_or_none()
        if reverse is not None:
            reverse.status = "ACCEPTED"
            reverse.responded_at = datetime.now(timezone.utc)
            friendship = await get_or_create_friendship(session, current.id, target.id)
            result: PendingRequestResult | FriendshipResult = friendship_result(friendship, target)
        else:
            request = FriendRequest(sender_id=current.id, recipient_id=target.id)
            session.add(request)
            await session.flush()
            result = PendingRequestResult(request_id=request.id)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return result


@router.get("/friends/requests", response_model=FriendRequestsOut)
async def list_friend_requests(
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    incoming_rows = (
        await session.execute(
            select(FriendRequest, User)
            .join(User, User.id == FriendRequest.sender_id)
            .where(
                FriendRequest.recipient_id == current.id,
                FriendRequest.status == "PENDING",
            )
            .order_by(FriendRequest.created_at.desc())
        )
    ).all()
    outgoing_rows = (
        await session.execute(
            select(FriendRequest, User)
            .join(User, User.id == FriendRequest.recipient_id)
            .where(
                FriendRequest.sender_id == current.id,
                FriendRequest.status == "PENDING",
            )
            .order_by(FriendRequest.created_at.desc())
        )
    ).all()
    return FriendRequestsOut(
        incoming=[
            FriendRequestOut(
                id=request.id, user=friend_user_out(user), created_at=request.created_at
            )
            for request, user in incoming_rows
        ],
        outgoing=[
            FriendRequestOut(
                id=request.id, user=friend_user_out(user), created_at=request.created_at
            )
            for request, user in outgoing_rows
        ],
    )


@router.post("/friends/requests/{request_id}/accept", response_model=FriendshipResult)
async def accept_friend_request(
    request_id: int,
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        request = (
            await session.execute(
                select(FriendRequest).where(
                    FriendRequest.id == request_id,
                    FriendRequest.recipient_id == current.id,
                    FriendRequest.status == "PENDING",
                )
            )
        ).scalar_one_or_none()
        if request is None:
            raise HTTPException(status_code=404, detail="Pending friend request not found")
        sender = await session.get(User, request.sender_id)
        if sender is None:
            raise HTTPException(status_code=404, detail="Request sender not found")
        request.status = "ACCEPTED"
        request.responded_at = datetime.now(timezone.utc)
        friendship = await get_or_create_friendship(session, current.id, request.sender_id)
        result = friendship_result(friendship, sender)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return result


@router.post("/friends/requests/{request_id}/decline", response_model=RequestStatusOut)
async def decline_friend_request(
    request_id: int,
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        request = (
            await session.execute(
                select(FriendRequest).where(
                    FriendRequest.id == request_id,
                    FriendRequest.recipient_id == current.id,
                    FriendRequest.status == "PENDING",
                )
            )
        ).scalar_one_or_none()
        if request is None:
            raise HTTPException(status_code=404, detail="Pending friend request not found")
        request.status = "DECLINED"
        request.responded_at = datetime.now(timezone.utc)
        result = RequestStatusOut(
            id=request.id,
            status="DECLINED",
            responded_at=request.responded_at,
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return result


@router.get("/friends", response_model=list[FriendOut])
async def list_friends(
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        (
            await session.execute(
                select(Friendship)
                .where(
                    or_(
                        Friendship.user_a_id == current.id,
                        Friendship.user_b_id == current.id,
                    )
                )
                .order_by(Friendship.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return []
    friend_ids = [row.user_b_id if row.user_a_id == current.id else row.user_a_id for row in rows]
    users = (await session.execute(select(User).where(User.id.in_(friend_ids)))).scalars().all()
    users_by_id = {user.id: user for user in users}
    return [
        FriendOut(
            id=friend_id,
            username=users_by_id[friend_id].username,
            display_name=users_by_id[friend_id].display_name,
            wins=users_by_id[friend_id].wins,
            losses=users_by_id[friend_id].losses,
            friends_since=row.created_at,
        )
        for row, friend_id in zip(rows, friend_ids, strict=True)
        if friend_id in users_by_id
    ]


@router.delete("/friends/{user_id}", response_model=RemovedFriendshipOut)
async def remove_friend(
    user_id: int,
    current: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        friendship = await find_friendship(session, current.id, user_id)
        if friendship is None:
            raise HTTPException(status_code=404, detail="Friendship not found")
        await session.delete(friendship)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return RemovedFriendshipOut()
