"""Lesson Orchestrator — composes GenerationOrchestrator with QuizService.

Produces a complete lesson: multiple sourced sections plus a quiz,
all durably committed. Owns no state beyond its dependencies.
"""

from dataclasses import dataclass

from cognitive_engine.quiz_generator import QuizGeneratorService
from content_engine.content_models import Section
from content_engine.generation_orchestrator import GenerationOrchestrator
from quiz_engine.quiz_models import Quiz
from quiz_engine.quiz_service import QuizService
from state_core.scoring_engine import AnswerKey


@dataclass
class LessonResult:
    """Result of generating a full lesson with sections and quiz."""

    sections: list[Section]
    quiz: Quiz


class LessonOrchestrator:
    """Composes GenerationOrchestrator and QuizService to produce a full lesson.

    This class owns no state beyond its dependencies. It coordinates:
    1. Generating and committing each lesson section via GenerationOrchestrator
    2. Generating quiz items dynamically from section content via QuizGeneratorService
    3. Creating a quiz and adding items via QuizService
    4. Returning the assembled sections and quiz

    If ANY section generation fails, the exception propagates uncaught —
    no quiz is created, no partial sections are committed (the event store
    is append-only but the in-memory state is rolled back by the exception).
    """

    def __init__(
        self,
        generation_orchestrator: GenerationOrchestrator,
        quiz_service: QuizService,
        quiz_generator: QuizGeneratorService,
    ) -> None:
        """Initialize the LessonOrchestrator.

        Args:
            generation_orchestrator: Orchestrator for generating and
                committing sections.
            quiz_service: Service for creating quizzes and adding items.
            quiz_generator: Service for dynamically generating quiz items
                from text.
        """
        self._generation = generation_orchestrator
        self._quiz = quiz_service
        self._quiz_generator = quiz_generator

    def generate_full_lesson(
        self,
        topic: str,
        level: str,
        section_specs: list[dict],
        quiz_id: str,
        num_quiz_questions: int = 3,
    ) -> LessonResult:
        """Generate a complete lesson: sections + quiz.

        Pipeline:
        1. For each section_spec, call
           generation_orchestrator.generate_and_commit_section.
           Collect committed Sections. If ANY fails, STOP — propagate
           the exception uncaught, do not create the quiz, do not
           partially commit.
        2. Once all sections succeed, concatenate all section body texts
           into a single string and pass to
           quiz_generator.generate_quiz_from_text().
        3. Call quiz_service.create_quiz(topic, quiz_id), then
           quiz_service.add_item(...) for each generated quiz item.
        4. Return {"sections": list[Section], "quiz": Quiz}.

        Args:
            topic: The lesson topic.
            level: Difficulty level (e.g., "beginner", "intermediate", "advanced").
            section_specs: List of dicts, each with "section_id" (str) and
                "max_chunks" (int).
            quiz_id: Unique identifier for the quiz.
            num_quiz_questions: Number of quiz questions to generate (default: 3).

        Returns:
            LessonResult containing the committed sections and the created quiz.

        Raises:
            GroundingFetchError: If grounding fetch fails for any section.
            NoGroundingAvailableError: If grounding returns zero chunks.
            LessonSectionGenerationError: If LLM generation or validation fails.
            QuizGenerationError: If quiz generation from text fails.
            ValueError: If quiz/quiz item creation fails.
        """
        # Step 1: Generate and commit all sections
        sections: list[Section] = []
        for spec in section_specs:
            section_id = spec["section_id"]
            max_chunks = spec.get("max_chunks", 5)

            section = self._generation.generate_and_commit_section(
                topic=topic,
                level=level,
                section_id=section_id,
                max_chunks=max_chunks,
            )
            sections.append(section)

        # Step 2: Concatenate all section bodies for quiz generation
        combined_text = "\n\n".join(section.body for section in sections)

        # Step 3: Generate quiz items from the combined content
        generated_items = self._quiz_generator.generate_quiz_from_text(
            topic=topic,
            text_content=combined_text,
            num_questions=num_quiz_questions,
        )

        # Step 4: Create the quiz and add generated items
        quiz = self._quiz.create_quiz(topic=topic, quiz_id=quiz_id)

        for item in generated_items:
            answer_key = AnswerKey(
                required_keywords=item.required_keywords,
                forbidden_keywords=[],
                min_length_chars=0,
            )

            self._quiz.add_item(
                quiz_id=quiz_id,
                quiz_item_id=item.quiz_item_id,
                question=item.question,
                category=item.category,
                difficulty=item.difficulty,
                answer_key=answer_key,
            )

        return LessonResult(sections=sections, quiz=quiz)
