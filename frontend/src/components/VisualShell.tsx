"use client";

import type { SessionUser } from "@/lib/types";

export type DashboardView =
  | "home"
  | "games"
  | "friends"
  | "stats"
  | "settings";

export interface PlayerProgress {
  games: number;
  accuracy: number;
  level: number;
  xpInLevel: number;
  xpNeeded: number;
  rank: "Bronze" | "Silver" | "Gold";
}

const NAV_ITEMS: Array<{
  id: DashboardView;
  label: string;
  shortLabel: string;
  icon: string;
}> = [
  { id: "home", label: "בית", shortLabel: "בית", icon: "⌂" },
  { id: "games", label: "משחקים", shortLabel: "משחקים", icon: "⚡" },
  { id: "friends", label: "חברים", shortLabel: "חברים", icon: "♙" },
  { id: "stats", label: "סטטיסטיקות", shortLabel: "נתונים", icon: "◫" },
  { id: "settings", label: "הגדרות", shortLabel: "הגדרות", icon: "⚙" },
];

// TODO: real progression backend
const LEADERBOARD = [
  { rank: 1, name: "נועה האלופה", xp: 4850 },
  { rank: 2, name: "מלך המילים", xp: 4620 },
  { rank: 3, name: "שירז", xp: 4310 },
  { rank: 4, name: "Flash77", xp: 3980 },
  { rank: 5, name: "מוח כריש", xp: 3740 },
];

export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand-lockup ${compact ? "brand-lockup--compact" : ""}`}>
      <div className="brand-symbol" aria-hidden="true">
        <span className="brand-card brand-card--purple" />
        <span className="brand-card brand-card--cream" />
        <span className="brand-bolt">ϟ</span>
      </div>
      <div>
        <div className="brand-title">קרב קטגוריות</div>
        {!compact && <div className="brand-subtitle">CATEGORY CLASH</div>}
      </div>
    </div>
  );
}

export function UserAvatar({
  name,
  online = false,
  size = "md",
}: {
  name: string;
  online?: boolean;
  size?: "sm" | "md" | "lg";
}) {
  const initials = name.trim().slice(0, 2) || "?";
  return (
    <span className={`user-avatar user-avatar--${size}`} aria-label={name}>
      {initials}
      {online && <span className="online-dot" />}
    </span>
  );
}

export function CoinPill({ coins }: { coins: number }) {
  return (
    <div className="coin-pill" aria-label={`${coins} מטבעות`}>
      <span>{coins.toLocaleString("he-IL")}</span>
      <span className="coin-icon" aria-hidden="true">●</span>
    </div>
  );
}

export function DesktopSidebar({
  user,
  progress,
  activeView,
  onNavigate,
}: {
  user: SessionUser;
  progress: PlayerProgress;
  activeView: DashboardView;
  onNavigate: (view: DashboardView) => void;
}) {
  const xpPercent = (progress.xpInLevel / progress.xpNeeded) * 100;

  return (
    <aside className="dashboard-left desktop-sidebar surface-panel" dir="rtl">
      <section className="sidebar-player-card">
        <div className="sidebar-player-card__top">
          <UserAvatar name={user.display_name} online size="lg" />
          <span className="level-badge">רמה {progress.level}</span>
        </div>
        <h2>{user.display_name}</h2>
        <p dir="ltr">@{user.username}</p>
        <div className="sidebar-xp-copy">
          <span>התקדמות לרמה הבאה</span>
          <b>{progress.xpInLevel}/{progress.xpNeeded} XP</b>
        </div>
        <div className="level-track" aria-label={`${progress.xpInLevel} מתוך ${progress.xpNeeded} נקודות ניסיון`}>
          <span style={{ width: `${xpPercent}%` }} />
        </div>
        <CoinPill coins={user.coins} />
      </section>

      <nav className="sidebar-nav" aria-label="ניווט ראשי">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            aria-current={activeView === item.id ? "page" : undefined}
            className={`sidebar-link ${
              activeView === item.id ? "sidebar-link--active" : ""
            }`}
          >
            <span className="sidebar-link__icon" aria-hidden="true">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      <section className="premium-card">
        <span aria-hidden="true">✦</span>
        <p>פתחו עוד אתגרים</p>
        <h3>שדרגו לפרימיום</h3>
        <button type="button">לפרטים נוספים</button>
      </section>
    </aside>
  );
}

function LeaderboardWidget() {
  return (
    <section className="dashboard-widget">
      <div className="widget-heading">
        <div>
          <span>הדירוג השבועי</span>
          <h2>טבלת מובילים</h2>
        </div>
        <b>🏆</b>
      </div>
      <ol className="leaderboard-list">
        {LEADERBOARD.map((player) => (
          <li key={player.rank}>
            <span className={`leaderboard-rank leaderboard-rank--${player.rank}`}>
              {player.rank}
            </span>
            <UserAvatar name={player.name} size="sm" />
            <span className="leaderboard-name">{player.name}</span>
            <b>{player.xp.toLocaleString("he-IL")} XP</b>
          </li>
        ))}
      </ol>
      <button type="button" className="widget-link">לכל הדירוגים ←</button>
    </section>
  );
}

function DailyChallengeWidget() {
  return (
    <section className="dashboard-widget daily-widget">
      <div className="daily-widget__icon" aria-hidden="true">⚡</div>
      <div className="min-w-0 flex-1">
        <span>האתגר היומי</span>
        <h2>שליטה בקטגוריות</h2>
        <div className="daily-progress-copy">
          <span>3 מתוך 5 סיבובים</span>
          <b>60%</b>
        </div>
        <div className="level-track"><span style={{ width: "60%" }} /></div>
        <p>השלימו וקבלו <strong>150 ●</strong></p>
      </div>
    </section>
  );
}

export function DashboardWidgets() {
  return (
    <div className="dashboard-widgets">
      <LeaderboardWidget />
      <DailyChallengeWidget />
    </div>
  );
}

export function RightSidebar({
  user,
  progress,
}: {
  user: SessionUser;
  progress: PlayerProgress;
}) {
  return (
    <aside className="dashboard-right" dir="rtl">
      <div className="right-sidebar__brand"><BrandMark compact /></div>
      <section className="right-mini-profile surface-panel">
        <UserAvatar name={user.display_name} online size="md" />
        <div className="min-w-0 flex-1">
          <strong>{user.display_name}</strong>
          <span>{progress.rank} · רמה {progress.level}</span>
        </div>
        <CoinPill coins={user.coins} />
      </section>
      <DashboardWidgets />
    </aside>
  );
}

export function MobileNav({
  activeView,
  onNavigate,
}: {
  activeView: DashboardView;
  onNavigate: (view: DashboardView) => void;
}) {
  return (
    <nav className="mobile-nav" aria-label="ניווט מובייל">
      {NAV_ITEMS.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onNavigate(item.id)}
          aria-current={activeView === item.id ? "page" : undefined}
          className={`mobile-nav__item ${
            activeView === item.id ? "mobile-nav__item--active" : ""
          } ${item.id === "games" ? "mobile-nav__play" : ""}`}
        >
          <b aria-hidden="true">{item.icon}</b>
          <span>{item.shortLabel}</span>
        </button>
      ))}
    </nav>
  );
}
