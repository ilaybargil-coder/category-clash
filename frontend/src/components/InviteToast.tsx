"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { GamepadIcon } from "@/components/icons";
import { useIncomingInvites } from "@/hooks/useIncomingInvites";
import { acceptInvite, declineInvite } from "@/lib/api";

export default function InviteToast() {
  const router = useRouter();
  const invites = useIncomingInvites();
  const [dismissedSenderIds, setDismissedSenderIds] = useState<Set<number>>(
    () => new Set()
  );
  const [respondingTo, setRespondingTo] = useState<number | null>(null);
  // Expiry must be checked against wall-clock time whenever polling triggers a render.
  // eslint-disable-next-line react-hooks/purity
  const now = Date.now();
  const activeInvites = invites.filter(
    (invite) =>
      invite.expiresAt > now && !dismissedSenderIds.has(invite.sender.id)
  );
  const invite = activeInvites.reduce(
    (newest, candidate) =>
      candidate.expiresAt > newest.expiresAt ? candidate : newest,
    activeInvites[0]
  );

  if (!invite) return null;

  function dismiss(senderId: number) {
    setDismissedSenderIds((current) => {
      const next = new Set(current);
      next.add(senderId);
      return next;
    });
  }

  async function accept() {
    setRespondingTo(invite.sender.id);
    try {
      const result = await acceptInvite(invite.sender.id);
      dismiss(invite.sender.id);
      router.push(`/room/${result.room_code}`);
    } catch {
      // Keep the invite visible so accepting can be retried.
    } finally {
      setRespondingTo(null);
    }
  }

  async function decline() {
    setRespondingTo(invite.sender.id);
    try {
      await declineInvite(invite.sender.id);
      dismiss(invite.sender.id);
    } catch {
      // Keep the invite visible so declining can be retried.
    } finally {
      setRespondingTo(null);
    }
  }

  const additionalInvites = activeInvites.length - 1;
  const busy = respondingTo === invite.sender.id;

  return (
    <aside
      dir="rtl"
      aria-live="polite"
      className="ui-toast surface-panel fixed inset-x-3 bottom-20 z-50 mx-auto flex max-w-md items-center gap-3 rounded-2xl border-violet-400/30 bg-violet-950/95 p-4 shadow-2xl lg:inset-x-auto lg:bottom-6 lg:right-6 lg:mx-0 lg:w-96"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span aria-hidden="true" className="text-xl">
            <GamepadIcon className="h-5 w-5" />
          </span>
          <p className="font-black text-white">
            {invite.sender.display_name} מזמין אותך למשחק!
          </p>
          {additionalInvites > 0 && (
            <span className="shrink-0 rounded-full bg-violet-500/25 px-2 py-0.5 text-xs font-black text-violet-200">
              +{additionalInvites}
            </span>
          )}
        </div>
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            onClick={() => void accept()}
            disabled={busy}
            className="primary-button min-h-0 px-4 py-2 text-sm disabled:opacity-50"
          >
            הצטרף
          </button>
          <button
            type="button"
            onClick={() => void decline()}
            disabled={busy}
            className="secondary-button px-4 py-2 text-sm disabled:opacity-50"
          >
            דחה
          </button>
        </div>
      </div>
    </aside>
  );
}
