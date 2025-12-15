"""
Unit tests for OpenFGA Configuration Validation.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests validate that OpenFGA configuration files are correct:
1. config/openfga/model.json - Authorization model schema and structure
2. config/openfga/sample-tuples.json - Relationship tuples structure
3. Cross-validation - Tuples reference valid types/relations from model

Reference: ADR-0068 - Gateway-Level Authentication
"""

import gc
import json
from pathlib import Path

import pytest

# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
]

# Config file paths
CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config" / "openfga"
MODEL_PATH = CONFIG_DIR / "model.json"
TUPLES_PATH = CONFIG_DIR / "sample-tuples.json"


@pytest.fixture
def model_data() -> dict:
    """Load and return the authorization model."""
    with open(MODEL_PATH) as f:
        return json.load(f)


@pytest.fixture
def tuples_data() -> dict:
    """Load and return the sample tuples config."""
    with open(TUPLES_PATH) as f:
        return json.load(f)


@pytest.mark.xdist_group(name="test_openfga_config")
class TestModelJsonStructure:
    """Test authorization model structure and schema."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_file_exists(self):
        """
        GIVEN: Project repository
        WHEN: Checking for model.json
        THEN: File should exist at config/openfga/model.json
        """
        assert MODEL_PATH.exists(), f"Model file not found at {MODEL_PATH}"

    def test_model_is_valid_json(self):
        """
        GIVEN: model.json file exists
        WHEN: Parsing as JSON
        THEN: Should parse without errors
        """
        with open(MODEL_PATH) as f:
            model = json.load(f)
        assert isinstance(model, dict), "Model should be a JSON object"

    def test_model_has_schema_version(self, model_data: dict):
        """
        GIVEN: Valid model.json
        WHEN: Checking schema version
        THEN: Should have schema_version field set to "1.1"
        """
        assert "schema_version" in model_data, "Model should have schema_version"
        assert model_data["schema_version"] == "1.1", "Model should use schema version 1.1"

    def test_model_has_type_definitions(self, model_data: dict):
        """
        GIVEN: Valid model.json
        WHEN: Checking type definitions
        THEN: Should have type_definitions array
        """
        assert "type_definitions" in model_data, "Model should have type_definitions"
        assert isinstance(model_data["type_definitions"], list), "type_definitions should be a list"
        assert len(model_data["type_definitions"]) > 0, "type_definitions should not be empty"

    def test_model_has_required_types(self, model_data: dict):
        """
        GIVEN: Valid model.json
        WHEN: Checking for required types
        THEN: Should include all required type definitions

        Required types per ADR-0068:
        - user: Individual users
        - organization: Organizations
        - tool: AI tools
        - conversation: Conversation threads
        - vector_store: Qdrant collections
        - authz: OpenFGA Playground access
        """
        type_defs = model_data["type_definitions"]
        type_names = [t.get("type") for t in type_defs]

        required_types = [
            "user",
            "organization",
            "tool",
            "conversation",
            "role",
            "service_principal",
            "vector_store",
            "authz",
        ]

        for required in required_types:
            assert required in type_names, f"Required type '{required}' not found in model"

    def test_vector_store_has_expected_relations(self, model_data: dict):
        """
        GIVEN: Valid model.json with vector_store type
        WHEN: Checking relations
        THEN: Should have owner, editor, viewer relations
        """
        type_defs = model_data["type_definitions"]
        vector_store = next((t for t in type_defs if t.get("type") == "vector_store"), None)

        assert vector_store is not None, "vector_store type not found"
        relations = vector_store.get("relations", {})

        expected_relations = ["owner", "editor", "viewer", "organization"]
        for rel in expected_relations:
            assert rel in relations, f"vector_store should have '{rel}' relation"

    def test_authz_has_expected_relations(self, model_data: dict):
        """
        GIVEN: Valid model.json with authz type
        WHEN: Checking relations
        THEN: Should have admin and viewer relations
        """
        type_defs = model_data["type_definitions"]
        authz = next((t for t in type_defs if t.get("type") == "authz"), None)

        assert authz is not None, "authz type not found"
        relations = authz.get("relations", {})

        expected_relations = ["admin", "viewer"]
        for rel in expected_relations:
            assert rel in relations, f"authz should have '{rel}' relation"


@pytest.mark.xdist_group(name="test_openfga_config")
class TestSampleTuplesStructure:
    """Test sample tuples configuration structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tuples_file_exists(self):
        """
        GIVEN: Project repository
        WHEN: Checking for sample-tuples.json
        THEN: File should exist at config/openfga/sample-tuples.json
        """
        assert TUPLES_PATH.exists(), f"Tuples file not found at {TUPLES_PATH}"

    def test_tuples_is_valid_json(self):
        """
        GIVEN: sample-tuples.json file exists
        WHEN: Parsing as JSON
        THEN: Should parse without errors
        """
        with open(TUPLES_PATH) as f:
            tuples = json.load(f)
        assert isinstance(tuples, dict), "Tuples config should be a JSON object"

    def test_tuples_has_metadata(self, tuples_data: dict):
        """
        GIVEN: Valid sample-tuples.json
        WHEN: Checking for metadata
        THEN: Should have metadata documenting purpose and users
        """
        assert "metadata" in tuples_data, "Tuples config should have metadata"
        metadata = tuples_data["metadata"]

        assert "purpose" in metadata, "Metadata should have purpose"
        assert "users" in metadata, "Metadata should document users"

    def test_tuples_has_tuples_array(self, tuples_data: dict):
        """
        GIVEN: Valid sample-tuples.json
        WHEN: Checking for tuples
        THEN: Should have tuples array with entries
        """
        assert "tuples" in tuples_data, "Tuples config should have tuples array"
        assert isinstance(tuples_data["tuples"], list), "tuples should be a list"
        assert len(tuples_data["tuples"]) > 0, "tuples should not be empty"

    def test_each_tuple_has_required_fields(self, tuples_data: dict):
        """
        GIVEN: Valid sample-tuples.json
        WHEN: Checking each tuple
        THEN: Each tuple should have user, relation, object fields
        """
        tuples = tuples_data["tuples"]

        for i, t in enumerate(tuples):
            assert "user" in t, f"Tuple {i} missing 'user' field"
            assert "relation" in t, f"Tuple {i} missing 'relation' field"
            assert "object" in t, f"Tuple {i} missing 'object' field"


@pytest.mark.xdist_group(name="test_openfga_config")
class TestTupleModelCrossValidation:
    """Cross-validate tuples against model definitions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _get_model_types_and_relations(self, model_data: dict) -> dict[str, set[str]]:
        """Extract type -> relations mapping from model."""
        result = {}
        for type_def in model_data.get("type_definitions", []):
            type_name = type_def.get("type")
            relations = set(type_def.get("relations", {}).keys())
            result[type_name] = relations
        return result

    def _extract_object_type(self, obj: str) -> str:
        """Extract type from object string (e.g., 'vector_store:default' -> 'vector_store')."""
        if ":" in obj:
            return obj.split(":")[0]
        return obj

    def _extract_user_type(self, user: str) -> str:
        """Extract type from user string (e.g., 'user:alice' -> 'user')."""
        if ":" in user:
            return user.split(":")[0]
        return user

    def test_all_tuple_object_types_exist_in_model(self, model_data: dict, tuples_data: dict):
        """
        GIVEN: model.json and sample-tuples.json
        WHEN: Checking tuple object types
        THEN: All object types in tuples should exist in model

        This prevents configuration drift where tuples reference undefined types.
        """
        type_relations = self._get_model_types_and_relations(model_data)
        valid_types = set(type_relations.keys())

        tuples = tuples_data["tuples"]
        errors = []

        for t in tuples:
            obj_type = self._extract_object_type(t["object"])
            if obj_type not in valid_types:
                errors.append(f"Object '{t['object']}' references undefined type '{obj_type}'")

        assert len(errors) == 0, "Invalid object types in tuples:\n" + "\n".join(errors)

    def test_all_tuple_relations_exist_for_object_type(self, model_data: dict, tuples_data: dict):
        """
        GIVEN: model.json and sample-tuples.json
        WHEN: Checking tuple relations
        THEN: All relations should be valid for the object's type

        This prevents configuration drift where tuples use undefined relations.
        """
        type_relations = self._get_model_types_and_relations(model_data)
        tuples = tuples_data["tuples"]
        errors = []

        for t in tuples:
            obj_type = self._extract_object_type(t["object"])
            relation = t["relation"]

            if obj_type in type_relations:
                valid_relations = type_relations[obj_type]
                if relation not in valid_relations:
                    errors.append(
                        f"Tuple ({t['user']}, {relation}, {t['object']}): "
                        f"relation '{relation}' not defined for type '{obj_type}'. "
                        f"Valid relations: {valid_relations}"
                    )

        assert len(errors) == 0, "Invalid relations in tuples:\n" + "\n".join(errors)

    def test_user_types_are_valid(self, model_data: dict, tuples_data: dict):
        """
        GIVEN: model.json and sample-tuples.json
        WHEN: Checking tuple user types
        THEN: All user types should exist in model (user, organization, etc.)

        Some relations allow organization members, so organization is valid.
        """
        type_relations = self._get_model_types_and_relations(model_data)
        valid_types = set(type_relations.keys())

        tuples = tuples_data["tuples"]
        errors = []

        for t in tuples:
            user_type = self._extract_user_type(t["user"])
            if user_type not in valid_types:
                errors.append(f"User '{t['user']}' references undefined type '{user_type}'")

        assert len(errors) == 0, "Invalid user types in tuples:\n" + "\n".join(errors)


@pytest.mark.xdist_group(name="test_openfga_config")
class TestRequiredTestUserPermissions:
    """Verify required test users have expected permissions in config."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _has_tuple(self, tuples: list, user: str, relation: str, obj: str) -> bool:
        """Check if a specific tuple exists in the list."""
        return any(t["user"] == user and t["relation"] == relation and t["object"] == obj for t in tuples)

    def test_admin_has_owner_on_vector_store(self, tuples_data: dict):
        """admin should have owner on vector_store:default."""
        tuples = tuples_data["tuples"]
        assert self._has_tuple(tuples, "user:admin", "owner", "vector_store:default"), (
            "admin should have owner on vector_store:default"
        )

    def test_admin_has_admin_on_authz_playground(self, tuples_data: dict):
        """admin should have admin on authz:playground."""
        tuples = tuples_data["tuples"]
        assert self._has_tuple(tuples, "user:admin", "admin", "authz:playground"), (
            "admin should have admin on authz:playground"
        )

    def test_alice_has_editor_on_vector_store(self, tuples_data: dict):
        """alice should have editor on vector_store:default (CRUD access)."""
        tuples = tuples_data["tuples"]
        assert self._has_tuple(tuples, "user:alice", "editor", "vector_store:default"), (
            "alice should have editor on vector_store:default"
        )

    def test_alice_has_viewer_on_authz_playground(self, tuples_data: dict):
        """alice should have viewer on authz:playground."""
        tuples = tuples_data["tuples"]
        assert self._has_tuple(tuples, "user:alice", "viewer", "authz:playground"), (
            "alice should have viewer on authz:playground"
        )

    def test_bob_has_viewer_on_vector_store(self, tuples_data: dict):
        """bob should have viewer on vector_store:default."""
        tuples = tuples_data["tuples"]
        assert self._has_tuple(tuples, "user:bob", "viewer", "vector_store:default"), (
            "bob should have viewer on vector_store:default"
        )

    def test_bob_has_no_authz_playground_access(self, tuples_data: dict):
        """bob should NOT have any access to authz:playground (intentional)."""
        tuples = tuples_data["tuples"]

        has_admin = self._has_tuple(tuples, "user:bob", "admin", "authz:playground")
        has_viewer = self._has_tuple(tuples, "user:bob", "viewer", "authz:playground")

        assert not has_admin, "bob should NOT have admin on authz:playground"
        assert not has_viewer, "bob should NOT have viewer on authz:playground"

    def test_all_users_can_execute_chat_tool(self, tuples_data: dict):
        """All test users should be able to execute tool:chat."""
        tuples = tuples_data["tuples"]

        for user in ["user:admin", "user:alice", "user:bob"]:
            assert self._has_tuple(tuples, user, "executor", "tool:chat"), f"{user} should have executor on tool:chat"

    def test_all_users_are_org_members(self, tuples_data: dict):
        """All test users should be members of organization:acme."""
        tuples = tuples_data["tuples"]

        for user in ["user:admin", "user:alice", "user:bob"]:
            assert self._has_tuple(tuples, user, "member", "organization:acme"), (
                f"{user} should be member of organization:acme"
            )
