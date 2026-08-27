"""Bridge CLI tool for the opencode AI agent.

The AI agent invokes this script to persist generated educational content
into the Helix Education Center engines. All content is created dynamically
by the LLM - this tool only handles storage/retrieval.

Usage:
  python -m helix_education.agent_tools create-lesson <topic> <title>
  python -m helix_education.agent_tools add-section <topic> <section_id> <title> <body> [--citations <json>]
  python -m helix_education.agent_tools create-quiz <topic> <quiz_id> [--title <title>]
  python -m helix_education.agent_tools add-quiz-item <quiz_id> <item_id> <question> <category> <difficulty> <answer_key_json>
  python -m helix_education.agent_tools start-topic <topic>
  python -m helix_education.agent_tools list-topics
  python -m helix_education.agent_tools list-quizzes <topic>
  python -m helix_education.agent_tools get-lesson <topic>
  python -m helix_education.agent_tools get-knowledge-map
  python -m helix_education.agent_tools get-profile
"""

import json
import sys

from cognitive_engine.cognitive_service import CognitiveService
from content_engine import ContentService
from learning_service import LearningService
from quiz_engine import QuizService
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig
from state_core.scoring_engine import AnswerKey

_STORE_PATH = "helix_events.jsonl"


def _get_services():
    store = EventStore(StoreConfig(path=_STORE_PATH))
    ks = SealedAnswerKeyStore()
    l = LearningService(store, ks)
    c = ContentService(l)
    q = QuizService(l)
    cog = CognitiveService(l)
    return l, c, q, cog


def _start_topic(args):
    if not args:
        return "Usage: start-topic <topic>"
    topic = args[0]
    l, c, q, cog = _get_services()
    from state_core.event_models import TopicStartedEvent

    existing = l._event_store.read_all()
    already = any(isinstance(e, TopicStartedEvent) and e.topic == topic for e in existing)
    if already:
        return f"Topic '{topic}' already exists."
    l.start_topic(topic)
    return f"Topic '{topic}' started."


def _create_lesson(args):
    if len(args) < 2:
        return "Usage: create-lesson <topic> <title>"
    topic, title = args[0], args[1]
    l, c, q, cog = _get_services()
    from state_core.event_models import TopicStartedEvent

    existing = c.get_lesson(topic)
    existing_started = any(isinstance(e, TopicStartedEvent) and e.topic == topic for e in l._event_store.read_all())
    if existing:
        existing.title = title
        l.start_topic(topic, lesson_title=title)
        return f"Lesson title updated to '{title}' for topic '{topic}'."
    if existing_started:
        c.create_lesson(topic, title)
        l.start_topic(topic, lesson_title=title)
        return f"Lesson title updated to '{title}' for topic '{topic}'."
    c.create_lesson(topic, title)
    l.start_topic(topic, lesson_title=title)
    return f"Lesson '{title}' created for topic '{topic}'."


def _add_section(args):
    if len(args) < 4:
        return "Usage: add-section <topic> <section_id> <title> <body> [--citations <json>]"
    topic, section_id, title, body = args[0], args[1], args[2], args[3]
    citations = []
    if "--citations" in args:
        idx = args.index("--citations")
        if idx + 1 < len(args):
            try:
                citations = json.loads(args[idx + 1])
            except json.JSONDecodeError:
                return f"Invalid citations JSON: {args[idx + 1]}"
    l, c, q, cog = _get_services()
    try:
        c.commit_section(topic, section_id, title, body, source_citations=citations)
        return f"Section '{title}' added to '{topic}'."
    except ValueError as e:
        return f"Error: {e}"


def _create_quiz(args):
    if len(args) < 2:
        return "Usage: create-quiz <topic> <quiz_id> [--title <title>]"
    topic, quiz_id = args[0], args[1]
    title = None
    if "--title" in args:
        idx = args.index("--title")
        if idx + 1 < len(args):
            title = args[idx + 1]
    l, c, q, cog = _get_services()
    try:
        q.create_quiz(topic, quiz_id, title=title)
        return f"Quiz '{quiz_id}' created for '{topic}'."
    except ValueError as e:
        return f"Quiz already exists: {e}"


def _add_quiz_item(args):
    if len(args) < 6:
        return "Usage: add-quiz-item <quiz_id> <item_id> <question> <category> <difficulty> <answer_key_json>"
    quiz_id, item_id, question, category, difficulty, key_json = (
        args[0],
        args[1],
        args[2],
        args[3],
        args[4],
        args[5],
    )
    try:
        key_data = json.loads(key_json)
    except json.JSONDecodeError as e:
        return f"Invalid answer key JSON: {e}"
    answer_key = AnswerKey(
        required_keywords=key_data.get("required_keywords", []),
        forbidden_keywords=key_data.get("forbidden_keywords", []),
        min_length_chars=key_data.get("min_length_chars", 0),
    )
    l, c, q, cog = _get_services()
    try:
        q.add_item(quiz_id, item_id, question, category, difficulty, answer_key)
        return f"Quiz item '{item_id}' added to '{quiz_id}'."
    except ValueError as e:
        return f"Error: {e}"


def _list_topics(args):
    l, c, q, cog = _get_services()
    topics = set(c.list_topics())
    from state_core.event_models import TopicStartedEvent

    for e in l._event_store.read_all():
        if isinstance(e, TopicStartedEvent):
            topics.add(e.topic)
    sorted_topics = sorted(topics)
    if not sorted_topics:
        return "No topics yet. Ask me to create one!"
    return "Available topics:\n" + "\n".join(f"  - {t}" for t in sorted_topics)


def _list_quizzes(args):
    if not args:
        return "Usage: list-quizzes <topic>"
    topic = args[0]
    l, c, q, cog = _get_services()
    quizzes = q.list_quizzes_for_topic(topic)
    if not quizzes:
        return f"No quizzes for '{topic}'."
    result = f"Quizzes for '{topic}':\n"
    for quiz in quizzes:
        result += f"\n  [{quiz.quiz_id}] {quiz.title or 'Untitled'} ({len(quiz.items)} items)"
    return result


def _get_lesson(args):
    if not args:
        return "Usage: get-lesson <topic>"
    topic = args[0]
    l, c, q, cog = _get_services()
    lesson = c.get_lesson(topic)
    if not lesson:
        return f"No lesson found for '{topic}'."
    result = f"# {lesson.title}\n\n"
    for sec in lesson.sections:
        result += f"## {sec.title}\n{sec.body}\n\n"
        if sec.source_citations:
            result += f"*Sources: {', '.join(sec.source_citations)}*\n\n"
    return result


def _get_knowledge_map(args):
    l, c, q, cog = _get_services()
    km = cog.build_knowledge_map()
    result = "# Knowledge Map\n\n"
    result += f"Overall Level: {km.overall_level}\n"
    result += f"Topics Studied: {km.topics_studied_count}\n"
    result += f"Quizzes Taken: {km.total_quizzes_taken}\n"
    result += f"Average Score: {km.average_quiz_score:.0%}\n\n"
    if km.weak_areas:
        result += "Weak Areas:\n" + "\n".join(f"  - {w}" for w in km.weak_areas[:5]) + "\n\n"
    if km.strong_areas:
        result += "Strong Areas:\n" + "\n".join(f"  - {s}" for s in km.strong_areas[:5]) + "\n"
    return result


def _get_profile(args):
    l, c, q, cog = _get_services()
    profile = l.get_learner_profile()
    km = cog.build_knowledge_map()
    from state_core.event_models import TopicStartedEvent

    started_topics = {e.topic for e in l._event_store.read_all() if isinstance(e, TopicStartedEvent)}
    topics = set(profile.topics_studied) | started_topics
    result = "# Learner Profile\n\n"
    result += f"Topics Studied: {len(topics)}\n"
    result += f"Overall Level: {km.overall_level}\n"
    result += f"Pending Deltas: {len(profile.pending_deltas)}\n"
    if profile.approved_traits:
        result += "\nTraits:\n"
        for k, v in profile.approved_traits.items():
            result += f"  {k} = {v}\n"
    if topics:
        result += f"\nTopics: {', '.join(sorted(topics))}\n"
    return result


_COMMANDS = {
    "create-lesson": _create_lesson,
    "add-section": _add_section,
    "create-quiz": _create_quiz,
    "add-quiz-item": _add_quiz_item,
    "start-topic": _start_topic,
    "list-topics": _list_topics,
    "list-quizzes": _list_quizzes,
    "get-lesson": _get_lesson,
    "get-knowledge-map": _get_knowledge_map,
    "get-profile": _get_profile,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return

    command = sys.argv[1]
    args = sys.argv[2:]

    handler = _COMMANDS.get(command)
    if handler is None:
        print(f"Unknown command: {command}")
        print("Available: " + ", ".join(sorted(_COMMANDS.keys())))
        sys.exit(1)

    result = handler(args)
    print(result)


if __name__ == "__main__":
    main()
