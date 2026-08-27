# QuizModule Deepening Decision

The quiz pipeline (QuizService, LearningService quiz methods, ScoringEngine, Router) was shallow across 4 modules with leaky seams. We collapsed it into a single deep QuizModule.

## Decisions

- **QuizModule** owns the quiz lifecycle end-to-end
- **Dependencies injected**: EventStore, SealedAnswerKeyStore (for testability)
- **Owns internally**: ScoringEngine (inlined as private methods)
- **Public interface**: 9 methods (start_quiz, answer_item, complete_session, get_summary, list_quizzes, get_quiz, create_quiz, get_topic_state, compute_topic_level)
- **Sessions**: Event-sourced (persisted to EventStore)
- **LearningService**: Delegates to QuizModule

## Prototype Validation

The throwaway prototype at `quiz_engine/quiz_module_prototype.py` validates:
- Session lifecycle: start → answer → answer → complete → summary ✅
- Topic state projection works (level=intermediate after 2 passed) ✅
- Event emission: AnswerSubmittedEvent + AnswerScoredEvent per answer ✅
- Scoring engine inline: keyword-based, deterministic, pure ✅

## Architectural Principle Applied

"Grading and content-authority cannot live inside a generative call." The deep QuizModule separates generation (Lesson/Quiz creation) from verification (scoring) — different trust levels, different modules.