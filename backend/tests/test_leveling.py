import pytest

from app.leveling import (
    cumulative_xp_for_level,
    level_for_xp,
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
        (9, "Bronze"),
        (10, "Silver"),
        (19, "Silver"),
        (20, "Gold"),
        (29, "Gold"),
        (30, "Platinum"),
        (39, "Platinum"),
        (40, "Diamond"),
        (100, "Diamond"),
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
