// @vitest-environment jsdom

import { createElement, StrictMode, type ReactNode } from "react";
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  HEARTBEAT_INTERVAL_MS,
  HEARTBEAT_TIMEOUT_MS,
  useGameSocket,
} from "./useGameSocket";

class FakeWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: FakeWebSocket[] = [];

  readonly url: string;
  readyState = FakeWebSocket.CONNECTING;
  sent: string[] = [];
  closeCalls = 0;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: ((event: { code: number }) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close(code?: number, reason?: string) {
    void code;
    void reason;
    this.closeCalls += 1;
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.({ code: 1000 });
  }

  open() {
    this.readyState = FakeWebSocket.OPEN;
    this.onopen?.();
  }

  serverClose(code: number) {
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.({ code });
  }

  serverMessage(message: Record<string, unknown>) {
    this.onmessage?.({ data: JSON.stringify(message) });
  }
}

const wrapper = ({ children }: { children: ReactNode }) =>
  createElement(StrictMode, null, children);

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("WebSocket", FakeWebSocket);
  FakeWebSocket.instances = [];
  sessionStorage.setItem("cc_token", "test-token");
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

describe("useGameSocket lifecycle", () => {
  it("Strict Mode remount leaves one live socket and cleanup cannot reconnect", () => {
    const { unmount } = renderHook(() => useGameSocket("ROOM1"), { wrapper });

    const initialSocketCount = FakeWebSocket.instances.length;
    expect(initialSocketCount).toBeGreaterThanOrEqual(1);
    expect(FakeWebSocket.instances.filter((ws) => ws.closeCalls === 0)).toHaveLength(1);

    unmount();
    expect(FakeWebSocket.instances.every((ws) => ws.closeCalls === 1)).toBe(true);

    act(() => vi.advanceTimersByTime(60_000));
    expect(FakeWebSocket.instances).toHaveLength(initialSocketCount);
  });

  it("terminal room-not-found close does not enter a reconnect loop", () => {
    const { result } = renderHook(() => useGameSocket("MISSING"));
    const socket = FakeWebSocket.instances[0];

    act(() => socket.serverClose(4404));
    expect(result.current.status).toBe("room_not_found");
    act(() => vi.advanceTimersByTime(60_000));
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("a transient close reconnects once", () => {
    vi.spyOn(Math, "random").mockReturnValue(0.5);
    renderHook(() => useGameSocket("ROOM1"));
    const socket = FakeWebSocket.instances[0];

    act(() => socket.serverClose(1006));
    act(() => vi.advanceTimersByTime(500));
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("uses a refreshed access token when reconnecting", () => {
    vi.spyOn(Math, "random").mockReturnValue(0.5);
    renderHook(() => useGameSocket("ROOM1"));
    const socket = FakeWebSocket.instances[0];

    sessionStorage.setItem("cc_token", "refreshed-token");
    act(() => socket.serverClose(1006));
    act(() => vi.advanceTimersByTime(500));

    expect(FakeWebSocket.instances[1].url).toContain("token=refreshed-token");
  });

  it("a repeated submit while pending reuses the same command id", () => {
    const { result } = renderHook(() => useGameSocket("ROOM1"));
    const socket = FakeWebSocket.instances[0];
    act(() => socket.open());

    act(() => {
      expect(result.current.submitAnswer("מנגו")).toBe(true);
      expect(result.current.submitAnswer("מנגו")).toBe(true);
    });

    const commands = socket.sent.map((raw) => JSON.parse(raw));
    expect(commands).toHaveLength(2);
    expect(commands[0].client_command_id).toBe(commands[1].client_command_id);
  });

  it("sends a rematch request while connected", () => {
    const { result } = renderHook(() => useGameSocket("ROOM1"));
    const socket = FakeWebSocket.instances[0];
    act(() => socket.open());

    act(() => expect(result.current.requestRematch()).toBe(true));

    expect(socket.sent.map((raw) => JSON.parse(raw))).toContainEqual({
      type: "request_rematch",
    });
  });

  it("sends application heartbeat pings while connected", () => {
    renderHook(() => useGameSocket("ROOM1"));
    const socket = FakeWebSocket.instances[0];
    act(() => socket.open());

    act(() => vi.advanceTimersByTime(HEARTBEAT_INTERVAL_MS));
    expect(socket.sent.map((raw) => JSON.parse(raw))).toContainEqual({ type: "ping" });
  });

  it("closes a stale socket and enters reconnect when pong stops", () => {
    renderHook(() => useGameSocket("ROOM1"));
    const socket = FakeWebSocket.instances[0];
    act(() => socket.open());

    act(() =>
      vi.advanceTimersByTime(HEARTBEAT_TIMEOUT_MS + HEARTBEAT_INTERVAL_MS)
    );
    expect(socket.closeCalls).toBe(1);
  });

  it("treats a forbidden origin as terminal", () => {
    const { result } = renderHook(() => useGameSocket("ROOM1"));
    const socket = FakeWebSocket.instances[0];

    act(() => socket.serverClose(4403));
    expect(result.current.status).toBe("origin_rejected");
    act(() => vi.advanceTimersByTime(60_000));
    expect(FakeWebSocket.instances).toHaveLength(1);
  });
});
