"use client";

import { useEffect, useRef, useState } from "react";
import { playTick } from "@/lib/sfx";

interface Props {
  deadlineEpochMs: number | null;
  turnSeconds: number;
  clockOffsetMs: number;
  active: boolean;
  isCurrentPlayerTurn: boolean;
}

/** Renders the countdown locally, but only from server-provided deadlines —
 * the client never decides when time is actually up. */
export default function TimerBar({
  deadlineEpochMs,
  turnSeconds,
  clockOffsetMs,
  active,
  isCurrentPlayerTurn,
}: Props) {
  const [countdown, setCountdown] = useState<{
    deadlineEpochMs: number;
    remainingMs: number;
  } | null>(null);
  const playedTicksRef = useRef<{
    deadlineEpochMs: number | null;
    isCurrentPlayerTurn: boolean;
    seconds: Set<number>;
  }>({ deadlineEpochMs: null, isCurrentPlayerTurn: false, seconds: new Set() });

  useEffect(() => {
    if (
      playedTicksRef.current.deadlineEpochMs !== deadlineEpochMs ||
      playedTicksRef.current.isCurrentPlayerTurn !== isCurrentPlayerTurn
    ) {
      playedTicksRef.current = {
        deadlineEpochMs,
        isCurrentPlayerTurn,
        seconds: new Set(),
      };
    }
    if (!active || deadlineEpochMs === null) return;

    const tick = () => {
      const serverNow = Date.now() + clockOffsetMs;
      const nextRemainingMs = Math.max(0, deadlineEpochMs - serverNow);
      const seconds = Math.ceil(nextRemainingMs / 1000);
      setCountdown({ deadlineEpochMs, remainingMs: nextRemainingMs });

      if (
        isCurrentPlayerTurn &&
        seconds >= 1 &&
        seconds <= 3 &&
        !playedTicksRef.current.seconds.has(seconds)
      ) {
        playedTicksRef.current.seconds.add(seconds);
        playTick();
      }
    };
    const initialTick = setTimeout(tick, 0);
    const interval = setInterval(tick, 100);
    return () => {
      clearTimeout(initialTick);
      clearInterval(interval);
    };
  }, [deadlineEpochMs, clockOffsetMs, active, isCurrentPlayerTurn]);

  const remainingMs =
    countdown?.deadlineEpochMs === deadlineEpochMs
      ? countdown.remainingMs
      : null;

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
  const critical = remainingMs < 3000;
  const fillColor =
    fraction > 0.5 ? "#4fb596" : fraction >= 0.2 ? "#f0a500" : "#e63946";

  return (
    <div className="mt-2 flex items-center justify-center gap-3">
      <div className="h-1 flex-1 overflow-hidden rounded-full bg-violet-300/20">
        <div
          className={`timer-bar-fill h-full rounded-full ${
            critical ? "timer-bar-fill--critical" : ""
          }`}
          style={{ width: `${fraction * 100}%`, backgroundColor: fillColor }}
        />
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
          className={`timer-bar-fill mr-auto h-full rounded-full ${
            critical ? "timer-bar-fill--critical" : ""
          }`}
          style={{ width: `${fraction * 100}%`, backgroundColor: fillColor }}
        />
      </div>
    </div>
  );
}
