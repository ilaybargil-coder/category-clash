export type Phase =
  | "WAITING_FOR_PLAYERS"
  | "QUESTION_PREVIEW"
  | "ROUND_ACTIVE"
  | "ROUND_FINISHED"
  | "MATCH_FINISHED"
  | "ABANDONED";

export type AnswerStatus =
  | "VALID"
  | "INVALID"
  | "DUPLICATE"
  | "TOO_SIMILAR"
  | "NOT_YOUR_TURN"
  | "ROUND_FINISHED"
  | "TIME_EXPIRED";

export interface PlayerInfo {
  user_id: number;
  username: string;
  display_name: string;
  avatar?: string | null;
  connected: boolean;
}

export interface ScoreEntry {
  user_id: number;
  points: number;
}

export interface AnswerItem {
  /** Server-generated unique id — the dedupe key for rendering. */
  submission_id: string;
  client_command_id: string | null;
  user_id: number;
  raw_text: string;
  status: AnswerStatus;
  canonical: string | null;
  at_ms: number;
}

export interface RoundResult {
  round_no: number;
  winner_user_id: number;
  loser_user_id: number;
  reason: string;
  score: ScoreEntry[];
}

export interface RematchState {
  requesting_user_ids: number[];
}

export interface GameState {
  seq: number;
  event_id: string;
  protocol_version: number;
  you: number;
  code: string;
  phase: Phase;
  players: PlayerInfo[];
  score: ScoreEntry[];
  round_no: number;
  rounds_to_win: number;
  question: { id: number; text: string } | null;
  turn_user_id: number | null;
  turn_seconds: number;
  deadline_epoch_ms: number | null;
  answers: AnswerItem[];
  last_round_result: RoundResult | null;
  match_winner_id: number | null;
  match_end_reason: string | null;
  match_result_seq: number | null;
  powerups: Record<string, {
    swap_question: boolean;
    extend_time: boolean;
    joker: boolean;
  }>;
  rematch: RematchState;
  /** offset (serverNow - clientNow) so timers render off the server clock */
  clock_offset_ms: number;
}

export interface SessionUser {
  id: number;
  username: string;
  display_name: string;
  avatar?: string | null;
  coins: number;
  wins: number;
  losses: number;
  xp: number;
  level: number;
  xp_into_level: number;
  xp_for_next_level: number;
  rank: string;
}

export interface DemoSession {
  token: string;
  user: SessionUser;
}
