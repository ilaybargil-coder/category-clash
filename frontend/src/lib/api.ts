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

export type FriendRelation =
  | "none"
  | "friends"
  | "outgoing_pending"
  | "incoming_pending";

export interface FriendUser {
  id: number;
  username: string;
  display_name: string;
}

export interface UserSearchResult extends FriendUser {
  wins: number;
  losses: number;
  relation: FriendRelation;
}

export interface FriendRequestItem {
  id: number;
  user: FriendUser;
  created_at: string;
}

export interface FriendRequests {
  incoming: FriendRequestItem[];
  outgoing: FriendRequestItem[];
}

export interface Friend extends FriendUser {
  wins: number;
  losses: number;
  friends_since: string;
}

export interface GameInvite {
  sender: FriendUser;
  room_code: string;
  expires_in_seconds: number;
}

export type SoloAnswerStatus =
  | "VALID"
  | "INVALID"
  | "DUPLICATE"
  | "TOO_SIMILAR"
  | "NOT_YOUR_TURN"
  | "ROUND_FINISHED"
  | "TIME_EXPIRED";

export interface SoloQuestion {
  solo_id: string;
  question_id: number;
  question_text: string;
  total_answers: number;
}

export interface SoloAnswerResult {
  status: SoloAnswerStatus;
  canonical: string | null;
  found_count: number;
  total_answers: number;
}

export interface SoloRevealedAnswer {
  canonical: string;
  semantic_group: string | null;
  found: boolean;
}

export interface SoloReveal {
  answers: SoloRevealedAnswer[];
  found_count: number;
  total_answers: number;
}

export type FriendRequestResult =
  | { status: "PENDING"; request_id: number }
  | {
      status: "FRIENDS";
      friendship_id: number;
      friend: FriendUser;
      friends_since: string;
    };

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

export function startSolo() {
  return request<SoloQuestion>("/api/solo/start", { method: "POST" });
}

export function submitSoloAnswer(soloId: string, text: string) {
  return request<SoloAnswerResult>(`/api/solo/${soloId}/answer`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export function reportAnswer(questionId: number, rawText: string) {
  return request<{ id: number }>("/api/reports", {
    method: "POST",
    body: JSON.stringify({ question_id: questionId, raw_text: rawText }),
  });
}

export function revealSolo(soloId: string) {
  return request<SoloReveal>(`/api/solo/${soloId}/reveal`, { method: "POST" });
}

export function nextSoloQuestion(soloId: string) {
  return request<SoloQuestion>(`/api/solo/${soloId}/next`, { method: "POST" });
}

export function endSolo(soloId: string) {
  return request<{ ended: boolean }>(`/api/solo/${soloId}`, { method: "DELETE" });
}

export function fetchRoom(code: string) {
  return request<{ code: string; phase: string; players: string[]; joinable: boolean }>(
    `/api/rooms/${code}`
  );
}

export function searchUsers(query: string) {
  return request<UserSearchResult[]>(
    `/api/users/search?q=${encodeURIComponent(query)}`
  );
}

export function sendFriendRequest(username: string) {
  return request<FriendRequestResult>("/api/friends/requests", {
    method: "POST",
    body: JSON.stringify({ username }),
  });
}

export function fetchFriendRequests() {
  return request<FriendRequests>("/api/friends/requests");
}

export function acceptFriendRequest(requestId: number) {
  return request<Extract<FriendRequestResult, { status: "FRIENDS" }>>(
    `/api/friends/requests/${requestId}/accept`,
    { method: "POST" }
  );
}

export function declineFriendRequest(requestId: number) {
  return request<{ id: number; status: "DECLINED"; responded_at: string }>(
    `/api/friends/requests/${requestId}/decline`,
    { method: "POST" }
  );
}

export function fetchFriends() {
  return request<Friend[]>("/api/friends");
}

export function sendPresenceHeartbeat() {
  return request<{ online_friend_ids: number[] }>("/api/presence/heartbeat", {
    method: "POST",
  });
}

export function sendGameInvite(username: string) {
  return request<{ room_code: string; expires_in_seconds: number }>("/api/invites", {
    method: "POST",
    body: JSON.stringify({ username }),
  });
}

export function fetchInvites() {
  return request<GameInvite[]>("/api/invites");
}

export function acceptInvite(senderId: number) {
  return request<{ room_code: string }>(`/api/invites/${senderId}/accept`, {
    method: "POST",
  });
}

export function declineInvite(senderId: number) {
  return request<{ declined: boolean }>(`/api/invites/${senderId}/decline`, {
    method: "POST",
  });
}

export function removeFriend(userId: number) {
  return request<{ removed: boolean }>(`/api/friends/${userId}`, {
    method: "DELETE",
  });
}
