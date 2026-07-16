// @vitest-environment jsdom

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useBackendHealth } from "./useBackendHealth";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("useBackendHealth", () => {
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
