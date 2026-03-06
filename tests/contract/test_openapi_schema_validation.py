"""
Contract Tests: OpenAPI Schema Validation

Validates that API responses match the OpenAPI schema definitions.
Prevents schema drift between backend implementation and API specification.

Sprint 4: Added for /api/v1/me endpoint validation.
"""

import gc
import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

# Load OpenAPI schema once at module level
OPENAPI_SCHEMA_PATH = Path(__file__).parent.parent.parent / "api" / "openapi.json"


def load_openapi_schema() -> dict[str, Any]:
    """Load the OpenAPI schema from api/openapi.json."""
    if not OPENAPI_SCHEMA_PATH.exists():
        pytest.skip(f"OpenAPI schema not found at {OPENAPI_SCHEMA_PATH}")
    with open(OPENAPI_SCHEMA_PATH) as f:
        return json.load(f)


def get_schema_for_ref(openapi_schema: dict, ref: str) -> dict[str, Any]:
    """Resolve a $ref to the actual schema definition."""
    # ref format: "#/components/schemas/UserInfoResponse"
    parts = ref.lstrip("#/").split("/")
    schema = openapi_schema
    for part in parts:
        schema = schema[part]
    return schema


def build_validator_with_resolver(openapi_schema: dict, schema_name: str) -> jsonschema.Draft7Validator:
    """Build a JSON Schema validator with proper $ref resolution."""
    # Get the component schema
    component_schema = openapi_schema["components"]["schemas"][schema_name]

    # Create a resolver that can handle $ref
    resolver = jsonschema.RefResolver.from_schema(openapi_schema)

    # Build validator with resolver
    return jsonschema.Draft7Validator(component_schema, resolver=resolver)


@pytest.mark.contract
@pytest.mark.xdist_group(name="openapi_validation")
class TestOpenAPISchemaValidation:
    """
    Contract tests validating API responses match OpenAPI schema.

    These tests catch:
    - Missing required fields in responses
    - Type mismatches (string vs array, etc.)
    - Extra fields not in schema
    - Schema drift between code and spec
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_openapi_schema_exists(self) -> None:
        """OpenAPI schema file should exist."""
        assert OPENAPI_SCHEMA_PATH.exists(), f"Schema not found: {OPENAPI_SCHEMA_PATH}"

    def test_openapi_schema_valid_json(self) -> None:
        """OpenAPI schema should be valid JSON."""
        schema = load_openapi_schema()
        assert "openapi" in schema
        assert "paths" in schema
        assert "components" in schema

    def test_user_info_response_schema_exists(self) -> None:
        """UserInfoResponse schema should be defined in OpenAPI spec."""
        schema = load_openapi_schema()
        assert "UserInfoResponse" in schema["components"]["schemas"]

    def test_me_endpoint_exists(self) -> None:
        """GET /api/v1/me endpoint should be defined."""
        schema = load_openapi_schema()
        assert "/api/v1/me" in schema["paths"]
        assert "get" in schema["paths"]["/api/v1/me"]


@pytest.mark.contract
@pytest.mark.xdist_group(name="openapi_validation")
class TestUserInfoResponseSchema:
    """
    Validate UserInfoResponse schema requirements.

    Ensures the schema has all required fields for frontend RBAC.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_user_info_response_has_required_fields(self) -> None:
        """UserInfoResponse schema should have required fields."""
        schema = load_openapi_schema()
        user_schema = schema["components"]["schemas"]["UserInfoResponse"]

        required = user_schema.get("required", [])
        assert "user_id" in required, "user_id should be required"
        assert "username" in required, "username should be required"
        assert "persona" in required, "persona should be required"

    def test_user_info_response_has_visible_modules_field(self) -> None:
        """UserInfoResponse should have visible_modules field (Sprint 4)."""
        schema = load_openapi_schema()
        user_schema = schema["components"]["schemas"]["UserInfoResponse"]
        properties = user_schema.get("properties", {})

        assert "visible_modules" in properties, "visible_modules field missing"

        # Should be array of strings
        visible_modules = properties["visible_modules"]
        assert visible_modules.get("type") == "array", "visible_modules should be array"
        assert visible_modules.get("items", {}).get("type") == "string"

    def test_user_info_response_has_feature_flags_field(self) -> None:
        """UserInfoResponse should have feature_flags field (Sprint 4)."""
        schema = load_openapi_schema()
        user_schema = schema["components"]["schemas"]["UserInfoResponse"]
        properties = user_schema.get("properties", {})

        assert "feature_flags" in properties, "feature_flags field missing"

        # Should be object with boolean values
        feature_flags = properties["feature_flags"]
        assert feature_flags.get("type") == "object"
        assert feature_flags.get("additionalProperties", {}).get("type") == "boolean"

    def test_user_info_response_has_sub_persona_field(self) -> None:
        """UserInfoResponse should have sub_persona field (Sprint 4)."""
        schema = load_openapi_schema()
        user_schema = schema["components"]["schemas"]["UserInfoResponse"]
        properties = user_schema.get("properties", {})

        assert "sub_persona" in properties, "sub_persona field missing"

    def test_user_info_response_has_api_version_field(self) -> None:
        """UserInfoResponse should have api_version field (Sprint 4)."""
        schema = load_openapi_schema()
        user_schema = schema["components"]["schemas"]["UserInfoResponse"]
        properties = user_schema.get("properties", {})

        assert "api_version" in properties, "api_version field missing"

    def test_persona_enum_values(self) -> None:
        """Persona field should have correct enum values."""
        schema = load_openapi_schema()
        user_schema = schema["components"]["schemas"]["UserInfoResponse"]
        persona_schema = user_schema.get("properties", {}).get("persona", {})

        expected_values = {"admin", "developer", "user"}
        actual_values = set(persona_schema.get("enum", []))

        assert actual_values == expected_values, f"Persona enum mismatch. Expected {expected_values}, got {actual_values}"


@pytest.mark.contract
@pytest.mark.xdist_group(name="openapi_validation")
class TestUserInfoResponseValidation:
    """
    Validate sample UserInfoResponse objects against the OpenAPI schema.

    Uses jsonschema to validate response structures match the spec.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_valid_admin_response_passes_validation(self) -> None:
        """Valid admin response should pass schema validation."""
        schema = load_openapi_schema()
        validator = build_validator_with_resolver(schema, "UserInfoResponse")

        valid_response = {
            "user_id": "user:admin",
            "username": "admin",
            "email": "admin@example.com",
            "roles": ["admin"],
            "persona": "admin",
            "sub_persona": "admin",
            "visible_modules": [
                "projects",
                "chat",
                "workflows",
                "agents",
                "admin",
            ],
            "feature_flags": {"enable_ai_suggestions": True},
            "api_version": "2",
        }

        # Should not raise
        validator.validate(valid_response)

    def test_valid_developer_response_passes_validation(self) -> None:
        """Valid developer response should pass schema validation."""
        schema = load_openapi_schema()
        validator = build_validator_with_resolver(schema, "UserInfoResponse")

        valid_response = {
            "user_id": "user:alice",
            "username": "alice",
            "email": "alice@example.com",
            "roles": ["developer"],
            "persona": "developer",
            "sub_persona": "alice-builder",
            "visible_modules": ["chat", "workflows", "agents", "mcp"],
            "feature_flags": {},
            "api_version": "2",
        }

        # Should not raise
        validator.validate(valid_response)

    def test_valid_user_response_passes_validation(self) -> None:
        """Valid user response should pass schema validation."""
        schema = load_openapi_schema()
        validator = build_validator_with_resolver(schema, "UserInfoResponse")

        valid_response = {
            "user_id": "user:bob",
            "username": "bob",
            "persona": "user",  # Minimal required fields
        }

        # Should not raise - only required fields
        validator.validate(valid_response)

    def test_missing_required_field_fails_validation(self) -> None:
        """Response missing required field should fail validation."""
        schema = load_openapi_schema()
        validator = build_validator_with_resolver(schema, "UserInfoResponse")

        invalid_response = {
            "user_id": "user:test",
            # Missing 'username' and 'persona' which are required
        }

        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid_response)

    def test_invalid_persona_value_fails_validation(self) -> None:
        """Response with invalid persona value should fail validation."""
        schema = load_openapi_schema()
        validator = build_validator_with_resolver(schema, "UserInfoResponse")

        invalid_response = {
            "user_id": "user:test",
            "username": "test",
            "persona": "superuser",  # Invalid - not in enum
        }

        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid_response)

    def test_visible_modules_must_be_array(self) -> None:
        """visible_modules must be an array of strings."""
        schema = load_openapi_schema()
        validator = build_validator_with_resolver(schema, "UserInfoResponse")

        invalid_response = {
            "user_id": "user:test",
            "username": "test",
            "persona": "user",
            "visible_modules": "chat,workflows",  # Should be array, not string
        }

        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid_response)

    def test_feature_flags_must_be_object(self) -> None:
        """feature_flags must be an object with boolean values."""
        schema = load_openapi_schema()
        validator = build_validator_with_resolver(schema, "UserInfoResponse")

        invalid_response = {
            "user_id": "user:test",
            "username": "test",
            "persona": "user",
            "feature_flags": ["flag1", "flag2"],  # Should be object, not array
        }

        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid_response)


@pytest.mark.contract
@pytest.mark.xdist_group(name="openapi_validation")
class TestModuleIdNormalization:
    """
    Validate that visible_modules use normalized IDs.

    Deprecated IDs (flows, costs, metrics) should not be used.
    """

    # Normalized module IDs that match ActivityBar NAV_ITEMS
    VALID_MODULE_IDS = {
        # Core Work
        "projects",
        "chat",
        "workflows",
        # AI & Data
        "agents",
        "mcp",
        "vectors",
        "connections",
        "files",
        # Observability
        "traces",
        "observability",
        "cost",
        # Admin
        "admin",
        "audit",
        "compliance",
        # Bottom items
        "help",
        "settings",
    }

    # Deprecated IDs that should NOT be used
    DEPRECATED_MODULE_IDS = {
        "flows": "workflows",  # Use 'workflows' instead
        "costs": "cost",  # Use 'cost' instead
        "metrics": "observability",  # Use 'observability' instead
    }

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_valid_module_ids_documented(self) -> None:
        """Verify VALID_MODULE_IDS matches expected count."""
        # Core(3) + AI(5) + Obs(3) + Admin(3) + Bottom(2) = 16
        assert len(self.VALID_MODULE_IDS) == 16

    def test_deprecated_module_ids_have_replacements(self) -> None:
        """Each deprecated ID should have a normalized replacement."""
        for deprecated, replacement in self.DEPRECATED_MODULE_IDS.items():
            assert replacement in self.VALID_MODULE_IDS, (
                f"Replacement '{replacement}' for deprecated '{deprecated}' is not a valid module ID"
            )

    def test_normalize_module_id_function(self) -> None:
        """Test module ID normalization logic."""
        from mcp_server_langgraph.api.v1.user import normalize_module_id

        # Deprecated IDs should be normalized
        assert normalize_module_id("flows") == "workflows"
        assert normalize_module_id("costs") == "cost"
        assert normalize_module_id("metrics") == "observability"

        # Valid IDs should pass through unchanged
        assert normalize_module_id("chat") == "chat"
        assert normalize_module_id("workflows") == "workflows"
        assert normalize_module_id("cost") == "cost"
