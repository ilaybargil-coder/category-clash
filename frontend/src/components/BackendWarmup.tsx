"use client";

import { useEffect } from "react";
import { API_URL } from "@/lib/api";

const HEARTBEAT_INTERVAL_MS = 5 * 60 * 1_000;

export default function BackendWarmup() {
  useEffect(() => {
    const warmBackend = () => {
      // Render Free may be asleep. Start waking it without ever blocking the
      // UI, and keep it active while a real player has the site open.
      void fetch(`${API_URL}/health`, { cache: "no-store" }).catch(() => undefined);
    };

    const warmWhenVisible = () => {
      if (document.visibilityState === "visible") warmBackend();
    };

    warmBackend();
    const heartbeat = window.setInterval(warmWhenVisible, HEARTBEAT_INTERVAL_MS);
    document.addEventListener("visibilitychange", warmWhenVisible);
    window.addEventListener("online", warmBackend);

    return () => {
      window.clearInterval(heartbeat);
      document.removeEventListener("visibilitychange", warmWhenVisible);
      window.removeEventListener("online", warmBackend);
    };
  }, []);

  return null;
}
