"use client";

import type { SessionUser } from "@/lib/types";

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
      <span className="coin-icon">●</span>
    </div>
  );
}

export function DesktopSidebar({
  user,
  onSignOut,
}: {
  user: SessionUser;
  onSignOut: () => void;
}) {
  const games = user.wins + user.losses;
  const winRate = games ? Math.round((user.wins / games) * 100) : 0;
  return (
    <aside className="desktop-sidebar surface-panel">
      <BrandMark />
      <section className="sidebar-profile">
        <UserAvatar name={user.display_name} online size="md" />
        <div className="min-w-0 flex-1">
          <p className="truncate font-black text-white">{user.display_name}</p>
          <p className="truncate text-xs text-slate-500">@{user.username}</p>
        </div>
        <span className="pro-chip">שחקן</span>
      </section>
      <div className="level-card">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>{games} משחקים</span>
          <span>{winRate}% ניצחונות</span>
        </div>
        <div className="level-track">
          <span style={{ width: `${Math.max(8, winRate)}%` }} />
        </div>
      </div>
      <nav className="sidebar-nav" aria-label="ניווט ראשי">
        <a href="#play" className="sidebar-link sidebar-link--active">
          <span>⌂</span> בית
        </a>
        <a href="#friends" className="sidebar-link">
          <span>◎</span> חברים
        </a>
        <a href="#stats" className="sidebar-link">
          <span>◫</span> סטטיסטיקות
        </a>
      </nav>
      <div className="mt-auto space-y-3">
        <button type="button" onClick={onSignOut} className="secondary-button w-full">
          התנתקות
        </button>
        <p className="text-center text-[10px] tracking-[0.25em] text-slate-600">
          BETA EDITION
        </p>
      </div>
    </aside>
  );
}

export function MobileNav() {
  return (
    <nav className="mobile-nav" aria-label="ניווט מובייל">
      <a href="#play" className="mobile-nav__item mobile-nav__item--active">
        <b>⌂</b>
        בית
      </a>
      <a href="#friends" className="mobile-nav__item">
        <b>◎</b>
        חברים
      </a>
      <a href="#stats" className="mobile-nav__item">
        <b>◫</b>
        סטטיסטיקה
      </a>
    </nav>
  );
}
