"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AuthScreen from "@/components/AuthScreen";
import { useAuthSession } from "@/hooks/useAuthSession";
import { createRoom, fetchDemoUsers, getUser, saveSession } from "@/lib/api";
import {
  SUPABASE_AUTH_CONFIGURED,
  SUPABASE_AUTH_ENABLED,
} from "@/lib/supabase";
import type { DemoSession, SessionUser } from "@/lib/types";

function BrandHeader() {
  return (
    <header className="text-center">
      <h1 className="bg-gradient-to-l from-violet-600 to-fuchsia-500 bg-clip-text text-5xl font-black text-transparent">
        קרב קטגוריות
      </h1>
      <p className="mt-2 text-slate-500">שאלה אחת. שני שחקנים. מי שנתקע — מפסיד.</p>
    </header>
  );
}

function GameActions({ user }: { user: SessionUser | null }) {
  const router = useRouter();
  const [joinCode, setJoinCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onCreateRoom() {
    setBusy(true);
    setError(null);
    try {
      const { code } = await createRoom();
      router.push(`/room/${code}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "יצירת החדר נכשלה");
      setBusy(false);
    }
  }

  function onJoin(event: React.FormEvent) {
    event.preventDefault();
    const code = joinCode.trim().toUpperCase();
    if (code) router.push(`/room/${code}`);
  }

  return (
    <>
      {error && (
        <div className="rounded-xl bg-rose-50 p-3 text-center text-sm text-rose-700">
          {error}
        </div>
      )}
      <section
        className={`rounded-2xl bg-white p-5 shadow-sm transition ${
          user ? "" : "pointer-events-none opacity-40"
        }`}
      >
        <h2 className="mb-3 text-sm font-bold text-slate-400">
          פתחו משחק או הצטרפו באמצעות קוד
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
            onChange={(event) => setJoinCode(event.target.value)}
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
    </>
  );
}

function AuthenticatedLobby() {
  const auth = useAuthSession();

  if (auth.status === "loading") {
    return (
      <main className="flex min-h-dvh items-center justify-center text-lg font-bold text-violet-700">
        בודקים את ההתחברות...
      </main>
    );
  }
  if (auth.status === "signed_out") {
    return <AuthScreen onProfileReady={auth.profileReady} />;
  }
  if (auth.status === "needs_profile" && auth.token) {
    return <AuthScreen profileToken={auth.token} onProfileReady={auth.profileReady} />;
  }
  if (auth.status === "error" || !auth.user) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-4 px-6 text-center">
        <h1 className="text-2xl font-black">לא הצלחנו לאמת את החשבון</h1>
        <p className="text-slate-500">{auth.error ?? "נסו להתחבר מחדש"}</p>
        <button
          type="button"
          onClick={() => auth.signOut()}
          className="rounded-xl bg-violet-600 px-6 py-3 font-bold text-white"
        >
          חזרה למסך הכניסה
        </button>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-6 px-4 py-8">
      <BrandHeader />
      <section className="rounded-2xl bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-bold text-slate-400">מחוברים בתור</p>
            <p className="text-xl font-black">{auth.user.display_name}</p>
            <p className="text-sm text-slate-400">@{auth.user.username}</p>
          </div>
          <button
            type="button"
            onClick={() => auth.signOut()}
            className="rounded-xl border-2 border-slate-200 px-4 py-2 text-sm font-bold text-slate-600"
          >
            התנתקות
          </button>
        </div>
        <p className="mt-3 text-sm text-emerald-600">
          {auth.user.wins} נצחונות · {auth.user.losses} הפסדים · {auth.user.coins} מטבעות
        </p>
      </section>
      <GameActions user={auth.user} />
    </main>
  );
}

function DemoLobby() {
  const [demoUsers, setDemoUsers] = useState<DemoSession[]>([]);
  const [user, setUser] = useState<SessionUser | null>(() => getUser());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDemoUsers()
      .then(setDemoUsers)
      .catch(() => setError("השרת זמין, אבל נתוני הדמו עדיין לא מוכנים."));
  }, []);

  function loginAs(demo: DemoSession) {
    setError(null);
    saveSession(demo.token, demo.user);
    setUser(demo.user);
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-6 px-4 py-8">
      <BrandHeader />
      {error && (
        <div className="rounded-xl bg-rose-50 p-3 text-center text-sm text-rose-700">
          {error}
        </div>
      )}
      <section className="rounded-2xl bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-bold text-slate-400">בחרו שחקן דמו</h2>
        <div className="grid grid-cols-2 gap-3">
          {demoUsers.map((demo) => (
            <button
              key={demo.user.username}
              onClick={() => loginAs(demo)}
              className={`rounded-xl border-2 p-4 text-center transition ${
                user?.username === demo.user.username
                  ? "border-violet-500 bg-violet-50"
                  : "border-slate-200 hover:border-violet-300"
              }`}
            >
              <div className="text-2xl font-black">{demo.user.display_name}</div>
              <div className="text-xs text-slate-400">@{demo.user.username}</div>
            </button>
          ))}
        </div>
        {user && (
          <p className="mt-3 text-center text-sm text-emerald-600">
            מחוברים בתור {user.display_name} · {user.wins} נצחונות · {user.losses} הפסדים
          </p>
        )}
      </section>
      <GameActions user={user} />
      <p className="text-center text-xs text-slate-400">
        טיפ: פתחו שני חלונות דפדפן ובחרו שחקן שונה בכל אחד
      </p>
    </main>
  );
}

export default function LobbyPage() {
  if (SUPABASE_AUTH_ENABLED && !SUPABASE_AUTH_CONFIGURED) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-3 px-6 text-center">
        <h1 className="text-2xl font-black">ההתחברות עדיין לא הוגדרה</h1>
        <p className="text-slate-500">
          חסרים משתני החיבור הציבוריים של Supabase בפריסת ה-frontend.
        </p>
      </main>
    );
  }
  return SUPABASE_AUTH_ENABLED ? <AuthenticatedLobby /> : <DemoLobby />;
}
