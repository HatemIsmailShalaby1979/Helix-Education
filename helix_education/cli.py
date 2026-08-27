"""Interactive CLI -- full cognitive learning system.

Flow: dashboard -> learn (read -> dig deeper -> quiz -> evaluate -> save) ->
profile & journey -> cognitive map -> recommendations (HITL approve) -> history.
"""

from api_layer.routes import Router
from cognitive_agent.agent_client import OllamaAgentClient
from cognitive_engine.cognitive_service import CognitiveService
from content_engine import ContentService
from delivery_engine import FeedbackService
from learning_service import LearningService
from progress_engine import StateMutatorService
from quiz_engine import QuizService
from state_core.event_models import ProfileDeltaProposedEvent
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig
from state_core.llm_evaluation import LLMEvaluationService

from .curriculum import topic_data, topic_names


def _build():
    store = EventStore(StoreConfig(path="helix_events.jsonl"))
    ks = SealedAnswerKeyStore()
    llm_eval = LLMEvaluationService(agent_client=OllamaAgentClient(model_name="lfm2.5:8b"), key_store=ks)
    l = LearningService(store, ks, llm_evaluation=llm_eval)
    c = ContentService(l)
    q = QuizService(l)
    f = FeedbackService(l)
    r = Router(l, f)
    cog = CognitiveService(l)
    mutator = StateMutatorService(store)
    return l, c, q, f, r, cog, mutator


def _p(text: str, default: str | None = None) -> str:
    if default:
        v = input(f"  {text} [{default}]: ").strip()
        return v if v else default
    return input(f"  {text}: ").strip()


# -- DASHBOARD ---------------------------------------------------


def _show_dashboard(l, cog) -> None:
    km = cog.build_knowledge_map()
    print()
    print("=" * 60)
    print(f"  HELIX EDUCATION CENTER -- Model Status: {km.overall_level.upper()}")
    print("=" * 60)
    print(f"  Topics studied:  {km.topics_studied_count}")
    print(f"  Quizzes taken:   {km.total_quizzes_taken}")
    print(f"  Average score:   {km.average_quiz_score:.0%}")
    print(f"  Strong areas:    {len(km.strong_areas)}")
    print(f"  Weak areas:      {len(km.weak_areas)}")
    recs = cog.get_pending_recommendations()
    if recs:
        print(f"  Recommendations: {len(recs)} pending (use 'recommend' to review)")
    print("=" * 60)
    print()


def _show_help() -> None:
    print("""
  COMMANDS:
    learn       Pick a topic -> read sections -> dig deeper -> take quiz
    take_quiz   Standalone quiz: pick topic -> pick quiz -> answer -> show state
    dashboard   Show model status and cognitive overview
    profile     Full learning journey with stats and history
    map         Cognitive knowledge map with understanding levels
    recommend   Review and approve/reject recommendations (HITL)
    history     Session history and progress timeline
    help        Show this help
    quit        Exit
""")


# -- LEARN FLOW --------------------------------------------------


def _do_learn(l, c, q, f, cog) -> None:
    names = topic_names()
    if not names:
        print("\n  No topics available.")
        return

    print(f"\n  Available topics ({len(names)}):")
    for i, name in enumerate(names, 1):
        td = topic_data(name)
        state = l.get_topic_state(name)
        prereqs = td.get("prerequisites", [])
        prereq_ok = all(l.get_topic_state(p).is_passed for p in prereqs)
        status = "PASSED" if state.is_passed else "ready" if prereq_ok else f"needs: {', '.join(prereqs)}"
        print(f"  {i}. {name:20s} [{status}]")

    choice = _p("Pick a topic (number or name)")
    topic = _resolve(choice, names)
    if topic is None:
        print("\n  Topic not found.")
        return

    td = topic_data(topic)
    prereqs = td.get("prerequisites", [])
    for p in prereqs:
        if not l.get_topic_state(p).is_passed:
            print(f"\n  Prerequisite not met: complete '{p}' first.")
            return

    lesson = c.get_lesson(topic)
    if not lesson or not lesson.sections:
        print(f"\n  No lesson content for '{topic}'.")
        return

    session_id = cog.start_session(topic)

    print(f"\n  -- {lesson.title} --")
    for idx, section in enumerate(lesson.sections, 1):
        print(f"\n  [{idx}/{len(lesson.sections)}] {section.title}")
        print("-" * (len(section.title) + 6))
        for line in section.body.split("\n"):
            print(f"  {line}")
        cog.record_section_read(session_id, section.section_id)

        # Dig deeper loop
        while True:
            dd = _p("Dig deeper? (y/n)").lower()
            if dd in ("y", "yes"):
                print("\n  [Deeper dive requested]")
                print("  Ask the AI tutor to generate advanced content for this section.")
                cog.record_dig_deeper(session_id)
            else:
                break

    # Quiz
    quizzes = q.list_quizzes_for_topic(topic)
    if quizzes and quizzes[0].items:
        take = _p("Take the quiz? (y/n)").lower()
        if take in ("y", "yes"):
            _take_quiz(topic, quizzes[0], session_id, q, l, f, cog)

    # Save and track
    print("\n  Session saved. Resources and scores documented in your journey.")
    print("  Cognitive memory updated with your progress.\n")


def _take_quiz(topic, quiz_obj, session_id, q, l, f, cog) -> None:
    print(f"\n  -- QUIZ: {quiz_obj.title} ({len(quiz_obj.items)} questions) --")
    session_qid = q.start_session(quiz_obj.quiz_id)
    correct = 0

    for item in quiz_obj.items:
        print(f"\n  Q: {item.question}")
        answer = input("  Your answer: ").strip()
        try:
            sr = q.answer_item(session_qid, item.quiz_item_id, answer)
            if sr.passed:
                correct += 1
                print(f"  CORRECT! Score: {sr.raw_score:.0%}")
            else:
                print(f"  INCORRECT  Score: {sr.raw_score:.0%}")
                if sr.missing_keywords:
                    print(f"  Missing: {', '.join(sr.missing_keywords)}")
                if sr.matched_keywords:
                    print(f"  Matched: {', '.join(sr.matched_keywords)}")
        except Exception as e:
            print(f"  Error: {e}")

    q.complete_session(session_qid)
    summary = q.get_session_summary(session_qid)
    if summary:
        score = summary["average_score"]
        passed = summary["pass_rate"] >= 0.6
        print("\n  -- RESULT --")
        print(f"  Score: {correct}/{len(quiz_obj.items)} correct ({score:.0%})")
        if passed:
            print("  TOPIC PASSED! Well done.")
        cog.record_quiz_result(session_id, score, passed)
    else:
        cog.record_quiz_result(session_id, 0.0, False)


# -- TAKE QUIZ (standalone) --------------------------------------


def _do_take_quiz(l, q, mutator) -> None:
    """Standalone quiz flow: pick topic -> pick quiz -> answer questions -> show state.

    Implements the complete evaluation path:
    1. Present questions (derived from QuizCreatedEvent or active session)
    2. Capture user input
    3. Pass input to ScoringEngine (via LearningService.submit_and_score_answer)
    4. Trigger StateMutatorService to record results
    5. Display updated UserLearningState to the user

    The flow maintains event log consistency - if the CLI restarts, it will
    reconstruct the mastery state by replaying all events from the log.
    """
    # Validate event log integrity before proceeding
    try:
        # Attempt to read all events to verify the log is readable
        events = l._event_store.read_all()
    except Exception as e:
        print(f"\n  STATE INTEGRITY ERROR: {e}")
        print("  The event log is corrupted or unreadable.")
        print("  Please check the event log file and try again.")
        return

    names = topic_names()
    if not names:
        print("\n  No topics available.")
        return

    print(f"\n  Available topics ({len(names)}):")
    for i, name in enumerate(names, 1):
        td = topic_data(name)
        state = l.get_topic_state(name)
        prereqs = td.get("prerequisites", [])
        prereq_ok = all(l.get_topic_state(p).is_passed for p in prereqs)
        status = "PASSED" if state.is_passed else "ready" if prereq_ok else f"needs: {', '.join(prereqs)}"
        print(f"  {i}. {name:20s} [{status}]")

    choice = _p("Pick a topic (number or name)")
    topic = _resolve(choice, names)
    if topic is None:
        print("\n  Topic not found.")
        return

    quizzes = q.list_quizzes_for_topic(topic)
    if not quizzes:
        print(f"\n  No quizzes available for '{topic}'.")
        return

    print(f"\n  Quizzes for '{topic}':")
    for i, quiz in enumerate(quizzes, 1):
        print(f"  {i}. {quiz.quiz_id} ({len(quiz.items)} questions)")

    quiz_choice = _p("Pick a quiz (number)")
    try:
        quiz_idx = int(quiz_choice) - 1
        if quiz_idx < 0 or quiz_idx >= len(quizzes):
            print("\n  Invalid quiz number.")
            return
    except ValueError:
        print("\n  Invalid input.")
        return

    quiz_obj = quizzes[quiz_idx]
    if not quiz_obj.items:
        print("\n  This quiz has no questions.")
        return

    print(f"\n  -- QUIZ: {quiz_obj.title or quiz_obj.quiz_id} ({len(quiz_obj.items)} questions) --")
    print("  Type 'quit' at any prompt to exit the quiz.\n")

    for item in quiz_obj.items:
        print(f"\n  Q: {item.question}")
        answer = input("  Your answer: ").strip()
        if answer.lower() in ("q", "quit", "exit"):
            print("\n  Quiz aborted.")
            return

        try:
            # Score the answer using the Learning Service (ScoringEngine)
            result = l.submit_and_score_answer(item.quiz_item_id, answer)

            # Process through StateMutatorService to record results
            # This updates the persistent UserLearningState and emits LearningStateUpdatedEvent
            mutator.process_quiz_result(
                quiz_id=quiz_obj.quiz_id,
                quiz_item_id=item.quiz_item_id,
                raw_score=result.raw_score,
                passed=result.passed,
            )

            if result.passed:
                print(f"  CORRECT! Score: {result.raw_score:.0%}")
            else:
                print(f"  INCORRECT  Score: {result.raw_score:.0%}")
                if result.missing_keywords:
                    print(f"  Missing: {', '.join(result.missing_keywords)}")
                if result.matched_keywords:
                    print(f"  Matched: {', '.join(result.matched_keywords)}")

        except Exception as e:
            print(f"  Error scoring answer: {e}")
            continue

    # Display updated learning state to the user
    state = mutator.get_state()
    print("\n  -- UPDATED LEARNING STATE --")
    print(f"  Total questions studied: {state.total_questions_studied}")
    print(f"  Running average score:   {state.running_average_score:.0%}")
    print(f"  Topics mastered:         {', '.join(state.topics_mastered) if state.topics_mastered else 'none'}")
    print(f"  Topics in progress:      {', '.join(state.topics_in_progress) if state.topics_in_progress else 'none'}")
    print()
    print("  Note: Your mastery state is fully event-sourced. If you restart the CLI,")
    print("  it will reconstruct this state by replaying all events from the log.")


# -- PROFILE & JOURNEY -------------------------------------------


def _do_profile(l, r, cog) -> None:
    km = cog.build_knowledge_map()
    profile = r.handle_get_profile()
    journey = cog.get_journey()

    print("\n  -- LEARNING JOURNEY --")
    print(f"  Topics studied:  {len(profile.topics_studied)}")
    print(f"  Overall level:   {km.overall_level}")
    print(f"  Quizzes taken:   {km.total_quizzes_taken}")
    print(f"  Average score:   {km.average_quiz_score:.0%}")
    print(f"  Pending deltas:  {profile.pending_delta_count}")
    print()

    if profile.approved_traits:
        print("  Cognitive traits:")
        for k, v in profile.approved_traits.items():
            print(f"    {k} = {v}")
        print()

    if journey:
        print("  Recent activity (last 10):")
        for entry in journey[-10:]:
            icon = {
                "session_started": "[S]",
                "section_read": "[R]",
                "dig_deeper": "[D]",
                "quiz_completed": "[Q]",
                "recommendation_approved": "[+]",
                "recommendation_rejected": "[-]",
            }.get(entry.entry_type, "[.]")
            print(f"  {icon} [{entry.timestamp[:19]}] {entry.topic:20s} {entry.detail}")
    print()


# -- COGNITIVE MAP -----------------------------------------------


def _do_map(cog) -> None:
    km = cog.build_knowledge_map()
    print("\n  -- COGNITIVE KNOWLEDGE MAP --")
    print(f"  Overall level: {km.overall_level.upper()}")
    print(f"  Topics: {km.topics_studied_count}  Quizzes: {km.total_quizzes_taken}")
    print(f"  Avg score: {km.average_quiz_score:.0%}")
    print()

    for topic, nodes in km.topics.items():
        print(f"  [{topic}]")
        for node in nodes:
            bar = "#" * int(node.understanding_level * 10) + "-" * (10 - int(node.understanding_level * 10))
            print(
                f"    {node.concept:25s} [{bar}] {node.understanding_level:.0%} (encountered: {node.times_encountered})"
            )
    print()

    if km.weak_areas:
        print("  Weak areas (need attention):")
        for w in km.weak_areas[:5]:
            print(f"    !  {w}")
        print()
    if km.strong_areas:
        print("  Strong areas (mastered):")
        for s in km.strong_areas[:5]:
            print(f"    +  {s}")
        print()


# -- RECOMMENDATIONS (HITL) --------------------------------------


def _do_recommendations(l, cog) -> None:
    recs = cog.get_recommendations()
    pending = cog.get_pending_recommendations()
    approved = cog.get_approved_recommendations()

    print("\n  -- RECOMMENDATIONS --")
    print(f"  Pending: {len(pending)}  |  Approved: {len(approved)}")
    print()

    if not pending:
        print("  No pending recommendations. Complete a quiz to generate insights.")
        print()

    for rec in pending:
        print(f"  [{rec.priority.upper()}] {rec.concept} ({rec.topic})")
        print(f"    Reason: {rec.reason}")
        print(f"    Action: {rec.suggested_action}")
        print(f"    Evidence: {rec.evidence}")
        action = _p("  Approve? (y/n/skip)").lower()
        if action in ("y", "yes"):
            if cog.approve_recommendation(rec.recommendation_id):
                print("    Approved! Cognitive memory updated.")
                for e in reversed(l._event_store.read_all()):
                    if isinstance(e, ProfileDeltaProposedEvent):
                        l.approve_profile_delta(e.event_id)
                        break
        elif action in ("n", "no"):
            cog.reject_recommendation(rec.recommendation_id)
            print("    Rejected.")
        print()

    if approved:
        print(f"  Previously approved ({len(approved)}):")
        for rec in approved[-5:]:
            print(f"    ✓ {rec.concept} -- {rec.suggested_action}")
        print()


# -- HISTORY -----------------------------------------------------


def _do_history(cog) -> None:
    journey = cog.get_journey()
    if not journey:
        print("\n  No history yet. Start learning with 'learn'.\n")
        return
    print(f"\n  -- LEARNING HISTORY ({len(journey)} entries) --")
    for entry in journey:
        icon = {
            "session_started": "📖",
            "section_read": "📄",
            "dig_deeper": "🔍",
            "quiz_completed": "📝",
            "recommendation_approved": "✅",
            "recommendation_rejected": "❌",
        }.get(entry.entry_type, "•")
        score_str = f" ({entry.score:.0%})" if entry.score is not None else ""
        print(f"  {icon} [{entry.timestamp[:19]}] {entry.topic:20s} {entry.detail}{score_str}")
    print()


# -- HELPERS -----------------------------------------------------


def _resolve(choice: str, names: list[str]) -> str | None:
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(names):
            return names[idx]
        return None
    for n in names:
        if n.lower() == choice.lower():
            return n
    return None


# -- MAIN --------------------------------------------------------


def main() -> None:
    l, c, q, f, r, cog, mutator = _build()
    _show_dashboard(l, cog)

    while True:
        try:
            cmd = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if cmd in ("q", "quit", "exit"):
            break
        elif cmd in ("h", "help", "?"):
            _show_help()
        elif cmd == "":
            continue
        elif cmd == "dashboard":
            _show_dashboard(l, cog)
        elif cmd == "learn":
            try:
                _do_learn(l, c, q, f, cog)
            except Exception as e:
                print(f"\n  Error: {e}\n")
        elif cmd == "take_quiz":
            try:
                _do_take_quiz(l, q, mutator)
            except Exception as e:
                print(f"\n  Error: {e}\n")
        elif cmd in ("profile", "journey"):
            try:
                _do_profile(l, r, cog)
            except Exception as e:
                print(f"\n  Error: {e}\n")
        elif cmd == "map":
            try:
                _do_map(cog)
            except Exception as e:
                print(f"\n  Error: {e}\n")
        elif cmd in ("recommend", "recommendations", "approve"):
            try:
                _do_recommendations(l, cog)
            except Exception as e:
                print(f"\n  Error: {e}\n")
        elif cmd == "history":
            try:
                _do_history(cog)
            except Exception as e:
                print(f"\n  Error: {e}\n")
        else:
            print(f"  Unknown: '{cmd}'. Type 'help'.\n")


if __name__ == "__main__":
    main()
