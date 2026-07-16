"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useGameSocket } from "@/hooks/useGameSocket";
import AnswerFeed from "./AnswerFeed";
import TimerBar from "./TimerBar";
import type { GameState, PlayerInfo } from "@/lib/types";

export default function GameRoom({ code }: { code: string }) {
  const { state, status, rejection, clearRejection, submitAnswer } =
    useGameSocket(code);

  if (status === "unauthorized") {
    return (
      <CenteredNote title="נדרשת התחברות">
        <Link href="/" className="font-bold text-violet-600 underline">
          חזרה למסך הראשי לבחירת שחקן
        </Link>
      </CenteredNote>
    );
  }
  if (status === "room_not_found") {
    return (
      <CenteredNote title="החדר לא נמצא">
        <p className="text-slate-500">
          ייתכן שהמשחק הסתיים או שהקוד שגוי.{" "}
          <Link href="/" className="font-bold text-violet-600 underline">
            חזרה למסך הראשי
          </Link>
        </p>
      </CenteredNote>
    );
  }
  if (status === "room_full") {
    return (
      <CenteredNote title="החדר מלא">
        <p className="text-slate-500">שני שחקנים כבר נמצאים במשחק הזה.</p>
      </CenteredNote>
    );
  }
  if (status === "origin_rejected") {
    return (
      <CenteredNote title="כתובת האתר אינה מורשית">
        <p className="text-slate-500">
          הגדרת האבטחה של שרת המשחק אינה כוללת את כתובת האתר הנוכחית. יש לעדכן
          את משתנה WEBSOCKET_ORIGINS בשרת.
        </p>
      </CenteredNote>
    );
  }
  if (!state) {
    return (
      <CenteredNote title="מתחברים לחדר...">
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-violet-200 border-t-violet-600" />
      </CenteredNote>
    );
  }

  return (
    <GameView
      state={state}
      reconnecting={status !== "open"}
      rejection={rejection}
      clearRejection={clearRejection}
      submitAnswer={submitAnswer}
    />
  );
}

function CenteredNote({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-2xl font-black">{title}</h1>
      {children}
    </main>
  );
}

function GameView({
  state,
  reconnecting,
  rejection,
  clearRejection,
  submitAnswer,
}: {
  state: GameState;
  reconnecting: boolean;
  rejection: string | null;
  clearRejection: () => void;
  submitAnswer: (text: string) => boolean;
}) {
  const me = state.players.find((p) => p.user_id === state.you);
  const opponent = state.players.find((p) => p.user_id !== state.you);
  const myTurn =
    state.phase === "ROUND_ACTIVE" && state.turn_user_id === state.you;

  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (myTurn) inputRef.current?.focus();
  }, [myTurn]);

  // New attempt clears any stale "not your turn" toast.
  useEffect(() => {
    if (rejection) {
      const t = setTimeout(clearRejection, 2500);
      return () => clearTimeout(t);
    }
  }, [rejection, clearRejection]);

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || !myTurn) return;
    if (submitAnswer(text)) setDraft("");
  }

  const pointsOf = (userId?: number) =>
    state.score.find((s) => s.user_id === userId)?.points ?? 0;

  return (
    <main className="mx-auto flex h-dvh max-w-md flex-col bg-slate-100">
      {/* Header: question + score */}
      <header className="space-y-3 bg-gradient-to-l from-violet-700 to-fuchsia-600 px-4 pb-4 pt-5 text-white shadow-md">
        <div className="flex items-center justify-between text-sm">
          <PlayerBadge player={me} points={pointsOf(me?.user_id)} isYou />
          <span className="font-mono text-xs text-violet-200">
            סיבוב {state.round_no || "-"} · עד {state.rounds_to_win} נצחונות
          </span>
          <PlayerBadge player={opponent} points={pointsOf(opponent?.user_id)} />
        </div>
        <h1 className="min-h-[3.5rem] text-center text-xl font-black leading-snug">
          {state.question?.text ?? "ממתינים לשאלה..."}
        </h1>
        <TimerBar
          deadlineEpochMs={state.deadline_epoch_ms}
          turnSeconds={state.turn_seconds}
          clockOffsetMs={state.clock_offset_ms}
          active={state.phase === "ROUND_ACTIVE"}
        />
        <p className="text-center text-sm font-bold">
          {state.phase === "ROUND_ACTIVE" &&
            (myTurn ? (
              <span className="text-amber-300">התור שלך — קדימה!</span>
            ) : (
              <span className="text-violet-200">
                התור של {opponent?.display_name ?? "היריב"}...
              </span>
            ))}
          {state.phase === "QUESTION_PREVIEW" && (
            <span className="text-violet-100">קראו את השאלה, מתחילים עוד רגע…</span>
          )}
          {state.phase === "WAITING_FOR_PLAYERS" && (
            <span className="text-violet-100">ממתינים ליריב…</span>
          )}
        </p>
      </header>

      {reconnecting && (
        <div className="bg-amber-400 px-4 py-1.5 text-center text-xs font-bold text-amber-950">
          החיבור נותק — מתחברים מחדש…
        </div>
      )}
      {rejection === "NOT_YOUR_TURN" && (
        <div className="bg-slate-800 px-4 py-1.5 text-center text-xs font-bold text-white">
          זה לא התור שלך כרגע
        </div>
      )}
      {opponent && !opponent.connected && state.phase !== "MATCH_FINISHED" && (
        <div className="bg-slate-200 px-4 py-1.5 text-center text-xs text-slate-600">
          {opponent.display_name} התנתק/ה — אם לא יחזרו בקרוב, הניצחון שלך
        </div>
      )}

      {/* Answer history */}
      <AnswerFeed
        answers={state.answers}
        myUserId={state.you}
        players={state.players}
      />

      {/* Composer */}
      <form
        onSubmit={onSubmit}
        className="flex gap-2 border-t border-slate-200 bg-white p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
      >
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={myTurn ? "כתבו תשובה…" : "ממתינים לתור שלך…"}
          disabled={!myTurn}
          maxLength={60}
          className="min-w-0 flex-1 rounded-full border-2 border-slate-200 px-4 py-2.5 text-base outline-none transition focus:border-violet-400 disabled:bg-slate-50"
        />
        <button
          type="submit"
          disabled={!myTurn || !draft.trim()}
          className="rounded-full bg-violet-600 px-6 font-bold text-white transition active:scale-95 disabled:opacity-40"
        >
          שליחה
        </button>
      </form>

      {/* Overlays */}
      {state.phase === "WAITING_FOR_PLAYERS" && (
        <WaitingOverlay code={state.code} />
      )}
      {state.phase === "ROUND_FINISHED" && state.last_round_result && (
        <RoundResultOverlay state={state} />
      )}
      {state.phase === "MATCH_FINISHED" && <MatchResultOverlay state={state} />}
      {state.phase === "ABANDONED" && (
        <Overlay>
          <h2 className="text-2xl font-black">המשחק בוטל</h2>
          <BackHomeLink />
        </Overlay>
      )}
    </main>
  );
}

function PlayerBadge({
  player,
  points,
  isYou = false,
}: {
  player?: PlayerInfo;
  points: number;
  isYou?: boolean;
}) {
  return (
    <div className="flex min-w-[4.5rem] flex-col items-center gap-0.5">
      <span className="max-w-24 truncate font-bold">
        {player ? player.display_name : "—"}
        {isYou && <span className="text-violet-200"> (את/ה)</span>}
      </span>
      <div className="flex gap-1">
        {[0, 1].map((i) => (
          <span
            key={i}
            className={`h-2.5 w-2.5 rounded-full ${
              i < points ? "bg-amber-300" : "bg-white/25"
            }`}
          />
        ))}
      </div>
    </div>
  );
}

function Overlay({ children }: { children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-slate-900/60 p-6 backdrop-blur-sm">
      <div className="w-full max-w-sm animate-pop-in rounded-3xl bg-white p-8 text-center shadow-2xl">
        {children}
      </div>
    </div>
  );
}

function BackHomeLink() {
  return (
    <Link
      href="/"
      className="mt-6 inline-block rounded-full bg-violet-600 px-8 py-3 font-bold text-white transition active:scale-95"
    >
      חזרה למסך הראשי
    </Link>
  );
}

function WaitingOverlay({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard
      ?.writeText(`${window.location.origin}/room/${code}`)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
  }

  return (
    <Overlay>
      <h2 className="text-2xl font-black">ממתינים ליריב…</h2>
      <p className="mt-2 text-slate-500">שתפו את קוד החדר:</p>
      <div
        dir="ltr"
        className="mt-4 rounded-2xl bg-slate-100 py-4 font-mono text-4xl font-black tracking-[0.3em] text-violet-700"
      >
        {code}
      </div>
      <button
        onClick={copy}
        className="mt-4 rounded-full border-2 border-violet-200 px-6 py-2 text-sm font-bold text-violet-700 transition active:scale-95"
      >
        {copied ? "הקישור הועתק ✓" : "העתקת קישור הזמנה"}
      </button>
    </Overlay>
  );
}

function RoundResultOverlay({ state }: { state: GameState }) {
  const result = state.last_round_result!;
  const iWon = result.winner_user_id === state.you;
  const winner = state.players.find(
    (p) => p.user_id === result.winner_user_id
  );
  return (
    <Overlay>
      <div className="text-5xl">{iWon ? "🎉" : "⏱️"}</div>
      <h2 className="mt-3 text-2xl font-black">
        {iWon ? "לקחת את הסיבוב!" : `${winner?.display_name} לקח/ה את הסיבוב`}
      </h2>
      <p className="mt-2 text-slate-500">
        {result.reason === "TIMEOUT" ? "הזמן נגמר ליריב שבתור" : "הסיבוב הוכרע"}
      </p>
      <ScoreLine state={state} />
      <p className="mt-4 text-sm text-slate-400">הסיבוב הבא מתחיל עוד רגע…</p>
    </Overlay>
  );
}

function MatchResultOverlay({ state }: { state: GameState }) {
  const iWon = state.match_winner_id === state.you;
  const winner = state.players.find(
    (p) => p.user_id === state.match_winner_id
  );
  return (
    <Overlay>
      <div className="text-6xl">{iWon ? "🏆" : "💔"}</div>
      <h2 className="mt-3 text-3xl font-black">
        {iWon ? "ניצחון!" : "הפסד הפעם"}
      </h2>
      <p className="mt-2 text-slate-500">
        {state.match_end_reason === "FORFEIT"
          ? iWon
            ? "היריב עזב את המשחק"
            : "המשחק הוכרע בגלל עזיבה"
          : `${winner?.display_name} ניצח/ה את המשחק`}
      </p>
      <ScoreLine state={state} />
      <BackHomeLink />
    </Overlay>
  );
}

function ScoreLine({ state }: { state: GameState }) {
  return (
    <div className="mt-4 flex items-center justify-center gap-4 text-lg font-bold">
      {state.players.map((p, i) => (
        <span key={p.user_id} className="flex items-center gap-2">
          {i === 1 && <span className="text-slate-300">:</span>}
          <span className="text-slate-600">{p.display_name}</span>
          <span className="rounded-lg bg-slate-100 px-2.5 py-0.5 font-mono">
            {state.score.find((s) => s.user_id === p.user_id)?.points ?? 0}
          </span>
        </span>
      ))}
    </div>
  );
}
