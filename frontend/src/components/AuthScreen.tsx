"use client";

import { useState } from "react";
import { createProfile } from "@/lib/api";
import { getSupabaseClient } from "@/lib/supabase";
import type { SessionUser } from "@/lib/types";

interface Props {
  profileToken?: string | null;
  onProfileReady: (token: string, user: SessionUser) => void;
}

export default function AuthScreen({ profileToken, onProfileReady }: Props) {
  const [mode, setMode] = useState<"login" | "register">(
    profileToken ? "register" : "login"
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const completingProfile = Boolean(profileToken);

  async function finishProfile(token: string) {
    const profile = await createProfile(token, username.trim(), displayName.trim());
    onProfileReady(token, profile);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setBusy(true);
    try {
      if (completingProfile && profileToken) {
        await finishProfile(profileToken);
        return;
      }

      const supabase = getSupabaseClient();
      if (mode === "login") {
        const { error: authError } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });
        if (authError) throw authError;
        return;
      }

      if (!/^[A-Za-z0-9_]{3,24}$/.test(username)) {
        throw new Error("שם משתמש חייב להכיל 3–24 אותיות באנגלית, מספרים או _");
      }
      if (displayName.trim().length < 2) {
        throw new Error("הכינוי חייב להכיל לפחות שני תווים");
      }
      if (password.length < 8) {
        throw new Error("הסיסמה חייבת להכיל לפחות 8 תווים");
      }
      if (password !== passwordConfirmation) {
        throw new Error("הסיסמאות אינן זהות");
      }

      const { data, error: authError } = await supabase.auth.signUp({
        email: email.trim(),
        password,
        options: {
          data: { username: username.toLowerCase(), display_name: displayName.trim() },
        },
      });
      if (authError) throw authError;
      if (data.session) {
        await finishProfile(data.session.access_token);
      } else {
        setMessage("ההרשמה נקלטה. בדקו את האימייל כדי לאשר את החשבון.");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "הפעולה נכשלה");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-6 px-4 py-8">
      <header className="text-center">
        <h1 className="bg-gradient-to-l from-violet-600 to-fuchsia-500 bg-clip-text text-5xl font-black text-transparent">
          קרב קטגוריות
        </h1>
        <p className="mt-2 text-slate-500">
          {completingProfile ? "עוד רגע מתחילים — בחרו זהות למשחק" : "מתחברים ומשחקים בזמן אמת"}
        </p>
      </header>

      <section className="rounded-3xl bg-white p-6 shadow-sm">
        {!completingProfile && (
          <div className="mb-6 grid grid-cols-2 rounded-xl bg-slate-100 p-1">
            <button
              type="button"
              onClick={() => setMode("login")}
              className={`rounded-lg py-2 font-bold ${mode === "login" ? "bg-white text-violet-700 shadow-sm" : "text-slate-500"}`}
            >
              כניסה
            </button>
            <button
              type="button"
              onClick={() => setMode("register")}
              className={`rounded-lg py-2 font-bold ${mode === "register" ? "bg-white text-violet-700 shadow-sm" : "text-slate-500"}`}
            >
              הרשמה
            </button>
          </div>
        )}

        <form onSubmit={submit} className="space-y-4">
          {!completingProfile && (
            <label className="block">
              <span className="mb-1 block text-sm font-bold text-slate-600">אימייל</span>
              <input
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full rounded-xl border-2 border-slate-200 px-4 py-3 outline-none focus:border-violet-400"
              />
            </label>
          )}

          {(mode === "register" || completingProfile) && (
            <>
              <label className="block">
                <span className="mb-1 block text-sm font-bold text-slate-600">שם משתמש</span>
                <input
                  dir="ltr"
                  autoComplete="username"
                  required
                  minLength={3}
                  maxLength={24}
                  placeholder="ilay_123"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  className="w-full rounded-xl border-2 border-slate-200 px-4 py-3 text-left outline-none focus:border-violet-400"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-sm font-bold text-slate-600">כינוי במשחק</span>
                <input
                  autoComplete="nickname"
                  required
                  minLength={2}
                  maxLength={64}
                  placeholder="איליי"
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  className="w-full rounded-xl border-2 border-slate-200 px-4 py-3 outline-none focus:border-violet-400"
                />
              </label>
            </>
          )}

          {!completingProfile && (
            <>
              <label className="block">
                <span className="mb-1 block text-sm font-bold text-slate-600">סיסמה</span>
                <input
                  type="password"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  required
                  minLength={8}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="w-full rounded-xl border-2 border-slate-200 px-4 py-3 outline-none focus:border-violet-400"
                />
              </label>
              {mode === "register" && (
                <label className="block">
                  <span className="mb-1 block text-sm font-bold text-slate-600">
                    אימות סיסמה
                  </span>
                  <input
                    type="password"
                    autoComplete="new-password"
                    required
                    minLength={8}
                    value={passwordConfirmation}
                    onChange={(event) => setPasswordConfirmation(event.target.value)}
                    className="w-full rounded-xl border-2 border-slate-200 px-4 py-3 outline-none focus:border-violet-400"
                  />
                </label>
              )}
            </>
          )}

          {error && <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
          {message && (
            <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">{message}</p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-xl bg-gradient-to-l from-violet-600 to-fuchsia-500 py-3.5 text-lg font-bold text-white shadow-md disabled:opacity-50"
          >
            {busy
              ? "רגע..."
              : completingProfile
                ? "שמירת פרופיל"
                : mode === "login"
                  ? "כניסה למשחק"
                  : "יצירת חשבון"}
          </button>
        </form>
      </section>
    </main>
  );
}
