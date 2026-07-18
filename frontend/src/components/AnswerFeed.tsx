"use client";

import { useEffect, useRef } from "react";
import type { AnswerItem, PlayerInfo } from "@/lib/types";

const STATUS_META: Record<
  string,
  { icon: string; label: string | null; tone: string }
> = {
  VALID: { icon: "✓", label: null, tone: "text-emerald-700 bg-emerald-100" },
  INVALID: {
    icon: "✕",
    label: "לא מתאים לשאלה",
    tone: "text-rose-700 bg-rose-100",
  },
  DUPLICATE: {
    icon: "=",
    label: "כבר נאמר",
    tone: "text-amber-700 bg-amber-100",
  },
  TOO_SIMILAR: {
    icon: "≈",
    label: "זהה במשמעות לתשובה קודמת",
    tone: "text-amber-700 bg-amber-100",
  },
};

interface Props {
  answers: AnswerItem[];
  myUserId: number;
  players: PlayerInfo[];
}

export default function AnswerFeed({ answers, myUserId, players }: Props) {
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const feed = feedRef.current;
    if (feed) feed.scrollTop = feed.scrollHeight;
  }, [answers.length]);

  const nameOf = (userId: number) =>
    players.find((p) => p.user_id === userId)?.display_name ?? "";

  return (
    <div
      ref={feedRef}
      className="answer-feed flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-3 py-4 sm:px-5"
    >
      {answers.length === 0 && (
        <div className="my-auto text-center">
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-full border border-white/10 bg-white/[0.025] text-xl text-slate-500">
            ◌
          </div>
          <p className="mt-3 text-sm font-bold text-slate-500">הזירה עדיין ריקה</p>
          <p className="mt-1 text-xs text-slate-600">התשובה הראשונה תופיע כאן</p>
        </div>
      )}
      {answers.map((answer) => {
        const mine = answer.user_id === myUserId;
        const meta = STATUS_META[answer.status] ?? STATUS_META.INVALID;
        const wrong = answer.status !== "VALID";
        const ownValid = mine && answer.status === "VALID";
        return (
          <div
            key={answer.submission_id}
            data-submission-id={answer.submission_id}
            className={`flex ${mine ? "justify-start" : "justify-end"}`}
          >
            <div
              className={`max-w-[82%] rounded-xl px-3.5 py-2.5 shadow-lg sm:max-w-[65%] ${
                ownValid ? "answer-own-valid" : "animate-pop-in"
              } ${
                mine
                  ? "rounded-br-sm border border-violet-300/20 bg-gradient-to-l from-violet-700 to-violet-600 text-white"
                  : "rounded-bl-sm border border-[#e4dbc8] bg-[#f5efdf] text-slate-900"
              } ${wrong ? "opacity-80" : ""} ${
                answer.status === "INVALID" ? "animate-shake" : ""
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-black ${meta.tone} ${
                    ownValid ? "answer-own-valid__mark" : ""
                  }`}
                >
                  {meta.icon}
                </span>
                <span
                  className={`text-base font-medium ${
                    wrong ? "line-through decoration-1" : ""
                  }`}
                >
                  {answer.status === "VALID"
                    ? (answer.canonical ?? answer.raw_text)
                    : answer.raw_text}
                </span>
              </div>
              <div
                className={`mt-0.5 flex items-baseline gap-2 text-[11px] ${
                  mine ? "text-violet-200" : "text-slate-500"
                }`}
              >
                <span>{nameOf(answer.user_id)}</span>
                {meta.label && <span>· {meta.label}</span>}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
