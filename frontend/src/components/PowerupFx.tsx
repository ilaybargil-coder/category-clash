"use client";

import { useEffect, useRef, useState } from "react";
import type { Phase } from "@/lib/types";

export type PowerupType = "swap_question" | "extend_time" | "use_joker";

export interface PowerupFxEvent {
  id: string;
  type: PowerupType;
  actor: "you" | "opponent";
  extendSeconds?: number;
  roundNo: number;
  phase: Phase;
}

const ANNOUNCEMENTS: Record<
  PowerupType,
  Record<PowerupFxEvent["actor"], string>
> = {
  use_joker: {
    you: "🃏 הפעלת ג'וקר!",
    opponent: "🃏 היריב הפעיל ג'וקר!",
  },
  swap_question: {
    you: "🔄 הפעלת החלפה!",
    opponent: "🔄 היריב הפעיל החלפה!",
  },
  extend_time: {
    you: "⏱️ הפעלת הארכה!",
    opponent: "⏱️ היריב הפעיל הארכה!",
  },
};

export default function PowerupFx({
  event,
  roundNo,
  phase,
}: {
  event: PowerupFxEvent | null;
  roundNo: number;
  phase: Phase;
}) {
  const [activeEvent, setActiveEvent] = useState<PowerupFxEvent | null>(null);
  const shownEventIdsRef = useRef(new Set<string>());

  useEffect(() => {
    if (
      !event ||
      event.roundNo !== roundNo ||
      event.phase !== phase ||
      shownEventIdsRef.current.has(event.id)
    ) {
      return;
    }

    const showTimer = window.setTimeout(() => {
      if (shownEventIdsRef.current.has(event.id)) return;
      shownEventIdsRef.current.add(event.id);
      setActiveEvent(event);
    }, 0);
    return () => window.clearTimeout(showTimer);
  }, [event, phase, roundNo]);

  useEffect(() => {
    if (!activeEvent) return;
    const isCurrentRound =
      activeEvent.roundNo === roundNo && activeEvent.phase === phase;
    const dismissTimer = window.setTimeout(
      () => setActiveEvent(null),
      isCurrentRound ? 1400 : 0
    );
    return () => window.clearTimeout(dismissTimer);
  }, [activeEvent, phase, roundNo]);

  const visibleEvent =
    activeEvent?.roundNo === roundNo && activeEvent.phase === phase
      ? activeEvent
      : null;

  if (!visibleEvent) return null;

  const announcement = ANNOUNCEMENTS[visibleEvent.type][visibleEvent.actor];

  return (
    <div
      className={`powerup-fx powerup-fx--${visibleEvent.type} pointer-events-none fixed inset-0 z-[9999]`}
      dir="rtl"
      role="status"
      aria-live="assertive"
      aria-label={announcement}
    >
      <div className="powerup-fx__tint" />

      {visibleEvent.type === "use_joker" && (
        <div className="powerup-fx__joker-stage" aria-hidden="true">
          <div className="powerup-fx__joker-card">
            <span>🃏</span>
          </div>
          <div className="powerup-fx__sparkles">
            {Array.from({ length: 12 }, (_, index) => (
              <i key={index}>✦</i>
            ))}
          </div>
        </div>
      )}

      {visibleEvent.type === "swap_question" && (
        <div className="powerup-fx__swap-stage" aria-hidden="true">
          <div className="powerup-fx__question-card powerup-fx__question-card--out">
            ?
          </div>
          <div className="powerup-fx__question-card powerup-fx__question-card--in">
            !
          </div>
        </div>
      )}

      {visibleEvent.type === "extend_time" && (
        <div className="powerup-fx__extend-stage" aria-hidden="true">
          <div className="powerup-fx__timer-track">
            <div className="powerup-fx__timer-fill" />
          </div>
          <strong className="powerup-fx__extra-time">
            +{visibleEvent.extendSeconds ?? 0} שניות
          </strong>
        </div>
      )}

      <div className="powerup-fx__announcement">{announcement}</div>
    </div>
  );
}
