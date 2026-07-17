// @vitest-environment jsdom

import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useDebouncedValue } from "./useDebouncedValue";

afterEach(() => {
  vi.useRealTimers();
});

describe("useDebouncedValue", () => {
  it("publishes only the latest value after the delay", () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(
      ({ value }) => useDebouncedValue(value, 300),
      { initialProps: { value: "da" } }
    );

    rerender({ value: "dana" });
    act(() => vi.advanceTimersByTime(299));
    expect(result.current).toBe("da");

    act(() => vi.advanceTimersByTime(1));
    expect(result.current).toBe("dana");
  });
});
