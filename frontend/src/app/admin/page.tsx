"use client";

import { useEffect, useState } from "react";
import { API_URL, getToken, getUser } from "@/lib/api";

interface PendingReport {
  question_id: number;
  question_text: string;
  normalized: string;
  sample_raw_text: string;
  occurrence_count: number;
  distinct_reporter_count: number;
  newest_created_at: string;
}

interface ApprovedAnswer {
  id: number;
  canonical: string;
}

interface ReportContext {
  question_id: number;
  question_text: string;
  answers: ApprovedAnswer[];
}

class RequestError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new RequestError(body.detail ?? `HTTP ${response.status}`, response.status);
  }
  return response.json() as Promise<T>;
}

function reportKey(report: PendingReport): string {
  return `${report.question_id}:${report.normalized}`;
}

export default function AdminPage() {
  const [access, setAccess] = useState<"checking" | "granted" | "denied">("checking");
  const [reports, setReports] = useState<PendingReport[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [contexts, setContexts] = useState<Record<number, ApprovedAnswer[]>>({});
  const [aliasOpen, setAliasOpen] = useState<string | null>(null);
  const [selectedTargets, setSelectedTargets] = useState<Record<string, number>>({});
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadReports() {
      await Promise.resolve();
      if (cancelled) return;
      const user = getUser();
      if (!getToken() || user?.username !== "ilaybargil") {
        setAccess("denied");
        return;
      }

      try {
        const pending = await request<PendingReport[]>("/api/reports/pending");
        if (cancelled) return;
        setReports(pending);
        setDrafts(
          Object.fromEntries(pending.map((report) => [reportKey(report), report.sample_raw_text]))
        );
        setAccess("granted");
      } catch (reason) {
        if (cancelled) return;
        if (reason instanceof RequestError && reason.status === 403) {
          setAccess("denied");
          return;
        }
        setError(reason instanceof Error ? reason.message : "טעינת הדיווחים נכשלה");
        setAccess("granted");
      }
    }
    void loadReports();

    return () => {
      cancelled = true;
    };
  }, []);

  function finishRow(report: PendingReport, message: string) {
    const key = reportKey(report);
    setReports((current) => current.filter((item) => reportKey(item) !== key));
    setAliasOpen((current) => (current === key ? null : current));
    setNote(message);
    setError(null);
  }

  function handleRequestError(reason: unknown) {
    if (reason instanceof RequestError && reason.status === 403) {
      setAccess("denied");
      return;
    }
    setError(reason instanceof Error ? reason.message : "הפעולה נכשלה");
  }

  async function approve(
    report: PendingReport,
    mode: "new_answer" | "alias",
    targetAnswerId?: number
  ) {
    const key = reportKey(report);
    const canonical = (drafts[key] ?? "").trim();
    if (!canonical) {
      setError("יש להזין תשובה לפני האישור");
      return;
    }
    setBusyKey(key);
    setError(null);
    try {
      await request("/api/reports/approve", {
        method: "POST",
        body: JSON.stringify({
          question_id: report.question_id,
          normalized: report.normalized,
          mode,
          canonical,
          ...(targetAnswerId ? { target_answer_id: targetAnswerId } : {}),
        }),
      });
      finishRow(
        report,
        mode === "new_answer" ? "התשובה נוספה למאגר" : "הכינוי נוסף לתשובה"
      );
    } catch (reason) {
      handleRequestError(reason);
    } finally {
      setBusyKey(null);
    }
  }

  async function openAliasPicker(report: PendingReport) {
    const key = reportKey(report);
    if (aliasOpen === key) {
      setAliasOpen(null);
      return;
    }
    setBusyKey(key);
    setError(null);
    try {
      let answers = contexts[report.question_id];
      if (!answers) {
        const context = await request<ReportContext>(
          `/api/reports/context/${report.question_id}`
        );
        answers = context.answers;
        setContexts((current) => ({ ...current, [report.question_id]: context.answers }));
      }
      if (answers.length === 0) {
        setError("אין תשובות פעילות שאפשר לצרף אליהן כינוי");
        return;
      }
      setSelectedTargets((current) => ({
        ...current,
        [key]: current[key] ?? answers[0].id,
      }));
      setAliasOpen(key);
    } catch (reason) {
      handleRequestError(reason);
    } finally {
      setBusyKey(null);
    }
  }

  async function reject(report: PendingReport) {
    const key = reportKey(report);
    setBusyKey(key);
    setError(null);
    try {
      await request("/api/reports/reject", {
        method: "POST",
        body: JSON.stringify({
          question_id: report.question_id,
          normalized: report.normalized,
        }),
      });
      finishRow(report, "הדיווח נדחה");
    } catch (reason) {
      handleRequestError(reason);
    } finally {
      setBusyKey(null);
    }
  }

  if (access === "checking") {
    return (
      <main className="app-background grid min-h-dvh place-items-center p-6" dir="rtl">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-violet-300/20 border-t-violet-300" />
      </main>
    );
  }

  if (access === "denied") {
    return (
      <main className="app-background grid min-h-dvh place-items-center p-6" dir="rtl">
        <section className="surface-panel w-full max-w-md rounded-2xl p-8 text-center">
          <h1>אין גישה</h1>
        </section>
      </main>
    );
  }

  return (
    <main className="app-background min-h-dvh px-4 py-8 sm:px-6" dir="rtl">
      <div className="mx-auto max-w-4xl">
        <header className="mb-6">
          <p className="text-sm font-bold text-violet-300">ניהול תוכן</p>
          <h1 className="mt-1">סקירת תשובות שדווחו</h1>
          <p className="mt-2 text-slate-400">אישור תשובה מוסיף אותה מיד למאגר הפעיל.</p>
        </header>

        {note && (
          <p className="mb-4 rounded-xl border border-emerald-400/25 bg-emerald-500/10 px-4 py-3 text-sm font-bold text-emerald-300">
            {note}
          </p>
        )}
        {error && (
          <p className="mb-4 rounded-xl border border-rose-400/25 bg-rose-500/10 px-4 py-3 text-sm font-bold text-rose-300">
            {error}
          </p>
        )}

        {reports.length === 0 ? (
          <section className="surface-panel rounded-2xl p-10 text-center">
            <h2>אין דיווחים ממתינים</h2>
            <p className="mt-2 text-slate-400">הכול מסודר כרגע.</p>
          </section>
        ) : (
          <div className="grid gap-4">
            {reports.map((report) => {
              const key = reportKey(report);
              const busy = busyKey === key;
              const answers = contexts[report.question_id] ?? [];
              const selectedTarget = selectedTargets[key];
              return (
                <article key={key} className="surface-panel rounded-2xl p-5 sm:p-6">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-bold text-violet-300">{report.question_text}</p>
                      <p className="mt-1 text-xs text-slate-400">
                        דווח {report.occurrence_count} פעמים · {report.distinct_reporter_count} מדווחים
                      </p>
                    </div>
                    <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-slate-300">
                      ממתין לבדיקה
                    </span>
                  </div>

                  <label className="mt-5 block text-sm font-bold text-slate-200" htmlFor={`answer-${key}`}>
                    התשובה שתתווסף
                  </label>
                  <input
                    id={`answer-${key}`}
                    value={drafts[key] ?? ""}
                    onChange={(event) =>
                      setDrafts((current) => ({ ...current, [key]: event.target.value }))
                    }
                    className="mt-2 w-full rounded-xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-500/25"
                    disabled={busy}
                  />

                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => approve(report, "new_answer")}
                      disabled={busy}
                      className="rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-black text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      אשר כתשובה חדשה
                    </button>
                    <button
                      type="button"
                      onClick={() => openAliasPicker(report)}
                      disabled={busy}
                      className="rounded-xl border border-violet-400/30 bg-violet-500/10 px-4 py-2.5 text-sm font-black text-violet-200 transition hover:bg-violet-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      אשר ככינוי
                    </button>
                    <button
                      type="button"
                      onClick={() => reject(report)}
                      disabled={busy}
                      className="rounded-xl border border-rose-400/25 bg-rose-500/10 px-4 py-2.5 text-sm font-black text-rose-300 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      דחה
                    </button>
                  </div>

                  {aliasOpen === key && (
                    <div className="mt-4 rounded-xl border border-violet-400/20 bg-violet-500/[0.08] p-4">
                      <label className="block text-sm font-bold text-violet-100" htmlFor={`target-${key}`}>
                        צירוף ככינוי לתשובה
                      </label>
                      <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                        <select
                          id={`target-${key}`}
                          value={selectedTarget ?? ""}
                          onChange={(event) =>
                            setSelectedTargets((current) => ({
                              ...current,
                              [key]: Number(event.target.value),
                            }))
                          }
                          className="min-w-0 flex-1 rounded-xl border border-white/15 bg-[#1f2836] px-4 py-3 text-white outline-none focus:border-violet-400"
                          disabled={busy}
                        >
                          {answers.map((answer) => (
                            <option key={answer.id} value={answer.id}>
                              {answer.canonical}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          onClick={() => approve(report, "alias", selectedTarget)}
                          disabled={busy || !selectedTarget}
                          className="rounded-xl bg-violet-600 px-4 py-3 text-sm font-black text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          אשר ככינוי
                        </button>
                      </div>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
