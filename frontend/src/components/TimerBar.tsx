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
    return (
      <div className="mt-2 flex items-center justify-center gap-3">
        <span className="h-1 flex-1 rounded-full bg-violet-300/25" />
        <span className="grid h-11 w-11 place-items-center rounded-full border-2 border-slate-300 bg-[#fff8e9] font-mono text-sm font-black text-slate-500">
          —
        </span>
        <span className="h-1 flex-1 rounded-full bg-emerald-500/25" />
      </div>
    );
  }

  const fraction = Math.min(1, remainingMs / (turnSeconds * 1000));
  const seconds = Math.ceil(remainingMs / 1000);
  const urgent = seconds <= 5;

  return (
    <div className="mt-2 flex items-center justify-center gap-3">
      <div className="h-1 flex-1 overflow-hidden rounded-full bg-violet-300/20">
        <div className="h-full rounded-full bg-violet-600" style={{ width: `${fraction * 100}%` }} />
      </div>
      <span
        className={`grid h-12 w-12 shrink-0 place-items-center rounded-full bg-[#fff8e9] font-mono text-lg font-black tabular-nums transition ${
          urgent ? "animate-pulse text-rose-600" : "text-slate-900"
        }`}
        style={{
          border: "3px solid transparent",
          background: `linear-gradient(#fff8e9, #fff8e9) padding-box, conic-gradient(${urgent ? "#e11d48" : "#8b5bc6"} ${fraction * 360}deg, #d7d0c2 0deg) border-box`,
        }}
      >
        {seconds}
      </span>
      <div className="h-1 flex-1 overflow-hidden rounded-full bg-emerald-500/20">
        <div
          className="mr-auto h-full rounded-full bg-emerald-600"
          style={{ width: `${fraction * 100}%` }}
        />
      </div>
    </div>
  );
}
