"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { BrandMark } from "@/components/VisualShell";
import {
  getSupabaseClient,
  SUPABASE_AUTH_CONFIGURED,
  SUPABASE_AUTH_ENABLED,
} from "@/lib/supabase";

type ResetStatus = "loading" | "ready" | "invalid" | "success";

const passwordResetAvailable =
  SUPABASE_AUTH_ENABLED && SUPABASE_AUTH_CONFIGURED;

export default function ResetPasswordPage() {
  const [status, setStatus] = useState<ResetStatus>(
    passwordResetAvailable ? "loading" : "invalid"
  );
  const [newPassword, setNewPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!passwordResetAvailable) return;

    const supabase = getSupabaseClient();
    let disposed = false;
    let recoveryDetected = false;

    const { data } = supabase.auth.onAuthStateChange((event, session) => {
      if (disposed || event !== "PASSWORD_RECOVERY" || !session) return;
      recoveryDetected = true;
      setError(null);
      setStatus("ready");
    });

    void supabase.auth
      .getSession()
      .then(({ data: sessionData, error: sessionError }) => {
        if (disposed) return;
        if (!sessionError && (sessionData.session || recoveryDetected)) {
          setStatus("ready");
          return;
        }
        setStatus("invalid");
      })
      .catch(() => {
        if (!disposed) setStatus("invalid");
      });

    return () => {
      disposed = true;
      data.subscription.unsubscribe();
    };
  }, []);

  async function updatePassword(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (newPassword.length < 8) {
      setError("הסיסמה חייבת להכיל לפחות 8 תווים");
      return;
    }
    if (newPassword !== passwordConfirmation) {
      setError("הסיסמאות אינן זהות");
      return;
    }

    setBusy(true);
    try {
      const { error: authError } = await getSupabaseClient().auth.updateUser({
        password: newPassword,
      });
      if (authError) throw authError;
      setStatus("success");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "עדכון הסיסמה נכשל");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-background flex min-h-dvh items-center justify-center p-4">
      <section className="w-full max-w-md rounded-2xl border border-white/10 bg-[#071019]/90 p-6 shadow-2xl sm:p-8">
        <BrandMark />

        {status === "loading" && (
          <div className="mt-8 flex items-center justify-center gap-3 text-sm font-bold text-violet-300">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-violet-300/20 border-t-violet-300" />
            בודקים את קישור האיפוס...
          </div>
        )}

        {status === "invalid" && (
          <div className="mt-8 text-center">
            <h1 className="text-2xl font-black text-white">הקישור אינו תקף</h1>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              קישור האיפוס פג או שכבר נעשה בו שימוש. חזרו למסך הכניסה ובקשו
              קישור חדש.
            </p>
            <Link
              href="/"
              className="primary-button mt-6 block w-full px-6 py-3"
            >
              חזרה למסך הכניסה
            </Link>
          </div>
        )}

        {status === "success" && (
          <div className="mt-8 text-center">
            <h1 className="text-2xl font-black text-white">הסיסמה עודכנה בהצלחה</h1>
            <p className="mt-3 text-sm text-slate-400">
              אפשר לחזור למשחק ולהתחבר עם הסיסמה החדשה.
            </p>
            <Link
              href="/"
              className="primary-button mt-6 block w-full px-6 py-3"
            >
              חזרה לכניסה
            </Link>
          </div>
        )}

        {status === "ready" && (
          <div className="mt-8">
            <p className="text-xs font-bold text-violet-300">כמעט סיימנו</p>
            <h1 className="mt-2 text-3xl font-black text-white">בוחרים סיסמה חדשה</h1>
            <p className="mt-2 text-sm text-slate-500">
              הסיסמה החדשה צריכה להכיל לפחות 8 תווים.
            </p>

            <form onSubmit={updatePassword} className="mt-6 space-y-4">
              <label className="block">
                <span className="mb-1.5 block text-xs font-bold text-slate-400">
                  סיסמה חדשה
                </span>
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  className="dark-input"
                />
              </label>

              <label className="block">
                <span className="mb-1.5 block text-xs font-bold text-slate-400">
                  אימות סיסמה
                </span>
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={passwordConfirmation}
                  onChange={(event) => setPasswordConfirmation(event.target.value)}
                  className="dark-input"
                />
              </label>

              {error && (
                <p className="rounded-xl border border-rose-400/20 bg-rose-500/10 p-3 text-sm text-rose-300">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={busy}
                className="primary-button w-full py-3.5 text-base"
              >
                {busy ? "מעדכנים..." : "עדכון הסיסמה"}
              </button>
            </form>
          </div>
        )}
      </section>
    </main>
  );
}
