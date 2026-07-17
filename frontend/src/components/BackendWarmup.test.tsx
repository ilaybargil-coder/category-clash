// @vitest-environment jsdom

import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import BackendWarmup from "./BackendWarmup";

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    value: "visible",
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("BackendWarmup", () => {
  it("warms immediately and sends a heartbeat while the site is visible", () => {
    render(<BackendWarmup />);
    expect(fetch).toHaveBeenCalledTimes(1);

    act(() => vi.advanceTimersByTime(5 * 60 * 1_000));
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});
