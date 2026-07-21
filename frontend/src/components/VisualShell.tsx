"use client";

import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import AppIcon from "@/components/AppIcon";
import { ArrowLeftIcon } from "@/components/icons";
import { avatarSrcFor } from "@/lib/avatar";
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
    icon: <AppIcon name="home" className="h-7 w-7" />,
  },
  {
    id: "games",
    label: "משחקים",
    shortLabel: "משחקים",
    icon: <AppIcon name="games" className="h-7 w-7" />,
  },
  {
    id: "friends",
    label: "חברים",
    shortLabel: "חברים",
    icon: <AppIcon name="friends" className="h-7 w-7" />,
  },
  {
    id: "stats",
    label: "סטטיסטיקות",
    shortLabel: "נתונים",
    icon: <AppIcon name="statistics" className="h-7 w-7" />,
  },
  {
    id: "settings",
    label: "הגדרות",
    shortLabel: "הגדרות",
    icon: <AppIcon name="settings" className="h-7 w-7" />,
  },
];

export function BrandMark({ compact = false }: { compact?: boolean }) {
  const size = compact ? 64 : 196;

  return (
    <Image
      src="/assets/logo.png"
      alt="קרב קטגוריות"
      width={size}
      height={size}
      priority={!compact}
    />
  );
}

export function UserAvatar({
  name,
  avatar,
  online = false,
  size = "md",
}: {
  name: string;
  avatar?: string | null;
  online?: boolean;
  size?: "sm" | "md" | "lg";
}) {
  const fixedSize = {
    sm: "h-9 w-9",
    md: "h-[3.2rem] w-[3.2rem]",
    lg: "h-20 w-20",
  }[size];

  return (
    <span
      className={`user-avatar user-avatar--${size} relative ${fixedSize} overflow-hidden rounded-full`}
      aria-label={name}
    >
      <img
        src={avatarSrcFor(avatar, name)}
        alt={name}
        className="absolute inset-0 h-full w-full object-cover"
      />
      {online && <span className="online-dot" />}
    </span>
  );
}

export function CoinPill({ coins }: { coins: number }) {
  return (
    <div className="coin-pill" aria-label={`${coins} מטבעות`}>
      <span>{coins.toLocaleString("he-IL")}</span>
      <span className="coin-icon" aria-hidden="true"><AppIcon name="coins" className="h-4 w-4" /></span>
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
        <UserAvatar name={user.display_name} avatar={user.avatar} online size="lg" />
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
      <div className="daily-widget__icon" aria-hidden="true"><AppIcon name="daily" className="h-6 w-6" /></div>
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
        <UserAvatar name={user.display_name} avatar={user.avatar} online size="md" />
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
