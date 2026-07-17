"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import {
  acceptFriendRequest,
  acceptInvite,
  declineInvite,
  declineFriendRequest,
  fetchFriendRequests,
  fetchFriends,
  fetchInvites,
  removeFriend,
  searchUsers,
  sendFriendRequest,
  sendGameInvite,
  sendPresenceHeartbeat,
} from "@/lib/api";
import type {
  Friend,
  FriendRequests,
  GameInvite,
  UserSearchResult,
} from "@/lib/api";

const EMPTY_REQUESTS: FriendRequests = { incoming: [], outgoing: [] };
type TimedInvite = GameInvite & { expiresAt: number };

export default function FriendsPanel() {
  const router = useRouter();
  const [friends, setFriends] = useState<Friend[]>([]);
  const [requests, setRequests] = useState<FriendRequests>(EMPTY_REQUESTS);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<UserSearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [confirmRemoveId, setConfirmRemoveId] = useState<number | null>(null);
  const [searchVersion, setSearchVersion] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [onlineFriendIds, setOnlineFriendIds] = useState<Set<number>>(new Set());
  const [invites, setInvites] = useState<TimedInvite[]>([]);
  const [countdownNow, setCountdownNow] = useState(() => Date.now());
  const heartbeatAttempted = useRef(false);
  const debouncedQuery = useDebouncedValue(query.trim(), 300);

  const loadFriendsData = useCallback(
    () => Promise.all([fetchFriends(), fetchFriendRequests()]),
    []
  );

  const heartbeat = useCallback(async () => {
    const isFirstAttempt = !heartbeatAttempted.current;
    heartbeatAttempted.current = true;
    try {
      const presence = await sendPresenceHeartbeat();
      setOnlineFriendIds(new Set(presence.online_friend_ids));
    } catch (cause) {
      if (isFirstAttempt) {
        setError(cause instanceof Error ? cause.message : "בדיקת החיבור נכשלה");
      }
    }
  }, []);

  useEffect(() => {
    const initialHeartbeat = window.setTimeout(() => void heartbeat(), 0);
    const interval = window.setInterval(() => void heartbeat(), 30_000);
    return () => {
      window.clearTimeout(initialHeartbeat);
      window.clearInterval(interval);
    };
  }, [heartbeat]);

  useEffect(() => {
    let active = true;
    const loadInvites = async () => {
      try {
        const nextInvites = await fetchInvites();
        if (active) {
          const now = Date.now();
          setInvites(
            nextInvites.map((invite) => ({
              ...invite,
              expiresAt: now + invite.expires_in_seconds * 1000,
            }))
          );
        }
      } catch {
        // Invite polling is best-effort, like presence heartbeats after the first try.
      }
    };
    void loadInvites();
    const interval = window.setInterval(() => void loadInvites(), 5_000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      const now = Date.now();
      setInvites((current) => current.filter((invite) => invite.expiresAt > now));
      setCountdownNow(now);
    }, 1_000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    let active = true;
    loadFriendsData()
      .then(([nextFriends, nextRequests]) => {
        if (active) {
          setFriends(nextFriends);
          setRequests(nextRequests);
        }
      })
      .catch((cause) => {
        if (active) {
          setError(cause instanceof Error ? cause.message : "טעינת החברים נכשלה");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [loadFriendsData]);

  useEffect(() => {
    if (debouncedQuery.length < 2) {
      return;
    }
    let active = true;
    searchUsers(debouncedQuery)
      .then((users) => {
        if (active) setResults(users);
      })
      .catch((cause) => {
        if (active) {
          setError(cause instanceof Error ? cause.message : "החיפוש נכשל");
        }
      });
    return () => {
      active = false;
    };
  }, [debouncedQuery, searchVersion]);

  useEffect(() => {
    if (confirmRemoveId === null) return;
    const timeout = window.setTimeout(() => setConfirmRemoveId(null), 3000);
    return () => window.clearTimeout(timeout);
  }, [confirmRemoveId]);

  async function mutate(key: string, action: () => Promise<unknown>) {
    setBusyKey(key);
    setError(null);
    try {
      await action();
      const [nextFriends, nextRequests] = await loadFriendsData();
      setFriends(nextFriends);
      setRequests(nextRequests);
      await heartbeat();
      setSearchVersion((version) => version + 1);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "הפעולה נכשלה");
    } finally {
      setBusyKey(null);
    }
  }

  function accept(requestId: number) {
    return mutate(`accept-${requestId}`, () => acceptFriendRequest(requestId));
  }

  function decline(requestId: number) {
    return mutate(`decline-${requestId}`, () => declineFriendRequest(requestId));
  }

  function addFromSearch(user: UserSearchResult) {
    if (user.relation === "none") {
      return mutate(`user-${user.id}`, () => sendFriendRequest(user.username));
    }
    if (user.relation === "incoming_pending") {
      const incoming = requests.incoming.find((request) => request.user.id === user.id);
      if (incoming) return accept(incoming.id);
    }
  }

  function unfriend(friendId: number) {
    if (confirmRemoveId !== friendId) {
      setConfirmRemoveId(friendId);
      return;
    }
    setConfirmRemoveId(null);
    void mutate(`remove-${friendId}`, () => removeFriend(friendId));
  }

  async function inviteFriend(friend: Friend) {
    setBusyKey(`invite-${friend.id}`);
    setError(null);
    try {
      const invite = await sendGameInvite(friend.username);
      router.push(`/room/${invite.room_code}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "שליחת ההזמנה נכשלה");
    } finally {
      setBusyKey(null);
    }
  }

  async function respondToInvite(invite: TimedInvite, accept: boolean) {
    setBusyKey(`${accept ? "accept" : "decline"}-invite-${invite.sender.id}`);
    setError(null);
    try {
      if (accept) {
        const result = await acceptInvite(invite.sender.id);
        setInvites((current) =>
          current.filter((item) => item.sender.id !== invite.sender.id)
        );
        router.push(`/room/${result.room_code}`);
      } else {
        await declineInvite(invite.sender.id);
        setInvites((current) =>
          current.filter((item) => item.sender.id !== invite.sender.id)
        );
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "התגובה להזמנה נכשלה");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <section className="rounded-2xl bg-white p-5 shadow-sm">
      <h2 className="text-2xl font-black text-slate-800">חברים</h2>

      {error && (
        <p className="mt-3 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{error}</p>
      )}

      {invites.length > 0 && (
        <div className="mt-4 space-y-3">
          {invites.map((invite) => (
            <div
              key={invite.sender.id}
              className="rounded-2xl border-2 border-violet-200 bg-violet-50 p-4"
            >
              <p className="font-black text-violet-900">
                {invite.sender.display_name} מזמין/ה אותך למשחק
              </p>
              <p className="mt-1 text-xs font-bold text-violet-600">
                נותרו {Math.max(0, Math.ceil((invite.expiresAt - countdownNow) / 1000))} שניות
              </p>
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  onClick={() => void respondToInvite(invite, true)}
                  disabled={busyKey !== null}
                  className="rounded-full bg-violet-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
                >
                  קבלת הזמנה
                </button>
                <button
                  type="button"
                  onClick={() => void respondToInvite(invite, false)}
                  disabled={busyKey !== null}
                  className="rounded-full border-2 border-violet-200 bg-white px-4 py-2 text-sm font-bold text-violet-700 disabled:opacity-50"
                >
                  דחייה
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {requests.incoming.length > 0 && (
        <div className="mt-5">
          <div className="mb-3 flex items-center gap-2">
            <h3 className="font-black text-slate-700">בקשות חברות</h3>
            <span className="rounded-full bg-violet-100 px-2 py-0.5 text-xs font-black text-violet-700">
              {requests.incoming.length}
            </span>
          </div>
          <div className="space-y-3">
            {requests.incoming.map((request) => (
              <div
                key={request.id}
                className="flex items-center justify-between gap-3 rounded-2xl bg-violet-50 p-3"
              >
                <div className="min-w-0">
                  <p className="truncate font-black">{request.user.display_name}</p>
                  <p dir="ltr" className="truncate text-left text-xs text-slate-400">
                    @{request.user.username}
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    onClick={() => void accept(request.id)}
                    disabled={busyKey !== null}
                    className="rounded-full bg-violet-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
                  >
                    אישור
                  </button>
                  <button
                    type="button"
                    onClick={() => void decline(request.id)}
                    disabled={busyKey !== null}
                    className="rounded-full border-2 border-slate-200 px-4 py-2 text-sm font-bold text-slate-600 disabled:opacity-50"
                  >
                    דחייה
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-5">
        <h3 className="mb-3 font-black text-slate-700">החברים שלי</h3>
        {loading ? (
          <p className="text-sm text-slate-400">טוענים חברים...</p>
        ) : friends.length === 0 ? (
          <p className="rounded-2xl bg-slate-50 p-4 text-center text-sm text-slate-500">
            עדיין אין חברים — חפשו שם משתמש כדי להוסיף
          </p>
        ) : (
          <div className="space-y-3">
            {friends.map((friend) => (
              <div
                key={friend.id}
                className="flex items-center justify-between gap-3 rounded-2xl border-2 border-slate-100 p-3"
              >
                <div className="min-w-0">
                  <p className="truncate font-black">{friend.display_name}</p>
                  <p dir="ltr" className="truncate text-left text-xs text-slate-400">
                    @{friend.username}
                  </p>
                  <p
                    className={`mt-1 flex items-center gap-1.5 text-xs font-bold ${
                      onlineFriendIds.has(friend.id)
                        ? "text-emerald-600"
                        : "text-slate-400"
                    }`}
                  >
                    <span
                      className={`h-2 w-2 rounded-full ${
                        onlineFriendIds.has(friend.id) ? "bg-emerald-500" : "bg-slate-300"
                      }`}
                    />
                    {onlineFriendIds.has(friend.id) ? "מחובר" : "לא מחובר"}
                  </p>
                  <p className="mt-1 text-xs text-emerald-600">
                    נצחונות: {friend.wins} · הפסדים: {friend.losses}
                  </p>
                </div>
                <div className="flex shrink-0 flex-col gap-2">
                  {onlineFriendIds.has(friend.id) && (
                    <button
                      type="button"
                      onClick={() => void inviteFriend(friend)}
                      disabled={busyKey !== null}
                      className="rounded-full bg-violet-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50"
                    >
                      הזמנה למשחק
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => unfriend(friend.id)}
                    disabled={busyKey !== null}
                    className={`rounded-full px-4 py-2 text-sm font-bold transition disabled:opacity-50 ${
                      confirmRemoveId === friend.id
                        ? "bg-rose-600 text-white"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {confirmRemoveId === friend.id ? "בטוח?" : "הסרה"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-6 border-t border-slate-100 pt-5">
        <h3 className="mb-3 font-black text-slate-700">הוספת חברים</h3>
        <input
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setResults([]);
          }}
          placeholder="חיפוש לפי שם משתמש…"
          dir="ltr"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          className="w-full rounded-full border-2 border-slate-200 px-4 py-3 text-left outline-none focus:border-violet-400"
        />
        {results.length > 0 && (
          <div className="mt-3 space-y-2">
            {results.map((user) => (
              <div
                key={user.id}
                className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 p-3"
              >
                <div className="min-w-0">
                  <p className="truncate font-black">{user.display_name}</p>
                  <p dir="ltr" className="truncate text-left text-xs text-slate-400">
                    @{user.username}
                  </p>
                </div>
                <RelationButton
                  user={user}
                  busy={busyKey !== null}
                  onClick={() => void addFromSearch(user)}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function RelationButton({
  user,
  busy,
  onClick,
}: {
  user: UserSearchResult;
  busy: boolean;
  onClick: () => void;
}) {
  const labels = {
    none: "הוספה",
    outgoing_pending: "נשלחה בקשה",
    incoming_pending: "אישור בקשה",
    friends: "חברים ✓",
  };
  const disabled = busy || user.relation === "outgoing_pending" || user.relation === "friends";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="shrink-0 rounded-full bg-violet-600 px-4 py-2 text-sm font-bold text-white disabled:bg-slate-200 disabled:text-slate-500"
    >
      {labels[user.relation]}
    </button>
  );
}
