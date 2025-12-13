"""
Workflow Bootstrap Integration Tests

Integration tests for /api/v1/sessions/{id}/bootstrap-workflow endpoint.
Tests the full workflow bootstrap process with realistic session data.
"""

from __future__ import annotations

import gc
from uuid import uuid4

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

pytestmark = [
    pytest.mark.integration,
    pytest.mark.api,
]


@pytest.fixture
def workflow_bootstrap_app() -> FastAPI:
    """Create a test FastAPI app with the workflow bootstrap router."""
    from mcp_server_langgraph.api.v1.workflow_bootstrap import (
        workflow_bootstrap_router,
    )

    app = FastAPI()
    app.include_router(workflow_bootstrap_router, prefix="/api/v1")
    return app


@pytest.fixture
def workflow_bootstrap_client(workflow_bootstrap_app: FastAPI) -> TestClient:
    """Create a test client for the workflow bootstrap app."""
    return TestClient(workflow_bootstrap_app)


@pytest.fixture
def realistic_session_data() -> dict:
    """Realistic session data with multi-step conversation."""
    return {
        "id": str(uuid4()),
        "title": "Customer Support Ticket Processing",
        "messages": [
            {
                "role": "user",
                "content": "I need help processing customer support tickets",
            },
            {
                "role": "assistant",
                "content": "I'll help you set up a ticket processing workflow. First, I'll fetch the pending tickets from the database.",
            },
            {
                "role": "assistant",
                "content": "I've retrieved 15 pending tickets. Now I'll categorize them by urgency and topic using sentiment analysis.",
            },
            {
                "role": "assistant",
                "content": "The tickets have been categorized. 5 are urgent, 10 are normal priority. I'll now assign them to the appropriate support agents.",
            },
            {
                "role": "assistant",
                "content": "All tickets have been assigned. I'll send notification emails to the assigned agents.",
            },
            {
                "role": "assistant",
                "content": "Notifications sent successfully. The ticket processing workflow is complete.",
            },
        ],
    }


@pytest.mark.xdist_group(name="test_workflow_bootstrap_integration")
class TestWorkflowBootstrapIntegration:
    """Integration tests for workflow bootstrap endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_bootstrap_workflow_full_cycle(self, workflow_bootstrap_client: TestClient) -> None:
        """
        GIVEN a complete session with realistic conversation
        WHEN POST request is made to bootstrap-workflow
        THEN a complete workflow should be created with proper structure
        """
        # This test will fail until implementation exists (RED phase)
        # Will be implemented after basic endpoint structure is in place
        pytest.skip("Integration test - implement after basic endpoint works")

    def test_bootstrap_workflow_with_minimal_session(self, workflow_bootstrap_client: TestClient) -> None:
        """
        GIVEN a session with minimal messages (2-3 messages)
        WHEN POST request is made to bootstrap-workflow
        THEN a simple workflow should be created
        """
        # This test will fail until implementation exists (RED phase)
        pytest.skip("Integration test - implement after basic endpoint works")

    def test_bootstrap_workflow_creates_valid_workflow_structure(self, workflow_bootstrap_client: TestClient) -> None:
        """
        GIVEN a bootstrapped workflow
        WHEN the workflow is retrieved
        THEN it should have valid nodes, edges, and be executable
        """
        # This test will fail until implementation exists (RED phase)
        pytest.skip("Integration test - implement after basic endpoint works")

    def test_bootstrap_workflow_preserves_conversation_order(self, workflow_bootstrap_client: TestClient) -> None:
        """
        GIVEN a session with sequential steps
        WHEN workflow is bootstrapped
        THEN the workflow nodes should preserve the conversation order
        """
        # This test will fail until implementation exists (RED phase)
        pytest.skip("Integration test - implement after basic endpoint works")

    def test_bootstrap_workflow_handles_complex_branching(self, workflow_bootstrap_client: TestClient) -> None:
        """
        GIVEN a session with conditional logic in conversation
        WHEN workflow is bootstrapped
        THEN the workflow should include conditional nodes
        """
        # This test will fail until implementation exists (RED phase)
        pytest.skip("Integration test - implement after basic endpoint works")
