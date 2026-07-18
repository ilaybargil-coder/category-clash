import type { AnswerItem, GameState, ScoreEntry } from "./types";
import type { ServerEventEnvelope } from "./protocol.generated";

export interface ServerEvent extends Partial<ServerEventEnvelope> {
  type: string;
  event_id?: string;
  protocol_version?: number;
  seq?: number;
  server_now_ms?: number;
  [key: string]: unknown;
}

/**
 * Pure reducer: (previous state, server event) -> next state.
 *
 * Idempotency guarantees:
 * - `state_sync` REPLACES local state wholesale (never merges/accumulates).
 * - `answer_result` is keyed by the server's `submission_id`; an event that
 *   was already applied (duplicate socket, replay, reconnect race) is a
 *   no-op for the answer list.
 */
export function applyServerEvent(
  prev: GameState | null,
  event: ServerEvent
): GameState | null {
  const offset =
    typeof event.server_now_ms === "number"
      ? event.server_now_ms - Date.now()
      : undefined;

  if (event.type === "state_sync") {
    if (prev && typeof event.seq === "number" && event.seq < prev.seq) {
      return prev;
    }
    const snap = event as unknown as GameState & ServerEvent;
    const seen = new Set<string>();
    const answers = (snap.answers ?? []).filter((answer) => {
      if (!answer.submission_id || seen.has(answer.submission_id)) return false;
      seen.add(answer.submission_id);
      return true;
    });
    return {
      ...snap,
      seq: typeof event.seq === "number" ? event.seq : 0,
      event_id: event.event_id ?? "",
      protocol_version: event.protocol_version ?? 0,
      answers,
      clock_offset_ms: offset ?? 0,
    };
  }
  if (!prev) return prev;
  if (typeof event.seq === "number" && event.seq <= prev.seq) return prev;

  const next: GameState = {
    ...prev,
    seq: typeof event.seq === "number" ? event.seq : prev.seq,
    event_id: event.event_id ?? prev.event_id,
    protocol_version: event.protocol_version ?? prev.protocol_version,
    clock_offset_ms: offset ?? prev.clock_offset_ms,
  };

  switch (event.type) {
    case "player_joined":
    case "player_left":
    case "player_disconnected":
    case "player_reconnected":
      next.players = event.players as GameState["players"];
      break;
    case "round_started":
      next.phase = "QUESTION_PREVIEW";
      next.round_no = event.round_no as number;
      next.question = event.question as GameState["question"];
      next.turn_user_id = event.starter_user_id as number;
      next.score = event.score as ScoreEntry[];
      next.answers = [];
      next.deadline_epoch_ms = null;
      next.last_round_result = null;
      next.match_winner_id = (event.match_winner_id as number | null) ?? null;
      next.match_end_reason = (event.match_end_reason as string | null) ?? null;
      next.powerups = event.powerups as GameState["powerups"];
      next.rematch = event.rematch as GameState["rematch"];
      break;
    case "round_active":
      next.phase = "ROUND_ACTIVE";
      next.turn_user_id = event.turn_user_id as number;
      next.turn_seconds = event.turn_seconds as number;
      next.deadline_epoch_ms = event.deadline_epoch_ms as number;
      break;
    case "answer_result": {
      // Turn/deadline reflect the latest server truth even on a replay.
      next.turn_user_id = event.turn_user_id as number;
      next.deadline_epoch_ms = event.deadline_epoch_ms as number | null;

      const item: AnswerItem = {
        submission_id: event.submission_id as string,
        client_command_id: (event.client_command_id as string) ?? null,
        user_id: event.user_id as number,
        raw_text: event.raw_text as string,
        status: event.status as AnswerItem["status"],
        canonical: (event.canonical as string) ?? null,
        at_ms: event.at_ms as number,
      };
      const alreadyApplied = prev.answers.some(
        (a) => a.submission_id === item.submission_id
      );
      if (!alreadyApplied) {
        next.answers = [...prev.answers, item];
      }
      break;
    }
    case "powerup_used":
      next.powerups = event.powerups as GameState["powerups"];
      next.question = event.question as GameState["question"];
      next.phase = event.phase as GameState["phase"];
      next.turn_user_id = event.turn_user_id as number;
      next.deadline_epoch_ms = event.deadline_epoch_ms as number | null;
      break;
    case "round_finished":
      next.phase = "ROUND_FINISHED";
      next.score = event.score as ScoreEntry[];
      next.deadline_epoch_ms = null;
      next.last_round_result = {
        round_no: event.round_no as number,
        winner_user_id: event.winner_user_id as number,
        loser_user_id: event.loser_user_id as number,
        reason: event.reason as string,
        score: event.score as ScoreEntry[],
      };
      break;
    case "match_finished":
      next.phase = "MATCH_FINISHED";
      next.match_winner_id = event.winner_user_id as number;
      next.match_end_reason = event.reason as string;
      next.score = event.score as ScoreEntry[];
      next.deadline_epoch_ms = null;
      next.rematch = event.rematch as GameState["rematch"];
      break;
    case "rematch_updated":
      next.rematch = event.rematch as GameState["rematch"];
      break;
    case "room_error":
      next.phase = "ABANDONED";
      break;
    default:
      break;
  }
  return next;
}
