"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  CheckIcon,
  JokerIcon,
  LosesIcon,
  ShareIcon,
  SoundOffIcon,
  SoundOnIcon,
  SwapIcon,
  TimerIcon,
  TrophyIcon,
} from "@/components/icons";
import { useGameSocket } from "@/hooks/useGameSocket";
import { useViewportHeight } from "@/hooks/useViewportHeight";
import { BrandMark, UserAvatar } from "./VisualShell";
import AnswerFeed from "./AnswerFeed";
import TimerBar from "./TimerBar";
import {
  isMuted,
  playMatchLoss,
  playMatchWin,
  playRoundLoss,
  playRoundWin,
  toggleMute,
} from "@/lib/sfx";
import type { GameState, PlayerInfo } from "@/lib/types";

export default function GameRoom({ code }: { code: string }) {
  useViewportHeight();

  const {
    state,
    stateSyncRevision,
    status,
    rejection,
    clearRejection,
    submitAnswer,
    usePowerup: triggerPowerup,
    requestRematch,
  } = useGameSocket(code);

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
      stateSyncRevision={stateSyncRevision}
      reconnecting={status !== "open"}
      rejection={rejection}
      clearRejection={clearRejection}
      submitAnswer={submitAnswer}
      triggerPowerup={triggerPowerup}
      requestRematch={requestRematch}
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
    <main className="app-background flex min-h-dvh items-center justify-center px-5 text-center">
      <section className="surface-panel w-full max-w-md rounded-2xl p-8">
        <BrandMark compact />
        <h1 className="mt-8 text-2xl font-black text-white">{title}</h1>
        <div className="mt-4 text-slate-400">{children}</div>
      </section>
    </main>
  );
}

function GameView({
  state,
  stateSyncRevision,
  reconnecting,
  rejection,
  clearRejection,
  submitAnswer,
  triggerPowerup,
  requestRematch,
}: {
  state: GameState;
  stateSyncRevision: number;
  reconnecting: boolean;
  rejection: string | null;
  clearRejection: () => void;
  submitAnswer: (text: string) => boolean;
  triggerPowerup: (type: "swap_question" | "extend_time" | "use_joker") => boolean;
  requestRematch: () => boolean;
}) {
  const me = state.players.find((p) => p.user_id === state.you);
  const opponent = state.players.find((p) => p.user_id !== state.you);
  const myTurn =
    state.phase === "ROUND_ACTIVE" && state.turn_user_id === state.you;
  const myPowerups = state.powerups?.[String(state.you)] ?? {
    swap_question: false,
    extend_time: false,
    joker: false,
  };

  const [draft, setDraft] = useState("");
  const [soundMuted, setSoundMuted] = useState(false);
  const [optimisticPowerups, setOptimisticPowerups] = useState<{
    stateSyncRevision: number;
    used: Set<PowerupType>;
  }>(() => ({ stateSyncRevision, used: new Set() }));
  const [optimisticExtend, setOptimisticExtend] = useState<{
    stateSyncRevision: number;
    authoritativeDeadlineEpochMs: number;
    displayedDeadlineEpochMs: number;
  } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const handledRoundResultRef = useRef(
    state.last_round_result
      ? `${state.last_round_result.round_no}:${state.last_round_result.winner_user_id}:${state.last_round_result.loser_user_id}`
      : null
  );
  const handledMatchResultRef = useRef(
    state.phase === "MATCH_FINISHED"
      ? `${state.match_winner_id}:${state.match_end_reason}`
      : null
  );
  const optimisticallyUsed =
    optimisticPowerups.stateSyncRevision === stateSyncRevision
      ? optimisticPowerups.used
      : null;
  // The pre-command deadline is the pending flag: as soon as the reducer
  // receives a different authoritative deadline, render that server value
  // directly instead of applying the optimistic extension a second time.
  const displayedDeadlineEpochMs =
    optimisticExtend?.stateSyncRevision === stateSyncRevision &&
    optimisticExtend.authoritativeDeadlineEpochMs === state.deadline_epoch_ms &&
    state.phase === "ROUND_ACTIVE"
      ? optimisticExtend.displayedDeadlineEpochMs
      : state.deadline_epoch_ms;

  useEffect(() => {
    if (myTurn) inputRef.current?.focus();
  }, [myTurn]);

  useEffect(() => {
    const updateMuteState = setTimeout(() => setSoundMuted(isMuted()), 0);
    return () => clearTimeout(updateMuteState);
  }, []);

  useEffect(() => {
    const result = state.last_round_result;
    if (!result) {
      handledRoundResultRef.current = null;
      return;
    }

    const resultKey = `${result.round_no}:${result.winner_user_id}:${result.loser_user_id}`;
    if (
      state.phase === "ROUND_FINISHED" &&
      handledRoundResultRef.current !== resultKey
    ) {
      handledRoundResultRef.current = resultKey;
      if (result.winner_user_id === state.you) playRoundWin();
      else playRoundLoss();
    }
  }, [state.last_round_result, state.phase, state.you]);

  useEffect(() => {
    if (state.phase !== "MATCH_FINISHED") {
      handledMatchResultRef.current = null;
      return;
    }

    const resultKey = `${state.match_winner_id}:${state.match_end_reason}`;
    if (handledMatchResultRef.current !== resultKey) {
      handledMatchResultRef.current = resultKey;
      if (state.match_winner_id === state.you) playMatchWin();
      else playMatchLoss();
    }
  }, [
    state.match_end_reason,
    state.match_winner_id,
    state.phase,
    state.you,
  ]);

  function onToggleMute() {
    setSoundMuted(toggleMute());
  }

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
    if (submitAnswer(text)) {
      setDraft("");
      inputRef.current?.focus({ preventScroll: true });
    }
  }

  function onPowerup(type: PowerupType) {
    if (!triggerPowerup(type)) return;
    if (type === "extend_time" && state.deadline_epoch_ms !== null) {
      setOptimisticExtend({
        stateSyncRevision,
        authoritativeDeadlineEpochMs: state.deadline_epoch_ms,
        displayedDeadlineEpochMs:
          state.deadline_epoch_ms + state.turn_seconds * 1000,
      });
    }
    setOptimisticPowerups((current) => {
      const used =
        current.stateSyncRevision === stateSyncRevision
          ? new Set(current.used)
          : new Set<PowerupType>();
      used.add(type);
      return { stateSyncRevision, used };
    });
  }

  const pointsOf = (userId?: number) =>
    state.score.find((s) => s.user_id === userId)?.points ?? 0;

  return (
    <main
      className="app-background overflow-hidden p-2 sm:p-4"
      style={{ height: "var(--app-vh, 100dvh)" }}
    >
      <div className="mx-auto flex h-full min-h-0 max-w-[1280px] flex-col">
        <header className="mb-2 flex shrink-0 items-center justify-between px-2 py-1 lg:mb-3">
          <BrandMark compact />
          <div className="flex items-center gap-2 text-[11px] text-slate-500">
            <button
              type="button"
              onClick={onToggleMute}
              aria-label={soundMuted ? "הפעלת צלילים" : "השתקת צלילים"}
              aria-pressed={soundMuted}
              title={soundMuted ? "הפעלת צלילים" : "השתקת צלילים"}
              className="grid h-8 w-8 touch-manipulation place-items-center rounded-full border border-white/10 bg-black/20 text-sm transition hover:bg-white/10"
            >
              <span aria-hidden="true">
                {soundMuted ? <SoundOffIcon className="h-4 w-4" /> : <SoundOnIcon className="h-4 w-4" />}
              </span>
            </button>
            <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1.5 font-mono tracking-wider">
              חדר {state.code}
            </span>
            <span className={`h-2 w-2 rounded-full ${reconnecting ? "bg-amber-400" : "bg-emerald-400"}`} />
          </div>
        </header>

        <section className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[210px_minmax(0,1fr)_210px]">
          <PlayerPanel
            player={me}
            points={pointsOf(me?.user_id)}
            totalAnswers={state.answers.filter((answer) => answer.user_id === me?.user_id).length}
            accent="purple"
            isYou
          />

          <div className="surface-panel flex min-h-0 flex-col overflow-hidden rounded-2xl">
            <div className="flex shrink-0 items-center justify-between border-b border-white/10 px-4 py-2.5 text-xs text-slate-500 lg:justify-center">
              <span className="lg:absolute lg:right-8">סיבוב {state.round_no || "-"}</span>
              <span className="rounded-full bg-black/25 px-4 py-1 font-bold text-slate-300">
                הטוב מ־{state.rounds_to_win * 2 - 1}
              </span>
              <span className="lg:hidden">עד {state.rounds_to_win} ניצחונות</span>
            </div>

            <div className="kb-hide grid shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-3 px-4 py-3 lg:hidden">
              <PlayerBadge player={me} points={pointsOf(me?.user_id)} isYou />
              <span className="text-sm font-black text-slate-600">VS</span>
              <PlayerBadge player={opponent} points={pointsOf(opponent?.user_id)} />
            </div>

            <section className="game-question kb-compact mx-3 shrink-0 rounded-xl bg-[#f7f0df] px-4 py-3 text-center text-slate-900 shadow-[0_8px_30px_rgba(0,0,0,0.22)] sm:mx-5 sm:px-7 sm:py-4">
              <p className="kb-category-label text-[10px] font-bold text-slate-500 sm:text-xs">קטגוריה</p>
              <h1 className="mt-1 min-h-12 text-lg font-black leading-snug sm:text-2xl">
                {state.question?.text ?? "ממתינים לשאלה..."}
              </h1>
              <TimerBar
                deadlineEpochMs={displayedDeadlineEpochMs}
                turnSeconds={state.turn_seconds}
                clockOffsetMs={state.clock_offset_ms}
                active={state.phase === "ROUND_ACTIVE"}
                isCurrentPlayerTurn={myTurn}
              />
              <p className="mt-1 min-h-5 text-xs font-bold sm:text-sm">
                {state.phase === "ROUND_ACTIVE" &&
                  (myTurn ? (
                    <span className="text-violet-700">התור שלך — קדימה!</span>
                  ) : (
                    <span className="text-emerald-700">
                      התור של {opponent?.display_name ?? "היריב"}...
                    </span>
                  ))}
                {state.phase === "QUESTION_PREVIEW" && (
                  <span className="text-slate-500">קראו את השאלה, מתחילים עוד רגע…</span>
                )}
                {state.phase === "WAITING_FOR_PLAYERS" && (
                  <span className="text-slate-500">ממתינים ליריב…</span>
                )}
              </p>
            </section>

            <div className="mt-3 shrink-0 space-y-1">
              {reconnecting && (
                <StatusBanner tone="amber">החיבור נותק — מתחברים מחדש…</StatusBanner>
              )}
              {rejection === "NOT_YOUR_TURN" && (
                <StatusBanner tone="slate">זה לא התור שלך כרגע</StatusBanner>
              )}
              {opponent && !opponent.connected && state.phase !== "MATCH_FINISHED" && (
                <StatusBanner tone="slate">
                  {opponent.display_name} התנתק/ה — אם לא יחזרו בקרוב, הניצחון שלך
                </StatusBanner>
              )}
            </div>

            <AnswerFeed answers={state.answers} myUserId={state.you} players={state.players} />

            <div className="grid shrink-0 grid-cols-3 gap-2 border-t border-white/10 px-3 py-2 sm:px-5">
              <PowerButton label={<><SwapIcon className="inline-block h-4 w-4 align-middle" /> החלפה</>} available={myPowerups.swap_question && !optimisticallyUsed?.has("swap_question")} disabled={state.answers.length > 0 || !["QUESTION_PREVIEW", "ROUND_ACTIVE"].includes(state.phase)} onClick={() => onPowerup("swap_question")} />
              <PowerButton label={<><TimerIcon className="inline-block h-4 w-4 align-middle" /> הארכה</>} available={myPowerups.extend_time && !optimisticallyUsed?.has("extend_time")} disabled={!myTurn} onClick={() => onPowerup("extend_time")} />
              <PowerButton label={<><JokerIcon className="inline-block h-4 w-4 align-middle" /> ג׳וקר</>} available={myPowerups.joker && !optimisticallyUsed?.has("use_joker")} disabled={!myTurn} onClick={() => onPowerup("use_joker")} />
            </div>

            <form
              onSubmit={onSubmit}
              className="flex shrink-0 gap-2 border-t border-white/10 bg-black/20 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-5"
            >
              <input
                ref={inputRef}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder={myTurn ? "הקלידו תשובה…" : "ממתינים לתור שלך…"}
                disabled={!myTurn}
                maxLength={60}
                className="dark-input min-w-0 flex-1 py-2.5 disabled:cursor-not-allowed disabled:opacity-45"
              />
              <button
                type="submit"
                aria-label="שליחת תשובה"
                disabled={!myTurn || !draft.trim()}
                className="primary-button grid w-12 touch-manipulation place-items-center text-xl transition-transform duration-75 active:scale-95 sm:w-auto sm:min-w-28 sm:px-6"
              >
                <span className="sm:hidden"><ShareIcon className="h-5 w-5" /></span>
                <span className="hidden sm:inline">שליחה</span>
              </button>
            </form>
          </div>

          <PlayerPanel
            player={opponent}
            points={pointsOf(opponent?.user_id)}
            totalAnswers={state.answers.filter((answer) => answer.user_id === opponent?.user_id).length}
            accent="green"
          />
        </section>
      </div>

      {/* Overlays */}
      {state.phase === "WAITING_FOR_PLAYERS" && (
        <WaitingOverlay code={state.code} />
      )}
      {state.phase === "ROUND_FINISHED" && state.last_round_result && (
        <RoundResultOverlay state={state} />
      )}
      {state.phase === "MATCH_FINISHED" && (
        <MatchResultOverlay
          state={state}
          reconnecting={reconnecting}
          requestRematch={requestRematch}
        />
      )}
      {state.phase === "ABANDONED" && (
        <Overlay>
          <h2 className="text-2xl font-black">המשחק בוטל</h2>
          <BackHomeLink />
        </Overlay>
      )}
    </main>
  );
}

type PowerupType = "swap_question" | "extend_time" | "use_joker";

function PowerButton({
  label,
  available,
  disabled,
  onClick,
}: {
  label: React.ReactNode;
  available: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  const lastTouchActivationAtRef = useRef(0);

  function handlePointerDown(event: React.PointerEvent<HTMLButtonElement>) {
    if (event.pointerType !== "touch" && event.pointerType !== "pen") return;
    lastTouchActivationAtRef.current = Date.now();
    onClick();
  }

  function handleClick() {
    if (Date.now() - lastTouchActivationAtRef.current < 750) return;
    onClick();
  }

  return (
    <button
      type="button"
      onPointerDown={handlePointerDown}
      onClick={handleClick}
      disabled={!available || disabled}
      aria-pressed={!available}
      className="touch-manipulation rounded-lg border border-violet-400/20 bg-violet-500/10 px-2 py-2 text-xs font-bold text-violet-200 transition-transform duration-75 active:scale-95 disabled:cursor-not-allowed disabled:opacity-30"
    >
      {label}
      {!available && <CheckIcon className="inline-block h-3.5 w-3.5 align-middle" />}
    </button>
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
    <div className="flex min-w-0 flex-col items-center gap-1">
      <UserAvatar name={player?.display_name ?? "?"} online={player?.connected} size="sm" />
      <span className="max-w-24 truncate text-xs font-bold text-white">
        {player ? player.display_name : "—"}
        {isYou && <span className="text-violet-300"> · את/ה</span>}
      </span>
      <div className="flex gap-1">
        {[0, 1].map((i) => (
          <span
            key={i}
            className={`h-1.5 w-5 rounded-full ${
              i < points ? "bg-violet-400" : "bg-white/10"
            }`}
          />
        ))}
      </div>
    </div>
  );
}

function PlayerPanel({
  player,
  points,
  totalAnswers,
  accent,
  isYou = false,
}: {
  player?: PlayerInfo;
  points: number;
  totalAnswers: number;
  accent: "purple" | "green";
  isYou?: boolean;
}) {
  const accentText = accent === "purple" ? "text-violet-400" : "text-emerald-400";
  return (
    <aside className="surface-panel hidden min-h-0 flex-col items-center rounded-2xl p-5 text-center lg:flex">
      <UserAvatar name={player?.display_name ?? "?"} online={player?.connected} size="lg" />
      <h2 className="mt-4 max-w-full truncate text-lg font-black text-white">
        {player?.display_name ?? "ממתינים..."}
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        {isYou ? "השחקן שלך" : player?.connected ? "מחובר לזירה" : "ממתינים לחיבור"}
      </p>
      <div className={`mt-7 text-6xl font-black ${accentText}`}>{points}</div>
      <p className="mt-2 text-xs text-slate-500">ניקוד בסדרה</p>
      <div className="mt-7 w-full space-y-3 border-t border-white/10 pt-5 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-slate-500">תשובות בסיבוב</span>
          <strong className="text-white">{totalAnswers}</strong>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-500">מצב חיבור</span>
          <strong className={player?.connected ? "text-emerald-400" : "text-amber-400"}>
            {player?.connected ? "מחובר" : "לא מחובר"}
          </strong>
        </div>
      </div>
      <div className="mt-auto flex gap-1.5 pt-8">
        {[0, 1].map((i) => (
          <span
            key={i}
            className={`h-2 w-14 rounded-full ${
              i < points
                ? accent === "purple"
                  ? "bg-violet-500"
                  : "bg-emerald-500"
                : "bg-white/10"
            }`}
          />
        ))}
      </div>
    </aside>
  );
}

function StatusBanner({
  tone,
  children,
}: {
  tone: "amber" | "slate";
  children: React.ReactNode;
}) {
  return (
    <div
      className={`mx-3 rounded-lg border px-3 py-1.5 text-center text-xs font-bold sm:mx-5 ${
        tone === "amber"
          ? "border-amber-400/20 bg-amber-400/10 text-amber-300"
          : "border-white/10 bg-white/[0.035] text-slate-400"
      }`}
    >
      {children}
    </div>
  );
}

function Overlay({ children }: { children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/75 p-5 backdrop-blur-md">
      <div className="surface-panel w-full max-w-sm animate-pop-in rounded-2xl p-8 text-center shadow-2xl">
        {children}
      </div>
    </div>
  );
}

function BackHomeLink() {
  return (
    <Link
      href="/"
      className="primary-button mt-6 inline-block px-8 py-3"
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
      <p className="mt-2 text-slate-400">שתפו את קוד החדר:</p>
      <div
        dir="ltr"
        className="mt-4 rounded-xl border border-violet-400/20 bg-violet-500/10 py-4 font-mono text-4xl font-black tracking-[0.3em] text-violet-300"
      >
        {code}
      </div>
      <button
        onClick={copy}
        className="secondary-button mt-4 text-sm"
      >
        {copied ? <>הקישור הועתק <CheckIcon className="inline-block h-4 w-4 align-middle" /></> : "העתקת קישור הזמנה"}
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
      <div className="text-5xl">
        {iWon ? <TrophyIcon className="mx-auto h-12 w-12" /> : <TimerIcon className="mx-auto h-12 w-12" />}
      </div>
      <h2 className="mt-3 text-2xl font-black">
        {iWon ? "לקחת את הסיבוב!" : `${winner?.display_name} לקח/ה את הסיבוב`}
      </h2>
      <p className="mt-2 text-slate-400">
        {result.reason === "TIMEOUT" ? "הזמן נגמר ליריב שבתור" : "הסיבוב הוכרע"}
      </p>
      <ScoreLine state={state} />
      <p className="mt-4 text-sm text-slate-500">הסיבוב הבא מתחיל עוד רגע…</p>
    </Overlay>
  );
}

function MatchResultOverlay({
  state,
  reconnecting,
  requestRematch,
}: {
  state: GameState;
  reconnecting: boolean;
  requestRematch: () => boolean;
}) {
  const iWon = state.match_winner_id === state.you;
  const winner = state.players.find(
    (p) => p.user_id === state.match_winner_id
  );
  const opponent = state.players.find((p) => p.user_id !== state.you);
  const myRequested = state.rematch.requesting_user_ids.includes(state.you);
  const opponentRequested = opponent
    ? state.rematch.requesting_user_ids.includes(opponent.user_id)
    : false;
  return (
    <Overlay>
      <div className="text-6xl">
        {iWon ? <TrophyIcon className="mx-auto h-14 w-14" /> : <LosesIcon className="mx-auto h-14 w-14" />}
      </div>
      <h2 className="mt-3 text-3xl font-black">
        {iWon ? "ניצחון!" : "הפסד הפעם"}
      </h2>
      <p className="mt-2 text-slate-400">
        {state.match_end_reason === "FORFEIT"
          ? iWon
            ? "היריב עזב את המשחק"
            : "המשחק הוכרע בגלל עזיבה"
          : `${winner?.display_name} ניצח/ה את המשחק`}
      </p>
      <ScoreLine state={state} />
      {opponentRequested && (
        <p className="mt-5 font-bold text-emerald-300">היריב רוצה רימאטצ&apos;</p>
      )}
      {myRequested ? (
        <div className="mt-5 rounded-xl border border-violet-400/20 bg-violet-500/10 px-5 py-3 font-bold text-violet-200">
          ממתין ליריב…
        </div>
      ) : (
        <button
          type="button"
          onClick={requestRematch}
          disabled={reconnecting}
          className="primary-button mt-5 px-8 py-3 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <SwapIcon className="inline-block h-4 w-4 align-middle" /> רימאטצ&apos;
        </button>
      )}
      <BackHomeLink />
    </Overlay>
  );
}

function ScoreLine({ state }: { state: GameState }) {
  return (
    <div className="mt-4 flex items-center justify-center gap-4 text-lg font-bold">
      {state.players.map((p, i) => (
        <span key={p.user_id} className="flex items-center gap-2">
          {i === 1 && <span className="text-slate-600">:</span>}
          <span className="text-slate-300">{p.display_name}</span>
          <span className="rounded-lg bg-white/10 px-2.5 py-0.5 font-mono text-white">
            {state.score.find((s) => s.user_id === p.user_id)?.points ?? 0}
          </span>
        </span>
      ))}
    </div>
  );
}
