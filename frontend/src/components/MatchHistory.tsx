"use client";

import { useEffect, useState } from "react";
import AppIcon from "@/components/AppIcon";
import { fetchMatchHistory, type MatchHistoryItem } from "@/lib/api";

const relativeTime = new Intl.RelativeTimeFormat("he", { numeric: "auto" });

function formatRelativeDate(value: string): string {
  const elapsedSeconds = (new Date(value).getTime() - Date.now()) / 1000;
  const intervals: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ["year", 60 * 60 * 24 * 365],
    ["month", 60 * 60 * 24 * 30],
    ["week", 60 * 60 * 24 * 7],
    ["day", 60 * 60 * 24],
    ["hour", 60 * 60],
    ["minute", 60],
  ];

  for (const [unit, seconds] of intervals) {
    if (Math.abs(elapsedSeconds) >= seconds) {
      return relativeTime.format(Math.round(elapsedSeconds / seconds), unit);
    }
  }
  return relativeTime.format(Math.round(elapsedSeconds), "second");
}

export default function MatchHistory() {
  const [matches, setMatches] = useState<MatchHistoryItem[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchMatchHistory()
      .then((result) => {
        if (!cancelled) setMatches(result);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="surface-panel rounded-2xl p-4 sm:p-5" aria-label="היסטוריית משחקים">
      <div className="flex items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold text-violet-300">הקרבות האחרונים</span>
          <h2 className="mt-1 text-xl font-black text-white">היסטוריית משחקים</h2>
        </div>
        <AppIcon name="list" className="h-6 w-6" />
      </div>

      {matches === null && !failed && (
        <p className="mt-5 text-center text-sm text-slate-500">טוענים משחקים…</p>
      )}
      {failed && (
        <p className="mt-5 text-center text-sm text-rose-300">לא הצלחנו לטעון את המשחקים</p>
      )}
      {matches?.length === 0 && (
        <p className="mt-5 text-center text-sm text-slate-400">עדיין אין משחקים</p>
      )}
      {matches && matches.length > 0 && (
        <ul className="mt-4 space-y-2">
          {matches.map((match) => (
            <li
              key={match.id}
              className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-xl border border-white/10 bg-white/[0.025] px-3 py-3 sm:grid-cols-[minmax(0,1fr)_auto_auto]"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-white">
                  {match.opponent.display_name}
                </p>
                <p className="truncate text-xs text-slate-500" dir="ltr">
                  @{match.opponent.username}
                </p>
              </div>
              <div className="text-left sm:order-3">
                <strong className="text-lg text-white" dir="ltr">
                  {match.score.player}–{match.score.opponent}
                </strong>
                <p className="text-xs text-slate-500">{formatRelativeDate(match.finished_at)}</p>
              </div>
              <span
                className={`w-fit rounded-full border px-2.5 py-1 text-xs font-black sm:order-2 ${
                  match.won
                    ? "border-emerald-300/25 bg-emerald-400/10 text-emerald-300"
                    : "border-rose-300/25 bg-rose-400/10 text-rose-300"
                }`}
                dir="ltr"
              >
                {match.won ? "WIN" : "LOSS"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
