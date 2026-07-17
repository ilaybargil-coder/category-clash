"use client";

import { useState } from "react";
import { BrandMark } from "@/components/VisualShell";
import { createProfile } from "@/lib/api";
import { getSupabaseClient } from "@/lib/supabase";
import type { SessionUser } from "@/lib/types";
import { isValidUsername, normalizeUsername } from "@/lib/username";

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

  async function finishProfile(
    token: string,
    cleanUsername: string,
    cleanDisplayName: string
  ) {
    const profile = await createProfile(token, cleanUsername, cleanDisplayName);
    onProfileReady(token, profile);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setBusy(true);
    try {
      const cleanUsername = normalizeUsername(username);
      const cleanDisplayName = displayName.trim();

      if (mode === "register" || completingProfile) {
        if (!isValidUsername(cleanUsername)) {
          throw new Error("שם משתמש חייב להכיל 3–24 אותיות באנגלית, מספרים או _");
        }
        if (cleanDisplayName.length < 2) {
          throw new Error("הכינוי חייב להכיל לפחות שני תווים");
        }
      }

      if (completingProfile && profileToken) {
        await finishProfile(profileToken, cleanUsername, cleanDisplayName);
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
          data: {
            username: cleanUsername.toLowerCase(),
            display_name: cleanDisplayName,
          },
        },
      });
      if (authError) throw authError;
      if (data.session) {
        await finishProfile(data.session.access_token, cleanUsername, cleanDisplayName);
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
    <main className="app-background min-h-dvh p-3 sm:p-5">
      <div className="mx-auto grid min-h-[calc(100dvh-1.5rem)] max-w-6xl overflow-hidden rounded-2xl border border-white/10 bg-[#071019]/85 shadow-2xl sm:min-h-[calc(100dvh-2.5rem)] lg:grid-cols-[1.05fr_0.95fr]">
        <section className="relative hidden overflow-hidden border-l border-white/10 p-12 lg:flex lg:flex-col lg:justify-between">
          <div className="pointer-events-none absolute -right-40 -top-40 h-96 w-96 rounded-full bg-violet-600/20 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-44 -left-24 h-96 w-96 rounded-full bg-emerald-500/10 blur-3xl" />
          <BrandMark />
          <div className="relative mx-auto max-w-md text-center">
            <p className="text-xs font-bold tracking-[0.2em] text-violet-300">
              שאלה אחת. שני שחקנים.
            </p>
            <h1 className="mt-4 text-5xl font-black leading-tight text-white">
              חושבים מהר.
              <br />
              נשארים אחרונים.
            </h1>
            <p className="mt-5 leading-7 text-slate-400">
              משחק קטגוריות תחרותי בזמן אמת, עם מאגר תשובות חכם שמתחשב
              בכתיבים חלופיים ובשגיאות אנושיות.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[
              ["31", "קטגוריות"],
              ["3,700+", "תשובות"],
              ["Live", "בזמן אמת"],
            ].map(([value, label]) => (
              <div key={label} className="rounded-xl border border-white/10 bg-white/[0.025] p-4 text-center">
                <strong className="block text-xl font-black text-white">{value}</strong>
                <span className="text-xs text-slate-500">{label}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="flex min-h-full items-center justify-center px-4 py-8 sm:px-10 lg:px-14">
          <div className="w-full max-w-md">
            <div className="mb-8 lg:hidden">
              <BrandMark />
            </div>
            <p className="text-xs font-bold text-violet-300">
              {completingProfile ? "שלב אחרון" : "ברוכים הבאים"}
            </p>
            <h2 className="mt-2 text-3xl font-black text-white">
              {completingProfile
                ? "בוחרים זהות למשחק"
                : mode === "login"
                  ? "חוזרים לזירה"
                  : "יוצרים שחקן חדש"}
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              {completingProfile
                ? "בחרו שם משתמש וכינוי שיופיע מול היריבים."
                : "חשבון אחד, וכל ההתקדמות נשמרת."}
            </p>

            {!completingProfile && (
              <div className="mt-7 grid grid-cols-2 rounded-xl border border-white/10 bg-black/20 p-1">
                <button
                  type="button"
                  onClick={() => setMode("login")}
                  className={`rounded-lg py-2.5 font-bold transition ${
                    mode === "login"
                      ? "bg-violet-500/20 text-violet-200 shadow-sm"
                      : "text-slate-500"
                  }`}
                >
                  כניסה
                </button>
                <button
                  type="button"
                  onClick={() => setMode("register")}
                  className={`rounded-lg py-2.5 font-bold transition ${
                    mode === "register"
                      ? "bg-violet-500/20 text-violet-200 shadow-sm"
                      : "text-slate-500"
                  }`}
                >
                  הרשמה
                </button>
              </div>
            )}

            <form onSubmit={submit} className="mt-6 space-y-4">
              {!completingProfile && (
                <Field label="אימייל">
                  <input
                    type="email"
                    autoComplete="email"
                    autoCapitalize="none"
                    autoCorrect="off"
                    spellCheck={false}
                    required
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="name@example.com"
                    className="dark-input text-left"
                    dir="ltr"
                  />
                </Field>
              )}

              {(mode === "register" || completingProfile) && (
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="שם משתמש">
                    <input
                      dir="ltr"
                      autoComplete="username"
                      autoCapitalize="none"
                      autoCorrect="off"
                      spellCheck={false}
                      required
                      minLength={3}
                      maxLength={24}
                      placeholder="ilay_123"
                      value={username}
                      onChange={(event) => setUsername(event.target.value)}
                      onBlur={() => setUsername(normalizeUsername(username))}
                      className="dark-input text-left"
                    />
                  </Field>
                  <Field label="כינוי במשחק">
                    <input
                      autoComplete="nickname"
                      required
                      minLength={2}
                      maxLength={64}
                      placeholder="עילאי"
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                      className="dark-input"
                    />
                  </Field>
                </div>
              )}

              {!completingProfile && (
                <>
                  <Field label="סיסמה">
                    <input
                      type="password"
                      autoComplete={mode === "login" ? "current-password" : "new-password"}
                      required
                      minLength={8}
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      className="dark-input"
                    />
                  </Field>
                  {mode === "register" && (
                    <Field label="אימות סיסמה">
                      <input
                        type="password"
                        autoComplete="new-password"
                        required
                        minLength={8}
                        value={passwordConfirmation}
                        onChange={(event) => setPasswordConfirmation(event.target.value)}
                        className="dark-input"
                      />
                    </Field>
                  )}
                </>
              )}

              {error && (
                <p className="rounded-xl border border-rose-400/20 bg-rose-500/10 p-3 text-sm text-rose-300">
                  {error}
                </p>
              )}
              {message && (
                <p className="rounded-xl border border-emerald-400/20 bg-emerald-500/10 p-3 text-sm text-emerald-300">
                  {message}
                </p>
              )}

              <button
                type="submit"
                disabled={busy}
                className="primary-button w-full py-3.5 text-base"
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
          </div>
        </section>
      </div>
    </main>
  );
}
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-bold text-slate-400">{label}</span>
      {children}
    </label>
  );
}
