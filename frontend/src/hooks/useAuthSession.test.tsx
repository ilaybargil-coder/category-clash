// @vitest-environment jsdom

import { act, renderHook } from "@testing-library/react";
import type { Session } from "@supabase/supabase-js";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  clearSession: vi.fn(),
  fetchProfile: vi.fn(),
  saveSession: vi.fn(),
  getSession: vi.fn(),
  onAuthStateChange: vi.fn(),
  signOut: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    constructor(
      message: string,
      public status: number
    ) {
      super(message);
    }
  },
  clearSession: mocks.clearSession,
  fetchProfile: mocks.fetchProfile,
  saveSession: mocks.saveSession,
}));

vi.mock("@/lib/supabase", () => ({
  getSupabaseClient: () => ({
    auth: {
      getSession: mocks.getSession,
      onAuthStateChange: mocks.onAuthStateChange,
      signOut: mocks.signOut,
    },
  }),
}));

import { useAuthSession } from "./useAuthSession";

const profile = {
  id: 7,
  username: "ilay",
  display_name: "איליי",
  coins: 100,
  wins: 0,
  losses: 0,
};

function session(accessToken: string): Session {
  return { access_token: accessToken } as Session;
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.getSession.mockResolvedValue({ data: { session: session("token-1") } });
  mocks.fetchProfile.mockResolvedValue(profile);
  mocks.onAuthStateChange.mockReturnValue({
    data: { subscription: { unsubscribe: vi.fn() } },
  });
  mocks.signOut.mockResolvedValue({ error: null });
});

describe("useAuthSession", () => {
  it("restores a persisted Supabase session and syncs the game profile", async () => {
    const { result } = renderHook(() => useAuthSession());

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.status).toBe("ready");
    expect(result.current.user).toEqual(profile);
    expect(mocks.fetchProfile).toHaveBeenCalledWith("token-1");
    expect(mocks.saveSession).toHaveBeenCalledWith("token-1", profile);
  });

  it("stores a refreshed token received from Supabase", async () => {
    let authListener: ((event: string, value: Session | null) => void) | undefined;
    mocks.onAuthStateChange.mockImplementation((listener) => {
      authListener = listener;
      return { data: { subscription: { unsubscribe: vi.fn() } } };
    });
    renderHook(() => useAuthSession());
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    await act(async () => {
      authListener?.("TOKEN_REFRESHED", session("token-2"));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(mocks.saveSession).toHaveBeenLastCalledWith("token-2", profile);
  });
});
