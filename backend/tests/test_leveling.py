import pytest

from app.leveling import (
    cumulative_xp_for_level,
    intense_game_bonus,
    level_for_xp,
    performance_bonus,
    rank_for_level,
    win_streak_bonus,
    xp_progress,
)


def test_cumulative_xp_for_level_boundaries() -> None:
    assert cumulative_xp_for_level(1) == 0
    assert cumulative_xp_for_level(2) == 50
    assert cumulative_xp_for_level(3) == 110
    assert cumulative_xp_for_level(10) == 810


def test_cumulative_xp_rejects_invalid_level() -> None:
    with pytest.raises(ValueError):
        cumulative_xp_for_level(0)


@pytest.mark.parametrize(
    ("xp", "expected_level"),
    [(0, 1), (49, 1), (50, 2), (109, 2), (110, 3), (809, 9), (810, 10)],
)
def test_level_for_xp_at_level_boundaries(xp: int, expected_level: int) -> None:
    assert level_for_xp(xp) == expected_level


def test_level_for_xp_rejects_negative_xp() -> None:
    with pytest.raises(ValueError):
        level_for_xp(-1)


@pytest.mark.parametrize(
    ("xp", "expected"),
    [(0, (1, 0, 50)), (25, (1, 25, 50)), (50, (2, 0, 60)), (109, (2, 59, 60))],
)
def test_xp_progress(xp: int, expected: tuple[int, int, int]) -> None:
    assert xp_progress(xp) == expected


def test_xp_progress_rejects_negative_xp() -> None:
    with pytest.raises(ValueError):
        xp_progress(-1)


@pytest.mark.parametrize(
    ("level", "expected_rank"),
    [
        (1, "Bronze"),
        (4, "Bronze"),
        (5, "Silver"),
        (9, "Silver"),
        (10, "Gold"),
        (14, "Gold"),
        (15, "Platinum"),
        (19, "Platinum"),
        (20, "Diamond"),
        (29, "Diamond"),
        (30, "Master"),
        (44, "Master"),
        (45, "Grandmaster"),
        (59, "Grandmaster"),
        (60, "Elite"),
        (74, "Elite"),
        (75, "Champion"),
        (99, "Champion"),
        (100, "Legend"),
        (10_000, "Legend"),
    ],
)
def test_rank_for_level_boundaries(level: int, expected_rank: str) -> None:
    assert rank_for_level(level) == expected_rank


def test_rank_for_level_rejects_invalid_level() -> None:
    with pytest.raises(ValueError):
        rank_for_level(0)


@pytest.mark.parametrize(
    ("streak", "expected_bonus"),
    [(0, 0), (1, 5), (2, 10), (5, 25), (6, 25), (100, 25)],
)
def test_win_streak_bonus_formula(streak: int, expected_bonus: int) -> None:
    assert win_streak_bonus(streak) == expected_bonus


def test_win_streak_bonus_rejects_negative_streak() -> None:
    with pytest.raises(ValueError):
        win_streak_bonus(-1)


@pytest.mark.parametrize(
    ("total_answers", "expected_bonus"),
    [(0, 0), (5, 1), (15, 3), (100, 5)],
)
def test_intense_game_bonus_formula(total_answers: int, expected_bonus: int) -> None:
    assert intense_game_bonus(total_answers) == expected_bonus


@pytest.mark.parametrize(
    ("player_valid_answers", "expected_bonus"),
    [(0, 0), (1, 1), (3, 3), (100, 5)],
)
def test_performance_bonus_formula(player_valid_answers: int, expected_bonus: int) -> None:
    assert performance_bonus(player_valid_answers) == expected_bonus


@pytest.mark.parametrize("bonus", [intense_game_bonus, performance_bonus])
def test_skill_bonuses_are_non_negative_and_monotonic(bonus) -> None:
    values = [bonus(answer_count) for answer_count in range(101)]

    assert all(value >= 0 for value in values)
    assert values == sorted(values)


@pytest.mark.parametrize("bonus", [intense_game_bonus, performance_bonus])
def test_skill_bonuses_reject_negative_answer_counts(bonus) -> None:
    with pytest.raises(ValueError):
        bonus(-1)
