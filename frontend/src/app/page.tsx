"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AuthScreen from "@/components/AuthScreen";
import FriendsPanel from "@/components/FriendsPanel";
import {
  BrandMark,
  CoinPill,
  DesktopSidebar,
  MobileNav,
  UserAvatar,
} from "@/components/VisualShell";
import { useAuthSession } from "@/hooks/useAuthSession";
import { createRoom, fetchDemoUsers, getUser, saveSession } from "@/lib/api";
import {
  SUPABASE_AUTH_CONFIGURED,
  SUPABASE_AUTH_ENABLED,
} from "@/lib/supabase";
import type { DemoSession, SessionUser } from "@/lib/types";

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
    <section
      id="play"
      className={`surface-panel overflow-hidden rounded-2xl ${
        user ? "" : "pointer-events-none opacity-40"
      }`}
    >
      <div className="relative overflow-hidden border-b border-white/10 px-5 py-6 sm:px-7 sm:py-8">
        <div className="pointer-events-none absolute -left-12 -top-16 h-52 w-52 rounded-full bg-violet-600/20 blur-3xl" />
        <p className="relative text-xs font-bold tracking-[0.16em] text-violet-300">
          משחק בזמן אמת
        </p>
        <h2 className="relative mt-2 max-w-xl text-2xl font-black text-white sm:text-4xl">
          מוכנים לקרב הבא?
        </h2>
        <p className="relative mt-2 max-w-lg text-sm leading-6 text-slate-400 sm:text-base">
          פתחו חדר, שלחו לחבר את הקוד ונסו להיות האחרונים שנשארים עם תשובה.
        </p>
        <div className="relative mt-6 flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={onCreateRoom}
            disabled={busy || !user}
            className="primary-button w-full px-6 py-3.5 sm:w-auto sm:min-w-56"
          >
            {busy ? "פותחים זירה..." : "＋ צור משחק חדש"}
          </button>
          <button
            type="button"
            onClick={() => router.push("/solo")}
            disabled={!user}
            className="secondary-button w-full px-6 py-3.5 sm:w-auto"
          >
            משחק יחיד 🎯
          </button>
        </div>
      </div>

      <div className="p-5 sm:p-7">
        <div className="mb-4 flex items-center gap-3 text-xs text-slate-500">
          <span className="h-px flex-1 bg-white/10" />
          יש לך קוד הזמנה?
          <span className="h-px flex-1 bg-white/10" />
        </div>
        <form onSubmit={onJoin} className="flex flex-col gap-3 sm:flex-row">
          <input
            value={joinCode}
            onChange={(event) => setJoinCode(event.target.value)}
            placeholder="7GX2Q"
            aria-label="קוד חדר"
            dir="ltr"
            maxLength={5}
            className="dark-input min-w-0 flex-1 text-center font-mono text-lg uppercase tracking-[0.28em]"
          />
          <button
            type="submit"
            disabled={!joinCode.trim() || !user}
            className="secondary-button min-h-12 px-8 disabled:opacity-40"
          >
            הצטרפות
          </button>
        </form>
        {error && (
          <p className="mt-4 rounded-xl border border-rose-400/20 bg-rose-500/10 p-3 text-sm text-rose-300">
            {error}
          </p>
        )}
      </div>
    </section>
  );
}

function StatsStrip({ user }: { user: SessionUser }) {
  const games = user.wins + user.losses;
  const rate = games ? Math.round((user.wins / games) * 100) : 0;
  return (
    <section id="stats" className="grid scroll-mt-4 grid-cols-3 gap-2 sm:gap-3">
      {[
        ["ניצחונות", user.wins],
        ["אחוז הצלחה", `${rate}%`],
        ["משחקים", games],
      ].map(([label, value]) => (
        <div key={label} className="surface-panel rounded-xl px-3 py-4 text-center sm:p-5">
          <strong className="block text-xl font-black text-white sm:text-2xl">{value}</strong>
          <span className="mt-1 block text-[11px] text-slate-500 sm:text-xs">{label}</span>
        </div>
      ))}
    </section>
  );
}

function ProfilePanel({ user }: { user: SessionUser }) {
  return (
    <aside id="profile" className="surface-panel hidden scroll-mt-4 rounded-2xl p-5 xl:block">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-black text-white">הפרופיל שלך</h2>
        <CoinPill coins={user.coins} />
      </div>
      <div className="mt-7 flex flex-col items-center text-center">
        <UserAvatar name={user.display_name} online size="lg" />
        <h3 className="mt-4 text-xl font-black text-white">{user.display_name}</h3>
        <p className="text-sm text-slate-500">@{user.username}</p>
      </div>
      <div className="mt-7 grid gap-3">
        <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
          <p className="text-xs font-bold text-violet-300">טיפ למשחק</p>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            כתיב קצר יכול להשלים אוטומטית רק כאשר קיימת תשובה אחת חד־משמעית.
          </p>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
          <p className="text-xs font-bold text-emerald-300">המאגר משתפר</p>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            תשובות שנדחות נשמרות לבדיקה ועוזרות לנו להרחיב את המשחק.
          </p>
        </div>
      </div>
    </aside>
  );
}

function LobbyDashboard({
  user,
  onSignOut,
}: {
  user: SessionUser;
  onSignOut: () => void;
}) {
  return (
    <main className="app-background min-h-dvh p-3 pb-24 sm:p-4 lg:pb-4">
      <div className="mx-auto grid min-h-[calc(100dvh-2rem)] max-w-[1500px] gap-4 lg:grid-cols-[230px_minmax(0,1fr)] xl:grid-cols-[230px_minmax(0,1fr)_310px]">
        <DesktopSidebar user={user} onSignOut={onSignOut} />

        <section className="min-w-0 py-1 lg:px-2 lg:py-3">
          <header className="mb-6 flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold text-violet-300">ברוכים הבאים לזירה</p>
              <h1 className="mt-1 text-2xl font-black text-white sm:text-3xl">
                ערב טוב, {user.display_name}
              </h1>
            </div>
            <div className="flex items-center gap-3 lg:hidden">
              <CoinPill coins={user.coins} />
              <UserAvatar name={user.display_name} online size="sm" />
            </div>
          </header>

          <div className="space-y-4">
            <GameActions user={user} />
            <StatsStrip user={user} />
            <FriendsPanel key={user.id} />
            <section className="surface-panel rounded-2xl p-5 sm:p-6">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-bold text-emerald-300">מצב אונליין</p>
                  <h2 className="mt-1 text-lg font-black text-white">השרת מוכן למשחק</h2>
                </div>
                <span className="flex items-center gap-2 text-xs font-bold text-emerald-300">
                  <i className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
                  פעיל
                </span>
              </div>
            </section>
          </div>
        </section>

        <ProfilePanel user={user} />
      </div>
      <MobileNav />
    </main>
  );
}

function AuthenticatedLobby() {
  const auth = useAuthSession();

  if (auth.status === "loading") {
    return <LoadingScreen text="בודקים את ההתחברות..." />;
  }
  if (auth.status === "signed_out") {
    return <AuthScreen onProfileReady={auth.profileReady} />;
  }
  if (auth.status === "needs_profile" && auth.token) {
    return <AuthScreen profileToken={auth.token} onProfileReady={auth.profileReady} />;
  }
  if (auth.status === "error" || !auth.user) {
    return (
      <main className="app-background flex min-h-dvh items-center justify-center px-5">
        <section className="surface-panel w-full max-w-md rounded-2xl p-7 text-center">
          <BrandMark compact />
          <h1 className="mt-7 text-2xl font-black">לא הצלחנו לאמת את החשבון</h1>
          <p className="mt-2 text-slate-400">{auth.error ?? "נסו להתחבר מחדש"}</p>
          <button
            type="button"
            onClick={() => auth.signOut()}
            className="primary-button mt-6 w-full px-6 py-3"
          >
            חזרה למסך הכניסה
          </button>
        </section>
      </main>
    );
  }

  return <LobbyDashboard user={auth.user} onSignOut={auth.signOut} />;
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

  if (user) return <LobbyDashboard user={user} onSignOut={() => setUser(null)} />;

  return (
    <main className="app-background flex min-h-dvh items-center justify-center p-4">
      <section className="surface-panel w-full max-w-lg rounded-2xl p-6 sm:p-8">
        <BrandMark />
        <h2 className="mt-8 text-center text-xl font-black">בחרו שחקן דמו</h2>
        {error && <p className="mt-4 text-center text-sm text-rose-300">{error}</p>}
        <div className="mt-5 grid grid-cols-2 gap-3">
          {demoUsers.map((demo) => (
            <button
              key={demo.user.username}
              onClick={() => {
                saveSession(demo.token, demo.user);
                setUser(demo.user);
              }}
              className="rounded-xl border border-white/10 bg-white/[0.025] p-4 text-center transition hover:border-violet-400/60 hover:bg-violet-500/10"
            >
              <UserAvatar name={demo.user.display_name} size="md" />
              <div className="mt-3 font-black text-white">{demo.user.display_name}</div>
              <div className="text-xs text-slate-500">@{demo.user.username}</div>
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}

function LoadingScreen({ text }: { text: string }) {
  return (
    <main className="app-background flex min-h-dvh flex-col items-center justify-center gap-7 text-center">
      <BrandMark />
      <div className="flex items-center gap-3 text-sm font-bold text-violet-300">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-violet-300/20 border-t-violet-300" />
        {text}
      </div>
    </main>
  );
}

export default function LobbyPage() {
  if (SUPABASE_AUTH_ENABLED && !SUPABASE_AUTH_CONFIGURED) {
    return (
      <main className="app-background flex min-h-dvh items-center justify-center px-6 text-center">
        <section className="surface-panel max-w-md rounded-2xl p-8">
          <BrandMark />
          <h1 className="mt-7 text-2xl font-black">ההתחברות עדיין לא הוגדרה</h1>
          <p className="mt-2 text-slate-400">
            חסרים משתני החיבור הציבוריים של Supabase בפריסת ה־frontend.
          </p>
        </section>
      </main>
    );
  }
  return SUPABASE_AUTH_ENABLED ? <AuthenticatedLobby /> : <DemoLobby />;
}
