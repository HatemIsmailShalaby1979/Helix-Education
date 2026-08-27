"""Cognitive agent client interface and implementations.

Provides abstract base class for cognitive agents and two concrete
implementations: a deterministic stub for testing and an Ollama client
for real LLM calls.
"""

from abc import ABC, abstractmethod

# Import ollama at module level for testing
import ollama


class CognitiveAgentClient(ABC):
    """Abstract base class for cognitive agent clients.

    All cognitive agent clients must implement the generate_raw method to
    send prompts to the LLM and return raw text responses.
    """

    @abstractmethod
    def generate_raw(self, prompt: str) -> str:
        """Send a prompt to the LLM and return the raw text response.

        Args:
            prompt: The prompt to send to the LLM.

        Returns:
            The raw text response from the LLM.

        Raises:
            Exception: If the LLM call fails.
        """
        pass


class StubCognitiveAgentClient(CognitiveAgentClient):
    """Deterministic, offline cognitive agent client for testing.

    Returns pre-configured responses for any prompt. Does not make
    any LLM calls.

    Args:
        canned_response: The canned response to return for any prompt.
    """

    def __init__(self, canned_response: str) -> None:
        self._canned_response = canned_response

    def generate_raw(self, prompt: str) -> str:
        """Return the canned response regardless of prompt."""
        return self._canned_response


class OllamaAgentClient(CognitiveAgentClient):
    """Ollama-based cognitive agent client for real LLM calls.

    Sends prompts to a local Ollama backend and returns the raw text
    response.

    Args:
        model_name: The name of the Ollama model to use.
        num_ctx: The context window size for the model (default: 8192).
    """

    def __init__(self, model_name: str, num_ctx: int = 8192) -> None:
        self._model_name = model_name
        self._num_ctx = num_ctx

    def generate_raw(self, prompt: str) -> str:
        """Send a prompt to the Ollama backend and return the raw response.

        Args:
            prompt: The prompt to send to the LLM.

        Returns:
            The raw text response from the LLM.

        Raises:
            Exception: If the Ollama call fails.
        """
        response = ollama.chat(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
            options={"num_ctx": self._num_ctx},
        )
        return response["message"]["content"]
