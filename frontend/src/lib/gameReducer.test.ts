import { describe, expect, it } from "vitest";
import { applyServerEvent, type ServerEvent } from "./gameReducer";
import type { GameState } from "./types";

const NOW = 1_800_000_000_000;

function syncEvent(overrides: Record<string, unknown> = {}): ServerEvent {
  return {
    type: "state_sync",
    event_id: "event-sync",
    protocol_version: 1,
    seq: 1,
    server_now_ms: NOW,
    you: 1,
    code: "TEST1",
    phase: "ROUND_ACTIVE",
    players: [
      { user_id: 1, username: "dana", display_name: "דנה", connected: true },
      { user_id: 2, username: "omer", display_name: "עומר", connected: true },
    ],
    score: [
      { user_id: 1, points: 0 },
      { user_id: 2, points: 0 },
    ],
    round_no: 1,
    rounds_to_win: 2,
    question: { id: 1, text: "כתבו שמות של כלי נגינה" },
    turn_user_id: 1,
    turn_seconds: 15,
    deadline_epoch_ms: NOW + 15000,
    answers: [],
    last_round_result: null,
    match_winner_id: null,
    match_end_reason: null,
    ...overrides,
  };
}

function answerEvent(
  submissionId: string,
  overrides: Record<string, unknown> = {}
): ServerEvent {
  return {
    type: "answer_result",
    event_id: `event-${submissionId}`,
    protocol_version: 1,
    seq: 2,
    server_now_ms: NOW + 1000,
    submission_id: submissionId,
    client_command_id: "00000000-0000-4000-8000-000000000001",
    user_id: 1,
    raw_text: "כינור",
    status: "VALID",
    canonical: "כינור",
    at_ms: NOW + 1000,
    turn_user_id: 2,
    deadline_epoch_ms: NOW + 16000,
    ...overrides,
  };
}

function initialState(): GameState {
  return applyServerEvent(null, syncEvent()) as GameState;
}

describe("applyServerEvent — answer idempotency", () => {
  it("one answer_result renders exactly one bubble", () => {
    const state = applyServerEvent(initialState(), answerEvent("sub-1"));
    expect(state?.answers).toHaveLength(1);
    expect(state?.answers[0].raw_text).toBe("כינור");
  });

  it("the same answer_result delivered twice (duplicate socket / replay) renders once", () => {
    let state = applyServerEvent(initialState(), answerEvent("sub-1"));
    state = applyServerEvent(state, answerEvent("sub-1"));
    expect(state?.answers).toHaveLength(1);
  });

  it("a replayed event with the same seq cannot overwrite newer local state", () => {
    let state = applyServerEvent(initialState(), answerEvent("sub-1"));
    state = applyServerEvent(
      state,
      answerEvent("sub-1", { turn_user_id: 2, deadline_epoch_ms: NOW + 20000 })
    );
    expect(state?.answers).toHaveLength(1);
    expect(state?.turn_user_id).toBe(2);
    expect(state?.deadline_epoch_ms).toBe(NOW + 16000);
  });

  it("two different submissions of the same text are two bubbles", () => {
    let state = applyServerEvent(initialState(), answerEvent("sub-1"));
    state = applyServerEvent(
      state,
      answerEvent("sub-2", { seq: 3, status: "DUPLICATE", user_id: 2 })
    );
    expect(state?.answers).toHaveLength(2);
  });
});

describe("applyServerEvent — state_sync replaces, never accumulates", () => {
  it("state_sync AFTER an already-applied event does not duplicate the answer", () => {
    // Client got the live event first, then reconnects and receives a
    // snapshot that already contains the same answer.
    let state = applyServerEvent(initialState(), answerEvent("sub-1"));
    const snapshotWithAnswer = syncEvent({
      seq: 2,
      answers: [
        {
          submission_id: "sub-1",
          user_id: 1,
          raw_text: "כינור",
          status: "VALID",
          canonical: "כינור",
          at_ms: NOW + 1000,
        },
      ],
    });
    state = applyServerEvent(state, snapshotWithAnswer);
    expect(state?.answers).toHaveLength(1);
  });

  it("repeated state_sync (remount/reconnect) is idempotent", () => {
    let state = applyServerEvent(null, syncEvent());
    state = applyServerEvent(state, answerEvent("sub-1"));
    state = applyServerEvent(state, syncEvent({ seq: 2, answers: state!.answers }));
    state = applyServerEvent(state, syncEvent({ seq: 2, answers: state!.answers }));
    expect(state?.answers).toHaveLength(1);
  });

  it("an event already reflected in a later snapshot is not re-appended after it", () => {
    // Race: snapshot (containing sub-1) arrives, then the original live
    // event for sub-1 arrives late from the old socket.
    let state = applyServerEvent(
      null,
      syncEvent({
        seq: 2,
        answers: [
          {
            submission_id: "sub-1",
            user_id: 1,
            raw_text: "כינור",
            status: "VALID",
            canonical: "כינור",
            at_ms: NOW + 1000,
          },
        ],
      })
    );
    state = applyServerEvent(state, answerEvent("sub-1"));
    expect(state?.answers).toHaveLength(1);
  });

  it("a stale state_sync cannot roll state backwards", () => {
    let state = applyServerEvent(initialState(), answerEvent("sub-1"));
    state = applyServerEvent(state, syncEvent({ seq: 1, answers: [] }));
    expect(state?.seq).toBe(2);
    expect(state?.answers).toHaveLength(1);
  });

  it("a snapshot defensively removes duplicate submission ids", () => {
    const answer = {
      submission_id: "sub-1",
      client_command_id: null,
      user_id: 1,
      raw_text: "כינור",
      status: "VALID",
      canonical: "כינור",
      at_ms: NOW,
    };
    const state = applyServerEvent(
      null,
      syncEvent({ answers: [answer, { ...answer }] })
    );
    expect(state?.answers).toHaveLength(1);
  });
});

describe("applyServerEvent — round lifecycle", () => {
  it("round_started clears the answer feed", () => {
    let state = applyServerEvent(initialState(), answerEvent("sub-1"));
    state = applyServerEvent(state, {
      type: "round_started",
      seq: 3,
      server_now_ms: NOW + 2000,
      round_no: 2,
      question: { id: 2, text: "שאלה חדשה" },
      starter_user_id: 2,
      preview_seconds: 4,
      score: [
        { user_id: 1, points: 1 },
        { user_id: 2, points: 0 },
      ],
    });
    expect(state?.answers).toHaveLength(0);
    expect(state?.round_no).toBe(2);
    expect(state?.phase).toBe("QUESTION_PREVIEW");
  });

  it("events before any state_sync are ignored (no crash, no phantom state)", () => {
    const state = applyServerEvent(null, answerEvent("sub-1"));
    expect(state).toBeNull();
  });
});
