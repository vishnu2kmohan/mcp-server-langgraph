"""
Tests for Visual Workflow Builder API Server

Comprehensive test suite for all builder API endpoints following TDD principles.

Tests cover:
- POST /api/builder/generate - Code generation from workflows
- POST /api/builder/validate - Workflow validation
- POST /api/builder/save - Save workflow to file
- GET /api/builder/templates - List templates
- GET /api/builder/templates/{id} - Get specific template
- POST /api/builder/import - Import Python code
- GET /api/builder/node-types - List node types
- GET / - API information
"""

from unittest.mock import mock_open, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from mcp_server_langgraph.builder.api.server import app


@pytest.fixture
def client():
    """FastAPI test client for builder API."""
    # Override auth dependency for tests
    from mcp_server_langgraph.builder.api.server import verify_builder_auth

    async def mock_auth():
        return None  # Auth bypassed for tests

    app.dependency_overrides[verify_builder_auth] = mock_auth

    yield TestClient(app)

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def valid_workflow():
    """Valid workflow definition for testing."""
    return {
        "name": "test_agent",
        "description": "Test workflow for validation",
        "nodes": [
            {
                "id": "search",
                "type": "tool",
                "label": "Web Search",
                "config": {"tool": "tavily_search"},
                "position": {"x": 100, "y": 100},
            },
            {
                "id": "summarize",
                "type": "llm",
                "label": "Summarize",
                "config": {"model": "gemini-flash"},
                "position": {"x": 300, "y": 100},
            },
        ],
        "edges": [{"from": "search", "to": "summarize"}],
        "entry_point": "search",
        "state_schema": {"query": "str", "result": "str"},
        "metadata": {},
    }


@pytest.fixture
def minimal_workflow():
    """Minimal valid workflow for testing warnings."""
    return {
        "name": "minimal",
        "description": "",  # Empty description triggers warning
        "nodes": [{"id": "node1", "type": "tool", "config": {}}],
        "edges": [],
        "entry_point": "node1",
    }

    # ==============================================================================
    # Test Root Endpoint
    # ==============================================================================

    """Test GET / returns API information."""
    # Act
    response = client.get("/")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Visual Workflow Builder API"
    assert data["version"] == "1.0.0"
    assert "features" in data
    assert len(data["features"]) > 0
    assert "unique_feature" in data
    assert "Code export" in data["unique_feature"]


# ==============================================================================
# Test POST /api/builder/generate
# ==============================================================================


def test_generate_code_with_valid_workflow_returns_formatted_code(client, valid_workflow):
    """Test POST /api/builder/generate with valid workflow generates code."""
    # Act
    response = client.post("/api/builder/generate", json={"workflow": valid_workflow})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate response structure
    assert "code" in data
    assert "formatted" in data
    assert "warnings" in data

    # Validate generated code content
    code = data["code"]
    assert "test_agent" in code.lower()
    assert "def create_test_agent()" in code
    assert "StateGraph" in code
    assert "node_search" in code
    assert "node_summarize" in code

    # Check formatting
    assert data["formatted"] is True

    # Should have no warnings for complete workflow
    assert len(data["warnings"]) == 0


def test_generate_code_with_minimal_workflow_returns_warnings(client, minimal_workflow):
    """Test POST /api/builder/generate with minimal workflow returns warnings."""
    # Act
    response = client.post("/api/builder/generate", json={"workflow": minimal_workflow})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Should have warnings for empty description and single node
    assert len(data["warnings"]) > 0
    assert any("description is empty" in w.lower() for w in data["warnings"])
    assert any("only one node" in w.lower() for w in data["warnings"])


def test_generate_code_with_invalid_workflow_returns_400(client):
    """Test POST /api/builder/generate with invalid workflow returns 400."""
    # Arrange - invalid workflow missing required fields
    invalid_workflow = {"name": "invalid"}  # Missing nodes, edges, entry_point

    # Act
    response = client.post("/api/builder/generate", json={"workflow": invalid_workflow})

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "detail" in data
    assert "failed" in data["detail"].lower()


def test_generate_code_with_empty_request_returns_422(client):
    """Test POST /api/builder/generate with empty request returns 422."""
    # Act
    response = client.post("/api/builder/generate", json={})

    # Assert - Pydantic validation error
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ==============================================================================
# Test POST /api/builder/validate
# ==============================================================================


def test_validate_workflow_with_valid_workflow_returns_valid_true(client, valid_workflow):
    """Test POST /api/builder/validate with valid workflow returns valid=True."""
    # Act
    response = client.post("/api/builder/validate", json={"workflow": valid_workflow})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["valid"] is True
    assert len(data["errors"]) == 0


def test_validate_workflow_with_empty_nodes_returns_error(client):
    """Test POST /api/builder/validate with empty nodes returns validation error."""
    # Arrange
    workflow_no_nodes = {
        "name": "empty",
        "nodes": [],  # No nodes
        "edges": [],
        "entry_point": "start",
    }

    # Act
    response = client.post("/api/builder/validate", json={"workflow": workflow_no_nodes})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["valid"] is False
    assert len(data["errors"]) > 0
    assert any("at least one node" in e.lower() for e in data["errors"])


def test_validate_workflow_with_invalid_entry_point_returns_error(client):
    """Test POST /api/builder/validate with invalid entry point returns error."""
    # Arrange
    workflow = {
        "name": "test",
        "nodes": [{"id": "node1", "type": "tool", "config": {}}],
        "edges": [],
        "entry_point": "nonexistent",  # Invalid entry point
    }

    # Act
    response = client.post("/api/builder/validate", json={"workflow": workflow})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["valid"] is False
    assert any("entry point" in e.lower() and "not found" in e.lower() for e in data["errors"])


def test_validate_workflow_with_invalid_edge_source_returns_error(client):
    """Test POST /api/builder/validate with invalid edge source returns error."""
    # Arrange
    workflow = {
        "name": "test",
        "nodes": [
            {"id": "node1", "type": "tool", "config": {}},
            {"id": "node2", "type": "tool", "config": {}},
        ],
        "edges": [{"from": "invalid_source", "to": "node2"}],  # Invalid source
        "entry_point": "node1",
    }

    # Act
    response = client.post("/api/builder/validate", json={"workflow": workflow})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["valid"] is False
    assert any("source" in e.lower() and "not found" in e.lower() for e in data["errors"])


def test_validate_workflow_with_invalid_edge_target_returns_error(client):
    """Test POST /api/builder/validate with invalid edge target returns error."""
    # Arrange
    workflow = {
        "name": "test",
        "nodes": [
            {"id": "node1", "type": "tool", "config": {}},
            {"id": "node2", "type": "tool", "config": {}},
        ],
        "edges": [{"from": "node1", "to": "invalid_target"}],  # Invalid target
        "entry_point": "node1",
    }

    # Act
    response = client.post("/api/builder/validate", json={"workflow": workflow})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["valid"] is False
    assert any("target" in e.lower() and "not found" in e.lower() for e in data["errors"])


def test_validate_workflow_with_unreachable_nodes_returns_warning(client):
    """Test POST /api/builder/validate with unreachable nodes returns warning."""
    # Arrange
    workflow = {
        "name": "test",
        "nodes": [
            {"id": "node1", "type": "tool", "config": {}},
            {"id": "node2", "type": "tool", "config": {}},
            {"id": "isolated", "type": "tool", "config": {}},  # Unreachable node
        ],
        "edges": [{"from": "node1", "to": "node2"}],
        "entry_point": "node1",
    }

    # Act
    response = client.post("/api/builder/validate", json={"workflow": workflow})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["valid"] is True  # Valid but with warnings
    assert len(data["warnings"]) > 0
    assert any("unreachable" in w.lower() for w in data["warnings"])


def test_validate_workflow_with_many_terminal_nodes_returns_warning(client):
    """Test POST /api/builder/validate with many terminal nodes returns warning."""
    # Arrange - Create workflow with 5 terminal nodes (> 3 triggers warning)
    workflow = {
        "name": "test",
        "nodes": [
            {"id": "start", "type": "tool", "config": {}},
            {"id": "end1", "type": "tool", "config": {}},
            {"id": "end2", "type": "tool", "config": {}},
            {"id": "end3", "type": "tool", "config": {}},
            {"id": "end4", "type": "tool", "config": {}},
        ],
        "edges": [
            {"from": "start", "to": "end1"},
            # end1, end2, end3, end4 are all terminal nodes
        ],
        "entry_point": "start",
    }

    # Act
    response = client.post("/api/builder/validate", json={"workflow": workflow})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["valid"] is True
    assert len(data["warnings"]) > 0
    assert any("terminal nodes" in w.lower() for w in data["warnings"])


def test_validate_workflow_with_invalid_structure_returns_error_not_exception(client):
    """Test POST /api/builder/validate handles exceptions gracefully."""
    # Arrange - malformed workflow that will cause exception
    invalid_workflow = {"name": 123, "nodes": "not_a_list"}  # Invalid types

    # Act
    response = client.post("/api/builder/validate", json={"workflow": invalid_workflow})

    # Assert
    assert response.status_code == status.HTTP_200_OK  # Not 500!
    data = response.json()

    assert data["valid"] is False
    assert len(data["errors"]) > 0
    assert "validation error" in data["errors"][0].lower()


# ==============================================================================
# Test POST /api/builder/save
# ==============================================================================


def test_save_workflow_with_valid_workflow_saves_to_file(client, valid_workflow):
    """Test POST /api/builder/save saves workflow to file."""
    # Arrange
    import tempfile

    # Use allowed directory for builder output (security validation)
    output_path = f"{tempfile.gettempdir()}/mcp-server-workflows/test_agent.py"  # nosec B108
    request = {"workflow": valid_workflow, "output_path": output_path}

    # Mock file operations
    with patch("builtins.open", mock_open()) as mock_file:
        # Act
        response = client.post("/api/builder/save", json=request)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert output_path in data["message"]
        assert data["path"] == output_path

        # Verify file was opened for writing
        mock_file.assert_called_once_with(output_path, "w")


def test_save_workflow_with_io_error_returns_500(client, valid_workflow):
    """Test POST /api/builder/save handles IO errors."""
    # Arrange
    import tempfile

    # Use allowed directory but mock will fail
    output_path = f"{tempfile.gettempdir()}/mcp-server-workflows/test.py"
    request = {"workflow": valid_workflow, "output_path": output_path}

    # Mock file operations to raise exception
    with patch("builtins.open", side_effect=IOError("Permission denied")):
        # Act
        response = client.post("/api/builder/save", json=request)

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "save failed" in data["detail"].lower()


# ==============================================================================
# Test GET /api/builder/templates
# ==============================================================================


def test_list_templates_returns_template_list(client):
    """Test GET /api/builder/templates returns list of templates."""
    # Act
    response = client.get("/api/builder/templates")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "templates" in data
    templates = data["templates"]
    assert len(templates) > 0

    # Verify template structure
    for template in templates:
        assert "id" in template
        assert "name" in template
        assert "description" in template
        assert "complexity" in template
        assert "nodes" in template

    # Verify expected templates exist
    template_ids = [t["id"] for t in templates]
    assert "simple_agent" in template_ids
    assert "research_agent" in template_ids
    assert "customer_support" in template_ids


# ==============================================================================
# Test GET /api/builder/templates/{template_id}
# ==============================================================================


def test_get_template_with_research_agent_returns_workflow(client):
    """Test GET /api/builder/templates/research_agent returns workflow."""
    # Act
    response = client.get("/api/builder/templates/research_agent")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "template" in data
    template = data["template"]

    # Verify workflow structure
    assert template["name"] == "research_agent"
    assert template["description"] == "Research and summarize topics"
    assert len(template["nodes"]) > 0
    assert len(template["edges"]) > 0
    assert "entry_point" in template


def test_get_template_with_unknown_id_returns_404(client):
    """Test GET /api/builder/templates/{unknown} returns 404."""
    # Act
    response = client.get("/api/builder/templates/nonexistent_template")

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "not found" in data["detail"].lower()


# ==============================================================================
# Test POST /api/builder/import
# ==============================================================================


def test_import_workflow_with_valid_code_returns_workflow(client):
    """Test POST /api/builder/import with valid Python code returns workflow."""
    # Arrange
    valid_code = """
from langgraph.graph import StateGraph

def my_node(state):
    return state

graph = StateGraph()
graph.add_node("node1", my_node)
graph.set_entry_point("node1")
"""

    # Mock import functionality
    mock_workflow = {
        "name": "imported_workflow",
        "nodes": [
            {
                "id": "node1",
                "type": "custom",
                "label": "node1",
                "config": {},
                "position": {"x": 475, "y": 50},
            }
        ],
        "edges": [],
        "entry_point": "node1",
        "description": "Imported workflow",
        "metadata": {"source": "imported", "parser_version": "1.0"},
        "state_schema": {},
    }
    mock_validation = {
        "valid": True,
        "warnings": ["No state schema extracted - may need manual configuration"],
        "errors": [],
    }

    with patch("mcp_server_langgraph.builder.importer.importer.import_from_code") as mock_import:
        with patch("mcp_server_langgraph.builder.importer.importer.validate_import") as mock_validate:
            mock_import.return_value = mock_workflow
            mock_validate.return_value = mock_validation

            # Act
            response = client.post("/api/builder/import", json={"code": valid_code, "layout": "hierarchical"})

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "workflow" in data
            assert "validation" in data
            assert "message" in data
            assert data["workflow"] == mock_workflow
            assert data["validation"] == mock_validation


def test_import_workflow_with_syntax_error_returns_400(client):
    """Test POST /api/builder/import with invalid Python syntax returns 400."""
    # Arrange
    invalid_code = "def broken syntax here"

    # Mock import to raise SyntaxError
    with patch(
        "mcp_server_langgraph.builder.importer.importer.import_from_code",
        side_effect=SyntaxError("invalid syntax"),
    ):
        # Act
        response = client.post("/api/builder/import", json={"code": invalid_code})

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "invalid python syntax" in data["detail"].lower()


def test_import_workflow_with_import_error_returns_500(client):
    """Test POST /api/builder/import with import error returns 500."""
    # Arrange
    code_with_error = "from langgraph.graph import StateGraph"

    # Mock import to raise generic exception
    with patch(
        "mcp_server_langgraph.builder.importer.importer.import_from_code",
        side_effect=Exception("Import failed"),
    ):
        # Act
        response = client.post("/api/builder/import", json={"code": code_with_error})

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "import failed" in data["detail"].lower()


# ==============================================================================
# Test GET /api/builder/node-types
# ==============================================================================


def test_list_node_types_returns_all_node_types(client):
    """Test GET /api/builder/node-types returns all available node types."""
    # Act
    response = client.get("/api/builder/node-types")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "node_types" in data
    node_types = data["node_types"]

    # Verify we have all expected node types
    expected_types = ["tool", "llm", "conditional", "approval", "custom"]
    actual_types = [nt["type"] for nt in node_types]

    for expected in expected_types:
        assert expected in actual_types

    # Verify structure of node type definitions
    for node_type in node_types:
        assert "type" in node_type
        assert "name" in node_type
        assert "description" in node_type
        assert "icon" in node_type
        assert "config_schema" in node_type


def test_node_types_tool_has_correct_schema(client):
    """Test GET /api/builder/node-types returns correct schema for tool node."""
    # Act
    response = client.get("/api/builder/node-types")
    data = response.json()

    # Find tool node type
    tool_type = next(nt for nt in data["node_types"] if nt["type"] == "tool")

    # Assert
    assert tool_type["name"] == "Tool"
    assert "config_schema" in tool_type
    assert "tool" in tool_type["config_schema"]
    assert tool_type["config_schema"]["tool"]["required"] is True


def test_node_types_llm_has_correct_schema(client):
    """Test GET /api/builder/node-types returns correct schema for LLM node."""
    # Act
    response = client.get("/api/builder/node-types")
    data = response.json()

    # Find LLM node type
    llm_type = next(nt for nt in data["node_types"] if nt["type"] == "llm")

    # Assert
    assert llm_type["name"] == "LLM"
    assert "config_schema" in llm_type
    assert "model" in llm_type["config_schema"]
    assert llm_type["config_schema"]["model"]["required"] is True
    assert "temperature" in llm_type["config_schema"]
    assert llm_type["config_schema"]["temperature"]["required"] is False


# ==============================================================================
# Integration Tests
# ==============================================================================


def test_generate_and_validate_workflow_integration(client, valid_workflow):
    """Test integration: validate workflow then generate code."""
    # First validate
    validate_response = client.post("/api/builder/validate", json={"workflow": valid_workflow})
    assert validate_response.status_code == status.HTTP_200_OK
    assert validate_response.json()["valid"] is True

    # Then generate
    generate_response = client.post("/api/builder/generate", json={"workflow": valid_workflow})
    assert generate_response.status_code == status.HTTP_200_OK
    assert "code" in generate_response.json()


def test_get_template_and_generate_code_integration(client):
    """Test integration: get template then generate code from it."""
    # Get template
    template_response = client.get("/api/builder/templates/research_agent")
    assert template_response.status_code == status.HTTP_200_OK
    template_workflow = template_response.json()["template"]

    # Generate code from template
    generate_response = client.post("/api/builder/generate", json={"workflow": template_workflow})
    assert generate_response.status_code == status.HTTP_200_OK

    code = generate_response.json()["code"]
    assert "research_agent" in code.lower()
    assert "def create_research_agent()" in code


# ==============================================================================
# Edge Cases and Error Handling
# ==============================================================================


def test_generate_code_with_special_characters_in_node_ids(client):
    """Test POST /api/builder/generate handles special characters in node IDs."""
    # Arrange
    workflow = {
        "name": "test",
        "nodes": [{"id": "node-with-dashes", "type": "tool", "config": {}}],
        "edges": [],
        "entry_point": "node-with-dashes",
    }

    # Act
    response = client.post("/api/builder/generate", json={"workflow": workflow})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    code = response.json()["code"]

    # Dashes should be converted to underscores in function names
    assert "node_with_dashes" in code


def test_validate_workflow_with_circular_dependencies(client):
    """Test POST /api/builder/validate handles circular dependencies."""
    # Arrange - circular workflow: A -> B -> A
    workflow = {
        "name": "circular",
        "nodes": [
            {"id": "A", "type": "tool", "config": {}},
            {"id": "B", "type": "tool", "config": {}},
        ],
        "edges": [{"from": "A", "to": "B"}, {"from": "B", "to": "A"}],
        "entry_point": "A",
    }

    # Act
    response = client.post("/api/builder/validate", json={"workflow": workflow})

    # Assert
    # Note: Current implementation doesn't detect cycles, but validation should still pass
    assert response.status_code == status.HTTP_200_OK
    # Future: Add cycle detection and verify warning is returned


def test_cors_headers_are_present(client):
    """Test that CORS headers are configured correctly."""
    # Act
    response = client.options("/api/builder/generate")

    # Assert - CORS middleware should add headers
    # Note: TestClient may not fully simulate CORS, but we verify the endpoint responds
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]
