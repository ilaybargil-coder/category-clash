"""Versioned WebSocket protocol helpers and validated client commands."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .config import settings

PROTOCOL_VERSION = 1


class SubmitAnswerCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["submit_answer"]
    client_command_id: uuid.UUID
    text: str = Field(max_length=settings.max_answer_length)


class PingCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["ping"]


class SwapQuestionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["swap_question"]
    client_command_id: uuid.UUID


class ExtendTimeCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["extend_time"]
    client_command_id: uuid.UUID


class UseJokerCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["use_joker"]
    client_command_id: uuid.UUID


ClientCommand = (
    SubmitAnswerCommand | SwapQuestionCommand | ExtendTimeCommand | UseJokerCommand | PingCommand
)


class ServerEventEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str
    event_type: str
    protocol_version: int
    server_timestamp: str
    server_now_ms: int
    match_id: str
    type: str
    seq: int
    payload: dict[str, object]


def parse_client_command(message: object) -> ClientCommand:
    if not isinstance(message, dict):
        raise ValueError("command must be a JSON object")
    command_type = message.get("type")
    try:
        if command_type == "submit_answer":
            return SubmitAnswerCommand.model_validate(message)
        if command_type == "ping":
            return PingCommand.model_validate(message)
        if command_type == "swap_question":
            return SwapQuestionCommand.model_validate(message)
        if command_type == "extend_time":
            return ExtendTimeCommand.model_validate(message)
        if command_type == "use_joker":
            return UseJokerCommand.model_validate(message)
        raise ValueError("unknown command type")
    except ValidationError as exc:
        raise ValueError("invalid command payload") from exc


def make_server_event(
    event_type: str,
    *,
    seq: int,
    match_id: str,
    **payload: object,
) -> dict[str, object]:
    """Build the additive v1 envelope while retaining flat v0 fields.

    The flat payload keeps the current frontend backward compatible. New
    clients can use the explicit envelope metadata immediately.
    """
    timestamp = datetime.now(timezone.utc)
    event = ServerEventEnvelope(
        event_id=uuid.uuid4().hex,
        event_type=event_type,
        protocol_version=PROTOCOL_VERSION,
        server_timestamp=timestamp.isoformat(),
        server_now_ms=int(timestamp.timestamp() * 1000),
        match_id=match_id,
        type=event_type,
        seq=seq,
        payload=payload,
        **payload,
    )
    return event.model_dump(mode="json")
