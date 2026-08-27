"""Rubric-based deterministic answer scoring engine.

This module implements a purely keyword/structural scoring algorithm.
It is deliberately primitive — a placeholder deterministic floor.
No semantic matching, embeddings, or ML is used.
Semantic/LLM-based verification is reserved for a later layer that does
not yet exist.
"""

from dataclasses import dataclass, field


@dataclass
class AnswerKey:
    """Scoring key for a quiz item.

    Inputs:
        required_keywords: Keywords that must appear in the answer.
        forbidden_keywords: Keywords that indicate a misconception.
        min_length_chars: Minimum character length for the answer.
    """

    required_keywords: list[str] = field(default_factory=list)
    forbidden_keywords: list[str] = field(default_factory=list)
    min_length_chars: int = 0


@dataclass
class ScoreResult:
    """Result of scoring a single answer.

    Inputs:
        raw_score: Float in [0.0, 1.0] computed as matched/required minus
            forbidden penalty.
        passed: True when raw_score >= 0.6.
        missing_keywords: Required keywords not found in the answer.
        matched_keywords: Required keywords found in the answer.
        attempt_number: The attempt number for this answer (1-based).
    """

    raw_score: float
    passed: bool
    missing_keywords: list[str]
    matched_keywords: list[str]
    attempt_number: int = 1


def _normalize(text: str) -> str:
    """Lowercase and strip whitespace for case-insensitive matching."""
    return text.strip().lower()


def score_answer_detailed(raw_answer: str, answer_key: AnswerKey, attempt_number: int = 1) -> ScoreResult:
    """Score a raw answer against a deterministic AnswerKey.

    Algorithm:
        1. Find which required keywords appear in the answer (case-insensitive).
        2. Base score = matched_count / required_count (1.0 if required is empty).
        3. For each forbidden keyword found, subtract 0.1 from the score.
        4. Clamp raw_score to [0.0, 1.0].
        5. passed = raw_score >= 0.6.

    Inputs:
        raw_answer: The learner's submitted answer text.
        answer_key: The AnswerKey containing required/forbidden keywords.
        attempt_number: The attempt number for this answer (1-based).

    Returns:
        A ScoreResult with all computed fields.

    Raises:
        ValueError: If raw_answer is empty.
    """
    if not raw_answer or not raw_answer.strip():
        raise ValueError("raw_answer must not be empty")

    normalized = _normalize(raw_answer)
    required_count = len(answer_key.required_keywords)

    matched: list[str] = []
    missing: list[str] = []
    for kw in answer_key.required_keywords:
        if _normalize(kw) in normalized:
            matched.append(kw)
        else:
            missing.append(kw)

    if required_count > 0:
        base_score = len(matched) / required_count
    else:
        base_score = 1.0

    forbidden_found = 0
    for kw in answer_key.forbidden_keywords:
        if _normalize(kw) in normalized:
            forbidden_found += 1

    penalty = forbidden_found * 0.1
    raw_score = max(0.0, base_score - penalty)

    passed = raw_score >= 0.6

    return ScoreResult(
        raw_score=raw_score,
        passed=passed,
        missing_keywords=missing,
        matched_keywords=matched,
        attempt_number=attempt_number,
    )


def score_answer(
    item_id: str,
    provided_answer: str,
    required_keywords: list[str],
) -> float:
    """Score a raw answer against a list of required keywords.

    Convenience wrapper around the keyword-match scoring algorithm.
    Constructs an AnswerKey from the provided keywords and delegates
    to the core score_answer_detailed function.

    Algorithm:
        1. Find which required keywords appear in the answer
           (case-insensitive).
        2. Base score = matched_count / required_count (1.0 if no
           keywords required).
        3. Clamp raw_score to [0.0, 1.0].

    Inputs:
        item_id: The quiz item identifier (for logging/context).
        provided_answer: The learner's submitted answer text.
        required_keywords: Keywords that must appear in the answer.

    Returns:
        A float in [0.0, 1.0] representing the keyword-match score.

    Raises:
        ValueError: If provided_answer is empty.
    """
    answer_key = AnswerKey(required_keywords=required_keywords)
    result = score_answer_detailed(provided_answer, answer_key)
    return result.raw_score


def score_answer_simple(
    item_id: str,
    provided_answer: str,
    required_keywords: list[str],
) -> float:
    """Score a raw answer against a list of required keywords.

    Alias for score_answer for backward compatibility.

    Inputs:
        item_id: The quiz item identifier (for logging/context).
        provided_answer: The learner's submitted answer text.
        required_keywords: Keywords that must appear in the answer.

    Returns:
        A float in [0.0, 1.0] representing the keyword-match score.

    Raises:
        ValueError: If provided_answer is empty.
    """
    return score_answer(item_id, provided_answer, required_keywords)
