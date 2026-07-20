"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeftIcon, CheckIcon, LightningIcon, ShareIcon, TrophyIcon } from "@/components/icons";
import { useViewportHeight } from "@/hooks/useViewportHeight";
import {
  API_URL,
  ApiError,
  getToken,
  getUser,
  refreshSessionUser,
  reportAnswer,
  type SoloAnswerStatus,
} from "@/lib/api";

interface DailyResult {
  id: number;
  date: string;
  question_id: number;
  score: number;
  created_at: string;
  share_text: string;
  xp_awarded: number;
}

interface DailyToday {
  date: string;
  question_id: number;
  question_text: string;
  total_answers: number;
  result: DailyResult | null;
}

interface DailyStart {
  date: string;
  question_id: number;
  question_text: string;
  total_answers: number;
  found_count: number;
  found_answers: string[];
}

interface DailyAnswer {
  status: SoloAnswerStatus;
  canonical: string | null;
  found_count: number;
  total_answers: number;
}

interface LeaderboardEntry {
  rank: number;
  user_id: number;
  username: string;
  display_name: string;
  score: number;
  created_at: string;
}

interface DailyLeaderboard {
  date: string;
  entries: LeaderboardEntry[];
}

interface Feedback {
  id: number;
  text: string;
  status: SoloAnswerStatus;
  canonical: string | null;
}

async function dailyRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_URL}/api/daily${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new ApiError(body.detail ?? `HTTP ${response.status}`, response.status);
  }
  return response.json() as Promise<T>;
}

export default function DailyPage() {
  useViewportHeight();

  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const user = getUser();
  const [today, setToday] = useState<DailyToday | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [active, setActive] = useState(false);
  const [draft, setDraft] = useState("");
  const [foundAnswers, setFoundAnswers] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<Feedback[]>([]);
  const [reportedIds, setReportedIds] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [shareMessage, setShareMessage] = useState<string | null>(null);
  const loadedRef = useRef(false);
  const feedbackId = useRef(0);

  const loadLeaderboard = useCallback(async () => {
    const result = await dailyRequest<DailyLeaderboard>("/leaderboard");
    setLeaderboard(result.entries);
  }, []);

  useEffect(() => {
    if (!getToken() || !user) {
      router.replace("/");
      return;
    }
    if (loadedRef.current) return;
    loadedRef.current = true;
    Promise.all([dailyRequest<DailyToday>("/today"), dailyRequest<DailyLeaderboard>("/leaderboard")])
      .then(([daily, board]) => {
        setToday(daily);
        setLeaderboard(board.entries);
      })
      .catch((cause) => {
        if (cause instanceof ApiError && cause.status === 401) {
          router.replace("/");
          return;
        }
        setMessage(cause instanceof Error ? cause.message : "לא הצלחנו לטעון את האתגר היומי");
      });
  }, [router, user]);

  async function startAttempt() {
    if (busy || today?.result) return;
    setBusy(true);
    setMessage(null);
    try {
      const started = await dailyRequest<DailyStart>("/start", { method: "POST" });
      setFoundAnswers(started.found_answers);
      setActive(true);
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "לא הצלחנו להתחיל את האתגר");
    } finally {
      setBusy(false);
    }
  }

  async function submitAnswer(event: React.FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || !active || busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const answer = await dailyRequest<DailyAnswer>("/answer", {
        method: "POST",
        body: JSON.stringify({ text }),
      });
      setFeedback((items) => [
        ...items,
        {
          id: ++feedbackId.current,
          text,
          status: answer.status,
          canonical: answer.canonical,
        },
      ]);
      if (answer.status === "VALID" && answer.canonical) {
        setFoundAnswers((items) => [...items, answer.canonical!]);
      }
      setDraft("");
      requestAnimationFrame(() => inputRef.current?.focus({ preventScroll: true }));
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "שליחת התשובה נכשלה");
    } finally {
      setBusy(false);
    }
  }

  async function finishAttempt() {
    if (!active || busy || !today) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await dailyRequest<DailyResult>("/finish", { method: "POST" });
      setToday({ ...today, result });
      setActive(false);
      await Promise.all([loadLeaderboard(), refreshSessionUser()]);
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "שמירת התוצאה נכשלה");
    } finally {
      setBusy(false);
    }
  }

  async function handleReport(item: Feedback) {
    if (!today) return;
    try {
      await reportAnswer(today.question_id, item.text);
      setReportedIds((previous) => new Set(previous).add(item.id));
    } catch {
      // Keep the answer reportable if the request fails.
    }
  }

  async function shareResult(result: DailyResult) {
    setShareMessage(null);
    try {
      if (navigator.share) {
        await navigator.share({
          title: "Category Clash — האתגר היומי",
          text: result.share_text,
          url: window.location.href,
        });
        return;
      }
      await navigator.clipboard.writeText(`${result.share_text} — ${window.location.href}`);
      setShareMessage("התוצאה הועתקה ללוח");
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "AbortError") return;
      setShareMessage("לא הצלחנו לשתף את התוצאה");
    }
  }

  if (!today) {
    return (
      <main dir="rtl" className="app-background flex min-h-dvh items-center justify-center px-6 text-center">
        <section className="surface-panel w-full max-w-md rounded-2xl p-8">
          {!message && (
            <div className="mx-auto h-9 w-9 animate-spin rounded-full border-4 border-violet-300/20 border-t-violet-300" />
          )}
          <p className="mt-4 font-bold text-slate-300">{message ?? "טוענים את האתגר של היום..."}</p>
          {message && (
            <button onClick={() => router.push("/")} className="mt-5 font-bold text-violet-300 underline">
              חזרה ללובי
            </button>
          )}
        </section>
      </main>
    );
  }

  return (
    <main
      dir="rtl"
      className="app-background overflow-hidden p-3 sm:p-5"
      style={{ height: "var(--app-vh, 100dvh)" }}
    >
      <div className="mx-auto grid h-full min-h-0 max-w-5xl gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <section className="surface-panel flex h-full min-h-0 flex-col overflow-hidden rounded-2xl">
          <header className="relative shrink-0 overflow-hidden border-b border-white/10 bg-violet-600/10 px-5 py-7 text-center sm:px-8">
            <div className="pointer-events-none absolute inset-x-1/4 -top-24 h-44 rounded-full bg-violet-500/20 blur-3xl" />
            <button
              type="button"
              onClick={() => router.push("/")}
              className="absolute right-4 top-4 text-sm font-bold text-slate-400 hover:text-white"
            >
              חזרה ללובי <ArrowLeftIcon className="inline-block h-4 w-4 align-middle" />
            </button>
            <p className="relative mt-7 text-xs font-black tracking-[0.16em] text-amber-300 sm:mt-0">
              האתגר היומי <LightningIcon className="inline-block h-4 w-4 align-middle" />
            </p>
            <h1 className="relative mx-auto mt-4 max-w-2xl text-2xl font-black leading-snug text-white sm:text-3xl">
              {today.question_text}
            </h1>
            <p className="relative mt-3 text-sm text-slate-400">קטגוריה אחת לכולם · ניסיון אחד היום</p>
          </header>

          <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4 sm:p-7">
            {today.result ? (
              <section className="rounded-2xl border border-emerald-400/25 bg-emerald-500/10 p-6 text-center">
                <p className="text-sm font-bold text-emerald-300">האתגר הושלם</p>
                <p className="mt-2 text-5xl font-black text-white">{today.result.score}</p>
                <p className="mt-1 text-slate-300">תשובות תקינות</p>
                <p className="mx-auto mt-4 w-fit rounded-full border border-amber-300/25 bg-amber-400/10 px-4 py-2 text-lg font-black text-amber-200" dir="ltr">
                  +{today.result.xp_awarded} XP
                </p>
                <button
                  type="button"
                  onClick={() => void shareResult(today.result!)}
                  className="primary-button mt-6 w-full px-6 py-3 sm:w-auto"
                >
                  שיתוף התוצאה <ShareIcon className="inline-block h-4 w-4 align-middle" />
                </button>
                {shareMessage && <p className="mt-3 text-sm font-bold text-slate-300">{shareMessage}</p>}
              </section>
            ) : active ? (
              <>
                <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                  <p className="text-lg font-black text-white">
                    נמצאו {foundAnswers.length} מתוך {today.total_answers}
                  </p>
                  {foundAnswers.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {foundAnswers.map((answer) => (
                        <span key={answer} className="rounded-full bg-emerald-500/15 px-3 py-1 text-sm font-bold text-emerald-300">
                          {answer}
                        </span>
                      ))}
                    </div>
                  )}
                </section>

                {feedback.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {feedback.slice(-8).map((item) => (
                      <FeedbackChip
                        key={item.id}
                        item={item}
                        reported={reportedIds.has(item.id)}
                        onReport={() => void handleReport(item)}
                      />
                    ))}
                  </div>
                )}
              </>
            ) : (
              <section className="py-8 text-center">
                <p className="mx-auto max-w-md leading-7 text-slate-400">
                  מרגע שמתחילים אפשר להזין כמה תשובות שרוצים. רק תשובות שהמאמת הקיים מאשר ייכנסו לציון.
                </p>
                <button
                  type="button"
                  onClick={() => void startAttempt()}
                  disabled={busy}
                  className="primary-button mt-6 min-w-56 px-7 py-3.5 disabled:opacity-40"
                >
                  {busy ? "מתחילים..." : "התחלת הניסיון היומי"}
                </button>
              </section>
            )}

            {message && (
              <p className="rounded-xl border border-amber-400/20 bg-amber-500/10 p-3 text-center font-bold text-amber-300">
                {message}
              </p>
            )}
          </div>

          {active && !today.result && (
            <footer className="shrink-0 border-t border-white/10 bg-black/20 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
              <form onSubmit={submitAnswer} className="flex shrink-0 gap-2">
                <input
                  ref={inputRef}
                  autoFocus
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  maxLength={60}
                  placeholder="כתבו תשובה…"
                  className="dark-input min-w-0 flex-1 py-3"
                />
                <button
                  onPointerDown={(event) => event.preventDefault()}
                  disabled={busy || !draft.trim()}
                  className="primary-button px-6 disabled:opacity-40"
                >
                  שליחה
                </button>
              </form>
              <button
                type="button"
                onClick={() => void finishAttempt()}
                disabled={busy}
                className="secondary-button w-full shrink-0 py-3 disabled:opacity-40"
              >
                סיימתי — שמירת תוצאה
              </button>
            </footer>
          )}
        </section>

        <aside className="surface-panel h-fit rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-violet-300">היום</p>
              <h2 className="mt-1 text-xl font-black text-white">טבלת המובילים</h2>
            </div>
            <span className="text-2xl"><TrophyIcon className="h-6 w-6" /></span>
          </div>
          {leaderboard.length === 0 ? (
            <p className="mt-6 rounded-xl border border-white/10 p-4 text-center text-sm text-slate-500">
              עוד אין תוצאות היום. אפשר להיות הראשונים.
            </p>
          ) : (
            <ol className="mt-5 space-y-2">
              {leaderboard.map((entry) => {
                const isCurrentUser = entry.user_id === user?.id;
                return (
                  <li
                    key={entry.user_id}
                    className={`flex items-center gap-3 rounded-xl border p-3 ${
                      isCurrentUser
                        ? "border-violet-400/30 bg-violet-500/10"
                        : "border-white/10 bg-white/[0.025]"
                    }`}
                  >
                    <span className="w-7 text-center font-black text-amber-300">{entry.rank}</span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-bold text-white">{entry.display_name}</p>
                      <p className="truncate text-xs text-slate-500">@{entry.username}</p>
                    </div>
                    <strong className="text-lg text-emerald-300">{entry.score}</strong>
                  </li>
                );
              })}
            </ol>
          )}
        </aside>
      </div>
    </main>
  );
}

function FeedbackChip({
  item,
  reported,
  onReport,
}: {
  item: Feedback;
  reported: boolean;
  onReport: () => void;
}) {
  if (item.status === "VALID") {
    return (
      <span className="rounded-full bg-emerald-500/15 px-3 py-1.5 text-sm font-bold text-emerald-300">
        <CheckIcon className="inline-block h-4 w-4 align-middle" /> {item.canonical}
      </span>
    );
  }
  if (item.status === "DUPLICATE" || item.status === "TOO_SIMILAR") {
    return (
      <span className="rounded-full bg-amber-500/15 px-3 py-1.5 text-sm font-bold text-amber-300">
        {item.text}: כבר נאמר
      </span>
    );
  }
  return (
    <span className="rounded-full bg-rose-500/15 px-3 py-1.5 text-sm font-bold text-rose-300">
      {item.text}: לא ברשימה{" "}
      <button
        type="button"
        disabled={reported}
        onClick={onReport}
        onPointerDown={(event) => event.preventDefault()}
        className="text-xs font-bold text-rose-300/70 underline"
      >
        {reported ? <><CheckIcon className="inline-block h-3.5 w-3.5 align-middle" /> דווח</> : "דווח"}
      </button>
    </span>
  );
}
