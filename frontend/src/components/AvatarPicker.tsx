"use client";

import { useState } from "react";
import { updateAvatar } from "@/lib/api";

const AVATAR_KEYS = Array.from(
  { length: 40 },
  (_, index) => `avatar-${String(index + 1).padStart(2, "0")}`
);

export default function AvatarPicker({
  currentAvatar,
  onAvatarChange,
}: {
  currentAvatar: string | null | undefined;
  onAvatarChange: (newAvatar: string) => void;
}) {
  const [savingAvatar, setSavingAvatar] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function selectAvatar(avatar: string) {
    if (savingAvatar || avatar === currentAvatar) return;
    setSavingAvatar(avatar);
    setError(null);
    try {
      const updated = await updateAvatar(avatar);
      onAvatarChange(updated.avatar ?? avatar);
    } catch {
      setError("עדכון האווטאר נכשל. נסו שוב.");
    } finally {
      setSavingAvatar(null);
    }
  }

  return (
    <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
      <h3 className="font-black text-white">בחר אווטאר</h3>
      <div className="mt-4 max-h-80 overflow-y-auto pr-1">
        <div className="grid grid-cols-4 place-items-center gap-3 sm:grid-cols-5">
          {AVATAR_KEYS.map((avatar) => (
            <button
              key={avatar}
              type="button"
              onClick={() => void selectAvatar(avatar)}
              disabled={savingAvatar !== null}
              aria-label={`בחירת אווטאר ${avatar.slice(-2)}`}
              aria-pressed={currentAvatar === avatar}
              className={`relative h-14 w-14 overflow-hidden rounded-full transition disabled:cursor-wait disabled:opacity-60 ${
                currentAvatar === avatar
                  ? "ring-2 ring-blue-500 ring-offset-2 ring-offset-slate-950"
                  : "ring-1 ring-white/15 hover:ring-2 hover:ring-violet-400"
              }`}
            >
              <img
                src={`/assets/avatars/${avatar}.png`}
                alt=""
                className="absolute inset-0 h-full w-full object-cover"
              />
            </button>
          ))}
        </div>
      </div>
      {error && <p className="mt-3 text-sm text-rose-300">{error}</p>}
    </section>
  );
}
