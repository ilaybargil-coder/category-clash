"""Pure XP curve, level, rank, and streak calculations."""

WIN_XP = 30
LOSS_XP = 10
DAILY_CHALLENGE_XP = 20


def cumulative_xp_for_level(level: int) -> int:
    """Return the total XP required to reach ``level`` from level 1."""

    if level < 1:
        raise ValueError("level must be at least 1")
    return (level - 1) * (40 + 5 * level)


def level_for_xp(xp: int) -> int:
    """Return the current level for a non-negative total XP value."""

    if xp < 0:
        raise ValueError("xp must be non-negative")
    level = 1
    while xp >= cumulative_xp_for_level(level + 1):
        level += 1
    return level


def xp_progress(xp: int) -> tuple[int, int, int]:
    """Return level, XP earned within it, and XP needed for its next level."""

    level = level_for_xp(xp)
    into_level = xp - cumulative_xp_for_level(level)
    needed_for_next = 40 + 10 * level
    return level, into_level, needed_for_next


def rank_for_level(level: int) -> str:
    """Return the rank tier for a level."""

    if level < 1:
        raise ValueError("level must be at least 1")
    if level < 10:
        return "Bronze"
    if level < 20:
        return "Silver"
    if level < 30:
        return "Gold"
    if level < 40:
        return "Platinum"
    return "Diamond"


def win_streak_bonus(current_streak: int) -> int:
    """Return the XP bonus for the winner's updated consecutive-win count."""

    if current_streak < 0:
        raise ValueError("current_streak must be non-negative")
    return min(current_streak, 5) * 5


def intense_game_bonus(total_answers: int) -> int:
    """Return shared XP for a match with many valid answers."""

    if total_answers < 0:
        raise ValueError("total_answers must be non-negative")
    return min(total_answers // 5, 5)


def performance_bonus(player_valid_answers: int) -> int:
    """Return XP for a player's own valid answers in one match."""

    if player_valid_answers < 0:
        raise ValueError("player_valid_answers must be non-negative")
    return min(player_valid_answers, 5)
