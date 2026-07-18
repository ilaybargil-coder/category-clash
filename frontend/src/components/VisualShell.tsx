"use client";

import Link from "next/link";
import type { SessionUser } from "@/lib/types";

export type DashboardView =
  | "home"
  | "games"
  | "friends"
  | "stats"
  | "settings";

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
  activeView,
  onNavigate,
}: {
  user: SessionUser;
  activeView: DashboardView;
  onNavigate: (view: DashboardView) => void;
}) {
  return (
    <aside className="dashboard-left desktop-sidebar surface-panel" dir="rtl">
      <section className="sidebar-player-card">
        <UserAvatar name={user.display_name} online size="lg" />
        <h2>{user.display_name}</h2>
        <p dir="ltr">@{user.username}</p>
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

    </aside>
  );
}

function DailyChallengeWidget() {
  return (
    <section className="dashboard-widget daily-widget">
      <div className="daily-widget__icon" aria-hidden="true">⚡</div>
      <div className="min-w-0 flex-1">
        <span>האתגר היומי</span>
        <h2>מוכנים לאתגר של היום?</h2>
        <Link href="/daily" className="daily-widget__link">לאתגר היומי ←</Link>
      </div>
    </section>
  );
}

export function DashboardWidgets() {
  return (
    <div className="dashboard-widgets">
      <DailyChallengeWidget />
    </div>
  );
}

export function RightSidebar({
  user,
}: {
  user: SessionUser;
}) {
  return (
    <aside className="dashboard-right" dir="rtl">
      <div className="right-sidebar__brand"><BrandMark compact /></div>
      <section className="right-mini-profile surface-panel">
        <UserAvatar name={user.display_name} online size="md" />
        <div className="min-w-0 flex-1">
          <strong>{user.display_name}</strong>
          <span dir="ltr">@{user.username}</span>
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
