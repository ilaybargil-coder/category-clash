import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from .auth import decode_token
from .config import settings
from .game.manager import room_manager
from .game.validator import AnswerStatus
from .protocol import PingCommand, SubmitAnswerCommand, make_server_event, parse_client_command

logger = logging.getLogger(__name__)

router = APIRouter()

WS_UNAUTHORIZED = 4401
WS_ORIGIN_FORBIDDEN = 4403
WS_ROOM_NOT_FOUND = 4404
WS_ROOM_FULL = 4409

# Attribute set on each socket so we can tell whether a user still has
# another open tab before marking them disconnected.
_USER_ATTR = "_game_user_id"


def websocket_origin_allowed(origin: str | None) -> bool:
    if origin is None:
        return settings.websocket_allow_missing_origin
    normalized = origin.rstrip("/")
    allowed = settings.websocket_origin_list
    return "*" in allowed or normalized in allowed


@router.websocket("/ws/rooms/{code}")
async def room_websocket(ws: WebSocket, code: str, token: str = Query(...)):
    # Accept first so protocol close codes reach the browser. Closing during
    # the HTTP upgrade is translated by ASGI/Uvicorn to a generic HTTP 403,
    # which clients cannot distinguish from a transient network failure.
    await ws.accept()

    if not websocket_origin_allowed(ws.headers.get("origin")):
        await ws.close(code=WS_ORIGIN_FORBIDDEN)
        return

    user = decode_token(token)
    if user is None:
        await ws.close(code=WS_UNAUTHORIZED)
        return

    code = code.upper()
    room = room_manager.get(code)
    if room is None:
        await ws.close(code=WS_ROOM_NOT_FOUND)
        return

    joined = await room.join(user.id, user.username, user.display_name)
    if not joined:
        await ws.close(code=WS_ROOM_FULL)
        return

    setattr(ws, _USER_ATTR, user.id)
    room_manager.register(code, ws)

    try:
        await room_manager.send(ws, room.snapshot(user.id))
        while True:
            try:
                message = await ws.receive_json()
            except ValueError:
                await room_manager.send(
                    ws,
                    make_server_event(
                        "error",
                        seq=room.event_sequence,
                        match_id=room.code,
                        code="BAD_JSON",
                    ),
                )
                continue

            try:
                command = parse_client_command(message)
            except ValueError:
                await room_manager.send(
                    ws,
                    make_server_event(
                        "error",
                        seq=room.event_sequence,
                        match_id=room.code,
                        code="INVALID_COMMAND",
                    ),
                )
                continue

            if isinstance(command, SubmitAnswerCommand):
                command_id = str(command.client_command_id)
                status = await room.submit_answer(
                    user.id,
                    command.text,
                    client_command_id=command_id,
                )
                # Protocol-level rejections are acked only to the sender;
                # real attempts were already broadcast by the engine.
                if status in {
                    AnswerStatus.NOT_YOUR_TURN,
                    AnswerStatus.ROUND_FINISHED,
                    AnswerStatus.TIME_EXPIRED,
                }:
                    await room_manager.send(
                        ws,
                        make_server_event(
                            "action_rejected",
                            seq=room.event_sequence,
                            match_id=room.code,
                            status=status.value,
                            client_command_id=command_id,
                        ),
                    )
            elif isinstance(command, PingCommand):
                await room_manager.send(
                    ws,
                    make_server_event(
                        "pong",
                        seq=room.event_sequence,
                        match_id=room.code,
                    ),
                )
    except WebSocketDisconnect:
        pass
    finally:
        room_manager.unregister(code, ws)
        has_other_socket = any(
            getattr(other, _USER_ATTR, None) == user.id for other in room_manager.sockets_for(code)
        )
        if not has_other_socket:
            await room.disconnect(user.id)
        room_manager.remove_if_unused(code)
