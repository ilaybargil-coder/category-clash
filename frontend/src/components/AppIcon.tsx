const MAP: Record<string, string> = {
  home: "01-home",
  games: "02-games",
  friends: "03-friends",
  statistics: "04-statistics",
  achievements: "05-achievements",
  settings: "06-settings",
  profile: "07-profile",
  rank: "08-rank",
  shield: "09-shield",
  "new-game": "10-new-game",
  "quick-game": "11-quick-game",
  daily: "12-daily-challenge",
  duel: "13-duel",
  "private-room": "14-private-room",
  "invite-friend": "15-invite-friend",
  "copy-link": "16-copy-link",
  share: "17-share",
  "invite-code": "18-invite-code",
  xp: "19-xp",
  level: "20-level",
  accuracy: "21-accuracy",
  wins: "22-wins",
  losses: "23-losses",
  streak: "24-win-streak",
  leaderboard: "25-leaderboard",
  medal: "26-medal",
  diamond: "27-diamond",
  coins: "28-coins",
  gift: "29-gift",
  star: "30-star",
  chat: "31-chat",
  messages: "32-messages",
  notifications: "33-notifications",
  search: "34-search",
  filter: "35-filter",
  correct: "36-correct",
  incorrect: "37-incorrect",
  timer: "38-timer",
  waiting: "39-waiting",
  random: "40-random",
  list: "41-list",
  missions: "42-missions",
  categories: "43-categories",
  report: "44-report",
  logout: "45-logout",
  "sound-on": "46-sound-on",
  "sound-off": "47-sound-off",
  back: "48-back",
  plus: "49-plus",
};

export default function AppIcon({
  name,
  className = "h-6 w-6",
  alt = "",
}: {
  name: string;
  className?: string;
  alt?: string;
}) {
  return (
    <img
      src={`/assets/icons/${MAP[name]}.png?v=3`}
      alt={alt}
      className={`${className} object-contain`}
      style={{ display: "block", maxWidth: "100%", maxHeight: "100%" }}
    />
  );
}
