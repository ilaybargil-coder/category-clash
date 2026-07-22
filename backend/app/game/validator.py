"""Answer normalization and conservative typo-tolerant validation.

The validator is pure Python with no I/O so it is fast, deterministic and
fully unit-testable. Exact canonical forms and aliases always win. Optional
spelling and fuzzy matching only accept a single approved answer; short typo
substitutions must also be between neighboring keyboard keys.
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
# Hebrew cantillation + niqqud marks. Explicit sin is converted to ס before
# these marks are removed, while an unpointed ש remains distinct.
_EXPLICIT_SIN_RE = re.compile(r"ש\u05c2")
_NIKUD_RE = re.compile(r"[\u0591-\u05bd\u05bf\u05c1\u05c2\u05c4\u05c5\u05c7]")
# Quote-like marks (geresh, gershayim, apostrophes) are removed entirely so
# that "ליצ'י" == "ליצי"; all other punctuation becomes a space so that
# "סוסון-ים" == "סוסון ים".
_QUOTES_RE = re.compile(r"[׳״'\"`”“’‘]")
_PUNCT_RE = re.compile(r"[^\w\s\u05c2]|_")
_WHITESPACE_RE = re.compile(r"\s+")
_DOUBLED_MATRES_RE = re.compile(r"([וי])\1+")
_HEBREW_RE = re.compile(r"^[\u05d0-\u05ea ]+$")

# Prefixes are stripped only from a submitted answer, after an exact lookup
# has failed. Short stems are deliberately excluded because strings such as
# כלוב/לוב and מדינה/דינה are different words, not safe prefix variants.
_HEBREW_PREFIX_MIN_STEM_LENGTH = {
    "וה": 3,
    "בה": 6,
    "כה": 6,
    "לה": 6,
    "מה": 6,
    "שה": 6,
    "ה": 3,
    "ו": 3,
    "ב": 6,
    "כ": 6,
    "ל": 6,
    "מ": 6,
    "ש": 6,
}

# Physical Hebrew keyboard positions. Final letters are normalized before
# matching, so a letter can legitimately have more than one key position.
_HEBREW_KEY_ROWS = (
    "קראטוןםפ",
    "שדגכעיחלךף",
    "זסבהנמצתץ",
)
_ENGLISH_KEY_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")

# Conservative Hebrew sound/spelling folds. The explicit sin sequence is
# handled before the single-character folds so ordinary ש is never folded.
SKELETON_FOLDS: dict[str, str] = {
    "ט": "ת",
    "ת": "ת",
    "כ": "כ",
    "ק": "כ",
    "ס": "ס",
    "א": "א",
    "ע": "א",
    "ה": "א",
    "ו": "ו",
    "ב": "ו",
}


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


def _compact(text: str) -> str:
    return text.replace(" ", "")


def normalize_answer(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.lower()
    normalized = _EXPLICIT_SIN_RE.sub("ס", normalized)
    normalized = _NIKUD_RE.sub("", normalized)
    normalized = "".join(
        str(unicodedata.digit(character)) if unicodedata.category(character) == "Nd" else character
        for character in normalized
    )
    normalized = normalized.translate(_FINAL_LETTERS)
    normalized = _QUOTES_RE.sub("", normalized)
    normalized = _PUNCT_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized


def skeleton_form(normalized: str) -> str:
    """Fold conservative Hebrew spelling variants into a stable skeleton."""

    skeleton = _DOUBLED_MATRES_RE.sub(r"\1", normalized)
    skeleton = "".join(SKELETON_FOLDS.get(character, character) for character in skeleton)
    return _DOUBLED_MATRES_RE.sub(r"\1", skeleton)


def _safe_skeleton_pair(typed: str, approved: str) -> bool:
    """Bound phonetic matching to short, recognizable spelling changes."""

    if typed == approved:
        return True
    typed_compact = _compact(typed)
    approved_compact = _compact(approved)
    if _DOUBLED_MATRES_RE.sub(r"\1", typed_compact) == _DOUBLED_MATRES_RE.sub(
        r"\1", approved_compact
    ):
        return min(len(typed_compact), len(approved_compact)) >= 3
    if min(len(typed_compact), len(approved_compact)) < 4:
        return False
    if len(typed_compact) != len(approved_compact):
        return False

    distance = _damerau_levenshtein(typed_compact, approved_compact, 2)
    if distance <= 1:
        if len(typed_compact) < 5:
            mismatches = {
                typed_char
                for typed_char, approved_char in zip(typed_compact, approved_compact, strict=True)
                if typed_char != approved_char
            } | {
                approved_char
                for typed_char, approved_char in zip(typed_compact, approved_compact, strict=True)
                if typed_char != approved_char
            }
            if mismatches and mismatches <= {"א", "ע", "ה"}:
                return False
        return True
    if distance > 2:
        return False

    # Two bet/vav substitutions occur in established transliterations such
    # as וולוו/בולבו. Other two-fold phonetic changes are too permissive.
    mismatches = [
        (typed_char, approved_char)
        for typed_char, approved_char in zip(typed_compact, approved_compact, strict=True)
        if typed_char != approved_char
    ]
    return len(typed_compact) >= 5 and all(set(pair) <= {"ב", "ו"} for pair in mismatches)


@dataclass(frozen=True)
class ApprovedEntry:
    answer_id: int
    canonical: str
    semantic_group: str | None


class QuestionIndex:
    """Normalized form -> approved answer lookup for a single question."""

    def __init__(self) -> None:
        self._by_form: dict[str, set[int]] = {}
        self._by_compact: dict[str, set[int]] = {}
        self._by_skeleton: dict[str, dict[int, set[str]]] = {}
        self._by_answer_id: dict[int, ApprovedEntry] = {}

    def add_form(self, form: str, entry: ApprovedEntry) -> None:
        key = normalize_answer(form)
        if not key:
            return
        self._by_answer_id.setdefault(entry.answer_id, entry)
        self._by_form.setdefault(key, set()).add(entry.answer_id)
        self._by_compact.setdefault(_compact(key), set()).add(entry.answer_id)
        forms = self._by_skeleton.setdefault(skeleton_form(key), {})
        forms.setdefault(entry.answer_id, set()).add(key)

    def lookup(self, normalized: str) -> ApprovedEntry | None:
        return self._unique_entry(self._by_form.get(normalized, set()))

    def lookup_compact(self, normalized: str) -> ApprovedEntry | None:
        """Ignore word separators only when they identify one answer."""

        compact = _compact(normalized)
        if len(compact) < 3:
            return None
        return self._unique_entry(self._by_compact.get(compact, set()))

    def lookup_skeleton(self, normalized: str) -> ApprovedEntry | None:
        """Resolve a spelling skeleton only when it identifies one answer."""

        candidates = self._by_skeleton.get(skeleton_form(normalized), {})
        answer_ids = {
            answer_id
            for answer_id, forms in candidates.items()
            if any(_safe_skeleton_pair(normalized, form) for form in forms)
        }
        return self._unique_entry(answer_ids)

    def lookup_prefixed(
        self,
        normalized: str,
        *,
        definite_article_enabled: bool,
    ) -> tuple[ApprovedEntry | None, bool]:
        """Resolve a bounded Hebrew grammatical prefix without guessing."""

        answer_ids: set[int] = set()
        for prefix, min_stem_length in _HEBREW_PREFIX_MIN_STEM_LENGTH.items():
            if prefix.endswith("ה") and not definite_article_enabled:
                continue
            if not normalized.startswith(prefix):
                continue
            stem = normalized[len(prefix) :].lstrip()
            if (
                len(_compact(stem)) < min_stem_length
                or not stem
                or _HEBREW_RE.fullmatch(stem) is None
            ):
                continue
            answer_ids.update(self._by_form.get(stem, set()))
            answer_ids.update(self._by_compact.get(_compact(stem), set()))
        return self._unique_entry(answer_ids), len(answer_ids) > 1

    def lookup_unique_prefix(
        self,
        normalized: str,
        *,
        min_length: int,
    ) -> ApprovedEntry | None:
        """Resolve a prefix only when every matching form is one answer.

        Completion is deliberately scoped to the current question.  It never
        guesses between two approved answers: ``דג`` remains ambiguous when a
        question contains several fish, while a distinctive prefix such as
        ``מחשבת`` can safely resolve to ``מחשבת ישראל``.
        """

        compact_length = len(normalized.replace(" ", ""))
        if compact_length < min_length:
            return None

        matches: dict[int, ApprovedEntry] = {}
        for form, answer_ids in self._by_form.items():
            if form.startswith(normalized):
                for answer_id in answer_ids:
                    matches[answer_id] = self._by_answer_id[answer_id]
                if len(matches) > 1:
                    return None
        if len(matches) != 1:
            return None
        return next(iter(matches.values()))

    def lookup_typo(
        self,
        normalized: str,
        *,
        min_length: int,
        max_distance: int,
        two_edit_min_length: int,
    ) -> ApprovedEntry | None:
        """Return the uniquely closest approved answer for a safe typo."""

        compact_length = len(normalized.replace(" ", ""))
        if compact_length < min_length or max_distance < 1:
            return None

        scaled_max_distance = 1 if compact_length < two_edit_min_length else 2
        allowed_distance = min(max_distance, scaled_max_distance)

        closest_distance = allowed_distance + 1
        matches: dict[int, ApprovedEntry] = {}
        closest_answer_ids: set[int] = set()
        for form, answer_ids in self._by_form.items():
            distance = _damerau_levenshtein(normalized, form, allowed_distance)
            if distance > allowed_distance:
                continue
            if distance < closest_distance:
                closest_distance = distance
                closest_answer_ids = set(answer_ids)
                matches = {}
            elif distance == closest_distance:
                closest_answer_ids.update(answer_ids)

            if distance == closest_distance and _safe_typo_pair(normalized, form):
                for answer_id in answer_ids:
                    matches[answer_id] = self._by_answer_id[answer_id]

        if len(closest_answer_ids) != 1 or len(matches) != 1:
            return None
        return next(iter(matches.values()))

    def __len__(self) -> int:
        return len(self._by_form)

    def _unique_entry(self, answer_ids: set[int]) -> ApprovedEntry | None:
        if len(answer_ids) != 1:
            return None
        return self._by_answer_id[next(iter(answer_ids))]


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
        fuzzy_max_distance: int = 2,
        fuzzy_min_length: int = 4,
        fuzzy_two_edit_min_length: int = 7,
        hebrew_skeleton_enabled: bool = False,
        unique_prefix_enabled: bool = True,
        unique_prefix_min_length: int = 3,
        definite_article_enabled: bool = True,
        hebrew_prefixes_enabled: bool = True,
    ) -> None:
        self._index = index
        self._max_length = max_length
        self._fuzzy_enabled = fuzzy_enabled
        self._fuzzy_max_distance = fuzzy_max_distance
        self._fuzzy_min_length = fuzzy_min_length
        self._fuzzy_two_edit_min_length = fuzzy_two_edit_min_length
        self._hebrew_skeleton_enabled = hebrew_skeleton_enabled
        self._unique_prefix_enabled = unique_prefix_enabled
        self._unique_prefix_min_length = unique_prefix_min_length
        self._definite_article_enabled = definite_article_enabled
        self._hebrew_prefixes_enabled = hebrew_prefixes_enabled
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
            entry = self._index.lookup_compact(normalized)
        if entry is None and self._hebrew_prefixes_enabled:
            # Exact forms always win, so legitimate answers that begin with a
            # prefix letter (for example, הולנד) are never altered.
            entry, prefix_is_ambiguous = self._index.lookup_prefixed(
                normalized,
                definite_article_enabled=self._definite_article_enabled,
            )
            if prefix_is_ambiguous:
                return ValidationResult(AnswerStatus.INVALID, None, normalized)
        if entry is None and self._unique_prefix_enabled:
            entry = self._index.lookup_unique_prefix(
                normalized,
                min_length=self._unique_prefix_min_length,
            )
        if entry is None and self._hebrew_skeleton_enabled:
            entry = self._index.lookup_skeleton(normalized)
        if entry is None and self._fuzzy_enabled:
            entry = self._index.lookup_typo(
                normalized,
                min_length=self._fuzzy_min_length,
                max_distance=self._fuzzy_max_distance,
                two_edit_min_length=self._fuzzy_two_edit_min_length,
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
    """Accept only keyboard-neighbor, transposition, or bounded insertion slips."""

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
            return _keys_are_neighbors(typed[index], approved[index])
        if len(mismatches) == 2:
            first, second = mismatches
            if (
                second == first + 1
                and typed[first] == approved[second]
                and typed[second] == approved[first]
            ):
                return min(len(_compact(typed)), len(_compact(approved))) >= 4
            return min(len(_compact(typed)), len(_compact(approved))) >= 7 and all(
                _keys_are_neighbors(typed[index], approved[index]) for index in mismatches
            )
        return False

    if abs(len(typed) - len(approved)) != 1:
        return False

    longer, shorter = (typed, approved) if len(typed) > len(approved) else (approved, typed)
    # Accidental doubled keystrokes are safe down to four-letter answers.
    for index in range(1, len(longer)):
        if longer[index] == longer[index - 1] and longer[:index] + longer[index + 1 :] == shorter:
            return len(_compact(shorter)) >= 4

    # Arbitrary missing/extra letters remain available only for long words;
    # they are too likely to turn one real short word into another.
    return max(len(_compact(typed)), len(_compact(approved))) >= 7
