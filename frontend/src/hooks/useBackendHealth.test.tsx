// @vitest-environment jsdom

import { act, render, renderHook, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import BackendWakeupGate from "@/components/BackendWakeupGate";
import { useBackendHealth } from "./useBackendHealth";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("useBackendHealth", () => {
  it("keeps the app visible while the initial health check is pending", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));

    render(
      <BackendWakeupGate>
        <div>לובי המשחק</div>
      </BackendWakeupGate>
    );

    expect(screen.getByText("לובי המשחק")).toBeTruthy();
    expect(screen.queryByText("שרת המשחק מתעורר")).toBeNull();
  });

  it("shows the wake screen only after a real health failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("sleeping")));

    render(
      <BackendWakeupGate>
        <div>לובי המשחק</div>
      </BackendWakeupGate>
    );
    await act(async () => Promise.resolve());

    expect(screen.getByText("שרת המשחק מתעורר")).toBeTruthy();
  });

  it("opens the gate when health responds successfully", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: "ok" }) })
    );
    const { result } = renderHook(() => useBackendHealth());

    await act(async () => Promise.resolve());
    expect(result.current.status).toBe("ready");
    expect(result.current.attempts).toBe(1);
  });

  it("polls again while a free backend is waking", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error("sleeping"))
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: "ok" }) });
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() => useBackendHealth());

    await act(async () => Promise.resolve());
    expect(result.current.status).toBe("waiting");

    await act(async () => {
      vi.advanceTimersByTime(3_000);
      await Promise.resolve();
    });
    expect(result.current.status).toBe("ready");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
