"use client";

import { useEffect } from "react";
import { API_URL } from "@/lib/api";

export default function BackendWarmup() {
  useEffect(() => {
    // Render Free may be asleep. Start waking it as soon as the page opens,
    // but never block authentication or hide the UI while it starts.
    void fetch(`${API_URL}/health`, { cache: "no-store" }).catch(() => undefined);
  }, []);

  return null;
}
