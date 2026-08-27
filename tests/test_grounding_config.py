"""Tests for load_grounding_config_from_env function.

Covers:
- Valid environment variables produce correct config
- Missing API_URL raises ValueError
- Malformed timeout raises ValueError
- Missing optional API_KEY defaults to None
- Missing optional timeout defaults to 15
"""

import os

import pytest

from grounding_engine.grounding_client import (
    load_grounding_config_from_env,
)


def test_valid_env_produces_correct_config():
    """Test that valid environment variables produce correct config."""
    # Set up environment variables
    os.environ["HELIX_GROUNDING_API_URL"] = "https://api.example.com"
    os.environ["HELIX_GROUNDING_API_KEY"] = "test-key"
    os.environ["HELIX_GROUNDING_TIMEOUT_SECONDS"] = "30"

    try:
        config = load_grounding_config_from_env()
        assert config.api_url == "https://api.example.com"
        assert config.api_key == "test-key"
        assert config.timeout_seconds == 30
    finally:
        # Clean up environment variables
        del os.environ["HELIX_GROUNDING_API_URL"]
        del os.environ["HELIX_GROUNDING_API_KEY"]
        del os.environ["HELIX_GROUNDING_TIMEOUT_SECONDS"]


def test_missing_api_url_raises_value_error():
    """Test that missing API_URL raises ValueError."""
    # Ensure API_URL is not set
    if "HELIX_GROUNDING_API_URL" in os.environ:
        del os.environ["HELIX_GROUNDING_API_URL"]

    with pytest.raises(ValueError) as exc_info:
        load_grounding_config_from_env()

    assert "HELIX_GROUNDING_API_URL environment variable is required" in str(exc_info.value)


def test_malformed_timeout_raises_value_error():
    """Test that malformed timeout raises ValueError."""
    # Set up environment variables
    os.environ["HELIX_GROUNDING_API_URL"] = "https://api.example.com"
    os.environ["HELIX_GROUNDING_TIMEOUT_SECONDS"] = "not-a-number"

    try:
        with pytest.raises(ValueError) as exc_info:
            load_grounding_config_from_env()

        assert "HELIX_GROUNDING_TIMEOUT_SECONDS must be a valid integer" in str(exc_info.value)
    finally:
        # Clean up environment variables
        del os.environ["HELIX_GROUNDING_API_URL"]
        del os.environ["HELIX_GROUNDING_TIMEOUT_SECONDS"]


def test_missing_optional_api_key_defaults_to_none():
    """Test that missing optional API_KEY defaults to None."""
    # Set up environment variables
    os.environ["HELIX_GROUNDING_API_URL"] = "https://api.example.com"
    # Don't set API_KEY

    try:
        config = load_grounding_config_from_env()
        assert config.api_key is None
    finally:
        # Clean up environment variables
        del os.environ["HELIX_GROUNDING_API_URL"]


def test_missing_optional_timeout_defaults_to_15():
    """Test that missing optional timeout defaults to 15."""
    # Set up environment variables
    os.environ["HELIX_GROUNDING_API_URL"] = "https://api.example.com"
    # Don't set timeout

    try:
        config = load_grounding_config_from_env()
        assert config.timeout_seconds == 15
    finally:
        # Clean up environment variables
        del os.environ["HELIX_GROUNDING_API_URL"]


def test_empty_api_url_raises_value_error():
    """Test that empty API_URL raises ValueError."""
    # Set up environment variables
    os.environ["HELIX_GROUNDING_API_URL"] = ""

    try:
        with pytest.raises(ValueError) as exc_info:
            load_grounding_config_from_env()

        assert "HELIX_GROUNDING_API_URL environment variable is required" in str(exc_info.value)
    finally:
        # Clean up environment variables
        del os.environ["HELIX_GROUNDING_API_URL"]


def test_zero_timeout_raises_value_error():
    """Test that zero timeout raises ValueError."""
    # Set up environment variables
    os.environ["HELIX_GROUNDING_API_URL"] = "https://api.example.com"
    os.environ["HELIX_GROUNDING_TIMEOUT_SECONDS"] = "0"

    try:
        with pytest.raises(ValueError) as exc_info:
            load_grounding_config_from_env()

        assert "HELIX_GROUNDING_TIMEOUT_SECONDS must be positive" in str(exc_info.value)
    finally:
        # Clean up environment variables
        del os.environ["HELIX_GROUNDING_API_URL"]
        del os.environ["HELIX_GROUNDING_TIMEOUT_SECONDS"]
