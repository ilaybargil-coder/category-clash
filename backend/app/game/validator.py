"""Answer normalization and validation.

The validator is pure Python with no I/O so it is fast, deterministic and
fully unit-testable. Fuzzy matching is intentionally deferred to Phase 3
(behind the FUZZY_MATCHING_ENABLED flag) — for the MVP an unrecognized
borderline answer is rejected rather than accepted.
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

    def __init__(self, index: QuestionIndex, max_length: int = 60) -> None:
        self._index = index
        self._max_length = max_length
        self._used_answer_ids: set[int] = set()
        self._used_groups: set[str] = set()

    def check(self, raw_text: str) -> ValidationResult:
        if raw_text and len(raw_text) > self._max_length:
            return ValidationResult(AnswerStatus.INVALID, None, "")
        normalized = normalize_answer(raw_text)
        if not normalized:
            return ValidationResult(AnswerStatus.INVALID, None, normalized)

        entry = self._index.lookup(normalized)
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
