"""Dynamic curriculum — loads topics from the event store.

No hardcoded topics. Everything is created dynamically by the AI agent
or the learner. The curriculum module now reflects whatever exists in
the content engine and event store.
"""

from content_engine import ContentService
from learning_service import LearningService
from state_core.event_models import TopicStartedEvent
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig

_STORE_PATH = "helix_events.jsonl"


def seed_all(learning, content, quiz) -> None:
    """No-op. Topics are created dynamically by the AI agent."""
    pass


def _get_store() -> EventStore:
    return EventStore(StoreConfig(path=_STORE_PATH))


def topic_names() -> list[str]:
    """Return topic names from the content service."""
    store = _get_store()
    ks = SealedAnswerKeyStore()
    l = LearningService(store, ks)
    c = ContentService(l)
    return c.list_topics()


def topic_data(name: str) -> dict:
    """Return minimal topic metadata from the event store (with content service fallback)."""
    store = _get_store()
    events = store.read_all()
    for e in events:
        if isinstance(e, TopicStartedEvent) and e.topic == name:
            return {
                "name": name,
                "level": e.requested_level or "beginner",
                "concepts": [],
                "prerequisites": [e.parent_topic] if e.parent_topic else [],
            }
    ks = SealedAnswerKeyStore()
    l = LearningService(store, ks)
    c = ContentService(l)
    lesson = c.get_lesson(name)
    if lesson is not None:
        return {"name": name, "level": "beginner", "concepts": [], "prerequisites": []}
    return {"name": name, "level": "beginner", "concepts": [], "prerequisites": []}


def get_dig_deeper(topic_name: str, section_id: str, current_depth: int) -> str:
    """Return placeholder — AI agent generates dig-deeper content on demand."""
    return "Ask the AI tutor to generate advanced content for this section."
