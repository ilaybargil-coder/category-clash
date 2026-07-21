"use client";

import Image from "next/image";
import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import AuthScreen from "@/components/AuthScreen";
import AvatarPicker from "@/components/AvatarPicker";
import DashboardFriendsCarousel from "@/components/DashboardFriendsCarousel";
import FriendsPanel from "@/components/FriendsPanel";
import InviteToast from "@/components/InviteToast";
import MatchHistory from "@/components/MatchHistory";
import AppIcon from "@/components/AppIcon";
import {
  PlusIcon,
  TargetIcon,
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
  deleteAccount,
  fetchDemoUsers,
  fetchXpLeaderboard,
  getToken,
  getUser,
  refreshSessionUser,
  saveSession,
  updateProfile,
} from "@/lib/api";
import {
  getSupabaseClient,
  SUPABASE_AUTH_CONFIGURED,
  SUPABASE_AUTH_ENABLED,
} from "@/lib/supabase";
import type { XpLeaderboard, XpLeaderboardEntry } from "@/lib/api";
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
  const [leaderboard, setLeaderboard] = useState<XpLeaderboard | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchXpLeaderboard()
      .then((result) => {
        if (!cancelled) setLeaderboard(result);
      })
      .catch(() => {
        // The rest of the dashboard stays usable if this secondary widget fails.
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
          <h1>שלום {user.display_name}!</h1>
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
              {creating ? "פותחים זירה…" : <><PlusIcon className="inline-block h-5 w-5 align-middle" /> משחק חדש</>}
            </button>
            <button type="button" onClick={() => router.push("/daily")} className="secondary-button">
              <AppIcon name="daily" className="inline-block h-5 w-5 align-middle" /> אתגר יומי
            </button>
          </div>
          {error && <p className="inline-error">{error}</p>}
        </div>
      </section>

      <LevelProgress user={user} />
      <StatsStrip user={user} stats={stats} />
      <XpLeaderboardPanel user={user} leaderboard={leaderboard} />
      <DashboardFriendsCarousel onOpenFriends={() => onNavigate("friends")} />
      <div className="mobile-home-widgets"><DashboardWidgets /></div>
    </div>
  );
}

function LevelProgress({ user }: { user: SessionUser }) {
  const rank = user.rank;
  const progress = Math.min(
    100,
    Math.round((user.xp_into_level / user.xp_for_next_level) * 100)
  );
  return (
    <section className="surface-panel rounded-2xl p-4" aria-label="התקדמות רמה">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-bold text-violet-300">Level {user.level}</p>
          <h2 className="mt-1 text-lg font-black text-white">הדרך לרמה הבאה</h2>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-300/20 bg-amber-400/10 px-3 py-1.5 text-sm font-black text-amber-200">
          <img
            src={`/assets/ranks/${rank.toLowerCase()}.png?v=2`}
            alt={rank}
            className="h-14 w-14 object-contain flex-shrink-0"
            onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
          />
          {rank}
        </span>
      </div>
      <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-gradient-to-l from-violet-400 to-fuchsia-500 transition-[width]"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="mt-2 text-left text-xs font-bold text-slate-400" dir="ltr">
        {user.xp_into_level}/{user.xp_for_next_level} XP
      </p>
    </section>
  );
}

function XpLeaderboardPanel({
  user,
  leaderboard,
}: {
  user: SessionUser;
  leaderboard: XpLeaderboard | null;
}) {
  const entries = leaderboard?.entries.slice(0, 5) ?? [];
  const currentEntry = leaderboard?.entries.find((entry) => entry.user_id === user.id);
  const currentIsVisible = entries.some((entry) => entry.user_id === user.id);
  const yourEntry: XpLeaderboardEntry | null = leaderboard
    ? currentEntry ?? {
        rank: leaderboard.you.rank,
        user_id: user.id,
        display_name: user.display_name,
        username: user.username,
        avatar: user.avatar,
        level: leaderboard.you.level,
        xp: leaderboard.you.xp,
      }
    : null;

  return (
    <section className="surface-panel rounded-2xl p-4" aria-label="טבלת מובילים לפי XP">
      <div className="section-heading">
        <div>
          <span className="text-xs font-bold text-violet-300">גלובלי</span>
          <h2>טבלת מובילים</h2>
        </div>
        <AppIcon name="leaderboard" className="h-6 w-6" />
      </div>
      {!leaderboard ? (
        <p className="mt-4 text-center text-sm text-slate-500">טוענים דירוג…</p>
      ) : (
        <ol className="mt-4 space-y-2">
          {entries.map((entry) => (
            <XpLeaderboardRow key={entry.user_id} entry={entry} current={entry.user_id === user.id} />
          ))}
          {!currentIsVisible && yourEntry && (
            <>
              <li className="text-center text-xs tracking-[0.2em] text-slate-600">•••</li>
              <XpLeaderboardRow entry={yourEntry} current />
            </>
          )}
        </ol>
      )}
    </section>
  );
}

function XpLeaderboardRow({
  entry,
  current,
}: {
  entry: XpLeaderboardEntry;
  current: boolean;
}) {
  return (
    <li
      className={`grid grid-cols-[2rem_2.25rem_minmax(0,1fr)_auto_auto] items-center gap-3 rounded-xl border px-3 py-2.5 ${
        current
          ? "border-violet-400/35 bg-violet-500/10"
          : "border-white/10 bg-white/[0.025]"
      }`}
    >
      <strong className="text-center text-amber-300">{entry.rank}</strong>
      <UserAvatar name={entry.display_name} avatar={entry.avatar} size="sm" />
      <div className="min-w-0">
        <p className="truncate text-sm font-bold text-white">{entry.display_name}</p>
        <p className="truncate text-xs text-slate-500" dir="ltr">@{entry.username}</p>
      </div>
      <span className="text-xs font-bold text-violet-300">Level {entry.level}</span>
      <strong className="text-sm text-emerald-300" dir="ltr">{entry.xp} XP</strong>
    </li>
  );
}

function StatsStrip({ user, stats }: { user: SessionUser; stats: UserStats }) {
  const statItems = [
    { label: "משחקים", value: stats.games, icon: <AppIcon name="games" className="h-10 w-10" /> },
    { label: "נצחונות", value: user.wins, icon: <AppIcon name="wins" className="h-10 w-10" /> },
    { label: "הפסדים", value: user.losses, icon: <AppIcon name="losses" className="h-10 w-10" /> },
    { label: "דיוק", value: `${stats.accuracy}%`, icon: <AppIcon name="accuracy" className="h-10 w-10" /> },
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
        <GameModeCard icon={<AppIcon name="new-game" className="h-6 w-6" />} label="מול חבר" title="משחק חדש" description="פתחו חדר פרטי והזמינו חבר לקרב בזמן אמת." action={creating ? "פותחים…" : "פתיחת חדר"} onClick={() => void createGame()} primary disabled={creating} />
        <GameModeCard icon={<AppIcon name="daily" className="h-6 w-6" />} label="פעם ביום" title="האתגר היומי" description="אותה קטגוריה לכולם. כמה גבוה תגיעו היום?" action="לאתגר היומי" onClick={() => router.push("/daily")} />
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
      <MatchHistory />
    </div>
  );
}

function SettingsView({
  user,
  onUserChange,
  onSignOut,
}: {
  user: SessionUser;
  onUserChange: (user: SessionUser) => void;
  onSignOut: () => void | Promise<void>;
}) {
  const [profile, setProfile] = useState(user);
  const [displayName, setDisplayName] = useState(user.display_name);
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [email, setEmail] = useState("");
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [busyAction, setBusyAction] = useState<
    "profile" | "password" | "email" | "delete" | null
  >(null);
  const [feedback, setFeedback] = useState<{
    action: "profile" | "password" | "email" | "delete";
    kind: "success" | "error";
    text: string;
  } | null>(null);
  const supabaseAccountActionsAvailable =
    SUPABASE_AUTH_ENABLED && SUPABASE_AUTH_CONFIGURED;

  async function changeDisplayName(event: React.FormEvent) {
    event.preventDefault();
    const cleanDisplayName = displayName.trim();
    setFeedback(null);
    if (cleanDisplayName.length < 2) {
      setFeedback({ action: "profile", kind: "error", text: "הכינוי חייב להכיל לפחות שני תווים" });
      return;
    }

    setBusyAction("profile");
    try {
      await updateProfile(user.username, cleanDisplayName);
      const refreshed = await refreshSessionUser();
      if (refreshed) {
        setProfile(refreshed);
        setDisplayName(refreshed.display_name);
        onUserChange(refreshed);
      }
      if (supabaseAccountActionsAvailable) {
        await getSupabaseClient().auth.refreshSession();
      }
      setFeedback({ action: "profile", kind: "success", text: "הכינוי עודכן בהצלחה" });
    } catch {
      setFeedback({
        action: "profile",
        kind: "error",
        text: "עדכון הכינוי נכשל. נסו שוב.",
      });
    } finally {
      setBusyAction(null);
    }
  }

  async function changePassword(event: React.FormEvent) {
    event.preventDefault();
    setFeedback(null);
    if (password.length < 8) {
      setFeedback({ action: "password", kind: "error", text: "הסיסמה חייבת להכיל לפחות 8 תווים" });
      return;
    }
    if (password !== passwordConfirmation) {
      setFeedback({ action: "password", kind: "error", text: "הסיסמאות אינן זהות" });
      return;
    }

    setBusyAction("password");
    try {
      const { error } = await getSupabaseClient().auth.updateUser({ password });
      if (error) throw error;
      setPassword("");
      setPasswordConfirmation("");
      setFeedback({ action: "password", kind: "success", text: "הסיסמה עודכנה בהצלחה" });
    } catch {
      setFeedback({
        action: "password",
        kind: "error",
        text: "עדכון הסיסמה נכשל. נסו שוב.",
      });
    } finally {
      setBusyAction(null);
    }
  }

  async function changeEmail(event: React.FormEvent) {
    event.preventDefault();
    const cleanEmail = email.trim();
    setFeedback(null);
    if (!cleanEmail) {
      setFeedback({ action: "email", kind: "error", text: "יש להזין כתובת אימייל" });
      return;
    }

    setBusyAction("email");
    try {
      const { error } = await getSupabaseClient().auth.updateUser({ email: cleanEmail });
      if (error) throw error;
      setEmail("");
      setFeedback({
        action: "email",
        kind: "success",
        text: "שלחנו הודעת אישור לכתובת החדשה. השינוי יושלם לאחר אישור האימייל.",
      });
    } catch {
      setFeedback({
        action: "email",
        kind: "error",
        text: "עדכון כתובת האימייל נכשל. נסו שוב.",
      });
    } finally {
      setBusyAction(null);
    }
  }

  async function removeAccount() {
    if (deleteConfirmation.trim() !== user.username) return;
    setFeedback(null);
    setBusyAction("delete");
    try {
      await deleteAccount();
      if (supabaseAccountActionsAvailable) {
        await getSupabaseClient().auth.signOut();
      }
      await onSignOut();
    } catch {
      setFeedback({
        action: "delete",
        kind: "error",
        text: "מחיקת החשבון נכשלה. נסו שוב.",
      });
      setBusyAction(null);
    }
  }

  function actionFeedback(action: "profile" | "password" | "email" | "delete") {
    if (!feedback || feedback.action !== action) return null;
    return (
      <p className={`mt-3 text-sm ${feedback.kind === "success" ? "text-emerald-300" : "text-rose-300"}`}>
        {feedback.text}
      </p>
    );
  }

  function changeAvatar(avatar: string) {
    const updated = { ...profile, avatar };
    setProfile(updated);
    onUserChange(updated);
  }

  return (
    <div className="dashboard-view">
      <ViewHeading eyebrow="החשבון שלך" title="הגדרות" description="פרטי החשבון ופעולות זמינות." />
      <section className="settings-panel surface-panel">
        <div className="settings-profile">
          <UserAvatar
            name={profile.display_name}
            avatar={profile.avatar}
            online
            size="lg"
          />
          <div><h2>{profile.display_name}</h2><p dir="ltr">@{profile.username}</p></div>
          <CoinPill coins={profile.coins} />
        </div>

        <div className="section-heading pt-5">
          <div><span>פרטים ואבטחה</span><h2>ניהול החשבון</h2></div>
        </div>

        <div className="grid gap-4 py-4 lg:grid-cols-2">
          <AvatarPicker
            currentAvatar={profile.avatar}
            onAvatarChange={changeAvatar}
          />
          <form onSubmit={changeDisplayName} className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
            <h3 className="font-black text-white">שינוי כינוי</h3>
            <p className="mt-1 text-sm text-slate-400">זהו השם שיוצג לשחקנים אחרים.</p>
            <label className="mt-4 block text-sm font-bold text-slate-300" htmlFor="settings-display-name">כינוי חדש</label>
            <input id="settings-display-name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} minLength={2} maxLength={64} className="dark-input mt-2 w-full" disabled={busyAction !== null} />
            <button type="submit" className="primary-button mt-3 w-full px-4 py-3" disabled={busyAction !== null || displayName.trim() === profile.display_name}>
              {busyAction === "profile" ? "מעדכנים…" : "עדכון הכינוי"}
            </button>
            {actionFeedback("profile")}
          </form>

          {supabaseAccountActionsAvailable && (
            <form onSubmit={changePassword} className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <h3 className="font-black text-white">שינוי סיסמה</h3>
              <p className="mt-1 text-sm text-slate-400">הסיסמה החדשה חייבת להכיל לפחות 8 תווים.</p>
              <label className="mt-4 block text-sm font-bold text-slate-300" htmlFor="settings-password">סיסמה חדשה</label>
              <input id="settings-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} autoComplete="new-password" className="dark-input mt-2 w-full" disabled={busyAction !== null} />
              <label className="mt-3 block text-sm font-bold text-slate-300" htmlFor="settings-password-confirmation">אימות סיסמה</label>
              <input id="settings-password-confirmation" type="password" value={passwordConfirmation} onChange={(event) => setPasswordConfirmation(event.target.value)} minLength={8} autoComplete="new-password" className="dark-input mt-2 w-full" disabled={busyAction !== null} />
              <button type="submit" className="primary-button mt-3 w-full px-4 py-3" disabled={busyAction !== null}>
                {busyAction === "password" ? "מעדכנים…" : "עדכון הסיסמה"}
              </button>
              {actionFeedback("password")}
            </form>
          )}

          {supabaseAccountActionsAvailable && (
            <form onSubmit={changeEmail} className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <h3 className="font-black text-white">שינוי כתובת אימייל</h3>
              <p className="mt-1 text-sm text-slate-400">לאישור השינוי יישלח אימייל לכתובת החדשה.</p>
              <label className="mt-4 block text-sm font-bold text-slate-300" htmlFor="settings-email">כתובת אימייל חדשה</label>
              <input id="settings-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" dir="ltr" className="dark-input mt-2 w-full text-left" disabled={busyAction !== null} />
              <button type="submit" className="primary-button mt-3 w-full px-4 py-3" disabled={busyAction !== null}>
                {busyAction === "email" ? "שולחים…" : "עדכון כתובת האימייל"}
              </button>
              {actionFeedback("email")}
            </form>
          )}
        </div>

        <div className="rounded-xl border border-rose-400/25 bg-rose-500/[0.06] p-4">
          <h3 className="font-black text-rose-200">מחיקת החשבון</h3>
          <p className="mt-1 text-sm leading-6 text-slate-400">הפעולה תמחק לצמיתות את החשבון, החברים, התוצאות וכל היסטוריית המשחקים שלך. לא ניתן לבטל אותה.</p>
          <label className="mt-4 block text-sm font-bold text-slate-300" htmlFor="settings-delete-confirmation">
            לאישור, יש להקליד את שם המשתמש <span dir="ltr" className="text-rose-200">{user.username}</span>
          </label>
          <input id="settings-delete-confirmation" value={deleteConfirmation} onChange={(event) => setDeleteConfirmation(event.target.value)} autoComplete="off" dir="ltr" className="dark-input mt-2 w-full text-left" disabled={busyAction !== null} />
          <button type="button" onClick={() => void removeAccount()} className="mt-3 w-full rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm font-black text-rose-200 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-50" disabled={busyAction !== null || deleteConfirmation.trim() !== user.username}>
            {busyAction === "delete" ? "מוחקים את החשבון…" : "מחיקת החשבון לצמיתות"}
          </button>
          {actionFeedback("delete")}
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

function LobbyDashboard({
  user,
  onUserChange,
  onSignOut,
}: {
  user: SessionUser;
  onUserChange: (user: SessionUser) => void;
  onSignOut: () => void | Promise<void>;
}) {
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
            <div><CoinPill coins={user.coins} /><UserAvatar name={user.display_name} avatar={user.avatar} online size="sm" /></div>
          </header>
          {activeView === "home" && <HomeView user={user} stats={stats} onNavigate={navigate} />}
          {activeView === "games" && <GameActions user={user} />}
          {activeView === "friends" && <div className="dashboard-view"><FriendsPanel key={user.id} /></div>}
          {activeView === "stats" && <StatsView user={user} stats={stats} />}
          {activeView === "settings" && (
            <SettingsView
              user={user}
              onUserChange={onUserChange}
              onSignOut={onSignOut}
            />
          )}
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
  return (
    <LobbyDashboard
      user={auth.user}
      onUserChange={auth.updateUser}
      onSignOut={auth.signOut}
    />
  );
}

function DemoLobby() {
  const [demoUsers, setDemoUsers] = useState<DemoSession[]>([]);
  const [user, setUser] = useState<SessionUser | null>(() => getUser());
  const userId = user?.id;
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDemoUsers().then(setDemoUsers).catch(() => setError("השרת זמין, אבל נתוני הדמו עדיין לא מוכנים."));
  }, []);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    refreshSessionUser()
      .then((freshUser) => {
        if (!cancelled && freshUser) setUser(freshUser);
      })
      .catch(() => {
        // Keep the cached demo profile available while the backend wakes.
      });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  if (user) {
    return (
      <LobbyDashboard
        user={user}
        onUserChange={(updated) => {
          const token = getToken();
          if (token) saveSession(token, updated);
          setUser(updated);
        }}
        onSignOut={() => { clearSession(); setUser(null); }}
      />
    );
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
              <UserAvatar name={demo.user.display_name} avatar={demo.user.avatar} size="md" />
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
