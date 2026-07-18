"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useViewportHeight } from "@/hooks/useViewportHeight";
import {
  ApiError,
  endSolo,
  getToken,
  getUser,
  nextSoloQuestion,
  revealSolo,
  startSolo,
  submitSoloAnswer,
  type SoloAnswerStatus,
  type SoloQuestion,
  type SoloRevealedAnswer,
} from "@/lib/api";

const TURN_SECONDS = 15;

interface Feedback {
  id: number;
  text: string;
  status: SoloAnswerStatus;
  canonical: string | null;
}

export default function SoloPage() {
  useViewportHeight();

  const router = useRouter();
  const [question, setQuestion] = useState<SoloQuestion | null>(null);
  const [draft, setDraft] = useState("");
  const [secondsLeft, setSecondsLeft] = useState(TURN_SECONDS);
  const [feedback, setFeedback] = useState<Feedback[]>([]);
  const [foundCanonicals, setFoundCanonicals] = useState<string[]>([]);
  const [revealed, setRevealed] = useState<SoloRevealedAnswer[] | null>(null);
  const [questionsPlayed, setQuestionsPlayed] = useState(0);
  const [totalFound, setTotalFound] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const startedRef = useRef(false);
  const revealingRef = useRef(false);
  const feedbackId = useRef(0);

  useEffect(() => {
    if (!getToken() || !getUser()) {
      router.replace("/");
      return;
    }
    if (startedRef.current) return;
    startedRef.current = true;
    startSolo()
      .then((nextQuestion) => {
        setQuestion(nextQuestion);
        setQuestionsPlayed(1);
      })
      .catch((cause) => {
        if (cause instanceof ApiError && cause.status === 401) {
          router.replace("/");
          return;
        }
        setMessage(cause instanceof Error ? cause.message : "לא הצלחנו להתחיל משחק יחיד");
      });
  }, [router]);

  const onReveal = useCallback(async () => {
    if (!question || revealed || revealingRef.current) return;
    revealingRef.current = true;
    setBusy(true);
    setMessage(null);
    try {
      const result = await revealSolo(question.solo_id);
      setRevealed(result.answers);
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "חשיפת התשובות נכשלה");
    } finally {
      revealingRef.current = false;
      setBusy(false);
    }
  }, [question, revealed]);

  useEffect(() => {
    if (!question || revealed) return;
    const timer = window.setTimeout(() => {
      if (secondsLeft <= 1) {
        setSecondsLeft(0);
        void onReveal();
      } else {
        setSecondsLeft(secondsLeft - 1);
      }
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [question, revealed, secondsLeft, onReveal]);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || !question || revealed || busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await submitSoloAnswer(question.solo_id, text);
      setFeedback((items) => [
        ...items,
        { id: ++feedbackId.current, text, status: result.status, canonical: result.canonical },
      ]);
      if (result.status === "VALID" && result.canonical) {
        setFoundCanonicals((items) => [...items, result.canonical!]);
        setTotalFound((value) => value + 1);
        setSecondsLeft(TURN_SECONDS);
      }
      setDraft("");
      requestAnimationFrame(() => inputRef.current?.focus({ preventScroll: true }));
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "שליחת התשובה נכשלה");
    } finally {
      setBusy(false);
    }
  }

  async function onNext() {
    if (!question || busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const nextQuestion = await nextSoloQuestion(question.solo_id);
      setQuestion(nextQuestion);
      setFeedback([]);
      setFoundCanonicals([]);
      setRevealed(null);
      setDraft("");
      setSecondsLeft(TURN_SECONDS);
      setQuestionsPlayed((value) => value + 1);
      requestAnimationFrame(() => inputRef.current?.focus({ preventScroll: true }));
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 409) {
        setMessage("סיימת את כל מאגר השאלות — כל הכבוד!");
      } else {
        setMessage(cause instanceof Error ? cause.message : "טעינת השאלה הבאה נכשלה");
      }
    } finally {
      setBusy(false);
    }
  }

  async function backToLobby() {
    if (question) {
      try {
        await endSolo(question.solo_id);
      } catch {
        // Navigating home remains available if the practice session already expired.
      }
    }
    router.push("/");
  }

  if (!question) {
    return (
      <main dir="rtl" className="app-background flex min-h-dvh items-center justify-center px-6 text-center">
        <div className="surface-panel rounded-2xl p-8">
          {!message && <div className="mx-auto h-9 w-9 animate-spin rounded-full border-4 border-violet-300/20 border-t-violet-300" />}
          <p className="mt-4 font-bold text-slate-300">{message ?? "מכינים שאלת אימון..."}</p>
          {message && <button onClick={() => router.push("/")} className="mt-4 font-bold text-violet-300 underline">חזרה ללובי</button>}
        </div>
      </main>
    );
  }

  return (
    <main
      dir="rtl"
      className="app-background overflow-hidden p-2 sm:p-4"
      style={{ height: "var(--app-vh, 100dvh)" }}
    >
      <div className="surface-panel mx-auto flex h-full min-h-0 max-w-2xl flex-col overflow-hidden rounded-2xl">
      <header className="shrink-0 border-b border-white/10 bg-violet-600/10 px-5 py-5 text-white">
        <div className="flex items-center justify-between text-sm font-bold text-violet-100">
          <span>משחק יחיד 🎯</span>
          <span>שאלות: {questionsPlayed} · תשובות: {totalFound}</span>
        </div>
        <h1 className="mx-auto mt-5 max-w-xl text-center text-2xl font-black leading-snug">{question.question_text}</h1>
        {!revealed && (
          <div className="mt-5">
            <div className="mb-1 flex justify-between text-xs font-bold"><span>זמן לתשובה</span><span>{secondsLeft}</span></div>
            <div className="h-2 overflow-hidden rounded-full bg-violet-900/40">
              <div className="h-full rounded-full bg-amber-300 transition-all duration-1000" style={{ width: `${(secondsLeft / TURN_SECONDS) * 100}%` }} />
            </div>
          </div>
        )}
      </header>

      <section className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
        <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
          <p className="text-lg font-black text-white">נמצאו {foundCanonicals.length} מתוך {question.total_answers}</p>
          {foundCanonicals.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{foundCanonicals.map((answer) => <span key={answer} className="rounded-full bg-emerald-500/15 px-3 py-1 text-sm font-bold text-emerald-300">{answer}</span>)}</div>}
        </div>

        {feedback.length > 0 && !revealed && <div className="flex flex-wrap gap-2">{feedback.slice(-8).map((item) => <FeedbackChip key={item.id} item={item} />)}</div>}

        {message && <div className="rounded-xl border border-amber-400/20 bg-amber-500/10 p-3 text-center font-bold text-amber-300">{message}</div>}

        {revealed && (
          <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
            <h2 className="mb-3 text-xl font-black text-white">כל התשובות המאושרות</h2>
            <div className="space-y-2">{revealed.map((answer) => (
              <div key={answer.canonical} className={`flex items-center justify-between gap-3 rounded-xl border p-3 ${answer.found ? "border-emerald-400/30 bg-emerald-500/10" : "border-white/10"}`}>
                <span className={`font-bold ${answer.found ? "text-emerald-300" : "text-slate-300"}`}>{answer.canonical}</span>
                {answer.semantic_group && <span className="shrink-0 rounded-full bg-violet-500/15 px-2.5 py-1 text-xs font-bold text-violet-300">{answer.semantic_group}</span>}
              </div>
            ))}</div>
          </section>
        )}
      </section>

      {!revealed ? (
        <div className="shrink-0 border-t border-white/10 bg-black/20 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
          <form onSubmit={onSubmit} className="flex gap-2">
            <input ref={inputRef} autoFocus value={draft} onChange={(event) => setDraft(event.target.value)} disabled={busy} maxLength={60} placeholder="כתבו תשובה…" className="dark-input min-w-0 flex-1 py-2.5" />
            <button disabled={busy || !draft.trim()} className="primary-button px-6 disabled:opacity-40">שליחה</button>
          </form>
          <button onClick={() => void onReveal()} disabled={busy} className="mt-3 w-full py-2 text-sm font-bold text-slate-500 disabled:opacity-40">סיימתי / חשיפת תשובות</button>
        </div>
      ) : (
        <div className="grid shrink-0 grid-cols-2 gap-3 border-t border-white/10 bg-black/20 p-4">
          <button onClick={() => void onNext()} disabled={busy} className="primary-button py-3 disabled:opacity-40">שאלה הבאה</button>
          <button onClick={() => void backToLobby()} className="secondary-button py-3">חזרה ללובי</button>
        </div>
      )}
      </div>
    </main>
  );
}

function FeedbackChip({ item }: { item: Feedback }) {
  if (item.status === "VALID") return <span className="rounded-full bg-emerald-500/15 px-3 py-1.5 text-sm font-bold text-emerald-300">✓ {item.canonical}</span>;
  if (item.status === "DUPLICATE" || item.status === "TOO_SIMILAR") return <span className="rounded-full bg-amber-500/15 px-3 py-1.5 text-sm font-bold text-amber-300">{item.text}: כבר נאמר</span>;
  return <span className="rounded-full bg-rose-500/15 px-3 py-1.5 text-sm font-bold text-rose-300">{item.text}: לא ברשימה</span>;
}
