"""Tests for state_core.event_store."""

import logging

import pytest

from state_core.event_models import TopicStartedEvent
from state_core.event_store import (
    EventStore,
    SealedAnswerKeyStore,
    StoreConfig,
    compute_key_hash,
)
from state_core.scoring_engine import AnswerKey


@pytest.fixture
def store(tmp_path):
    """Provide an EventStore backed by a temp file."""
    path = tmp_path / "events.jsonl"
    return EventStore(StoreConfig(path=str(path)))


class TestEventStore:
    """Tests for the append-only event store."""

    def test_append_and_read_all(self, store) -> None:
        e1 = TopicStartedEvent.create(topic="algebra")
        e2 = TopicStartedEvent.create(topic="geometry")
        store.append(e1)
        store.append(e2)
        events = store.read_all()
        assert len(events) == 2
        assert events[0].topic == "algebra"
        assert events[1].topic == "geometry"

    def test_read_all_empty_file(self, store) -> None:
        assert store.read_all() == []

    def test_read_all_nonexistent_file(self) -> None:
        s = EventStore(StoreConfig(path="/nonexistent/path.jsonl"))
        assert s.read_all() == []

    def test_read_since(self, store) -> None:
        e1 = TopicStartedEvent.create(topic="early")
        e2 = TopicStartedEvent.create(topic="late")
        store.append(e1)
        store.append(e2)
        later_events = store.read_since(e1.timestamp)
        assert len(later_events) == 1
        assert later_events[0].topic == "late"

    def test_read_since_returns_empty_when_no_newer(self, store) -> None:
        e = TopicStartedEvent.create(topic="only")
        store.append(e)
        assert store.read_since("2099-12-31T23:59:59") == []

    def test_flush_on_append(self, store, tmp_path) -> None:
        e = TopicStartedEvent.create(topic="flush-test")
        store.append(e)
        raw = tmp_path / "events.jsonl"
        content = raw.read_text(encoding="utf-8").strip()
        assert len(content) > 0
        assert e.topic in content

    def test_append_validates_event_type(self, store) -> None:
        with pytest.raises(ValueError, match="Event instance"):
            store.append("not an event")


class TestCorruptionHandling:
    """Store must skip corrupt lines without crashing the replay."""

    def test_skip_corrupt_line(self, store, tmp_path) -> None:
        path = tmp_path / "events.jsonl"
        e = TopicStartedEvent.create(topic="good")
        store.append(e)
        with open(path, "a", encoding="utf-8") as f:
            f.write("not valid json\n")
        e2 = TopicStartedEvent.create(topic="also-good")
        store.append(e2)

        events = store.read_all()
        assert len(events) == 2
        assert events[0].topic == "good"
        assert events[1].topic == "also-good"

    def test_skip_corrupt_line_in_middle(self, store, tmp_path) -> None:
        path = tmp_path / "events.jsonl"
        e1 = TopicStartedEvent.create(topic="first")
        store.append(e1)
        with open(path, "a", encoding="utf-8") as f:
            f.write("{bad json\n")
        e3 = TopicStartedEvent.create(topic="third")
        store.append(e3)

        events = store.read_all()
        assert len(events) == 2
        assert events[0].topic == "first"
        assert events[1].topic == "third"

    def test_skip_empty_lines(self, store, tmp_path) -> None:
        path = tmp_path / "events.jsonl"
        e = TopicStartedEvent.create(topic="data")
        store.append(e)
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n")
            f.write("\n")
        e2 = TopicStartedEvent.create(topic="after-blanks")
        store.append(e2)
        events = store.read_all()
        assert len(events) == 2

    def test_corrupt_line_logs_warning(self, store, tmp_path, caplog) -> None:
        caplog.set_level(logging.WARNING)
        path = tmp_path / "events.jsonl"
        e = TopicStartedEvent.create(topic="good")
        store.append(e)
        with open(path, "a", encoding="utf-8") as f:
            f.write("{{{garbage}}}\n")
        store.read_all()
        assert any("Corrupt event at line" in rec.message for rec in caplog.records)


class TestSealedAnswerKeyStore:
    """Tests for the sealed answer key store stub."""

    def test_store_and_retrieve(self) -> None:
        s = SealedAnswerKeyStore()
        key = AnswerKey(required_keywords=["foo", "bar"])
        h = s.store("q_001", key)
        assert isinstance(h, str)
        assert len(h) == 64
        retrieved = s.retrieve("q_001")
        assert retrieved is not None
        assert retrieved.required_keywords == ["foo", "bar"]

    def test_retrieve_missing(self) -> None:
        s = SealedAnswerKeyStore()
        assert s.retrieve("nonexistent") is None

    def test_compute_key_hash_deterministic(self) -> None:
        key = AnswerKey(required_keywords=["a"], forbidden_keywords=["b"])
        assert compute_key_hash(key) == compute_key_hash(key)

    def test_hash_changes_with_key_content(self) -> None:
        k1 = AnswerKey(required_keywords=["a"])
        k2 = AnswerKey(required_keywords=["b"])
        assert compute_key_hash(k1) != compute_key_hash(k2)
