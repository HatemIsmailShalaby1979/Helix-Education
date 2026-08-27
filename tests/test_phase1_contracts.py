import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


# Mocking the API layer components for contract testing
def test_training_content_api_schema():
    """Verify the OpenAPI spec structure matches the expected contract."""
    with open(_PROJECT_ROOT / "api_layer" / "openapi_training_content.yaml") as f:
        # In a real Pact test, we would use pact-python here.
        # For now, we verify the file exists and contains key endpoints.
        content = f.read()
        assert "/training-content/generate" in content
        assert "/training-content/{lesson_id}" in content
        assert "/training-content/gap-patterns" in content
        assert "JWT" in content or "Bearer" in content


def test_assessment_event_schema_validity():
    """Verify the Avro schema is valid JSON and contains required fields."""
    with open(_PROJECT_ROOT / "api_layer" / "assessment_event_schema.avsc") as f:
        schema = json.load(f)
        assert schema["name"] == "AssessmentResultEvent"
        field_names = [field["name"] for field in schema["fields"]]
        assert "learner_id" in field_names
        assert "score" in field_names
        assert "competency_tags" in field_names


def test_auth_middleware_scopes():
    """Verify the auth middleware defines the correct scopes."""
    with open(_PROJECT_ROOT / "api_layer" / "auth.py") as f:
        content = f.read()
        assert "training:generate" in content
        assert "gaps:query" in content
        assert "HS256" in content
