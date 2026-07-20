"use client";

import { useEffect, useState } from "react";
import { fetchInvites, type GameInvite } from "@/lib/api";

export type IncomingInvite = GameInvite & { expiresAt: number };

export function useIncomingInvites(): IncomingInvite[] {
  const [invites, setInvites] = useState<IncomingInvite[]>([]);

  useEffect(() => {
    let active = true;

    const loadInvites = async () => {
      try {
        const nextInvites = await fetchInvites();
        if (!active) return;

        const now = Date.now();
        setInvites(
          nextInvites
            .map((invite) => ({
              ...invite,
              expiresAt: now + invite.expires_in_seconds * 1000,
            }))
            .filter((invite) => invite.expiresAt > now)
        );
      } catch {
        // Invite polling is best-effort after the initial attempt.
      }
    };

    void loadInvites();
    const interval = window.setInterval(() => void loadInvites(), 5_000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  return invites;
}
