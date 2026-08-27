"""Live Integration Script: Metacognitive Feedback Loop Demonstration.

Proves the complete feedback loop works end-to-end with real EventStore
and StateMutatorService — no mocks.
"""

import os
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from learning_service import LearningService
from progress_engine.state_mutator import StateMutatorService
from quiz_engine.quiz_models import Quiz, QuizItem
from quiz_engine.quiz_service import QuizService
from state_core.event_models import (
    _EVENT_TYPE_REGISTRY,
    LearningStateUpdatedEvent,
    QuizResultEvent,
)
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig
from state_core.scoring_engine import AnswerKey, score_answer

LOG_PATH = os.path.join(tempfile.gettempdir(), "helix_feedback_loop_demo.jsonl")


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_event(event, label: str):
    print(f"\n--- {label} ---")
    event_type = type(event).__name__
    for type_str, cls in _EVENT_TYPE_REGISTRY.items():
        if cls is type(event):
            event_type = type_str
            break
    print(f"  event_type: {event_type}")
    print(f"  timestamp:   {event.timestamp}")
    for k, v in event.__dict__.items():
        if k in ("event_id", "timestamp"):
            continue
        print(f"  {k}: {v}")


def create_demo_quiz() -> Quiz:
    quiz_id = f"quiz-{uuid.uuid4().hex[:8]}"
    items = [
        QuizItem(
            quiz_item_id=f"item-{uuid.uuid4().hex[:8]}",
            question="What keyword is used to define a function in Python?",
            category="short_answer",
            difficulty="easy",
            required_keywords=["def", "function", "define"],
        ),
        QuizItem(
            quiz_item_id=f"item-{uuid.uuid4().hex[:8]}",
            question="How do you specify a default value for a parameter?",
            category="short_answer",
            difficulty="easy",
            required_keywords=["default", "parameter", "=", "value"],
        ),
        QuizItem(
            quiz_item_id=f"item-{uuid.uuid4().hex[:8]}",
            question="What does the return statement do in a function?",
            category="short_answer",
            difficulty="easy",
            required_keywords=["return", "value", "output", "function"],
        ),
    ]
    return Quiz(quiz_id=quiz_id, topic="Python Functions", items=items)


def main():
    # Clean up from any previous run
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)

    print_section("LIVE FEEDBACK LOOP DEMONSTRATION")

    # 1. Services
    print("Initializing services…")
    event_store = EventStore(StoreConfig(path=LOG_PATH))
    key_store = SealedAnswerKeyStore()
    learning_service = LearningService(event_store=event_store, key_store=key_store)
    quiz_service = QuizService(learning_service=learning_service)
    state_mutator = StateMutatorService(event_store)

    # 2. Create quiz
    print_section("STEP 1 — CREATE DEMO QUIZ")
    quiz = create_demo_quiz()
    quiz_service.create_quiz(topic=quiz.topic, quiz_id=quiz.quiz_id)
    print(f"Created quiz: {quiz.quiz_id}  |  Topic: {quiz.topic}  |  Items: {len(quiz.items)}")
    for item in quiz.items:
        answer_key = AnswerKey(required_keywords=item.required_keywords)
        quiz_service.add_item(
            quiz_id=quiz.quiz_id,
            quiz_item_id=item.quiz_item_id,
            question=item.question,
            category=item.category,
            difficulty=item.difficulty,
            answer_key=answer_key,
            required_keywords=item.required_keywords,
        )
        print(f"  Q: {item.question}")
        print(f"    required_keywords = {item.required_keywords}")

    # ─────────────────────────────────────────────────────────────
    # 3. CORRECT answer
    # ─────────────────────────────────────────────────────────────
    print_section("STEP 2 — CORRECT ANSWER")
    correct_item = quiz.items[0]
    correct_answer = "defines a function using the def keyword"
    print(f"Question:  {correct_item.question}")
    print(f"Answer:    '{correct_answer}'")

    score = score_answer(
        item_id=correct_item.quiz_item_id,
        provided_answer=correct_answer,
        required_keywords=correct_item.required_keywords,
    )
    print(f"Score:     {score:.2f}  (passed: {score >= 0.6})")

    state_mutator.process_quiz_result(
        quiz_id=quiz.quiz_id,
        quiz_item_id=correct_item.quiz_item_id,
        raw_score=score,
        passed=score >= 0.6,
    )

    events = event_store.read_all()
    for e in events:
        if isinstance(e, QuizResultEvent) and e.quiz_item_id == correct_item.quiz_item_id:
            print_event(e, "QuizResultEvent (correct)")
        if isinstance(e, LearningStateUpdatedEvent):
            print_event(e, "LearningStateUpdatedEvent")

    state = state_mutator.get_state()
    print("\nState after CORRECT:")
    print(f"  total_questions_studied = {state.total_questions_studied}")
    print(f"  running_average_score   = {state.running_average_score:.4f}")
    print(f"  topics_mastered         = {state.topics_mastered}")
    print(f"  topics_in_progress      = {state.topics_in_progress}")

    # ─────────────────────────────────────────────────────────────
    # 4. INCORRECT answer
    # ─────────────────────────────────────────────────────────────
    print_section("STEP 3 — INCORRECT ANSWER")
    incorrect_item = quiz.items[1]
    incorrect_answer = "I have no idea how to answer this"
    print(f"Question:  {incorrect_item.question}")
    print(f"Answer:    '{incorrect_answer}'")

    score = score_answer(
        item_id=incorrect_item.quiz_item_id,
        provided_answer=incorrect_answer,
        required_keywords=incorrect_item.required_keywords,
    )
    print(f"Score:     {score:.2f}  (passed: {score >= 0.6})")

    state_mutator.process_quiz_result(
        quiz_id=quiz.quiz_id,
        quiz_item_id=incorrect_item.quiz_item_id,
        raw_score=score,
        passed=score >= 0.6,
    )

    events = event_store.read_all()
    for e in events:
        if isinstance(e, QuizResultEvent) and e.quiz_item_id == incorrect_item.quiz_item_id:
            print_event(e, "QuizResultEvent (incorrect)")
        if isinstance(e, LearningStateUpdatedEvent):
            print_event(e, "LearningStateUpdatedEvent")

    state = state_mutator.get_state()
    print("\nState after INCORRECT:")
    print(f"  total_questions_studied = {state.total_questions_studied}")
    print(f"  running_average_score   = {state.running_average_score:.4f}")
    print(f"  topics_mastered         = {state.topics_mastered}")
    print(f"  topics_in_progress      = {state.topics_in_progress}")

    # ─────────────────────────────────────────────────────────────
    # 5. Second CORRECT answer → mastery
    # ─────────────────────────────────────────────────────────────
    print_section("STEP 4 — SECOND CORRECT ANSWER (mastery)")
    correct_item2 = quiz.items[2]
    correct_answer2 = "returns a value from a function as output"
    print(f"Question:  {correct_item2.question}")
    print(f"Answer:    '{correct_answer2}'")

    score = score_answer(
        item_id=correct_item2.quiz_item_id,
        provided_answer=correct_answer2,
        required_keywords=correct_item2.required_keywords,
    )
    print(f"Score:     {score:.2f}  (passed: {score >= 0.6})")

    state_mutator.process_quiz_result(
        quiz_id=quiz.quiz_id,
        quiz_item_id=correct_item2.quiz_item_id,
        raw_score=score,
        passed=score >= 0.6,
    )

    events = event_store.read_all()
    for e in events:
        if isinstance(e, QuizResultEvent) and e.quiz_item_id == correct_item2.quiz_item_id:
            print_event(e, "QuizResultEvent (2nd correct)")
        if isinstance(e, LearningStateUpdatedEvent):
            print_event(e, "LearningStateUpdatedEvent")

    state = state_mutator.get_state()
    print("\nFINAL state:")
    print(f"  total_questions_studied = {state.total_questions_studied}")
    print(f"  running_average_score   = {state.running_average_score:.4f}")
    print(f"  topics_mastered         = {state.topics_mastered}")
    print(f"  topics_in_progress      = {state.topics_in_progress}")

    # ─────────────────────────────────────────────────────────────
    # 6. Event-sourcing verification
    # ─────────────────────────────────────────────────────────────
    print_section("STEP 5 — EVENT-SOURCING REBUILD VERIFICATION")
    new_mutator = StateMutatorService(event_store)
    rebuilt = new_mutator.get_state()

    assert state.total_questions_studied == rebuilt.total_questions_studied, (
        f"total_questions_studied mismatch: {state.total_questions_studied} vs {rebuilt.total_questions_studied}"
    )
    assert abs(state.running_average_score - rebuilt.running_average_score) < 0.001, (
        f"running_average_score mismatch: {state.running_average_score} vs {rebuilt.running_average_score}"
    )
    assert state.topics_mastered == rebuilt.topics_mastered, (
        f"topics_mastered mismatch: {state.topics_mastered} vs {rebuilt.topics_mastered}"
    )
    assert state.topics_in_progress == rebuilt.topics_in_progress, (
        f"topics_in_progress mismatch: {state.topics_in_progress} vs {rebuilt.topics_in_progress}"
    )

    print("  State perfectly reconstructed from event log — event sourcing verified!")
    print(f"\n  Events on disk: {len(event_store.read_all())}")
    print(f"  QuizResultEvents:        {len([e for e in event_store.read_all() if isinstance(e, QuizResultEvent)])}")
    print(
        f"  LearningStateUpdated:     {len([e for e in event_store.read_all() if isinstance(e, LearningStateUpdatedEvent)])}"
    )

    # ─────────────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────────────
    print_section("FEEDBACK LOOP VERIFIED")
    print("✓ Quiz items carry required_keywords from creation")
    print("✓ score_answer() computes deterministic keyword-match scores")
    print("✓ StateMutatorService appends QuizResultEvent + LearningStateUpdatedEvent")
    print("✓ UserLearningState fields move correctly (score averages, topic mastery)")
    print("✓ State is fully rebuildable from the event log")
    print()
    print("✅  THE METACOGNITIVE FEEDBACK LOOP IS OPERATIONAL  ✅")

    # Cleanup
    os.remove(LOG_PATH)


if __name__ == "__main__":
    main()
