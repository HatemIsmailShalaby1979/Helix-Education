"""Shared test fixtures for the Helix Education Center.

Provides reusable pytest fixtures for all micro-engines.
"""

from collections.abc import Generator
from pathlib import Path

import pytest

from state_core.event_models import (
    AnswerScoredEvent,
    AnswerSubmittedEvent,
    Event,
    QuizItemCreatedEvent,
)
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig


@pytest.fixture(autouse=True)
def isolate_sealed_key_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Point the default sealed-key store at a per-test temporary path.

    A full test run must not write runtime state into the repository. The
    store resolves its default path from HELIX_SEALED_KEY_PATH at
    construction time, so setting that variable here covers every test that
    builds a SealedAnswerKeyStore without an explicit path.

    Inputs:
        tmp_path: pytest's per-test temporary directory.
        monkeypatch: pytest's environment patcher, reverted after the test.
    """
    monkeypatch.setenv("HELIX_SEALED_KEY_PATH", str(tmp_path / "sealed_answer_keys.jsonl"))
    yield


@pytest.fixture
def sealed_key_store() -> SealedAnswerKeyStore:
    """Provide a fresh in-memory SealedAnswerKeyStore."""
    return SealedAnswerKeyStore()


@pytest.fixture
def event_store(tmp_path: Path) -> Generator[EventStore]:
    """Provide an EventStore backed by a temporary JSON Lines file."""
    path = tmp_path / "events.jsonl"
    yield EventStore(StoreConfig(path=str(path)))


def make_quiz_events(topic: str, quiz_id: str, scores: list[float]) -> list[Event]:
    """Helper: build a sequence of quiz creation + answer + score events.

    Inputs:
        topic: Topic name for the quiz.
        quiz_id: Unique quiz item identifier.
        scores: List of score values (0.0-1.0) for each attempt.
    Returns:
        A list of Event instances representing the full quiz flow.
    """
    events: list[Event] = []
    events.append(
        QuizItemCreatedEvent.create(
            topic=topic,
            quiz_item_id=quiz_id,
            category="mc",
            difficulty="easy",
            answer_key_hash="abc",
        )
    )
    for i, score in enumerate(scores, start=1):
        passed = score >= 0.6
        events.append(
            AnswerSubmittedEvent.create(
                quiz_item_id=quiz_id,
                raw_answer="answer",
                attempt_number=i,
            )
        )
        events.append(
            AnswerScoredEvent.create(
                quiz_item_id=quiz_id,
                raw_score=score,
                passed=passed,
                scoring_method="keyword",
            )
        )
    return events
