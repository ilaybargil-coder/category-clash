import type { SessionUser } from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

const TOKEN_KEY = "cc_token";
const USER_KEY = "cc_user";

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
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function fetchDemoUsers() {
  return request<{ username: string; display_name: string }[]>("/api/users/demo");
}

export function demoLogin(username: string, password: string) {
  return request<{ token: string; user: SessionUser }>("/api/auth/demo-login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
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
