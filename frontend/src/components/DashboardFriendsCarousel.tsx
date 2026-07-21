"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeftIcon } from "@/components/icons";
import { UserAvatar } from "@/components/VisualShell";
import {
  fetchFriends,
  sendGameInvite,
  sendPresenceHeartbeat,
  type Friend,
} from "@/lib/api";

export default function DashboardFriendsCarousel({
  onOpenFriends,
}: {
  onOpenFriends: () => void;
}) {
  const router = useRouter();
  const [friends, setFriends] = useState<Friend[]>([]);
  const [onlineIds, setOnlineIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([fetchFriends(), sendPresenceHeartbeat()])
      .then(([nextFriends, presence]) => {
        if (!active) return;
        setOnlineIds(new Set(presence.online_friend_ids));
        setFriends(
          [...nextFriends].sort(
            (a, b) =>
              Number(presence.online_friend_ids.includes(b.id)) -
              Number(presence.online_friend_ids.includes(a.id))
          )
        );
      })
      .catch(() => {
        if (active) setFriends([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function invite(friend: Friend) {
    setBusyId(friend.id);
    setError(null);
    try {
      const result = await sendGameInvite(friend.username);
      router.push(`/room/${result.room_code}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "שליחת ההזמנה נכשלה");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="friends-carousel-panel surface-panel">
      <div className="section-heading">
        <div>
          <span>הצוות שלכם</span>
          <h2>חברים למשחק</h2>
        </div>
        <button type="button" onClick={onOpenFriends}>לכל החברים <ArrowLeftIcon className="inline-block h-3.5 w-3.5 align-middle" /></button>
      </div>

      {error && <p className="inline-error mt-3">{error}</p>}

      {loading ? (
        <div className="carousel-empty">טוענים את החברים שלכם…</div>
      ) : friends.length === 0 ? (
        <button type="button" onClick={onOpenFriends} className="carousel-empty carousel-empty--button">
          עדיין אין כאן חברים. הוסיפו חברים והזמינו אותם לקרב הראשון שלכם.
        </button>
      ) : (
        <div className="friends-carousel" role="list">
          {friends.map((friend) => {
            const games = friend.wins + friend.losses;
            const level = Math.floor(games / 5) + 1;
            const online = onlineIds.has(friend.id);
            return (
              <article key={friend.id} className="friend-quick-card" role="listitem">
                <div className="friend-quick-card__head">
                  <UserAvatar
                    name={friend.display_name}
                    avatar={friend.avatar}
                    online={online}
                    size="md"
                  />
                  <span className={online ? "is-online" : ""}>
                    {online ? "מחובר/ת" : `רמה ${level}`}
                  </span>
                </div>
                <strong>{friend.display_name}</strong>
                <small dir="ltr">@{friend.username}</small>
                <div className="friend-score">
                  <span><b>{friend.wins}</b> נצ׳</span>
                  <i />
                  <span><b>{friend.losses}</b> הפס׳</span>
                </div>
                <button
                  type="button"
                  onClick={() => void invite(friend)}
                  disabled={busyId !== null}
                  className="invite-friend-button"
                >
                  {busyId === friend.id ? "שולחים…" : "הזמן למשחק"}
                </button>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
