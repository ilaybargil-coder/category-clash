"use client";

import { useEffect, useState } from "react";

interface Props {
  deadlineEpochMs: number | null;
  turnSeconds: number;
  clockOffsetMs: number;
  active: boolean;
}

/** Renders the countdown locally, but only from server-provided deadlines —
 * the client never decides when time is actually up. */
export default function TimerBar({
  deadlineEpochMs,
  turnSeconds,
  clockOffsetMs,
  active,
}: Props) {
  const [remainingMs, setRemainingMs] = useState<number | null>(null);

  useEffect(() => {
    if (!active || deadlineEpochMs === null) return;
    const tick = () => {
      const serverNow = Date.now() + clockOffsetMs;
      setRemainingMs(Math.max(0, deadlineEpochMs - serverNow));
    };
    const initialTick = setTimeout(tick, 0);
    const interval = setInterval(tick, 100);
    return () => {
      clearTimeout(initialTick);
      clearInterval(interval);
    };
  }, [deadlineEpochMs, clockOffsetMs, active]);

  if (!active || deadlineEpochMs === null || remainingMs === null) {
    return <div className="h-2 rounded-full bg-slate-200" />;
  }

  const fraction = Math.min(1, remainingMs / (turnSeconds * 1000));
  const seconds = Math.ceil(remainingMs / 1000);
  const urgent = seconds <= 5;

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
        <div
          className={`h-full rounded-full transition-[width] duration-100 ease-linear ${
            urgent ? "bg-rose-500" : "bg-violet-500"
          }`}
          style={{ width: `${fraction * 100}%` }}
        />
      </div>
      <span
        className={`w-7 text-center font-mono text-sm font-bold tabular-nums ${
          urgent ? "animate-pulse text-rose-600" : "text-slate-500"
        }`}
      >
        {seconds}
      </span>
    </div>
  );
}
