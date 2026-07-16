"use client";

import { useEffect, useRef } from "react";
import type { AnswerItem, PlayerInfo } from "@/lib/types";

const STATUS_META: Record<
  string,
  { icon: string; label: string | null; tone: string }
> = {
  VALID: { icon: "✓", label: null, tone: "text-emerald-600 bg-emerald-100" },
  INVALID: {
    icon: "✕",
    label: "לא מתאים לשאלה",
    tone: "text-rose-600 bg-rose-100",
  },
  DUPLICATE: {
    icon: "=",
    label: "כבר נאמר",
    tone: "text-amber-600 bg-amber-100",
  },
  TOO_SIMILAR: {
    icon: "≈",
    label: "זהה במשמעות לתשובה קודמת",
    tone: "text-amber-600 bg-amber-100",
  },
};

interface Props {
  answers: AnswerItem[];
  myUserId: number;
  players: PlayerInfo[];
}

export default function AnswerFeed({ answers, myUserId, players }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [answers.length]);

  const nameOf = (userId: number) =>
    players.find((p) => p.user_id === userId)?.display_name ?? "";

  return (
    <div className="flex flex-1 flex-col gap-2 overflow-y-auto px-4 py-3">
      {answers.length === 0 && (
        <p className="my-auto text-center text-sm text-slate-400">
          עוד אין תשובות בסיבוב הזה — בהצלחה!
        </p>
      )}
      {answers.map((answer) => {
        const mine = answer.user_id === myUserId;
        const meta = STATUS_META[answer.status] ?? STATUS_META.INVALID;
        const wrong = answer.status !== "VALID";
        return (
          <div
            key={answer.submission_id}
            data-submission-id={answer.submission_id}
            className={`flex ${mine ? "justify-start" : "justify-end"}`}
          >
            <div
              className={`max-w-[80%] animate-pop-in rounded-2xl px-3.5 py-2 shadow-sm ${
                mine
                  ? "rounded-br-md bg-violet-600 text-white"
                  : "rounded-bl-md bg-white text-slate-800"
              } ${wrong ? "opacity-80" : ""} ${
                answer.status === "INVALID" ? "animate-shake" : ""
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-black ${meta.tone}`}
                >
                  {meta.icon}
                </span>
                <span
                  className={`text-base font-medium ${
                    wrong ? "line-through decoration-1" : ""
                  }`}
                >
                  {answer.raw_text}
                </span>
              </div>
              <div
                className={`mt-0.5 flex items-baseline gap-2 text-[11px] ${
                  mine ? "text-violet-200" : "text-slate-400"
                }`}
              >
                <span>{nameOf(answer.user_id)}</span>
                {meta.label && <span>· {meta.label}</span>}
              </div>
            </div>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
