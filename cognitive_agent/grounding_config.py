"""Grounding configuration loading from environment variables.

This module provides the load_grounding_config_from_env() function that
builds a GroundingConfig from environment variables. This is the ONLY
place os.environ is read for grounding configuration.
"""

import os

from grounding_engine.grounding_client import GroundingConfig


def load_grounding_config_from_env() -> GroundingConfig:
    """Build a GroundingConfig from environment variables.

    Reads:
        HELIX_GROUNDING_API_URL (required — raise ValueError with a
          clear message if unset, do not silently default to a fake URL)
        HELIX_GROUNDING_API_KEY (optional, defaults to None)
        HELIX_GROUNDING_TIMEOUT_SECONDS (optional, defaults to 15, must
          parse as int, raise ValueError with a clear message on
          malformed value — do not silently fall back on a parse error)
    Returns:
        A populated GroundingConfig.
    Raises:
        ValueError: if HELIX_GROUNDING_API_URL is unset or empty, or if
          HELIX_GROUNDING_TIMEOUT_SECONDS is set but not a valid integer.
    """
    # Read and validate HELIX_GROUNDING_API_URL (required)
    api_url = os.environ.get("HELIX_GROUNDING_API_URL")
    if not api_url:
        raise ValueError(
            "HELIX_GROUNDING_API_URL environment variable is required but not set. "
            "Please set it to the base URL of the search API endpoint."
        )

    # Read HELIX_GROUNDING_API_KEY (optional)
    api_key = os.environ.get("HELIX_GROUNDING_API_KEY")

    # Read and validate HELIX_GROUNDING_TIMEOUT_SECONDS (optional)
    timeout_seconds = 15  # Default value
    timeout_env = os.environ.get("HELIX_GROUNDING_TIMEOUT_SECONDS")
    if timeout_env is not None:
        try:
            timeout_seconds = int(timeout_env)
            if timeout_seconds <= 0:
                raise ValueError(f"HELIX_GROUNDING_TIMEOUT_SECONDS must be positive, got {timeout_seconds}")
        except ValueError as e:
            raise ValueError(
                f"HELIX_GROUNDING_TIMEOUT_SECONDS must be a valid integer, got '{timeout_env}'. Error: {e}"
            ) from e

    return GroundingConfig(
        api_url=api_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
