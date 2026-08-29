"""
ROLE: You are a senior Python engineer writing a SINGLE standalone script,
not a new architectural module. This composes ONLY existing, already-tested
services. Do not modify any existing file. If anything is unclear, stop and
ask rather than improvising new logic into an existing service.

PROJECT: Helix Education Center â€” Learning Engine (existing, not new)
New location: scripts/run_first_real_lesson.py (create a scripts/
directory if one doesn't exist)
"""

import os
try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc

from cognitive_agent.agent_client import OllamaAgentClient
from cognitive_agent.agent_service import CognitiveAgentService
from content_engine.content_service import ContentService, ContentStoreConfig
from content_engine.generation_orchestrator import GenerationOrchestrator
from grounding_engine.grounding_client import StubGroundingClient
from grounding_engine.grounding_models import GroundingResult, SourceChunk
from grounding_engine.grounding_service import GroundingService
from learning_service import LearningService
from state_core.event_models import LessonSectionCommittedEvent
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig

# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ
# TOP-OF-FILE CONFIGURATION
# â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ

TOPIC = "Python modules"
LEVEL = "beginner"
SECTION_ID = "sec-001-what-is-a-module"
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

for excerpt in CURATED_EXCERPTS:
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


SOURCE_CHUNKS = build_source_chunks(CURATED_EXCERPTS)

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
    # 1. EventStore pointed at a REAL, PERSISTENT path: ./data/events.jsonl
    os.makedirs("data", exist_ok=True)
    event_store = EventStore(StoreConfig(path="./data/events.jsonl"))

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

    # 9. GenerationOrchestrator composing all of the above
    orchestrator = GenerationOrchestrator(
        grounding_service=grounding_service,
        agent_service=agent_service,
        content_service=content_service,
    )

    # 10. Call orchestrator.generate_and_commit_section
    print(f"\n{'=' * 60}")
    print(f"Generating lesson section for topic: {TOPIC}")
    print(f"Level: {LEVEL}")
    print(f"Section ID: {SECTION_ID}")
    print(f"{'=' * 60}\n")

    section = orchestrator.generate_and_commit_section(
        topic=TOPIC,
        level=LEVEL,
        section_id=SECTION_ID,
        max_chunks=len(CURATED_EXCERPTS),
    )

    # 11. Print, in order, clearly labeled:

    # - The grounding chunks fetched
    print(f"\n{'=' * 60}")
    print("GROUNDING CHUNKS FETCHED")
    print(f"{'=' * 60}")
    grounding_result = grounding_service.get_grounding(TOPIC, max_chunks=len(CURATED_EXCERPTS))
    for i, chunk in enumerate(grounding_result.chunks):
        print(f"\n--- Chunk {i} ---")
        print(f"Source: {chunk.source_title}")
        print(f"URL: {chunk.source_url}")
        print(f"Content: {chunk.content[:200]}...")
        print(f"Citation: {chunk.citation_text}")

    # - The raw section_title and body produced
    print(f"\n{'=' * 60}")
    print("RAW SECTION OUTPUT")
    print(f"{'=' * 60}")
    print(f"Title: {section.title}")
    print(f"Body:\n{section.body}")

    # - The citations attached to the committed section
    print(f"\n{'=' * 60}")
    print("CITATIONS ATTACHED TO SECTION")
    print(f"{'=' * 60}")
    for i, citation in enumerate(section.source_citations):
        print(f"  [{i}] {citation}")

    # - The final committed Section object's key fields
    print(f"\n{'=' * 60}")
    print("COMMITTED SECTION OBJECT (KEY FIELDS)")
    print(f"{'=' * 60}")
    print(f"  section_id: {section.section_id}")
    print(f"  title: {section.title}")
    print(f"  body_length: {len(section.body)} chars")
    print(f"  source_citations_count: {len(section.source_citations)}")
    print(f"  source_citations: {section.source_citations}")

    # - Confirmation the event was written (read back via event_store.read_all()
    #   and print the count of LessonSectionCommittedEvent found)
    print(f"\n{'=' * 60}")
    print("EVENT STORE VERIFICATION")
    print(f"{'=' * 60}")
    all_events = event_store.read_all()
    committed_events = [e for e in all_events if isinstance(e, LessonSectionCommittedEvent)]
    print(f"Total events in store: {len(all_events)}")
    print(f"LessonSectionCommittedEvent count: {len(committed_events)}")
    for event in committed_events:
        print(f"  - {event.section_id} for topic '{event.topic}' at {event.timestamp}")

    print(f"\n{'=' * 60}")
    print("SUCCESS: First real lesson section generated and committed!")
    print(f"{'=' * 60}\n")
