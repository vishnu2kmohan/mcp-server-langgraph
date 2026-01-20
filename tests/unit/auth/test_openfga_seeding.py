"""
Unit tests for OpenFGA seeding functionality.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. load_sample_tuples reads from config/openfga/sample-tuples.json
2. Config file contains required tuples for test users
3. seed_sample_data calls write_tuples with loaded data

Reference: ADR-0068 - Gateway-Level Authentication
"""

import gc
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
]


@pytest.mark.xdist_group(name="test_openfga_seeding")
class TestLoadSampleTuples:
    """Test load_sample_tuples function reads config correctly."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_load_sample_tuples_from_config_file(self) -> None:
        """
        GIVEN: Config file at config/openfga/sample-tuples.json exists
        WHEN: load_sample_tuples is called
        THEN: Should return list of tuples from config file
        """
        from mcp_server_langgraph.auth.openfga import load_sample_tuples

        tuples = load_sample_tuples()

        # Should return a list of tuples
        assert isinstance(tuples, list)
        assert len(tuples) >= 20, f"Expected at least 20 tuples, got {len(tuples)}"

        # Each tuple should have user, relation, object keys
        for t in tuples:
            assert "user" in t, f"Tuple missing 'user' key: {t}"
            assert "relation" in t, f"Tuple missing 'relation' key: {t}"
            assert "object" in t, f"Tuple missing 'object' key: {t}"
            # Should NOT have _comment key (should be filtered out)
            assert "_comment" not in t, f"Tuple should not have '_comment' key: {t}"

    def test_config_file_includes_vector_store_tuples(self) -> None:
        """
        GIVEN: Config file exists
        WHEN: load_sample_tuples is called
        THEN: Should include vector_store tuples for admin, alice, bob
        """
        from mcp_server_langgraph.auth.openfga import load_sample_tuples

        tuples = load_sample_tuples()

        # Check vector_store tuples exist
        vector_store_tuples = [t for t in tuples if "vector_store" in t["object"]]

        assert len(vector_store_tuples) >= 3, "Should have at least 3 vector_store tuples"

        # Verify admin is owner
        admin_owner = any(
            t["user"] == "user:admin" and t["relation"] == "owner" and t["object"] == "vector_store:default"
            for t in vector_store_tuples
        )
        assert admin_owner, "Admin should be owner of vector_store:default"

        # Verify alice is editor (CRUD access per ADR-0068)
        alice_editor = any(
            t["user"] == "user:alice" and t["relation"] == "editor" and t["object"] == "vector_store:default"
            for t in vector_store_tuples
        )
        assert alice_editor, "Alice should be editor of vector_store:default"

        # Verify bob is viewer
        bob_viewer = any(
            t["user"] == "user:bob" and t["relation"] == "viewer" and t["object"] == "vector_store:default"
            for t in vector_store_tuples
        )
        assert bob_viewer, "Bob should be viewer of vector_store:default"

    # Note: test_config_file_includes_authz_playground_tuples removed - playground deprecated

    def test_config_file_includes_organization_tuples(self) -> None:
        """
        GIVEN: Config file exists
        WHEN: load_sample_tuples is called
        THEN: Should include organization tuples for all test users
        """
        from mcp_server_langgraph.auth.openfga import load_sample_tuples

        tuples = load_sample_tuples()

        # Check organization tuples exist
        org_tuples = [t for t in tuples if "organization:acme" in t["object"]]

        # Should have at least 5 (alice member+admin, bob member, admin member+admin)
        assert len(org_tuples) >= 5, "Should have at least 5 organization tuples"

        # Verify admin is member of acme
        admin_member = any(
            t["user"] == "user:admin" and t["relation"] == "member" and t["object"] == "organization:acme" for t in org_tuples
        )
        assert admin_member, "Admin should be member of organization:acme"

    def test_config_file_includes_tool_permissions(self) -> None:
        """
        GIVEN: Config file exists
        WHEN: load_sample_tuples is called
        THEN: Should include tool permissions for all test users
        """
        from mcp_server_langgraph.auth.openfga import load_sample_tuples

        tuples = load_sample_tuples()

        # Check tool tuples exist
        tool_tuples = [t for t in tuples if "tool:chat" in t["object"]]

        # All three users should be executors
        for user in ["user:admin", "user:alice", "user:bob"]:
            is_executor = any(
                t["user"] == user and t["relation"] == "executor" and t["object"] == "tool:chat" for t in tool_tuples
            )
            assert is_executor, f"{user} should be executor of tool:chat"

    def test_load_sample_tuples_file_not_found(self, tmp_path: Path) -> None:
        """
        GIVEN: Non-existent config file path
        WHEN: load_sample_tuples is called with that path
        THEN: Should raise FileNotFoundError
        """
        from mcp_server_langgraph.auth.openfga import load_sample_tuples

        with pytest.raises(FileNotFoundError):
            load_sample_tuples(tmp_path / "nonexistent.json")


@pytest.mark.xdist_group(name="test_openfga_seeding")
class TestSeedSampleData:
    """Test seed_sample_data function uses config file."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_seed_sample_data_calls_write_tuples(self) -> None:
        """
        GIVEN: OpenFGA client mock
        WHEN: seed_sample_data is called
        THEN: Should call write_tuples with tuples from config file
        """
        from mcp_server_langgraph.auth.openfga import seed_sample_data

        # Create mock client with explicit return values
        mock_client = AsyncMock(return_value=None)
        mock_client.write_tuples = AsyncMock(return_value=None)

        # Call seed function
        await seed_sample_data(mock_client)

        # Verify write_tuples was called
        mock_client.write_tuples.assert_called_once()

        # Get the tuples that were written
        tuples = mock_client.write_tuples.call_args[0][0]

        # Should have at least 20 tuples (org + tool + conversation + role + vector_store + authz)
        assert len(tuples) >= 20, f"Expected at least 20 tuples, got {len(tuples)}"

    @pytest.mark.asyncio
    async def test_seed_sample_data_with_custom_path(self, tmp_path: Path) -> None:
        """
        GIVEN: Custom tuples config file
        WHEN: seed_sample_data is called with path
        THEN: Should load from custom path
        """
        from mcp_server_langgraph.auth.openfga import seed_sample_data

        # Create custom config file (using Path.write_text to avoid blocking open)
        custom_config = {
            "tuples": [
                {"user": "user:test", "relation": "viewer", "object": "test:resource"},
            ]
        }
        custom_path = tmp_path / "custom-tuples.json"
        custom_path.write_text(json.dumps(custom_config))

        # Create mock client with explicit return values
        mock_client = AsyncMock(return_value=None)
        mock_client.write_tuples = AsyncMock(return_value=None)

        # Call seed function with custom path
        await seed_sample_data(mock_client, tuples_path=custom_path)

        # Verify write_tuples was called with custom tuples
        mock_client.write_tuples.assert_called_once()
        tuples = mock_client.write_tuples.call_args[0][0]

        assert len(tuples) == 1
        assert tuples[0]["user"] == "user:test"


@pytest.mark.xdist_group(name="test_openfga_seeding")
class TestConfigFileContent:
    """Test the config file structure and content."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_config_file_is_valid_json(self) -> None:
        """
        GIVEN: config/openfga/sample-tuples.json exists
        WHEN: Reading the file
        THEN: Should be valid JSON
        """
        config_path = Path(__file__).parent.parent.parent.parent / "config/openfga/sample-tuples.json"

        assert config_path.exists(), f"Config file not found at {config_path}"

        with open(config_path) as f:
            config = json.load(f)

        assert "tuples" in config, "Config should have 'tuples' key"
        assert isinstance(config["tuples"], list), "tuples should be a list"

    def test_config_file_has_metadata(self) -> None:
        """
        GIVEN: config/openfga/sample-tuples.json exists
        WHEN: Reading the file
        THEN: Should have metadata documenting purpose
        """
        config_path = Path(__file__).parent.parent.parent.parent / "config/openfga/sample-tuples.json"

        with open(config_path) as f:
            config = json.load(f)

        assert "metadata" in config, "Config should have 'metadata' key"
        assert "purpose" in config["metadata"], "Metadata should have 'purpose'"
        assert "users" in config["metadata"], "Metadata should document users"
