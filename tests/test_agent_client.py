"""Tests for CognitiveAgentClient implementations.

Covers:
- StubCognitiveAgentClient returns canned response correctly
- OllamaAgentClient tested via mocked ollama.chat call only
"""

from unittest.mock import patch

import pytest

from cognitive_agent.agent_client import (
    CognitiveAgentClient,
    OllamaAgentClient,
    StubCognitiveAgentClient,
)


def test_stub_cognitive_agent_client_returns_canned_response():
    """Test that StubCognitiveAgentClient returns canned response correctly."""
    canned_response = "This is a canned response"
    client = StubCognitiveAgentClient(canned_response)

    result = client.generate_raw("Any prompt")

    assert result == canned_response


def test_stub_cognitive_agent_client_with_empty_response():
    """Test that StubCognitiveAgentClient handles empty response."""
    canned_response = ""
    client = StubCognitiveAgentClient(canned_response)

    result = client.generate_raw("Any prompt")

    assert result == ""


def test_stub_cognitive_agent_client_with_multiline_response():
    """Test that StubCognitiveAgentClient handles multiline response."""
    canned_response = "Line 1\nLine 2\nLine 3"
    client = StubCognitiveAgentClient(canned_response)

    result = client.generate_raw("Any prompt")

    assert result == "Line 1\nLine 2\nLine 3"


@pytest.mark.integration
def test_ollama_agent_client_with_mocked_ollama():
    """Test that OllamaAgentClient works with mocked ollama.chat."""
    with patch("cognitive_agent.agent_client.ollama") as mock_ollama:
        mock_ollama.chat.return_value = {"message": {"content": "Mocked Ollama response"}}

        client = OllamaAgentClient("test-model", num_ctx=4096)
        result = client.generate_raw("Test prompt")

        mock_ollama.chat.assert_called_once_with(
            model="test-model",
            messages=[{"role": "user", "content": "Test prompt"}],
            options={"num_ctx": 4096},
        )

        assert result == "Mocked Ollama response"


def test_ollama_agent_client_with_different_context_sizes():
    """Test that OllamaAgentClient uses different context sizes."""
    with patch("cognitive_agent.agent_client.ollama") as mock_ollama:
        mock_ollama.chat.return_value = {"message": {"content": "Response"}}

        # Test with default context size
        client1 = OllamaAgentClient("test-model")
        client1.generate_raw("Prompt")

        mock_ollama.chat.assert_called_with(
            model="test-model",
            messages=[{"role": "user", "content": "Prompt"}],
            options={"num_ctx": 8192},
        )

        # Test with custom context size
        mock_ollama.chat.reset_mock()
        client2 = OllamaAgentClient("test-model", num_ctx=16384)
        client2.generate_raw("Prompt")

        mock_ollama.chat.assert_called_with(
            model="test-model",
            messages=[{"role": "user", "content": "Prompt"}],
            options={"num_ctx": 16384},
        )


def test_cognitive_agent_client_abstract_class():
    """Test that CognitiveAgentClient is an abstract class."""
    with pytest.raises(TypeError):
        CognitiveAgentClient()  # type: ignore
