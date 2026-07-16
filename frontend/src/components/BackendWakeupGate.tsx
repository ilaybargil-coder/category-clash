"use client";

import type { ReactNode } from "react";
import { useBackendHealth } from "@/hooks/useBackendHealth";

export default function BackendWakeupGate({ children }: { children: ReactNode }) {
  const { status, attempts, retryNow } = useBackendHealth();

  // Do not flash a full-page wake screen on every refresh. The app remains
  // usable while the cheap health probe runs in the background; we only block
  // after a real network failure or timeout indicates that Render is asleep.
  if (status !== "waiting") return children;

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-5 px-6 text-center">
      <div className="relative h-16 w-16">
        <div className="absolute inset-0 animate-ping rounded-full bg-violet-200 opacity-60" />
        <div className="relative flex h-16 w-16 items-center justify-center rounded-full bg-violet-600 text-3xl">
          ⚡
        </div>
      </div>
      <div>
        <h1 className="text-2xl font-black">שרת המשחק מתעורר</h1>
        <p className="mt-2 leading-relaxed text-slate-500">
          גרסת הבטא פועלת על שרת חינמי, ולכן אחרי זמן ללא פעילות ההתעוררות יכולה
          לקחת עד כדקה. העמוד ימשיך לנסות אוטומטית.
        </p>
      </div>
      <div className="flex items-center gap-2 text-sm font-bold text-violet-700">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-violet-200 border-t-violet-600" />
        בדיקת שרת {attempts > 1 ? `· ניסיון ${attempts}` : ""}
      </div>
      {status === "waiting" && (
        <button
          type="button"
          onClick={retryNow}
          className="rounded-full border-2 border-violet-200 px-6 py-2 text-sm font-bold text-violet-700"
        >
          נסו עכשיו
        </button>
      )}
    </main>
  );
}
