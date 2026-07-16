"use client";

import { useCallback, useEffect, useState } from "react";
import { API_URL } from "@/lib/api";

export type BackendHealthStatus = "checking" | "waiting" | "ready";

const POLL_INTERVAL_MS = 3_000;
const REQUEST_TIMEOUT_MS = 8_000;

export function useBackendHealth() {
  const [status, setStatus] = useState<BackendHealthStatus>("checking");
  const [attempts, setAttempts] = useState(0);
  const [retryVersion, setRetryVersion] = useState(0);

  const retryNow = useCallback(() => {
    setRetryVersion((version) => version + 1);
  }, []);

  useEffect(() => {
    let disposed = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let requestTimer: ReturnType<typeof setTimeout> | null = null;
    let controller: AbortController | null = null;

    const check = async () => {
      if (disposed) return;
      controller = new AbortController();
      requestTimer = setTimeout(() => controller?.abort(), REQUEST_TIMEOUT_MS);
      setAttempts((value) => value + 1);

      try {
        const response = await fetch(`${API_URL}/health`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(`Health returned ${response.status}`);
        const payload = (await response.json()) as { status?: string };
        if (payload.status !== "ok") throw new Error("Health payload is not ready");
        if (!disposed) setStatus("ready");
      } catch {
        if (!disposed) {
          setStatus("waiting");
          retryTimer = setTimeout(check, POLL_INTERVAL_MS);
        }
      } finally {
        if (requestTimer) clearTimeout(requestTimer);
      }
    };

    void check();
    return () => {
      disposed = true;
      controller?.abort();
      if (retryTimer) clearTimeout(retryTimer);
      if (requestTimer) clearTimeout(requestTimer);
    };
  }, [retryVersion]);

  return { status, attempts, retryNow };
}
