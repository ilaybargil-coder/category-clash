"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { ArrowLeftIcon, CoinIcon, LightningIcon } from "@/components/icons";
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
  icon: ReactNode;
}> = [
  {
    id: "home",
    label: "בית",
    shortLabel: "בית",
    icon: (
      <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d="m3 11 9-8 9 8" />
        <path d="M5 10v11h14V10" />
        <path d="M9 21v-6h6v6" />
      </svg>
    ),
  },
  {
    id: "games",
    label: "משחקים",
    shortLabel: "משחקים",
    icon: (
      <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8Z" />
      </svg>
    ),
  },
  {
    id: "friends",
    label: "חברים",
    shortLabel: "חברים",
    icon: (
      <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    id: "stats",
    label: "סטטיסטיקות",
    shortLabel: "נתונים",
    icon: (
      <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 3v18h18" />
        <path d="M7 16v-5" />
        <path d="M12 16V7" />
        <path d="M17 16v-3" />
      </svg>
    ),
  },
  {
    id: "settings",
    label: "הגדרות",
    shortLabel: "הגדרות",
    icon: (
      <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.5 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6h.08A1.65 1.65 0 0 0 10 3.09V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.12.6.64 1.04 1.25 1.08H21a2 2 0 1 1 0 4h-.09A1.65 1.65 0 0 0 19.4 15Z" />
      </svg>
    ),
  },
];

export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand-lockup ${compact ? "brand-lockup--compact" : ""}`}>
      <div className="brand-symbol" aria-hidden="true">
        <span className="brand-card brand-card--purple" />
        <span className="brand-card brand-card--cream" />
        <span className="brand-bolt">
          <LightningIcon size={compact ? 30 : 48} />
        </span>
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
      <span className="coin-icon" aria-hidden="true"><CoinIcon className="h-3.5 w-3.5" /></span>
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
            <span className="sidebar-link__icon" aria-hidden="true">
              {item.icon}
            </span>
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
      <div className="daily-widget__icon" aria-hidden="true"><LightningIcon className="h-5 w-5" /></div>
      <div className="min-w-0 flex-1">
        <span>האתגר היומי</span>
        <h2>מוכנים לאתגר של היום?</h2>
        <Link href="/daily" className="daily-widget__link">לאתגר היומי <ArrowLeftIcon className="h-3.5 w-3.5" /></Link>
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
