import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.auth import create_access_token
from app.game.manager import room_manager
from app.main import app
from app.protocol import (
    PingCommand,
    RequestRematchCommand,
    SubmitAnswerCommand,
    parse_client_command,
)
from app.protocol_codegen import OUTPUT_PATH, generate_types


def token_for(user_id: int = 1) -> str:
    return create_access_token(user_id, f"user{user_id}", f"User {user_id}")


def test_submit_answer_command_requires_uuid_and_bounded_text():
    command = parse_client_command(
        {
            "type": "submit_answer",
            "client_command_id": "00000000-0000-4000-8000-000000000001",
            "text": "מנגו",
        }
    )
    assert isinstance(command, SubmitAnswerCommand)
    assert command.text == "מנגו"

    with pytest.raises(ValueError):
        parse_client_command(
            {
                "type": "submit_answer",
                "client_command_id": {"not": "hashable"},
                "text": "מנגו",
            }
        )


def test_ping_rejects_unknown_fields():
    assert isinstance(parse_client_command({"type": "ping"}), PingCommand)
    with pytest.raises(ValueError):
        parse_client_command({"type": "ping", "unexpected": True})


def test_request_rematch_rejects_unknown_fields():
    assert isinstance(parse_client_command({"type": "request_rematch"}), RequestRematchCommand)
    with pytest.raises(ValueError):
        parse_client_command({"type": "request_rematch", "unexpected": True})


def test_generated_types_match_pydantic_protocol():
    assert OUTPUT_PATH.read_text(encoding="utf-8") == generate_types()


def test_room_not_found_close_code_reaches_client_without_reconnect_ambiguity():
    client = TestClient(app)
    with client.websocket_connect(f"/ws/rooms/NOPE1?token={token_for()}") as websocket:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_json()
    assert exc_info.value.code == 4404


def test_invalid_token_close_code_reaches_client():
    client = TestClient(app)
    with client.websocket_connect("/ws/rooms/NOPE1?token=invalid") as websocket:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_json()
    assert exc_info.value.code == 4401


def test_malformed_command_returns_versioned_error_and_socket_stays_open():
    client = TestClient(app)
    room = room_manager.create_room()
    try:
        with client.websocket_connect(f"/ws/rooms/{room.code}?token={token_for()}") as websocket:
            snapshot = websocket.receive_json()
            assert snapshot["type"] == "state_sync"

            websocket.send_json(
                {
                    "type": "submit_answer",
                    "client_command_id": "not-a-uuid",
                    "text": "מנגו",
                }
            )
            error = websocket.receive_json()
            assert error["type"] == "error"
            assert error["code"] == "INVALID_COMMAND"
            assert error["protocol_version"] == 1

            websocket.send_json({"type": "ping"})
            assert websocket.receive_json()["type"] == "pong"
    finally:
        room_manager.rooms.pop(room.code, None)
