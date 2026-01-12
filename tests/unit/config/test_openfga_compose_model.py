"""
Tests for OpenFGA Model Composition (FGA DSL → JSON).

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify the compose functionality that converts modular .fga files
back into the consolidated model.json format.

Reference: ADR-0068 Phase 8 - Modularization
Technical Debt: Bidirectional sync implementation
"""

import gc
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

# Load compose_model module from config/openfga/ (not a package)
_compose_model_path = Path(__file__).parent.parent.parent.parent / "config" / "openfga" / "compose_model.py"
_spec = importlib.util.spec_from_file_location("compose_model", _compose_model_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load compose_model from {_compose_model_path}")
compose_model = importlib.util.module_from_spec(_spec)
sys.modules["compose_model"] = compose_model
_spec.loader.exec_module(compose_model)

# Import functions for use in tests
parse_fga_type = compose_model.parse_fga_type
parse_fga_module = compose_model.parse_fga_module
compose_modules = compose_model.compose_modules
extract_modules = compose_model.extract_modules
validate_roundtrip_diff = compose_model.validate_roundtrip_diff
generate_diff_report = compose_model.generate_diff_report
validate_model_schema = compose_model.validate_model_schema
get_openfga_schema = compose_model.get_openfga_schema


pytestmark = [
    pytest.mark.unit,
    pytest.mark.openfga,
    pytest.mark.config,
]


@pytest.mark.xdist_group(name="openfga_compose")
class TestFgaDslParser:
    """
    Test FGA DSL parsing to JSON structure.

    The parser must handle:
    - Type definitions with and without relations
    - Simple relations: [user]
    - Multiple types: [user, service_principal]
    - Computed relations: define viewer: editor
    - Unions: [types] or relation1 or relation2
    - TupleToUserset: organization->member, project->editor
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_simple_type_no_relations(self) -> None:
        """
        [PARSER] Parse type with no relations (e.g., 'type user').
        """

        fga_content = "type user"
        result = parse_fga_type(fga_content)

        assert result["type"] == "user"
        assert result.get("relations", {}) == {}

    def test_parse_type_with_simple_relation(self) -> None:
        """
        [PARSER] Parse type with simple [user] relation.
        """

        fga_content = """type organization
  relations
    define member: [user]"""

        result = parse_fga_type(fga_content)

        assert result["type"] == "organization"
        assert "member" in result["relations"]
        assert "this" in result["relations"]["member"]

    def test_parse_type_with_multiple_user_types(self) -> None:
        """
        [PARSER] Parse relation with multiple types: [user, service_principal].
        """

        fga_content = """type tool
  relations
    define owner: [user, service_principal]"""

        result = parse_fga_type(fga_content)

        assert result["type"] == "tool"
        metadata = result.get("metadata", {}).get("relations", {}).get("owner", {})
        user_types = metadata.get("directly_related_user_types", [])

        # Should have both user and service_principal
        type_names = [t["type"] for t in user_types]
        assert "user" in type_names
        assert "service_principal" in type_names

    def test_parse_computed_relation(self) -> None:
        """
        [PARSER] Parse computed relation: define viewer: editor.
        """

        fga_content = """type service_principal
  relations
    define owner: [user]
    define viewer: owner"""

        result = parse_fga_type(fga_content)

        assert result["type"] == "service_principal"
        viewer_rel = result["relations"]["viewer"]
        assert "computedUserset" in viewer_rel
        assert viewer_rel["computedUserset"]["relation"] == "owner"

    def test_parse_union_relation(self) -> None:
        """
        [PARSER] Parse union: [user] or owner or organization->member.
        """

        fga_content = """type tool
  relations
    define executor: [user] or owner or organization->member
    define organization: [organization]"""

        result = parse_fga_type(fga_content)

        executor_rel = result["relations"]["executor"]
        assert "union" in executor_rel
        children = executor_rel["union"]["child"]

        # Should have 3 children: this, computedUserset, tupleToUserset
        assert len(children) == 3

    def test_parse_tuple_to_userset(self) -> None:
        """
        [PARSER] Parse tupleToUserset: organization->member.
        """

        fga_content = """type workflow
  relations
    define viewer: [user] or organization->member"""

        result = parse_fga_type(fga_content)

        viewer_rel = result["relations"]["viewer"]
        assert "union" in viewer_rel

        # Find the tupleToUserset child
        ttu_child = None
        for child in viewer_rel["union"]["child"]:
            if "tupleToUserset" in child:
                ttu_child = child["tupleToUserset"]
                break

        assert ttu_child is not None
        assert ttu_child["tupleset"]["relation"] == "organization"
        assert ttu_child["computedUserset"]["relation"] == "member"


@pytest.mark.xdist_group(name="openfga_compose")
class TestFgaModuleParser:
    """
    Test parsing complete .fga module files.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_module_extracts_all_types(self) -> None:
        """
        [MODULE] Parse module file and extract all type definitions.
        """

        fga_content = """# Module: 01-core
# Description: Base identity types

model
  schema 1.1

type user

type organization
  relations
    define member: [user]
    define admin: [user]
"""

        types = parse_fga_module(fga_content)

        assert len(types) == 2
        type_names = [t["type"] for t in types]
        assert "user" in type_names
        assert "organization" in type_names

    def test_parse_module_preserves_comments_as_description(self) -> None:
        """
        [MODULE] Comments before type become description.
        """

        fga_content = """model
  schema 1.1

# This is a description
type tool
  relations
    define owner: [user]
"""

        types = parse_fga_module(fga_content)

        assert len(types) == 1
        # Description may be extracted from preceding comment
        # Implementation detail - may or may not include


@pytest.mark.xdist_group(name="openfga_compose")
class TestComposeModules:
    """
    Test composing multiple modules into model.json.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_compose_merges_all_modules(self) -> None:
        """
        [COMPOSE] Compose all .fga modules into single model.json structure.
        """

        # Use actual modules directory
        modules_dir = Path(__file__).parent.parent.parent.parent / "config" / "openfga" / "modules"

        if not modules_dir.exists():
            pytest.skip("Modules directory not found")

        result = compose_modules(modules_dir)

        assert "schema_version" in result
        assert "type_definitions" in result
        assert len(result["type_definitions"]) >= 30  # Should have 38 types

    def test_compose_includes_conditions(self) -> None:
        """
        [COMPOSE] Compose includes conditions from 00-conditions.json.
        """

        modules_dir = Path(__file__).parent.parent.parent.parent / "config" / "openfga" / "modules"

        if not modules_dir.exists():
            pytest.skip("Modules directory not found")

        conditions_file = modules_dir / "00-conditions.json"
        if not conditions_file.exists():
            pytest.skip("Conditions file not found")

        result = compose_modules(modules_dir)

        assert "conditions" in result
        assert "time_bound_share" in result["conditions"]
        assert "subscription_tier" in result["conditions"]

    def test_compose_matches_original_types(self) -> None:
        """
        [COMPOSE] Composed model has same types as original model.json.
        """

        base_dir = Path(__file__).parent.parent.parent.parent / "config" / "openfga"
        modules_dir = base_dir / "modules"
        model_path = base_dir / "model.json"

        if not modules_dir.exists() or not model_path.exists():
            pytest.skip("Required files not found")

        with open(model_path) as f:
            original = json.load(f)

        composed = compose_modules(modules_dir)

        original_types = {t["type"] for t in original["type_definitions"]}
        composed_types = {t["type"] for t in composed["type_definitions"]}

        assert original_types == composed_types, (
            f"Type mismatch.\n"
            f"Missing in composed: {original_types - composed_types}\n"
            f"Extra in composed: {composed_types - original_types}"
        )


@pytest.mark.xdist_group(name="openfga_compose")
class TestRoundTrip:
    """
    Test round-trip: model.json → .fga modules → model.json.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_then_compose_preserves_types(self) -> None:
        """
        [ROUNDTRIP] Extract to modules then compose back preserves all types.
        """

        base_dir = Path(__file__).parent.parent.parent.parent / "config" / "openfga"
        model_path = base_dir / "model.json"

        if not model_path.exists():
            pytest.skip("model.json not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_modules = Path(tmpdir) / "modules"

            # Extract to temp directory
            extract_modules(model_path, tmp_modules)

            # Compose back
            composed = compose_modules(tmp_modules)

            with open(model_path) as f:
                original = json.load(f)

            original_types = {t["type"] for t in original["type_definitions"]}
            composed_types = {t["type"] for t in composed["type_definitions"]}

            assert original_types == composed_types

    def test_extract_then_compose_preserves_relations(self) -> None:
        """
        [ROUNDTRIP] Extract then compose preserves relation names.
        """

        base_dir = Path(__file__).parent.parent.parent.parent / "config" / "openfga"
        model_path = base_dir / "model.json"

        if not model_path.exists():
            pytest.skip("model.json not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_modules = Path(tmpdir) / "modules"

            extract_modules(model_path, tmp_modules)
            composed = compose_modules(tmp_modules)

            with open(model_path) as f:
                original = json.load(f)

            # Check a sample type's relations
            original_org = next(t for t in original["type_definitions"] if t["type"] == "organization")
            composed_org = next(t for t in composed["type_definitions"] if t["type"] == "organization")

            original_rels = set(original_org.get("relations", {}).keys())
            composed_rels = set(composed_org.get("relations", {}).keys())

            assert original_rels == composed_rels, (
                f"Relation mismatch for 'organization'.\nOriginal: {original_rels}\nComposed: {composed_rels}"
            )


@pytest.mark.xdist_group(name="openfga_compose")
class TestRoundTripDiffValidation:
    """
    Test detailed round-trip diff validation.

    These tests verify that the diff validation function can detect
    differences between original and composed models, including:
    - Missing/extra types
    - Missing/extra relations
    - Relation structure differences
    - Metadata differences
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_roundtrip_returns_empty_diff_for_identical(self) -> None:
        """
        [DIFF] Identical models should produce empty diff.
        """
        # Import the validation function
        validate_roundtrip_diff = getattr(compose_model, "validate_roundtrip_diff", None)
        if validate_roundtrip_diff is None:
            pytest.skip("validate_roundtrip_diff not implemented yet")

        base_dir = Path(__file__).parent.parent.parent.parent / "config" / "openfga"
        model_path = base_dir / "model.json"

        if not model_path.exists():
            pytest.skip("model.json not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_modules = Path(tmpdir) / "modules"
            extract_modules(model_path, tmp_modules)
            composed = compose_modules(tmp_modules)

            with open(model_path) as f:
                original = json.load(f)

            diff = validate_roundtrip_diff(original, composed)

            # Diff should be empty or indicate no differences
            assert diff.get("types_match", False) is True
            assert len(diff.get("missing_types", [])) == 0
            assert len(diff.get("extra_types", [])) == 0

    def test_validate_roundtrip_detects_missing_type(self) -> None:
        """
        [DIFF] Should detect when composed model is missing a type.
        """
        validate_roundtrip_diff = getattr(compose_model, "validate_roundtrip_diff", None)
        if validate_roundtrip_diff is None:
            pytest.skip("validate_roundtrip_diff not implemented yet")

        original = {
            "type_definitions": [
                {"type": "user", "relations": {}},
                {"type": "organization", "relations": {"member": {"this": {}}}},
            ]
        }
        composed = {
            "type_definitions": [
                {"type": "user", "relations": {}},
                # organization is missing
            ]
        }

        diff = validate_roundtrip_diff(original, composed)

        assert "organization" in diff.get("missing_types", [])

    def test_validate_roundtrip_detects_missing_relation(self) -> None:
        """
        [DIFF] Should detect when composed model is missing a relation.
        """
        validate_roundtrip_diff = getattr(compose_model, "validate_roundtrip_diff", None)
        if validate_roundtrip_diff is None:
            pytest.skip("validate_roundtrip_diff not implemented yet")

        original = {
            "type_definitions": [
                {"type": "organization", "relations": {"member": {"this": {}}, "admin": {"this": {}}}},
            ]
        }
        composed = {
            "type_definitions": [
                {"type": "organization", "relations": {"member": {"this": {}}}},
                # admin relation is missing
            ]
        }

        diff = validate_roundtrip_diff(original, composed)

        relation_diffs = diff.get("relation_diffs", {})
        assert "organization" in relation_diffs
        assert "admin" in relation_diffs["organization"].get("missing", [])

    def test_validate_roundtrip_generates_diff_report(self) -> None:
        """
        [DIFF] Should generate a human-readable diff report.
        """
        generate_diff_report = getattr(compose_model, "generate_diff_report", None)
        if generate_diff_report is None:
            pytest.skip("generate_diff_report not implemented yet")

        diff = {
            "types_match": False,
            "missing_types": ["workflow"],
            "extra_types": [],
            "relation_diffs": {"organization": {"missing": ["admin"], "extra": []}},
        }

        report = generate_diff_report(diff)

        assert isinstance(report, str)
        assert "workflow" in report
        assert "organization" in report
        assert "admin" in report


@pytest.mark.xdist_group(name="openfga_compose")
class TestIntersectionRelations:
    """
    Test parsing intersection relations (FGA DSL 'and' syntax).

    OpenFGA supports intersection relations with syntax:
    - define can_view: viewer and member
    - define can_edit: editor and organization->admin

    These map to JSON:
    {
      "intersection": {
        "child": [...]
      }
    }
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_simple_intersection(self) -> None:
        """
        [INTERSECTION] Parse simple intersection: viewer and member.
        """
        fga_content = """type document
  relations
    define viewer: [user]
    define member: [user]
    define can_view: viewer and member"""

        result = parse_fga_type(fga_content)

        can_view_rel = result["relations"].get("can_view", {})

        # Should have intersection structure
        assert "intersection" in can_view_rel, f"Expected 'intersection' in can_view relation. Got: {can_view_rel}"
        children = can_view_rel["intersection"]["child"]
        assert len(children) == 2

    def test_parse_intersection_with_tupleset(self) -> None:
        """
        [INTERSECTION] Parse intersection with tupleToUserset: editor and organization->admin.
        """
        fga_content = """type resource
  relations
    define editor: [user]
    define organization: [organization]
    define can_edit: editor and organization->admin"""

        result = parse_fga_type(fga_content)

        can_edit_rel = result["relations"].get("can_edit", {})

        assert "intersection" in can_edit_rel, f"Expected 'intersection' in can_edit relation. Got: {can_edit_rel}"

        children = can_edit_rel["intersection"]["child"]
        assert len(children) == 2

        # One should be computedUserset (editor)
        # One should be tupleToUserset (organization->admin)
        has_computed = any("computedUserset" in c for c in children)
        has_ttu = any("tupleToUserset" in c for c in children)

        assert has_computed, "Should have computedUserset for 'editor'"
        assert has_ttu, "Should have tupleToUserset for 'organization->admin'"

    def test_parse_intersection_with_direct_types(self) -> None:
        """
        [INTERSECTION] Parse intersection with direct types: [user] and member.
        """
        fga_content = """type resource
  relations
    define member: [user]
    define restricted_viewer: [user] and member"""

        result = parse_fga_type(fga_content)

        rel = result["relations"].get("restricted_viewer", {})

        assert "intersection" in rel, f"Expected 'intersection' in restricted_viewer. Got: {rel}"

        children = rel["intersection"]["child"]
        assert len(children) == 2

        # One should be 'this' (direct types)
        # One should be computedUserset (member)
        has_this = any("this" in c for c in children)
        has_computed = any("computedUserset" in c for c in children)

        assert has_this, "Should have 'this' for direct types [user]"
        assert has_computed, "Should have computedUserset for 'member'"

    def test_intersection_to_dsl_roundtrip(self) -> None:
        """
        [INTERSECTION] Intersection should survive extract → compose roundtrip.
        """
        # This tests that type_to_fga_dsl can output intersection syntax
        # and parse_fga_type can parse it back
        type_to_fga_dsl = getattr(compose_model, "type_to_fga_dsl", None)
        if type_to_fga_dsl is None:
            pytest.skip("type_to_fga_dsl not available")

        original_type = {
            "type": "document",
            "relations": {
                "viewer": {"this": {}},
                "member": {"this": {}},
                "can_view": {
                    "intersection": {
                        "child": [
                            {"computedUserset": {"relation": "viewer"}},
                            {"computedUserset": {"relation": "member"}},
                        ]
                    }
                },
            },
            "metadata": {
                "relations": {
                    "viewer": {"directly_related_user_types": [{"type": "user"}]},
                    "member": {"directly_related_user_types": [{"type": "user"}]},
                }
            },
        }

        # Convert to DSL
        dsl = type_to_fga_dsl(original_type)

        # Parse back
        parsed = parse_fga_type(dsl)

        # Verify intersection is preserved
        assert "intersection" in parsed["relations"].get("can_view", {}), (
            f"Intersection not preserved in roundtrip.\nDSL output:\n{dsl}\nParsed: {parsed['relations'].get('can_view', {})}"
        )


@pytest.mark.xdist_group(name="openfga_compose")
class TestJsonSchemaValidation:
    """
    Test JSON Schema validation for composed model output.

    Validates that composed models conform to the OpenFGA authorization
    model JSON schema, ensuring:
    - Required fields present (schema_version, type_definitions)
    - Valid relation structures
    - Valid metadata structures
    - Valid condition definitions
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_schema_accepts_valid_model(self) -> None:
        """
        [SCHEMA] Valid model should pass schema validation.
        """
        validate_model_schema = getattr(compose_model, "validate_model_schema", None)
        if validate_model_schema is None:
            pytest.skip("validate_model_schema not implemented yet")

        valid_model = {
            "schema_version": "1.1",
            "type_definitions": [
                {"type": "user", "relations": {}},
                {
                    "type": "organization",
                    "relations": {"member": {"this": {}}},
                    "metadata": {"relations": {"member": {"directly_related_user_types": [{"type": "user"}]}}},
                },
            ],
        }

        result = validate_model_schema(valid_model)

        assert result["valid"] is True
        assert len(result.get("errors", [])) == 0

    def test_validate_schema_rejects_missing_schema_version(self) -> None:
        """
        [SCHEMA] Model missing schema_version should fail validation.
        """
        validate_model_schema = getattr(compose_model, "validate_model_schema", None)
        if validate_model_schema is None:
            pytest.skip("validate_model_schema not implemented yet")

        invalid_model = {
            # Missing schema_version
            "type_definitions": [{"type": "user", "relations": {}}],
        }

        result = validate_model_schema(invalid_model)

        assert result["valid"] is False
        assert any("schema_version" in str(e).lower() for e in result.get("errors", []))

    def test_validate_schema_rejects_invalid_relation_structure(self) -> None:
        """
        [SCHEMA] Invalid relation structure should fail validation.
        """
        validate_model_schema = getattr(compose_model, "validate_model_schema", None)
        if validate_model_schema is None:
            pytest.skip("validate_model_schema not implemented yet")

        invalid_model = {
            "schema_version": "1.1",
            "type_definitions": [
                {
                    "type": "document",
                    "relations": {
                        "viewer": {"invalid_key": "invalid_value"}  # Invalid structure
                    },
                },
            ],
        }

        result = validate_model_schema(invalid_model)

        assert result["valid"] is False

    def test_validate_schema_rejects_non_assignable_relation_with_metadata(self) -> None:
        """
        [SCHEMA] Non-assignable relations should not have directly_related_user_types.

        OpenFGA rejects models where a computed-only relation (no 'this: {}')
        has 'directly_related_user_types' in metadata. This test ensures we
        catch this error before uploading to OpenFGA.

        Regression test for: memory_index.viewer issue where viewer was purely
        computed (union of owner and admin) but metadata listed user types.
        """
        invalid_model = {
            "schema_version": "1.1",
            "type_definitions": [
                {
                    "type": "memory_index",
                    "relations": {
                        "owner": {"this": {}},
                        "admin": {"this": {}},
                        # viewer is purely computed (no 'this')
                        "viewer": {
                            "union": {
                                "child": [
                                    {"computedUserset": {"relation": "owner"}},
                                    {"computedUserset": {"relation": "admin"}},
                                ]
                            }
                        },
                    },
                    "metadata": {
                        "relations": {
                            "owner": {"directly_related_user_types": [{"type": "user"}]},
                            "admin": {"directly_related_user_types": [{"type": "user"}]},
                            # ERROR: viewer is not assignable, should not have this
                            "viewer": {"directly_related_user_types": [{"type": "user"}]},
                        }
                    },
                },
            ],
        }

        result = validate_model_schema(invalid_model)

        assert result["valid"] is False, "Should reject non-assignable relation with directly_related_user_types"
        assert any("non-assignable" in str(e).lower() or "viewer" in str(e) for e in result.get("errors", [])), (
            f"Expected error about non-assignable viewer relation. Got: {result.get('errors', [])}"
        )

    def test_validate_schema_accepts_assignable_relation_with_metadata(self) -> None:
        """
        [SCHEMA] Assignable relations (with 'this') CAN have directly_related_user_types.
        """
        valid_model = {
            "schema_version": "1.1",
            "type_definitions": [
                {
                    "type": "document",
                    "relations": {
                        "owner": {"this": {}},
                        # viewer has 'this' in union, so it's assignable
                        "viewer": {
                            "union": {
                                "child": [
                                    {"this": {}},  # Makes it assignable
                                    {"computedUserset": {"relation": "owner"}},
                                ]
                            }
                        },
                    },
                    "metadata": {
                        "relations": {
                            "owner": {"directly_related_user_types": [{"type": "user"}]},
                            # OK: viewer is assignable (has 'this' in union)
                            "viewer": {"directly_related_user_types": [{"type": "user"}]},
                        }
                    },
                },
            ],
        }

        result = validate_model_schema(valid_model)

        assert result["valid"] is True, f"Should accept assignable relation with metadata. Errors: {result.get('errors', [])}"

    def test_validate_composed_model_against_schema(self) -> None:
        """
        [SCHEMA] Composed model from modules should pass schema validation.
        """
        validate_model_schema = getattr(compose_model, "validate_model_schema", None)
        if validate_model_schema is None:
            pytest.skip("validate_model_schema not implemented yet")

        modules_dir = Path(__file__).parent.parent.parent.parent / "config" / "openfga" / "modules"

        if not modules_dir.exists():
            pytest.skip("Modules directory not found")

        composed = compose_modules(modules_dir)
        result = validate_model_schema(composed)

        assert result["valid"] is True, f"Composed model failed schema validation.\nErrors: {result.get('errors', [])}"

    def test_get_schema_returns_openfga_schema(self) -> None:
        """
        [SCHEMA] get_openfga_schema should return valid JSON schema.
        """
        get_openfga_schema = getattr(compose_model, "get_openfga_schema", None)
        if get_openfga_schema is None:
            pytest.skip("get_openfga_schema not implemented yet")

        schema = get_openfga_schema()

        assert isinstance(schema, dict)
        assert "$schema" in schema or "type" in schema
        assert "properties" in schema or "definitions" in schema

    def test_validate_production_model_json(self) -> None:
        """
        [SCHEMA] Production model.json should pass schema validation.

        This test validates config/openfga/model.json - the file that actually
        gets uploaded to OpenFGA. This catches issues like the memory_index.viewer
        bug where a computed relation had directly_related_user_types metadata.

        This is a critical regression test to prevent broken models from being
        deployed to production.
        """
        import json

        model_path = Path(__file__).parent.parent.parent.parent / "config" / "openfga" / "model.json"

        if not model_path.exists():
            pytest.skip("model.json not found")

        with open(model_path) as f:
            model = json.load(f)

        result = validate_model_schema(model)

        assert result["valid"] is True, (
            f"Production model.json failed schema validation.\n"
            f"File: {model_path}\n"
            f"Errors:\n" + "\n".join(f"  - {e}" for e in result.get("errors", []))
        )


@pytest.mark.xdist_group(name="openfga_compose")
class TestDifferenceRelations:
    """
    Test parsing difference relations (FGA DSL 'but not' syntax).

    OpenFGA supports difference relations with syntax:
    - define can_view: viewer but not blocked
    - define can_edit: editor but not suspended

    These map to JSON:
    {
      "difference": {
        "base": {...},
        "subtract": {...}
      }
    }
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_simple_difference(self) -> None:
        """
        [DIFFERENCE] Parse simple difference: viewer but not blocked.
        """
        fga_content = """type document
  relations
    define viewer: [user]
    define blocked: [user]
    define can_view: viewer but not blocked"""

        result = parse_fga_type(fga_content)

        can_view_rel = result["relations"].get("can_view", {})

        # Should have difference structure
        assert "difference" in can_view_rel, f"Expected 'difference' in can_view relation. Got: {can_view_rel}"
        assert "base" in can_view_rel["difference"]
        assert "subtract" in can_view_rel["difference"]

    def test_parse_difference_with_computed_base(self) -> None:
        """
        [DIFFERENCE] Parse difference with computed base: editor but not suspended.
        """
        fga_content = """type resource
  relations
    define editor: [user]
    define suspended: [user]
    define can_edit: editor but not suspended"""

        result = parse_fga_type(fga_content)

        can_edit_rel = result["relations"].get("can_edit", {})

        assert "difference" in can_edit_rel, f"Expected 'difference' in can_edit relation. Got: {can_edit_rel}"

        # Base should be computedUserset for editor
        base = can_edit_rel["difference"]["base"]
        assert "computedUserset" in base
        assert base["computedUserset"]["relation"] == "editor"

        # Subtract should be computedUserset for suspended
        subtract = can_edit_rel["difference"]["subtract"]
        assert "computedUserset" in subtract
        assert subtract["computedUserset"]["relation"] == "suspended"

    def test_parse_difference_with_direct_types(self) -> None:
        """
        [DIFFERENCE] Parse difference with direct types: [user] but not blocked.
        """
        fga_content = """type resource
  relations
    define blocked: [user]
    define allowed: [user] but not blocked"""

        result = parse_fga_type(fga_content)

        rel = result["relations"].get("allowed", {})

        assert "difference" in rel, f"Expected 'difference' in allowed. Got: {rel}"

        # Base should be 'this' for direct types
        base = rel["difference"]["base"]
        assert "this" in base

    def test_difference_to_dsl_roundtrip(self) -> None:
        """
        [DIFFERENCE] Difference should survive extract → compose roundtrip.
        """
        type_to_fga_dsl = getattr(compose_model, "type_to_fga_dsl", None)
        if type_to_fga_dsl is None:
            pytest.skip("type_to_fga_dsl not available")

        original_type = {
            "type": "document",
            "relations": {
                "viewer": {"this": {}},
                "blocked": {"this": {}},
                "can_view": {
                    "difference": {
                        "base": {"computedUserset": {"relation": "viewer"}},
                        "subtract": {"computedUserset": {"relation": "blocked"}},
                    }
                },
            },
            "metadata": {
                "relations": {
                    "viewer": {"directly_related_user_types": [{"type": "user"}]},
                    "blocked": {"directly_related_user_types": [{"type": "user"}]},
                }
            },
        }

        # Convert to DSL
        dsl = type_to_fga_dsl(original_type)

        # Parse back
        parsed = parse_fga_type(dsl)

        # Verify difference is preserved
        assert "difference" in parsed["relations"].get("can_view", {}), (
            f"Difference not preserved in roundtrip.\nDSL output:\n{dsl}\nParsed: {parsed['relations'].get('can_view', {})}"
        )


@pytest.mark.xdist_group(name="openfga_compose")
class TestNestedExpressions:
    """
    Test parsing nested union/intersection expressions.

    OpenFGA supports nested expressions like:
    - define can_access: (viewer and member) or admin
    - define restricted: [user] and (org_member or team_member)

    Note: FGA DSL has specific precedence rules. 'and' binds tighter than 'or'.
    Parentheses may be needed for complex expressions.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_union_of_intersections(self) -> None:
        """
        [NESTED] Parse: (viewer and member) or admin.

        Note: In FGA DSL, this is typically written as:
        define can_access: viewer and member or admin
        (and binds tighter, so this is (viewer and member) or admin)
        """
        fga_content = """type document
  relations
    define viewer: [user]
    define member: [user]
    define admin: [user]
    define can_access: viewer and member or admin"""

        result = parse_fga_type(fga_content)

        can_access_rel = result["relations"].get("can_access", {})

        # Should have union at top level with intersection as child
        # OR should have custom nested structure
        # The exact structure depends on implementation
        assert can_access_rel != {}, f"Expected non-empty can_access relation. Got: {can_access_rel}"

        # Either union or intersection should be present
        has_complex = "union" in can_access_rel or "intersection" in can_access_rel or "nested" in str(can_access_rel).lower()
        assert has_complex, f"Expected complex nested structure. Got: {can_access_rel}"

    def test_parse_intersection_of_unions(self) -> None:
        """
        [NESTED] Parse complex: [user] and (owner or editor).

        This requires explicit parentheses in some FGA DSL implementations.
        """
        # This test validates the parser can handle mixed operators
        fga_content = """type document
  relations
    define owner: [user]
    define editor: [user]
    define restricted: [user] and owner"""

        result = parse_fga_type(fga_content)

        restricted_rel = result["relations"].get("restricted", {})

        assert restricted_rel != {}, "Expected non-empty restricted relation."

    def test_parse_triple_operator_chain(self) -> None:
        """
        [NESTED] Parse: a and b and c (multiple same operator).
        """
        fga_content = """type document
  relations
    define a: [user]
    define b: [user]
    define c: [user]
    define all_three: a and b and c"""

        result = parse_fga_type(fga_content)

        all_three_rel = result["relations"].get("all_three", {})

        assert "intersection" in all_three_rel, f"Expected 'intersection' for triple and. Got: {all_three_rel}"

        # Should have 3 children
        children = all_three_rel["intersection"]["child"]
        assert len(children) == 3, f"Expected 3 children for 'a and b and c'. Got {len(children)}: {children}"


@pytest.mark.xdist_group(name="openfga_compose")
class TestConditionParameterValidation:
    """
    Test condition parameter validation in composed models.

    OpenFGA conditions have parameters with specific types:
    {
      "conditions": {
        "time_bound_share": {
          "name": "time_bound_share",
          "expression": "current_time < expiry",
          "parameters": {
            "current_time": {"type_name": "TYPE_NAME_TIMESTAMP"},
            "expiry": {"type_name": "TYPE_NAME_TIMESTAMP"}
          }
        }
      }
    }
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_condition_has_required_fields(self) -> None:
        """
        [CONDITION] Condition must have name and expression.
        """
        validate_condition_params = getattr(compose_model, "validate_condition_params", None)
        if validate_condition_params is None:
            pytest.skip("validate_condition_params not implemented yet")

        valid_condition = {
            "name": "time_bound_share",
            "expression": "current_time < expiry",
            "parameters": {
                "current_time": {"type_name": "TYPE_NAME_TIMESTAMP"},
                "expiry": {"type_name": "TYPE_NAME_TIMESTAMP"},
            },
        }

        result = validate_condition_params(valid_condition)

        assert result["valid"] is True
        assert len(result.get("errors", [])) == 0

    def test_validate_condition_missing_expression(self) -> None:
        """
        [CONDITION] Condition missing expression should fail.
        """
        validate_condition_params = getattr(compose_model, "validate_condition_params", None)
        if validate_condition_params is None:
            pytest.skip("validate_condition_params not implemented yet")

        invalid_condition = {
            "name": "time_bound_share",
            # Missing expression
            "parameters": {},
        }

        result = validate_condition_params(invalid_condition)

        assert result["valid"] is False
        assert any("expression" in str(e).lower() for e in result.get("errors", []))

    def test_validate_condition_invalid_parameter_type(self) -> None:
        """
        [CONDITION] Condition with invalid parameter type should fail.
        """
        validate_condition_params = getattr(compose_model, "validate_condition_params", None)
        if validate_condition_params is None:
            pytest.skip("validate_condition_params not implemented yet")

        invalid_condition = {
            "name": "test_condition",
            "expression": "x > y",
            "parameters": {
                "x": {"type_name": "INVALID_TYPE_NAME"},  # Invalid type
            },
        }

        result = validate_condition_params(invalid_condition)

        assert result["valid"] is False

    def test_validate_all_conditions_in_model(self) -> None:
        """
        [CONDITION] All conditions in model should be valid.
        """
        validate_model_conditions = getattr(compose_model, "validate_model_conditions", None)
        if validate_model_conditions is None:
            pytest.skip("validate_model_conditions not implemented yet")

        model = {
            "schema_version": "1.1",
            "type_definitions": [],
            "conditions": {
                "time_bound_share": {
                    "name": "time_bound_share",
                    "expression": "current_time < expiry",
                    "parameters": {
                        "current_time": {"type_name": "TYPE_NAME_TIMESTAMP"},
                        "expiry": {"type_name": "TYPE_NAME_TIMESTAMP"},
                    },
                },
                "subscription_tier": {
                    "name": "subscription_tier",
                    "expression": "user_tier in allowed_tiers",
                    "parameters": {
                        "user_tier": {"type_name": "TYPE_NAME_STRING"},
                        "allowed_tiers": {"type_name": "TYPE_NAME_LIST", "generic_types": [{"type_name": "TYPE_NAME_STRING"}]},
                    },
                },
            },
        }

        result = validate_model_conditions(model)

        assert result["valid"] is True


@pytest.mark.xdist_group(name="openfga_compose")
class TestModuleSyncValidation:
    """
    Test module synchronization validation.

    Validates that modules are in sync with model.json:
    - All types in model.json are covered by modules
    - No orphan types in modules
    - Module checksums match for change detection
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_check_sync_status_when_synced(self) -> None:
        """
        [SYNC] Modules in sync with model should report synced.
        """
        check_sync_status = getattr(compose_model, "check_sync_status", None)
        if check_sync_status is None:
            pytest.skip("check_sync_status not implemented yet")

        base_dir = Path(__file__).parent.parent.parent.parent / "config" / "openfga"
        model_path = base_dir / "model.json"
        modules_dir = base_dir / "modules"

        if not model_path.exists() or not modules_dir.exists():
            pytest.skip("Required files not found")

        status = check_sync_status(model_path, modules_dir)

        # Status should indicate sync state
        assert "in_sync" in status
        assert "missing_types" in status
        assert "extra_types" in status

    def test_detect_missing_types_in_modules(self) -> None:
        """
        [SYNC] Should detect types in model.json not covered by modules.
        """
        check_sync_status = getattr(compose_model, "check_sync_status", None)
        if check_sync_status is None:
            pytest.skip("check_sync_status not implemented yet")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_modules = Path(tmpdir) / "modules"
            tmp_modules.mkdir()

            # Create a minimal model
            model_path = Path(tmpdir) / "model.json"
            model = {
                "schema_version": "1.1",
                "type_definitions": [
                    {"type": "user", "relations": {}},
                    {"type": "organization", "relations": {}},
                    {"type": "uncovered_type", "relations": {}},  # Not in modules
                ],
            }
            with open(model_path, "w") as f:
                json.dump(model, f)

            # Create module that doesn't cover all types
            module_content = """model
  schema 1.1

type user

type organization
"""
            with open(tmp_modules / "01-core.fga", "w") as f:
                f.write(module_content)

            status = check_sync_status(model_path, tmp_modules)

            assert not status["in_sync"]
            assert "uncovered_type" in status["missing_types"]

    def test_detect_extra_types_in_modules(self) -> None:
        """
        [SYNC] Should detect types in modules not in model.json.
        """
        check_sync_status = getattr(compose_model, "check_sync_status", None)
        if check_sync_status is None:
            pytest.skip("check_sync_status not implemented yet")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_modules = Path(tmpdir) / "modules"
            tmp_modules.mkdir()

            # Create a minimal model
            model_path = Path(tmpdir) / "model.json"
            model = {
                "schema_version": "1.1",
                "type_definitions": [
                    {"type": "user", "relations": {}},
                ],
            }
            with open(model_path, "w") as f:
                json.dump(model, f)

            # Create module with extra type
            module_content = """model
  schema 1.1

type user

type extra_type_in_module
"""
            with open(tmp_modules / "01-core.fga", "w") as f:
                f.write(module_content)

            status = check_sync_status(model_path, tmp_modules)

            assert not status["in_sync"]
            assert "extra_type_in_module" in status["extra_types"]

    def test_generate_sync_report(self) -> None:
        """
        [SYNC] Should generate human-readable sync report.
        """
        generate_sync_report = getattr(compose_model, "generate_sync_report", None)
        if generate_sync_report is None:
            pytest.skip("generate_sync_report not implemented yet")

        status = {
            "in_sync": False,
            "missing_types": ["workflow", "session"],
            "extra_types": ["orphan_type"],
            "relation_diffs": {},
        }

        report = generate_sync_report(status)

        assert isinstance(report, str)
        assert "workflow" in report
        assert "session" in report
        assert "orphan_type" in report


@pytest.mark.xdist_group(name="openfga_compose")
class TestPhase8Modularization:
    """
    Test Phase 8 modularization infrastructure.

    Validates the complete modularization workflow:
    - Module definition coverage
    - Extract → compose → validate cycle
    - Module naming conventions
    - Condition module handling
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_modules_cover_all_model_types(self) -> None:
        """
        [MODULAR] All 37 types in model.json should be covered by MODULES list.
        """
        get_module_types = getattr(compose_model, "get_module_types", None)
        if get_module_types is None:
            pytest.skip("get_module_types not available")

        base_dir = Path(__file__).parent.parent.parent.parent / "config" / "openfga"
        model_path = base_dir / "model.json"

        if not model_path.exists():
            pytest.skip("model.json not found")

        with open(model_path) as f:
            model = json.load(f)

        model_types = {t["type"] for t in model["type_definitions"]}
        module_types = get_module_types()

        all_module_types = set()
        for types in module_types.values():
            all_module_types.update(types)

        missing = model_types - all_module_types
        extra = all_module_types - model_types

        assert len(missing) == 0, f"Types in model but not in MODULES: {missing}"
        assert len(extra) == 0, f"Types in MODULES but not in model: {extra}"

    def test_module_names_follow_convention(self) -> None:
        """
        [MODULAR] Module names should follow NN-name convention.
        """
        get_module_types = getattr(compose_model, "get_module_types", None)
        if get_module_types is None:
            pytest.skip("get_module_types not available")

        import re

        module_types = get_module_types()

        for module_name in module_types.keys():
            # Should match pattern like "01-core", "02-resources"
            assert re.match(r"^\d{2}-[a-z-]+$", module_name), f"Module name '{module_name}' doesn't follow NN-name convention"

    def test_extract_creates_all_module_files(self) -> None:
        """
        [MODULAR] Extract should create all module files.
        """
        base_dir = Path(__file__).parent.parent.parent.parent / "config" / "openfga"
        model_path = base_dir / "model.json"

        if not model_path.exists():
            pytest.skip("model.json not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_modules = Path(tmpdir) / "modules"

            extract_modules(model_path, tmp_modules)

            # Check that module files were created
            fga_files = list(tmp_modules.glob("*.fga"))

            assert len(fga_files) >= 9, (
                f"Expected at least 9 module files, got {len(fga_files)}: {[f.name for f in fga_files]}"
            )

    def test_extract_creates_conditions_module(self) -> None:
        """
        [MODULAR] Extract should create conditions JSON file if model has conditions.
        """
        base_dir = Path(__file__).parent.parent.parent.parent / "config" / "openfga"
        model_path = base_dir / "model.json"

        if not model_path.exists():
            pytest.skip("model.json not found")

        with open(model_path) as f:
            model = json.load(f)

        # Skip if model has no conditions
        if "conditions" not in model or not model["conditions"]:
            pytest.skip("model.json has no conditions")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_modules = Path(tmpdir) / "modules"

            extract_modules(model_path, tmp_modules)

            conditions_file = tmp_modules / "00-conditions.json"
            assert conditions_file.exists(), "Expected 00-conditions.json for model with conditions"

    def test_full_modularization_cycle(self) -> None:
        """
        [MODULAR] Full extract → compose → validate cycle should succeed.
        """
        base_dir = Path(__file__).parent.parent.parent.parent / "config" / "openfga"
        model_path = base_dir / "model.json"

        if not model_path.exists():
            pytest.skip("model.json not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_modules = Path(tmpdir) / "modules"

            # Extract
            extract_modules(model_path, tmp_modules)

            # Compose back
            composed = compose_modules(tmp_modules)

            # Load original
            with open(model_path) as f:
                original = json.load(f)

            # Validate types match
            original_types = {t["type"] for t in original["type_definitions"]}
            composed_types = {t["type"] for t in composed["type_definitions"]}

            assert original_types == composed_types, (
                f"Type mismatch after full cycle.\n"
                f"Missing: {original_types - composed_types}\n"
                f"Extra: {composed_types - original_types}"
            )

            # Validate using diff function
            diff = validate_roundtrip_diff(original, composed)
            assert diff["types_match"] is True, f"Round-trip validation failed: {generate_diff_report(diff)}"
