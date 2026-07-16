import { describe, expect, it } from "vitest";
import { isValidUsername, normalizeUsername } from "./username";

describe("username normalization", () => {
  it("removes whitespace added around a valid username", () => {
    expect(normalizeUsername("  Test  ")).toBe("Test");
    expect(isValidUsername("  Test  ")).toBe(true);
  });

  it("removes invisible mobile and directionality characters", () => {
    expect(normalizeUsername("\u200fTest\u200b")).toBe("Test");
    expect(isValidUsername("\u200fTest\u200b")).toBe(true);
  });

  it("still rejects characters outside the documented username alphabet", () => {
    expect(isValidUsername("Test!")).toBe(false);
  });
});
