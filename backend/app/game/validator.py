"""Answer normalization and conservative typo-tolerant validation.

The validator is pure Python with no I/O so it is fast, deterministic and
fully unit-testable. Exact canonical forms and aliases always win. Optional
fuzzy matching only accepts one-edit mistakes when the match is unambiguous;
short substitutions must also be between neighboring keyboard keys.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum


class AnswerStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    DUPLICATE = "DUPLICATE"
    TOO_SIMILAR = "TOO_SIMILAR"
    NOT_YOUR_TURN = "NOT_YOUR_TURN"
    ROUND_FINISHED = "ROUND_FINISHED"
    TIME_EXPIRED = "TIME_EXPIRED"


# Hebrew final letters -> regular form, so "אגוזין" == "אגוזים" style typos
# in final position don't break matching.
_FINAL_LETTERS = str.maketrans({"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"})
# Hebrew cantillation + niqqud marks.
_NIKUD_RE = re.compile(r"[֑-ׇ]")
# Quote-like marks (geresh, gershayim, apostrophes) are removed entirely so
# that "ליצ'י" == "ליצי"; all other punctuation becomes a space so that
# "סוסון-ים" == "סוסון ים".
_QUOTES_RE = re.compile(r"[׳״'\"`”“’‘]")
_PUNCT_RE = re.compile(r"[^\w\s]|_")
_WHITESPACE_RE = re.compile(r"\s+")

# Physical Hebrew keyboard positions. Final letters are normalized before
# matching, so a letter can legitimately have more than one key position.
_HEBREW_KEY_ROWS = (
    "קראטוןםפ",
    "שדגכעיחלךף",
    "זסבהנמצתץ",
)
_ENGLISH_KEY_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")


def _keyboard_positions() -> dict[str, list[tuple[int, float]]]:
    positions: dict[str, list[tuple[int, float]]] = {}
    offsets = (0.0, 0.25, 0.75)
    for rows in (_HEBREW_KEY_ROWS, _ENGLISH_KEY_ROWS):
        for row_no, row in enumerate(rows):
            for column, character in enumerate(row):
                normalized = character.translate(_FINAL_LETTERS)
                positions.setdefault(normalized, []).append((row_no, column + offsets[row_no]))
    return positions


_KEY_POSITIONS = _keyboard_positions()


def normalize_answer(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.lower()
    normalized = _NIKUD_RE.sub("", normalized)
    normalized = normalized.translate(_FINAL_LETTERS)
    normalized = _QUOTES_RE.sub("", normalized)
    normalized = _PUNCT_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized


@dataclass(frozen=True)
class ApprovedEntry:
    answer_id: int
    canonical: str
    semantic_group: str | None


class QuestionIndex:
    """Normalized form -> approved answer lookup for a single question."""

    def __init__(self) -> None:
        self._by_form: dict[str, ApprovedEntry] = {}

    def add_form(self, form: str, entry: ApprovedEntry) -> None:
        key = normalize_answer(form)
        if key and key not in self._by_form:
            self._by_form[key] = entry

    def lookup(self, normalized: str) -> ApprovedEntry | None:
        return self._by_form.get(normalized)

    def lookup_typo(
        self,
        normalized: str,
        *,
        min_length: int,
        max_distance: int,
    ) -> ApprovedEntry | None:
        """Return one unambiguous approved answer for a safe one-edit typo."""

        compact_length = len(normalized.replace(" ", ""))
        if compact_length < min_length or max_distance < 1:
            return None

        closest_distance = max_distance + 1
        matches: dict[int, ApprovedEntry] = {}
        for form, entry in self._by_form.items():
            distance = _damerau_levenshtein(normalized, form, max_distance)
            if distance > max_distance or not _safe_typo_pair(normalized, form):
                continue
            if distance < closest_distance:
                closest_distance = distance
                matches = {entry.answer_id: entry}
            elif distance == closest_distance:
                matches[entry.answer_id] = entry

        if len(matches) != 1:
            return None
        return next(iter(matches.values()))

    def __len__(self) -> int:
        return len(self._by_form)


@dataclass
class QuestionData:
    id: int
    text: str
    index: QuestionIndex


def build_question_index(
    answers: list[tuple[int, str, str | None, list[str]]],
) -> QuestionIndex:
    """answers: list of (answer_id, canonical, semantic_group, aliases)."""
    index = QuestionIndex()
    for answer_id, canonical, group, aliases in answers:
        entry = ApprovedEntry(answer_id=answer_id, canonical=canonical, semantic_group=group)
        index.add_form(canonical, entry)
        for alias in aliases:
            index.add_form(alias, entry)
    return index


@dataclass
class ValidationResult:
    status: AnswerStatus
    entry: ApprovedEntry | None
    normalized: str


class RoundValidator:
    """Tracks answers used within a single round and classifies new ones."""

    def __init__(
        self,
        index: QuestionIndex,
        max_length: int = 60,
        *,
        fuzzy_enabled: bool = False,
        fuzzy_max_distance: int = 1,
        fuzzy_min_length: int = 4,
    ) -> None:
        self._index = index
        self._max_length = max_length
        self._fuzzy_enabled = fuzzy_enabled
        self._fuzzy_max_distance = fuzzy_max_distance
        self._fuzzy_min_length = fuzzy_min_length
        self._used_answer_ids: set[int] = set()
        self._used_groups: set[str] = set()

    def check(self, raw_text: str) -> ValidationResult:
        if raw_text and len(raw_text) > self._max_length:
            return ValidationResult(AnswerStatus.INVALID, None, "")
        normalized = normalize_answer(raw_text)
        if not normalized:
            return ValidationResult(AnswerStatus.INVALID, None, normalized)

        entry = self._index.lookup(normalized)
        if entry is None and self._fuzzy_enabled:
            entry = self._index.lookup_typo(
                normalized,
                min_length=self._fuzzy_min_length,
                max_distance=self._fuzzy_max_distance,
            )
        if entry is None:
            return ValidationResult(AnswerStatus.INVALID, None, normalized)
        if entry.answer_id in self._used_answer_ids:
            # Same answer (or one of its aliases) was already given.
            return ValidationResult(AnswerStatus.DUPLICATE, entry, normalized)
        if entry.semantic_group and entry.semantic_group in self._used_groups:
            # A different approved answer that means the same thing was given.
            return ValidationResult(AnswerStatus.TOO_SIMILAR, entry, normalized)

        self._used_answer_ids.add(entry.answer_id)
        if entry.semantic_group:
            self._used_groups.add(entry.semantic_group)
        return ValidationResult(AnswerStatus.VALID, entry, normalized)


def _damerau_levenshtein(left: str, right: str, limit: int) -> int:
    """Bounded optimal-string-alignment distance with adjacent transpositions."""

    if abs(len(left) - len(right)) > limit:
        return limit + 1
    previous_previous: list[int] | None = None
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        row_minimum = left_index
        for right_index, right_char in enumerate(right, start=1):
            cost = 0 if left_char == right_char else 1
            value = min(
                current[right_index - 1] + 1,
                previous[right_index] + 1,
                previous[right_index - 1] + cost,
            )
            if (
                previous_previous is not None
                and left_index > 1
                and right_index > 1
                and left_char == right[right_index - 2]
                and left[left_index - 2] == right_char
            ):
                value = min(value, previous_previous[right_index - 2] + 1)
            current.append(value)
            row_minimum = min(row_minimum, value)
        if row_minimum > limit:
            return limit + 1
        previous_previous, previous = previous, current
    return previous[-1]


def _keys_are_neighbors(left: str, right: str) -> bool:
    left_positions = _KEY_POSITIONS.get(left, ())
    right_positions = _KEY_POSITIONS.get(right, ())
    return any(
        abs(left_row - right_row) <= 1 and abs(left_column - right_column) <= 1.25
        for left_row, left_column in left_positions
        for right_row, right_column in right_positions
    )


def _safe_typo_pair(typed: str, approved: str) -> bool:
    """Apply stricter rules to short words where one edit is more dangerous."""

    if typed == approved:
        return True
    if len(typed) == len(approved):
        mismatches = [
            index
            for index, pair in enumerate(zip(typed, approved, strict=True))
            if pair[0] != pair[1]
        ]
        if len(mismatches) == 1:
            index = mismatches[0]
            if min(len(typed.replace(" ", "")), len(approved.replace(" ", ""))) <= 4:
                return _keys_are_neighbors(typed[index], approved[index])
            return True
        if len(mismatches) == 2:
            first, second = mismatches
            return (
                second == first + 1
                and typed[first] == approved[second]
                and typed[second] == approved[first]
            )
        return False

    # Missing/extra letters are common, but too risky for words of four or
    # fewer letters (for example, one short real word becoming another).
    return max(len(typed.replace(" ", "")), len(approved.replace(" ", ""))) >= 5
