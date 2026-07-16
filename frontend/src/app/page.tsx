"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  createRoom,
  demoLogin,
  fetchDemoUsers,
  getUser,
  saveSession,
} from "@/lib/api";
import type { SessionUser } from "@/lib/types";

// Phase 1: demo users share a fixed password (seeded server-side).
const DEMO_PASSWORD = "demo1234";

export default function LobbyPage() {
  const router = useRouter();
  const [demoUsers, setDemoUsers] = useState<
    { username: string; display_name: string }[]
  >([]);
  const [user, setUser] = useState<SessionUser | null>(() => getUser());
  const [joinCode, setJoinCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDemoUsers()
      .then(setDemoUsers)
      .catch(() => setError("השרת זמין, אבל הנתונים עדיין לא מוכנים. נסו לרענן."));
  }, []);

  async function loginAs(username: string) {
    setBusy(true);
    setError(null);
    try {
      const { token, user } = await demoLogin(username, DEMO_PASSWORD);
      saveSession(token, user);
      setUser(user);
    } catch (e) {
      setError(e instanceof Error ? e.message : "ההתחברות נכשלה");
    } finally {
      setBusy(false);
    }
  }

  async function onCreateRoom() {
    setBusy(true);
    setError(null);
    try {
      const { code } = await createRoom();
      router.push(`/room/${code}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "יצירת החדר נכשלה");
      setBusy(false);
    }
  }

  function onJoin(e: React.FormEvent) {
    e.preventDefault();
    const code = joinCode.trim().toUpperCase();
    if (code) router.push(`/room/${code}`);
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-6 px-4 py-8">
      <header className="text-center">
        <h1 className="bg-gradient-to-l from-violet-600 to-fuchsia-500 bg-clip-text text-5xl font-black text-transparent">
          קרב קטגוריות
        </h1>
        <p className="mt-2 text-slate-500">
          שאלה אחת. שני שחקנים. מי שנתקע — מפסיד.
        </p>
      </header>

      {error && (
        <div className="rounded-xl bg-rose-50 p-3 text-center text-sm text-rose-700">
          {error}
        </div>
      )}

      <section className="rounded-2xl bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-bold text-slate-400">
          שלב 1 · בחרו שחקן דמו
        </h2>
        <div className="grid grid-cols-2 gap-3">
          {demoUsers.map((demo) => (
            <button
              key={demo.username}
              onClick={() => loginAs(demo.username)}
              disabled={busy}
              className={`rounded-xl border-2 p-4 text-center transition ${
                user?.username === demo.username
                  ? "border-violet-500 bg-violet-50"
                  : "border-slate-200 hover:border-violet-300"
              }`}
            >
              <div className="text-2xl font-black">{demo.display_name}</div>
              <div className="text-xs text-slate-400">@{demo.username}</div>
            </button>
          ))}
        </div>
        {user && (
          <p className="mt-3 text-center text-sm text-emerald-600">
            מחוברים בתור {user.display_name} · {user.wins} נצחונות ·{" "}
            {user.losses} הפסדים
          </p>
        )}
      </section>

      <section
        className={`rounded-2xl bg-white p-5 shadow-sm transition ${
          user ? "" : "pointer-events-none opacity-40"
        }`}
      >
        <h2 className="mb-3 text-sm font-bold text-slate-400">
          שלב 2 · פתחו משחק או הצטרפו
        </h2>
        <button
          onClick={onCreateRoom}
          disabled={busy || !user}
          className="w-full rounded-xl bg-gradient-to-l from-violet-600 to-fuchsia-500 py-3.5 text-lg font-bold text-white shadow-md transition active:scale-[0.98] disabled:opacity-50"
        >
          משחק חדש
        </button>
        <div className="my-4 flex items-center gap-3 text-xs text-slate-300">
          <div className="h-px flex-1 bg-slate-200" />
          או
          <div className="h-px flex-1 bg-slate-200" />
        </div>
        <form onSubmit={onJoin} className="flex gap-2">
          <input
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value)}
            placeholder="קוד חדר, למשל 7GX2Q"
            dir="ltr"
            maxLength={5}
            className="min-w-0 flex-1 rounded-xl border-2 border-slate-200 px-4 py-3 text-center font-mono text-lg uppercase tracking-widest outline-none focus:border-violet-400"
          />
          <button
            type="submit"
            disabled={!joinCode.trim() || !user}
            className="rounded-xl bg-slate-800 px-6 font-bold text-white transition active:scale-[0.98] disabled:opacity-40"
          >
            הצטרפות
          </button>
        </form>
      </section>

      <p className="text-center text-xs text-slate-400">
        טיפ: פתחו שני חלונות דפדפן (רגיל + גלישה בסתר) ובחרו שחקן שונה בכל אחד
      </p>
    </main>
  );
}
