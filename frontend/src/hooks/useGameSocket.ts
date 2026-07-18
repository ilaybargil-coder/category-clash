"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { WS_URL, getToken } from "@/lib/api";
import { applyServerEvent, type ServerEvent } from "@/lib/gameReducer";
import type {
  ClientCommand,
  PingCommand,
  RequestRematchCommand,
  SubmitAnswerCommand,
} from "@/lib/protocol.generated";
import type { GameState } from "@/lib/types";

export type ConnectionStatus =
  | "connecting"
  | "open"
  | "closed"
  | "room_not_found"
  | "room_full"
  | "origin_rejected"
  | "unauthorized";

const RECONNECT_BASE_DELAY_MS = 500;
const RECONNECT_MAX_DELAY_MS = 10_000;
export const HEARTBEAT_INTERVAL_MS = 25_000;
export const HEARTBEAT_TIMEOUT_MS = 75_000;
const TERMINAL_CLOSE_CODES = new Set([4401, 4403, 4404, 4409]);

type PendingAnswerCommand = SubmitAnswerCommand;

export function reconnectDelayMs(attempt: number, random = Math.random): number {
  const capped = Math.min(
    RECONNECT_MAX_DELAY_MS,
    RECONNECT_BASE_DELAY_MS * 2 ** Math.max(0, attempt)
  );
  return Math.round(capped * (0.75 + random() * 0.5));
}

export function useGameSocket(code: string) {
  const [state, setState] = useState<GameState | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>(() =>
    getToken() ? "connecting" : "unauthorized"
  );
  const [rejection, setRejection] = useState<string | null>(null);
  const [stateSyncRevision, setStateSyncRevision] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const pendingAnswerRef = useRef<PendingAnswerCommand | null>(null);

  useEffect(() => {
    if (!getToken()) return;

    // Lifecycle state is LOCAL to this effect run. Under React Strict Mode
    // the effect runs twice; each run owns exactly one connection chain and
    // its cleanup kills that chain completely — including any reconnect
    // timer scheduled AFTER cleanup by a late onclose (the `disposed` flag
    // is checked before every reconnect, so a dead effect can never spawn a
    // zombie socket).
    let disposed = false;
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
    let reconnectAttempt = 0;
    let lastPongAt = Date.now();

    const stopHeartbeat = () => {
      if (heartbeatTimer) clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    };

    const connect = () => {
      if (disposed) return;
      const token = getToken();
      if (!token) {
        setStatus("unauthorized");
        return;
      }
      setStatus("connecting");
      const ws = new WebSocket(
        `${WS_URL}/ws/rooms/${encodeURIComponent(code)}?token=${encodeURIComponent(token)}`
      );
      socket = ws;
      wsRef.current = ws;

      ws.onopen = () => {
        if (!disposed && wsRef.current === ws) {
          reconnectAttempt = 0;
          lastPongAt = Date.now();
          setStatus("open");
          stopHeartbeat();
          heartbeatTimer = setInterval(() => {
            if (disposed || wsRef.current !== ws || ws.readyState !== WebSocket.OPEN) return;
            if (Date.now() - lastPongAt > HEARTBEAT_TIMEOUT_MS) {
              ws.close(4000, "heartbeat timeout");
              return;
            }
            const ping = { type: "ping" } satisfies PingCommand;
            ws.send(JSON.stringify(ping));
          }, HEARTBEAT_INTERVAL_MS);
        }
      };

      ws.onmessage = (msg) => {
        // Ignore frames from a socket that is no longer the active one.
        if (disposed || wsRef.current !== ws) return;
        let event: ServerEvent;
        try {
          event = JSON.parse(msg.data as string) as ServerEvent;
        } catch {
          return;
        }
        if (event.type === "pong") lastPongAt = Date.now();
        const commandId = event.client_command_id;
        if (
          typeof commandId === "string" &&
          pendingAnswerRef.current?.client_command_id === commandId
        ) {
          pendingAnswerRef.current = null;
        }
        if (event.type === "state_sync" && pendingAnswerRef.current) {
          const answers = Array.isArray(event.answers) ? event.answers : [];
          const wasApplied = answers.some(
            (answer) =>
              typeof answer === "object" &&
              answer !== null &&
              "client_command_id" in answer &&
              answer.client_command_id ===
                pendingAnswerRef.current?.client_command_id
          );
          if (wasApplied) {
            pendingAnswerRef.current = null;
          } else {
            ws.send(JSON.stringify(pendingAnswerRef.current));
          }
        }
        if (event.type === "state_sync") {
          setStateSyncRevision((revision) => revision + 1);
        }
        setState((prev) => applyServerEvent(prev, event));
        if (event.type === "action_rejected") {
          setRejection(event.status as string);
        }
      };

      ws.onclose = (ev) => {
        stopHeartbeat();
        if (wsRef.current === ws) wsRef.current = null;
        if (disposed) return;
        if (ev.code === 4404) setStatus("room_not_found");
        else if (ev.code === 4409) setStatus("room_full");
        else if (ev.code === 4403) setStatus("origin_rejected");
        else if (ev.code === 4401) setStatus("unauthorized");
        else if (!TERMINAL_CLOSE_CODES.has(ev.code)) {
          setStatus("closed");
          // Transient drop: reconnect. The server sends a full state_sync on
          // every connect, and the reducer replaces state, so this is safe.
          const delay = reconnectDelayMs(reconnectAttempt);
          reconnectAttempt += 1;
          retryTimer = setTimeout(connect, delay);
        }
      };
    };

    connect();
    return () => {
      disposed = true;
      stopHeartbeat();
      if (retryTimer) clearTimeout(retryTimer);
      if (socket) {
        if (wsRef.current === socket) wsRef.current = null;
        socket.close();
      }
    };
  }, [code]);

  const submitAnswer = useCallback((text: string): boolean => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    const existing = pendingAnswerRef.current;
    if (existing && existing.text !== text) return false;
    const command =
      existing ??
      ({
        type: "submit_answer",
        text,
        client_command_id: crypto.randomUUID(),
      } satisfies PendingAnswerCommand);
    pendingAnswerRef.current = command;
    ws.send(JSON.stringify(command));
    return true;
  }, []);

  const clearRejection = useCallback(() => setRejection(null), []);

  const usePowerup = useCallback((type: "swap_question" | "extend_time" | "use_joker"): boolean => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    const command = { type, client_command_id: crypto.randomUUID() } as ClientCommand;
    ws.send(JSON.stringify(command));
    return true;
  }, []);

  const requestRematch = useCallback((): boolean => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    const command = { type: "request_rematch" } satisfies RequestRematchCommand;
    ws.send(JSON.stringify(command));
    return true;
  }, []);

  return {
    state,
    rematch: state?.rematch ?? null,
    stateSyncRevision,
    status,
    rejection,
    clearRejection,
    submitAnswer,
    usePowerup,
    requestRematch,
  };
}
