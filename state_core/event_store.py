"""Append-only event store backed by a JSON Lines file.

Events are serialized as one JSON object per line. The file is never
rewritten — only appended to. Corruption of a single line never crashes
a full replay; the bad line is logged and skipped.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass

from observability.metrics import metrics

from .event_models import Event
from .scoring_engine import AnswerKey

logger = logging.getLogger(__name__)


@dataclass
class StoreConfig:
    """Configuration for the event store.

    Inputs:
        path: Absolute or relative path to the JSON Lines file.
        sealed_keys_path: Optional path to persisted sealed answer keys store (JSON file).
    """

    path: str
    sealed_keys_path: str | None = None


class EventStore:
    """Append-only, JSON Lines-backed event store.

    Inputs:
        config: StoreConfig pointing to the file path.
    """

    def __init__(self, config: StoreConfig) -> None:
        self._config = config

    def append(self, event: Event) -> None:
        """Validate and append an event to the store.

        The event is immediately flushed to disk (no buffering).

        Inputs:
            event: An Event subclass instance.
        Raises:
            ValueError: If the event fails validation.
        """
        start_time = time.time()
        if not isinstance(event, Event):
            raise ValueError("Expected Event instance")
        event.validate()
        line = json.dumps(event.to_dict()) + "\n"
        with open(self._config.path, "a") as f:
            f.write(line)

        latency = time.time() - start_time
        metrics.increment_counter("events_appended_total")
        metrics.observe_histogram("event_append_latency_seconds", latency)
        logger.info(f"Event appended: {event.event_type} (latency: {latency:.4f}s)")

    def _append_raw(self, event: Event) -> None:
        """Internal raw append without metrics (used for replay/migration)."""
        if not isinstance(event, Event):
            raise ValueError("Expected Event instance")
        event.validate()
        line = json.dumps(event.to_dict()) + "\n"
        with open(self._config.path, "a") as f:
            f.write(line)

    def read_all(self) -> list[Event]:
        """Read and replay all events from the store.

        Returns:
            A list of Event instances in append order.
            If the file does not exist, returns an empty list.
        """
        return self._read_lines(0)

    def read_since(self, timestamp: str) -> list[Event]:
        """Read events whose timestamp is strictly after the given timestamp.

        Inputs:
            timestamp: ISO8601 UTC timestamp string for comparison.
        Returns:
            A list of Event instances with timestamp > given timestamp.
        """
        return [e for e in self.read_all() if e.timestamp > timestamp]

    def _read_lines(self, _min_line: int = 0) -> list[Event]:
        """Internal: read and parse all lines from the store file.

        Corrupt lines are logged with a warning and skipped.
        """
        events: list[Event] = []
        try:
            with open(self._config.path, encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    if line_no < _min_line:
                        continue
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        data = json.loads(stripped)
                        event = Event.from_dict(data)
                        events.append(event)
                    except (json.JSONDecodeError, ValueError, TypeError) as exc:
                        logger.warning(
                            "Corrupt event at line %d: %s; skipping",
                            line_no,
                            exc,
                        )
        except FileNotFoundError:
            pass
        return events


class SealedAnswerKeyStore:
    """File-backed sealed answer key store.

    Stores AnswerKey objects to a JSON Lines file separate from the main
    event log. Each line is a canonical JSON record containing the quiz
    item id and the AnswerKey fields. This is a minimal production-ready
    placeholder: a true sealed store should use an external KMS and
    encryption. This implementation provides durable, testable storage
    for deterministic scoring and CI.
    """

    def __init__(self, config: StoreConfig | None = None) -> None:
        self._config = config
        self._path = config.sealed_keys_path if (config and config.sealed_keys_path) else ".sealed_answer_keys.jsonl"
        self._keys: dict[str, AnswerKey] = {}
        try:
            with open(self._path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                        qid = rec.get("quiz_item_id")
                        key = AnswerKey(
                            required_keywords=rec.get("required_keywords", []),
                            forbidden_keywords=rec.get("forbidden_keywords", []),
                            min_length_chars=rec.get("min_length_chars", 0),
                        )
                        if qid:
                            self._keys[qid] = key
                    except Exception:
                        # skip malformed lines — don't raise
                        continue
        except FileNotFoundError:
            # no persisted keys yet
            pass

    def store(self, quiz_item_id: str, key: AnswerKey) -> str:
        """Store an AnswerKey and return its SHA-256 hash.

        The AnswerKey is appended as a canonical JSON line to the sealed
        keys file for durability. The in-memory index is also updated.
        """
        self._keys[quiz_item_id] = key
        record = {
            "quiz_item_id": quiz_item_id,
            "required_keywords": key.required_keywords,
            "forbidden_keywords": key.forbidden_keywords,
            "min_length_chars": key.min_length_chars,
        }
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
        return compute_key_hash(key)

    def retrieve(self, quiz_item_id: str) -> AnswerKey | None:
        """Retrieve a stored AnswerKey by quiz item ID."""
        return self._keys.get(quiz_item_id)


def compute_key_hash(key: AnswerKey) -> str:
    """Compute a deterministic SHA-256 hash of an AnswerKey.

    Inputs:
        key: The AnswerKey to hash.
    Returns:
        SHA-256 hex digest string.
    """
    canonical = json.dumps(
        {
            "required_keywords": sorted(key.required_keywords),
            "forbidden_keywords": sorted(key.forbidden_keywords),
            "min_length_chars": key.min_length_chars,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
