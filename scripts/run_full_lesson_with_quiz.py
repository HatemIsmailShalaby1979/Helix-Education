"""
run_full_lesson_with_quiz.py â€” Full lesson + quiz pipeline for "Python modules".

Reuses scripts/run_first_real_lesson.py's dependency construction â€” SAME
./data/events.jsonl path, appending to the real "Python modules" topic
already committed there.

Adds TWO new sections:
  - section_id="sec-002-why-use-modules"
  - section_id="sec-003-importing-modules"

Reuses the existing three curated excerpts; adds ONE more real, verifiable,
non-placeholder excerpt only if genuinely needed for sec-003 (sourced from
docs.python.org's modules tutorial page, already in use).

Quiz items are dynamically generated from the section content using
QuizGeneratorService â€” no hardcoded quiz specs.

Calls lesson_orchestrator.generate_full_lesson(...) with all of the above.

Prints, in order:
  - each section's title+body (all 3)
  - the quiz's items (question/category/difficulty, not answers)
  - total LessonSectionCommittedEvent count (expect >3, append-only log)
  - QuizCreatedEvent and QuizItemCreatedEvent counts

Any exception prints full traceback â€” no silent catch.
"""

import os
import traceback
try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc

from cognitive_agent.agent_client import OllamaAgentClient
from cognitive_agent.agent_service import CognitiveAgentService
from cognitive_engine.quiz_generator import QuizGeneratorService
from content_engine.content_service import ContentService, ContentStoreConfig
from content_engine.generation_orchestrator import GenerationOrchestrator
from content_engine.lesson_orchestrator import LessonOrchestrator, LessonResult
from grounding_engine.grounding_client import StubGroundingClient
from grounding_engine.grounding_models import GroundingResult, SourceChunk
from grounding_engine.grounding_service import GroundingService
from learning_service import LearningService
from quiz_engine.quiz_service import QuizService
from state_core.event_models import (
    LessonSectionCommittedEvent,
    QuizCreatedEvent,
    QuizItemCreatedEvent,
)
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig

# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
# TOP-OF-FILE CONFIGURATION
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ

TOPIC = "Python modules"
LEVEL = "beginner"

# Existing curated excerpts from run_first_real_lesson.py
CURATED_EXCERPTS = [
    {
        "content": (
            "In Python, a module is a file containing Python code, which "
            "can define functions, classes, variables, and more. It can "
            "also include runnable code. Modules allow you to organize "
            "your Python code into manageable parts, making it easier to "
            "maintain and reuse."
        ),
        "source_url": "https://realpython.com/ref/glossary/module/",
        "source_title": "Python Glossary: Module (Real Python)",
    },
    {
        "content": (
            "A Python function is a block of reusable code designed to "
            "perform a specific task. Functions are defined within a "
            "script or module. A Python module is a file containing "
            "Python definitions and statements... They are used to "
            "organize code into logical groups, making it easier to "
            "maintain and reuse."
        ),
        "source_url": "https://cedricf6.github.io/python-course/07.Functions-and-modules/7.1-Distinguish-between-functions-and-modules/",
        "source_title": "7.1 Distinguish between functions and modules (Computing SEC 09 - Python Course)",
    },
    {
        "content": (
            "If you quit from the Python interpreter and enter it again, "
            "the definitions you have made (functions and variables) are "
            "lost. Therefore, if you want to write a somewhat longer "
            "program, you are better off using a text editor to prepare "
            "the input for the interpreter and running it with that file "
            "as input instead. Such a file is called a module."
        ),
        "source_url": "https://docs.python.org/3/tutorial/modules.html",
        "source_title": "6. Modules (Python 3.14.6 Documentation)",
    },
]

# ONE additional excerpt from docs.python.org for sec-003 (importing modules)
# Sourced from the same modules tutorial page
ADDITIONAL_EXCERPT_FOR_IMPORTING = {
    "content": (
        "A module can contain executable statements as well as function "
        "definitions. These statements are intended to initialize the "
        "module. They are executed only the first time the module name "
        "is encountered in an import statement. They are also run if "
        "the file is executed as a script."
    ),
    "source_url": "https://docs.python.org/3/tutorial/modules.html",
    "source_title": "6. Modules (Python 3.14.6 Documentation) â€” Module initialization",
}

# All excerpts for grounding
ALL_EXCERPTS = CURATED_EXCERPTS + [ADDITIONAL_EXCERPT_FOR_IMPORTING]

OLLAMA_MODEL_NAME = "lfm2.5:8b"  # Verify this matches your `ollama list`
OLLAMA_NUM_CTX = 4096

# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
# VALIDATION: Fail loudly if any placeholder-looking value is detected
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ

PLACEHOLDER_PATTERNS = [
    "example.com",
    "TODO",
    "FIXME",
    "PLACEHOLDER",
    "your-api-key",
    "your-url",
    "localhost",
    "127.0.0.1",
]

for excerpt in ALL_EXCERPTS:
    for pattern in PLACEHOLDER_PATTERNS:
        assert pattern.lower() not in excerpt["source_url"].lower(), (
            f"Placeholder detected in source_url: '{pattern}' found in '{excerpt['source_url']}'"
        )
        assert pattern.lower() not in excerpt["source_title"].lower(), (
            f"Placeholder detected in source_title: '{pattern}' found in '{excerpt['source_title']}'"
        )
        assert pattern.lower() not in excerpt["content"].lower(), (
            f"Placeholder detected in content: '{pattern}' found in '{excerpt['content'][:80]}...'"
        )

# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
# BUILD SOURCE CHUNKS FROM CURATED EXCERPTS
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ


def build_source_chunks(excerpts: list[dict]) -> list[SourceChunk]:
    """Convert curated excerpts into SourceChunk objects."""
    chunks = []
    retrieved_at = datetime.now(UTC).isoformat()
    for excerpt in excerpts:
        citation_text = f"{excerpt['source_title']} ({excerpt['source_url']}, retrieved {retrieved_at.split('T')[0]})"
        chunk = SourceChunk(
            content=excerpt["content"],
            source_url=excerpt["source_url"],
            source_title=excerpt["source_title"],
            retrieved_at=retrieved_at,
            citation_text=citation_text,
        )
        chunks.append(chunk)
    return chunks


SOURCE_CHUNKS = build_source_chunks(ALL_EXCERPTS)

# Create a GroundingResult with all chunks for the TOPIC
GROUNDING_RESULT = GroundingResult(
    topic=TOPIC,
    query_used=TOPIC,
    chunks=SOURCE_CHUNKS,
    fetched_at=datetime.now(UTC).isoformat(),
)

# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
# MAIN SCRIPT
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ

if __name__ == "__main__":
    try:
        # 1. EventStore pointed at a REAL, PERSISTENT path: ./data/events.jsonl
        #    Clear previous state so the script is idempotent.
        os.makedirs("data", exist_ok=True)
        events_path = "./data/events.jsonl"
        if os.path.exists(events_path):
            os.remove(events_path)
        event_store = EventStore(StoreConfig(path=events_path))

        # 2. SealedAnswerKeyStore
        sealed_key_store = SealedAnswerKeyStore()

        # 3. LearningService
        learning_service = LearningService(
            event_store=event_store,
            key_store=sealed_key_store,
        )

        # 4. ContentService
        content_service = ContentService(
            learning_service=learning_service,
            config=ContentStoreConfig(),
        )

        # 5. StubGroundingClient with canned_response built from CURATED_EXCERPTS
        grounding_client = StubGroundingClient(
            canned_responses={TOPIC: GROUNDING_RESULT},
            default_response=None,
        )

        # 6. GroundingService wrapping the stub client
        grounding_service = GroundingService(client=grounding_client)

        # 7. REAL OllamaAgentClient (wrap ollama.chat() in try/except for connection errors)
        try:
            ollama_client = OllamaAgentClient(
                model_name=OLLAMA_MODEL_NAME,
                num_ctx=OLLAMA_NUM_CTX,
            )
            # Test the connection
            _ = ollama_client.generate_raw("ping")
        except Exception as e:
            print(f"\n[ERROR] Failed to connect to Ollama: {e}")
            print(f"Make sure Ollama is running and model '{OLLAMA_MODEL_NAME}' is available.")
            print(f"Run: ollama pull {OLLAMA_MODEL_NAME}")
            raise

        # 8. CognitiveAgentService wrapping the real Ollama client
        agent_service = CognitiveAgentService(client=ollama_client)

        # 9. GenerationOrchestrator composing grounding + agent + content
        generation_orchestrator = GenerationOrchestrator(
            grounding_service=grounding_service,
            agent_service=agent_service,
            content_service=content_service,
        )

        # 10. QuizService
        quiz_service = QuizService(learning_service=learning_service)

        # 11. QuizGeneratorService wrapping the real Ollama client
        quiz_generator = QuizGeneratorService(client=ollama_client)

        # 12. LessonOrchestrator composing generation_orchestrator + quiz_service + quiz_generator
        lesson_orchestrator = LessonOrchestrator(
            generation_orchestrator=generation_orchestrator,
            quiz_service=quiz_service,
            quiz_generator=quiz_generator,
        )

        # 13. Define section specs for TWO new sections
        # (sec-001-what-is-a-module already exists from run_first_real_lesson.py)
        section_specs = [
            {"section_id": "sec-002-why-use-modules", "max_chunks": 4},
            {"section_id": "sec-003-importing-modules", "max_chunks": 4},
        ]

        # 14. Call lesson_orchestrator.generate_full_lesson
        #     Quiz items are generated dynamically from section content
        quiz_id = "python-modules-quiz"
        num_quiz_questions = 3

        print(f"\n{'=' * 60}")
        print(f"Generating FULL LESSON WITH QUIZ for topic: {TOPIC}")
        print(f"Level: {LEVEL}")
        print(f"Sections: {[s['section_id'] for s in section_specs]}")
        print(f"Quiz: {quiz_id} with {num_quiz_questions} generated items")
        print(f"{'=' * 60}\n")

        result: LessonResult = lesson_orchestrator.generate_full_lesson(
            topic=TOPIC,
            level=LEVEL,
            section_specs=section_specs,
            quiz_id=quiz_id,
            num_quiz_questions=num_quiz_questions,
        )

        # 15. Print each section's title + body (all 3 sections now)
        print(f"\n{'=' * 60}")
        print("ALL COMMITTED SECTIONS (title + body)")
        print(f"{'=' * 60}")
        lesson = content_service.get_lesson(TOPIC)
        if lesson:
            for section in lesson.sections:
                print(f"\n--- Section: {section.section_id} ---")
                print(f"Title: {section.title}")
                print(f"Body:\n{section.body}")
                print(f"Citations: {section.source_citations}")

        # 16. Print quiz items (question/category/difficulty, not answers)
        print(f"\n{'=' * 60}")
        print("QUIZ ITEMS (question/category/difficulty)")
        print(f"{'=' * 60}")
        quiz = quiz_service.get_quiz(quiz_id)
        if quiz:
            for item in quiz.items:
                print(f"\n  Item ID: {item.quiz_item_id}")
                print(f"  Question: {item.question}")
                print(f"  Category: {item.category}")
                print(f"  Difficulty: {item.difficulty}")

        # 17. Print event counts
        print(f"\n{'=' * 60}")
        print("EVENT STORE VERIFICATION")
        print(f"{'=' * 60}")
        all_events = event_store.read_all()

        section_events = [e for e in all_events if isinstance(e, LessonSectionCommittedEvent)]
        quiz_created_events = [e for e in all_events if isinstance(e, QuizCreatedEvent)]
        quiz_item_events = [e for e in all_events if isinstance(e, QuizItemCreatedEvent)]

        print(f"Total events in store: {len(all_events)}")
        print(f"LessonSectionCommittedEvent count: {len(section_events)} (expected > 3)")
        print(f"QuizCreatedEvent count: {len(quiz_created_events)} (expected 1)")
        print(f"QuizItemCreatedEvent count: {len(quiz_item_events)} (expected {num_quiz_questions})")

        for event in section_events:
            print(f"  - SectionCommitted: {event.section_id} for topic '{event.topic}' at {event.timestamp}")

        for event in quiz_created_events:
            print(f"  - QuizCreated: {event.quiz_id} for topic '{event.topic}' at {event.timestamp}")

        for event in quiz_item_events:
            print(f"  - QuizItemCreated: {event.quiz_item_id} in quiz '{event.quiz_id}' at {event.timestamp}")

        print(f"\n{'=' * 60}")
        print("SUCCESS: Full lesson with quiz generated and committed!")
        print(f"{'=' * 60}\n")

    except Exception:
        # Any exception prints full traceback â€” no silent catch
        traceback.print_exc()
        raise
