"use client";

import { useEffect, useRef, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import {
  ApiError,
  clearSession,
  fetchProfile,
  saveSession,
} from "@/lib/api";
import { getSupabaseClient } from "@/lib/supabase";
import type { SessionUser } from "@/lib/types";

export type AuthStatus =
  | "loading"
  | "signed_out"
  | "needs_profile"
  | "ready"
  | "error";

export function useAuthSession() {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<SessionUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const syncGeneration = useRef(0);

  useEffect(() => {
    const supabase = getSupabaseClient();
    let disposed = false;

    async function syncSession(session: Session | null) {
      const sequence = ++syncGeneration.current;
      if (disposed) return;
      if (!session) {
        clearSession();
        setToken(null);
        setUser(null);
        setError(null);
        setStatus("signed_out");
        return;
      }

      const accessToken = session.access_token;
      setToken(accessToken);
      try {
        const profile = await fetchProfile(accessToken);
        if (disposed || sequence !== syncGeneration.current) return;
        saveSession(accessToken, profile);
        setUser(profile);
        setError(null);
        setStatus("ready");
      } catch (cause) {
        if (disposed || sequence !== syncGeneration.current) return;
        if (cause instanceof ApiError && cause.status === 404) {
          clearSession();
          setUser(null);
          setStatus("needs_profile");
          return;
        }
        setError(cause instanceof Error ? cause.message : "אימות המשתמש נכשל");
        setStatus("error");
      }
    }

    void supabase.auth.getSession().then(({ data }) => syncSession(data.session));
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      void syncSession(session);
    });
    return () => {
      disposed = true;
      data.subscription.unsubscribe();
    };
  }, []);

  function profileReady(accessToken: string, profile: SessionUser) {
    syncGeneration.current += 1;
    saveSession(accessToken, profile);
    setToken(accessToken);
    setUser(profile);
    setError(null);
    setStatus("ready");
  }

  async function signOut() {
    syncGeneration.current += 1;
    await getSupabaseClient().auth.signOut();
    clearSession();
    setToken(null);
    setUser(null);
    setStatus("signed_out");
  }

  return { status, user, token, error, profileReady, signOut };
}
