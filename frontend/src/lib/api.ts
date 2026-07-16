import type { DemoSession, SessionUser } from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

const TOKEN_KEY = "cc_token";
const USER_KEY = "cc_user";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number
  ) {
    super(message);
  }
}

export function saveSession(token: string, user: SessionUser) {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function getUser(): SessionUser | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as SessionUser) : null;
}

export function clearSession() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? getToken() : null;
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail ?? `HTTP ${res.status}`, res.status);
  }
  return res.json() as Promise<T>;
}

export function fetchDemoUsers() {
  return request<DemoSession[]>("/api/users/demo");
}

export function demoLogin(username: string, password: string) {
  return request<{ token: string; user: SessionUser }>("/api/auth/demo-login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function fetchProfile(token: string) {
  return request<SessionUser>("/api/profile", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function createProfile(token: string, username: string, displayName: string) {
  return request<SessionUser>("/api/profile", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ username, display_name: displayName }),
  });
}

export function createRoom() {
  return request<{ code: string }>("/api/rooms", { method: "POST" });
}

export function fetchRoom(code: string) {
  return request<{ code: string; phase: string; players: string[]; joinable: boolean }>(
    `/api/rooms/${code}`
  );
}
