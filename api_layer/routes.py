"""Route handlers for the Education Center API.

Pure handler functions that translate HTTP request models into
service calls and return response models. No HTTP framework coupling —
testable without a running server.
"""

from fastapi import Response

from cognitive_engine.cognitive_service import CognitiveService
from content_engine import ContentService
from delivery_engine import FeedbackService
from learning_service import LearningService
from observability.metrics import metrics
from quiz_engine import QuizService
from state_core.scoring_engine import AnswerKey

from .api_models import (
    AnswerFeedbackResponse,
    CreateQuizItemRequest,
    LearnerProfileResponse,
    StartTopicRequest,
    SubmitAnswerRequest,
    TopicStateResponse,
)


class Router:
    """Collection of route handlers for the Education Center API.

    Each method maps to an HTTP endpoint. Handlers are pure
    transformations between request/response models and service calls.

    Inputs:
        learning_service: A LearningService instance.
        feedback_service: A FeedbackService instance.
        content_service: Optional ContentService for lesson management.
        quiz_service: Optional QuizService for quiz management.
        cognitive_service: Optional CognitiveService for knowledge map.
    """

    def __init__(
        self,
        learning_service: LearningService,
        feedback_service: FeedbackService,
        content_service: ContentService | None = None,
        quiz_service: QuizService | None = None,
        cognitive_service: CognitiveService | None = None,
    ) -> None:
        self._learning = learning_service
        self._feedback = feedback_service
        self._content = content_service
        self._quiz = quiz_service

    def get_metrics(self) -> Response:
        """Expose metrics in Prometheus text format."""
        summary = metrics.get_metrics_summary()
        output = []

        for name, value in summary["counters"].items():
            safe_name = name.replace(" ", "_").lower()
            output.append(f"# HELP {safe_name} Total count of {name}")
            output.append(f"# TYPE {safe_name} counter")
            output.append(f"{safe_name} {value}")

        for name, value in summary["gauges"].items():
            safe_name = name.replace(" ", "_").lower()
            output.append(f"# HELP {safe_name} Current value of {name}")
            output.append(f"# TYPE {safe_name} gauge")
            output.append(f"{safe_name} {value}")

        for name, stats in summary["histograms"].items():
            safe_name = name.replace(" ", "_").lower()
            output.append(f"# HELP {safe_name}_count Total observations for {name}")
            output.append(f"# TYPE {safe_name}_count counter")
            output.append(f"{safe_name}_count {stats['count']}")

        return Response(content="\n".join(output), media_type="text/plain")
        self._cog = cognitive_service

    # ── Topic Lifecycle ───────────────────────────────────────────

    def handle_start_topic(self, req: StartTopicRequest) -> TopicStateResponse:
        """POST /topics — Start a new topic."""
        state = self._learning.start_topic(
            topic=req.topic,
            requested_level=req.requested_level,
            parent_topic=req.parent_topic,
        )
        return TopicStateResponse(
            topic=state.topic,
            current_level=state.current_level,
            attempts_total=state.attempts_total,
            pass_count=state.pass_count,
            fail_count=state.fail_count,
            is_passed=state.is_passed,
            branch_children=list(state.branch_children),
            last_activity_timestamp=state.last_activity_timestamp,
        )

    def handle_get_topic(self, topic: str) -> TopicStateResponse | None:
        """GET /topics/{topic} — Get topic state."""
        state = self._learning.get_topic_state(topic)
        if state is None:
            return None
        return TopicStateResponse(
            topic=state.topic,
            current_level=state.current_level,
            attempts_total=state.attempts_total,
            pass_count=state.pass_count,
            fail_count=state.fail_count,
            is_passed=state.is_passed,
            branch_children=list(state.branch_children),
            last_activity_timestamp=state.last_activity_timestamp,
        )

    def handle_get_profile(self) -> LearnerProfileResponse:
        """GET /profile — Get learner profile."""
        profile = self._learning.get_learner_profile()
        return LearnerProfileResponse(
            approved_traits=dict(profile.approved_traits),
            pending_delta_count=len(profile.pending_deltas),
            topics_studied=list(profile.topics_studied),
        )

    def handle_submit_answer(
        self,
        req: SubmitAnswerRequest,
    ) -> AnswerFeedbackResponse:
        """POST /answers — Submit and score an answer."""
        result = self._learning.submit_and_score_answer(
            quiz_item_id=req.quiz_item_id,
            raw_answer=req.raw_answer,
        )
        feedback = self._feedback.score_feedback(result)
        return AnswerFeedbackResponse(
            raw_score=result.raw_score,
            passed=result.passed,
            missing_keywords=list(result.missing_keywords),
            matched_keywords=list(result.matched_keywords),
            message=f"{feedback.title}: {feedback.body}",
        )

    # ── Lesson Lifecycle ──────────────────────────────────────────

    def handle_create_lesson(self, topic: str, title: str) -> dict:
        """POST /lessons — Create a new lesson for a topic."""
        if self._content is None:
            return {"status": "error", "message": "ContentService not configured"}
        self._content.create_lesson(topic, title)
        return {"topic": topic, "title": title, "status": "created"}

    def handle_commit_section(
        self,
        topic: str,
        section_id: str,
        title: str,
        body: str,
        source_citations: list[str] | None = None,
    ) -> dict:
        """POST /sections — Add a section to a lesson."""
        if self._content is None:
            return {"status": "error", "message": "ContentService not configured"}
        self._content.commit_section(
            topic,
            section_id,
            title,
            body,
            source_citations=source_citations or [],
        )
        return {"topic": topic, "section_id": section_id, "status": "created"}

    def handle_get_lesson(self, topic: str) -> dict | None:
        """GET /lessons/{topic} — Get lesson content."""
        if self._content is None:
            return None
        lesson = self._content.get_lesson(topic)
        if lesson is None:
            return None
        return {
            "topic": lesson.topic,
            "title": lesson.title,
            "sections": [
                {
                    "section_id": s.section_id,
                    "title": s.title,
                    "body": s.body,
                    "source_citations": list(s.source_citations),
                }
                for s in lesson.sections
            ],
        }

    def handle_list_topics(self) -> list[str]:
        """GET /topics — List all topics with lessons."""
        if self._content is None:
            return []
        return self._content.list_topics()

    # ── Quiz Lifecycle ────────────────────────────────────────────

    def handle_create_quiz(self, topic: str, quiz_id: str, title: str | None = None) -> dict:
        """POST /quizzes — Create a quiz for a topic."""
        if self._quiz is None:
            return {"status": "error", "message": "QuizService not configured"}
        self._quiz.create_quiz(topic, quiz_id, title=title)
        return {"topic": topic, "quiz_id": quiz_id, "status": "created"}

    def handle_list_quizzes(self, topic: str) -> list[dict]:
        """GET /quizzes/{topic} — List quizzes for a topic."""
        if self._quiz is None:
            return []
        quizzes = self._quiz.list_quizzes_for_topic(topic)
        return [
            {
                "quiz_id": q.quiz_id,
                "topic": q.topic,
                "title": q.title,
                "item_count": len(q.items),
            }
            for q in quizzes
        ]

    def handle_start_quiz_session(self, quiz_id: str) -> dict | None:
        """POST /quiz-sessions — Start a quiz session."""
        if self._quiz is None:
            return None
        try:
            session_id = self._quiz.start_session(quiz_id)
            return {"session_id": session_id, "quiz_id": quiz_id, "status": "started"}
        except ValueError:
            return None

    def handle_answer_quiz_item(
        self,
        session_id: str,
        quiz_item_id: str,
        raw_answer: str,
    ) -> dict | None:
        """POST /quiz-answers — Submit an answer within a session."""
        if self._quiz is None:
            return None
        try:
            result = self._quiz.answer_item(session_id, quiz_item_id, raw_answer)
            return {
                "quiz_item_id": result.quiz_item_id,
                "question": result.question,
                "attempt_number": result.attempt_number,
                "raw_score": result.raw_score,
                "passed": result.passed,
            }
        except ValueError:
            return None

    # ── Quiz Items ────────────────────────────────────────────────

    def handle_create_quiz_item(
        self,
        req: CreateQuizItemRequest,
    ) -> dict:
        """POST /quiz-items — Create a quiz item."""
        key = AnswerKey(
            required_keywords=req.required_keywords,
            forbidden_keywords=req.forbidden_keywords,
            min_length_chars=req.min_length_chars,
        )
        self._learning.create_quiz_item(
            topic=req.topic,
            quiz_id=f"{req.topic}-quiz",
            quiz_item_id=req.quiz_item_id,
            question=req.question,
            category=req.category,
            difficulty=req.difficulty,
            answer_key=key,
        )
        return {"quiz_item_id": req.quiz_item_id, "status": "created"}

    # ── Profile ───────────────────────────────────────────────────

    def handle_approve_delta(self, delta_event_id: str) -> dict:
        """POST /deltas/{id}/approve — Approve a profile delta."""
        self._learning.approve_profile_delta(delta_event_id=delta_event_id)
        return {"delta_event_id": delta_event_id, "status": "approved"}

    # ── Cognitive Map ─────────────────────────────────────────────

    def handle_get_knowledge_map(self) -> dict | None:
        """GET /knowledge-map — Get the learner's knowledge map."""
        if self._cog is None:
            return None
        km = self._cog.build_knowledge_map()
        return {
            "overall_level": km.overall_level,
            "topics_studied_count": km.topics_studied_count,
            "total_quizzes_taken": km.total_quizzes_taken,
            "average_quiz_score": km.average_quiz_score,
            "weak_areas": list(km.weak_areas),
            "strong_areas": list(km.strong_areas),
        }
