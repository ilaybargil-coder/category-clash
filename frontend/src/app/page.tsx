"use client";

import Image from "next/image";
import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import AuthScreen from "@/components/AuthScreen";
import DashboardFriendsCarousel from "@/components/DashboardFriendsCarousel";
import FriendsPanel from "@/components/FriendsPanel";
import InviteToast from "@/components/InviteToast";
import {
  AccuracyIcon,
  GamepadIcon,
  LightningIcon,
  LosesIcon,
  PlusIcon,
  TargetIcon,
  TrophyIcon,
  WaveIcon,
} from "@/components/icons";
import {
  BrandMark,
  CoinPill,
  DashboardWidgets,
  DesktopSidebar,
  MobileNav,
  RightSidebar,
  UserAvatar,
  type DashboardView,
} from "@/components/VisualShell";
import { useAuthSession } from "@/hooks/useAuthSession";
import { useViewportHeight } from "@/hooks/useViewportHeight";
import {
  clearSession,
  createRoom,
  fetchDemoUsers,
  getUser,
  saveSession,
} from "@/lib/api";
import {
  SUPABASE_AUTH_CONFIGURED,
  SUPABASE_AUTH_ENABLED,
} from "@/lib/supabase";
import type { DemoSession, SessionUser } from "@/lib/types";

interface UserStats {
  games: number;
  accuracy: number;
}

function getUserStats(user: SessionUser): UserStats {
  const games = user.wins + user.losses;
  return {
    games,
    accuracy: games > 0 ? Math.round((user.wins / games) * 100) : 0,
  };
}

function HomeView({
  user,
  stats,
  onNavigate,
}: {
  user: SessionUser;
  stats: UserStats;
  onNavigate: (view: DashboardView) => void;
}) {
  const router = useRouter();
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function createGame() {
    setCreating(true);
    setError(null);
    try {
      const { code } = await createRoom();
      router.push(`/room/${code}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "יצירת המשחק נכשלה");
      setCreating(false);
    }
  }

  return (
    <div className="dashboard-view home-view">
      <header className="view-greeting">
        <div>
          <span>מוכנים לסיבוב הבא?</span>
          <h1>שלום {user.display_name}! <WaveIcon className="inline-block h-[1em] w-[1em] align-[-0.12em]" /></h1>
        </div>
      </header>

      <section className="dashboard-hero surface-panel">
        <div className="dashboard-hero__art">
          <Image
            src="/assets/category-clash-hero.webp"
            alt="שני שחקנים מתחרים בקרב קטגוריות"
            fill
            priority
            sizes="(max-width: 1023px) 100vw, 36vw"
          />
        </div>

        <div className="dashboard-hero__content">
          <div className="hero-main-stats">
            <div
              className="accuracy-ring"
              style={{ "--accuracy": `${stats.accuracy * 3.6}deg` } as React.CSSProperties}
              aria-label={`${stats.accuracy} אחוז דיוק`}
            >
              <span><b>{stats.accuracy}%</b><small>דיוק</small></span>
            </div>
            <div className="hero-record">
              <div><b>{stats.games}</b><span>משחקים</span></div>
              <div><b>{user.wins}</b><span>נצחונות</span></div>
              <div><b>{user.losses}</b><span>הפסדים</span></div>
            </div>
          </div>
          <div className="hero-actions">
            <button type="button" onClick={() => void createGame()} disabled={creating} className="primary-button">
              {creating ? "פותחים זירה…" : <><PlusIcon className="inline-block h-4 w-4 align-middle" /> משחק חדש</>}
            </button>
            <button type="button" onClick={() => router.push("/daily")} className="secondary-button">
              אתגר יומי <LightningIcon className="inline-block h-4 w-4 align-middle" />
            </button>
          </div>
          {error && <p className="inline-error">{error}</p>}
        </div>
      </section>

      <StatsStrip user={user} stats={stats} />
      <DashboardFriendsCarousel onOpenFriends={() => onNavigate("friends")} />
      <div className="mobile-home-widgets"><DashboardWidgets /></div>
    </div>
  );
}

function StatsStrip({ user, stats }: { user: SessionUser; stats: UserStats }) {
  const statItems = [
    { label: "משחקים", value: stats.games, icon: <GamepadIcon className="h-5 w-5" /> },
    { label: "נצחונות", value: user.wins, icon: <TrophyIcon className="h-5 w-5" /> },
    { label: "הפסדים", value: user.losses, icon: <LosesIcon className="h-5 w-5" /> },
    { label: "דיוק", value: `${stats.accuracy}%`, icon: <AccuracyIcon className="h-5 w-5" /> },
  ];

  return (
    <section className="dashboard-stat-grid" aria-label="סיכום סטטיסטיקות">
      {statItems.map((stat) => (
        <article key={stat.label} className="dashboard-stat-card surface-panel">
          <span className="stat-icon">{stat.icon}</span>
          <small>{stat.label}</small>
          <strong>{stat.value}</strong>
        </article>
      ))}
    </section>
  );
}

function GameActions({ user }: { user: SessionUser }) {
  const router = useRouter();
  const [joinCode, setJoinCode] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function createGame() {
    setCreating(true);
    setError(null);
    try {
      const { code } = await createRoom();
      router.push(`/room/${code}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "יצירת החדר נכשלה");
      setCreating(false);
    }
  }

  function joinGame(event: React.FormEvent) {
    event.preventDefault();
    const code = joinCode.trim().toUpperCase();
    if (code) router.push(`/room/${code}`);
  }

  return (
    <div className="dashboard-view">
      <ViewHeading eyebrow={`הזירה של ${user.display_name}`} title="בוחרים מצב משחק" description="קרב מול חברים, אתגר יומי או אימון בקצב שלכם." />
      <section className="game-mode-grid">
        <GameModeCard icon={<GamepadIcon className="h-6 w-6" />} label="מול חבר" title="משחק חדש" description="פתחו חדר פרטי והזמינו חבר לקרב בזמן אמת." action={creating ? "פותחים…" : "פתיחת חדר"} onClick={() => void createGame()} primary disabled={creating} />
        <GameModeCard icon={<LightningIcon className="h-6 w-6" />} label="פעם ביום" title="האתגר היומי" description="אותה קטגוריה לכולם. כמה גבוה תגיעו היום?" action="לאתגר היומי" onClick={() => router.push("/daily")} />
        <GameModeCard icon={<TargetIcon className="h-6 w-6" />} label="אימון חופשי" title="משחק יחיד" description="חדדו מהירות וגלו תשובות חדשות בלי לחץ." action="מתחילים להתאמן" onClick={() => router.push("/solo")} />
      </section>
      <section className="join-room-panel surface-panel">
        <div>
          <span>קיבלתם הזמנה?</span>
          <h2>הצטרפות לחדר</h2>
          <p>הקלידו את קוד החדר בן חמשת התווים.</p>
        </div>
        <form onSubmit={joinGame}>
          <input value={joinCode} onChange={(event) => setJoinCode(event.target.value)} placeholder="קוד חדר" aria-label="קוד חדר" dir="ltr" maxLength={5} className="dark-input" />
          <button type="submit" disabled={!joinCode.trim()} className="primary-button">הצטרפות</button>
        </form>
      </section>
      {error && <p className="inline-error">{error}</p>}
    </div>
  );
}

function GameModeCard({
  icon,
  label,
  title,
  description,
  action,
  onClick,
  primary = false,
  disabled = false,
}: {
  icon: ReactNode;
  label: string;
  title: string;
  description: string;
  action: string;
  onClick: () => void;
  primary?: boolean;
  disabled?: boolean;
}) {
  return (
    <article className={`game-mode-card surface-panel ${primary ? "game-mode-card--featured" : ""}`}>
      <span className="game-mode-card__icon" aria-hidden="true">{icon}</span>
      <small>{label}</small>
      <h2>{title}</h2>
      <p>{description}</p>
      <button type="button" onClick={onClick} disabled={disabled} className={primary ? "primary-button" : "secondary-button"}>{action}</button>
    </article>
  );
}

function StatsView({ user, stats }: { user: SessionUser; stats: UserStats }) {
  const winWidth = stats.games ? (user.wins / stats.games) * 100 : 0;
  const lossWidth = stats.games ? (user.losses / stats.games) * 100 : 0;
  return (
    <div className="dashboard-view">
      <ViewHeading eyebrow="המספרים שלך" title="סטטיסטיקות ביצועים" description="נתוני המשחקים ששוחקו בחשבון הזה." />
      <StatsStrip user={user} stats={stats} />
      <article className="surface-panel performance-panel">
        <div className="section-heading"><div><span>מאזן כולל</span><h2>נצחונות מול הפסדים</h2></div><b>{stats.accuracy}%</b></div>
        <div className="performance-row"><span>נצחונות</span><div><i style={{ width: `${winWidth}%` }} /></div><b>{user.wins}</b></div>
        <div className="performance-row performance-row--loss"><span>הפסדים</span><div><i style={{ width: `${lossWidth}%` }} /></div><b>{user.losses}</b></div>
      </article>
    </div>
  );
}

function SettingsView({ user, onSignOut }: { user: SessionUser; onSignOut: () => void | Promise<void> }) {
  return (
    <div className="dashboard-view">
      <ViewHeading eyebrow="החשבון שלך" title="הגדרות" description="פרטי החשבון ופעולות זמינות." />
      <section className="settings-panel surface-panel">
        <div className="settings-profile">
          <UserAvatar name={user.display_name} online size="lg" />
          <div><h2>{user.display_name}</h2><p dir="ltr">@{user.username}</p></div>
          <CoinPill coins={user.coins} />
        </div>
        <button type="button" onClick={() => void onSignOut()} className="sign-out-button">התנתקות מהחשבון</button>
      </section>
    </div>
  );
}

function ViewHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <header className="view-heading">
      <span>{eyebrow}</span>
      <h1>{title}</h1>
      <p>{description}</p>
    </header>
  );
}

function LobbyDashboard({ user, onSignOut }: { user: SessionUser; onSignOut: () => void | Promise<void> }) {
  useViewportHeight();
  const [activeView, setActiveView] = useState<DashboardView>("home");
  const stats = getUserStats(user);

  function navigate(view: DashboardView) {
    setActiveView(view);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <main className="app-background lobby-dashboard" style={{ minHeight: "var(--app-vh, 100dvh)" }}>
      <div className="dashboard-grid">
        <DesktopSidebar user={user} activeView={activeView} onNavigate={navigate} />
        <section className="dashboard-center" dir="rtl">
          <header className="dashboard-mobile-header surface-panel">
            <BrandMark compact />
            <div><CoinPill coins={user.coins} /><UserAvatar name={user.display_name} online size="sm" /></div>
          </header>
          {activeView === "home" && <HomeView user={user} stats={stats} onNavigate={navigate} />}
          {activeView === "games" && <GameActions user={user} />}
          {activeView === "friends" && <div className="dashboard-view"><FriendsPanel key={user.id} /></div>}
          {activeView === "stats" && <StatsView user={user} stats={stats} />}
          {activeView === "settings" && <SettingsView user={user} onSignOut={onSignOut} />}
        </section>
        <ProfilePanel user={user} />
      </div>
      <InviteToast />
      <MobileNav activeView={activeView} onNavigate={navigate} />
    </main>
  );
}

function ProfilePanel({ user }: { user: SessionUser }) {
  return <RightSidebar user={user} />;
}

function AuthenticatedLobby() {
  const auth = useAuthSession();
  if (auth.status === "loading") return <LoadingScreen text="בודקים את ההתחברות..." />;
  if (auth.status === "signed_out") return <AuthScreen onProfileReady={auth.profileReady} />;
  if (auth.status === "needs_profile" && auth.token) return <AuthScreen profileToken={auth.token} onProfileReady={auth.profileReady} />;
  if (auth.status === "error" || !auth.user) {
    return (
      <main className="app-background flex min-h-dvh items-center justify-center px-5">
        <section className="surface-panel w-full max-w-md rounded-2xl p-7 text-center">
          <BrandMark compact />
          <h1 className="mt-7 text-2xl font-black">לא הצלחנו לאמת את החשבון</h1>
          <p className="mt-2 text-slate-400">{auth.error ?? "נסו להתחבר מחדש"}</p>
          <button type="button" onClick={() => void auth.signOut()} className="primary-button mt-6 w-full px-6 py-3">חזרה למסך הכניסה</button>
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
    fetchDemoUsers().then(setDemoUsers).catch(() => setError("השרת זמין, אבל נתוני הדמו עדיין לא מוכנים."));
  }, []);

  if (user) {
    return <LobbyDashboard user={user} onSignOut={() => { clearSession(); setUser(null); }} />;
  }

  return (
    <main className="app-background flex min-h-dvh items-center justify-center p-4">
      <section className="surface-panel w-full max-w-lg rounded-2xl p-6 sm:p-8">
        <BrandMark />
        <h2 className="mt-8 text-center text-xl font-black">בחרו שחקן דמו</h2>
        {error && <p className="mt-4 text-center text-sm text-rose-300">{error}</p>}
        <div className="mt-5 grid grid-cols-2 gap-3">
          {demoUsers.map((demo) => (
            <button key={demo.user.username} onClick={() => { saveSession(demo.token, demo.user); setUser(demo.user); }} className="rounded-xl border border-white/10 bg-white/[0.025] p-4 text-center transition hover:border-violet-400/60 hover:bg-violet-500/10">
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
      <div className="flex items-center gap-3 text-sm font-bold text-violet-300"><span className="h-5 w-5 animate-spin rounded-full border-2 border-violet-300/20 border-t-violet-300" />{text}</div>
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
          <p className="mt-2 text-slate-400">חסרים משתני החיבור הציבוריים של Supabase בפריסת ה־frontend.</p>
        </section>
      </main>
    );
  }
  return SUPABASE_AUTH_ENABLED ? <AuthenticatedLobby /> : <DemoLobby />;
}
