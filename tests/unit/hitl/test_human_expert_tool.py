"""Tests for HumanExpertTool.

TDD: These tests define the contract for the HumanExpertTool that
allows treating humans as experts in the tool-calling loop.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="human_expert_tool_basic")
class TestHumanExpertToolBasic:
    """Tests for HumanExpertTool basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_human_expert_tool_exists(self) -> None:
        """Test HumanExpertTool class exists."""
        from mcp_server_langgraph.hitl.human_expert import HumanExpertTool

        assert HumanExpertTool is not None

    def test_human_expert_tool_has_name(self) -> None:
        """Test HumanExpertTool has a name attribute."""
        from mcp_server_langgraph.hitl.human_expert import HumanExpertTool

        tool = HumanExpertTool()

        assert hasattr(tool, "name")
        assert tool.name == "human_expert"

    def test_human_expert_tool_has_description(self) -> None:
        """Test HumanExpertTool has a description attribute."""
        from mcp_server_langgraph.hitl.human_expert import HumanExpertTool

        tool = HumanExpertTool()

        assert hasattr(tool, "description")
        assert len(tool.description) > 0

    def test_human_expert_tool_has_ask_method(self) -> None:
        """Test HumanExpertTool has ask method."""
        from mcp_server_langgraph.hitl.human_expert import HumanExpertTool

        tool = HumanExpertTool()

        assert hasattr(tool, "ask")


@pytest.mark.unit
@pytest.mark.xdist_group(name="human_expert_tool_request")
class TestHumanExpertToolRequest:
    """Tests for HumanExpertTool request creation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_human_expert_request_exists(self) -> None:
        """Test HumanExpertRequest dataclass exists."""
        from mcp_server_langgraph.hitl.human_expert import HumanExpertRequest

        assert HumanExpertRequest is not None

    def test_human_expert_request_has_question(self) -> None:
        """Test HumanExpertRequest has question field."""
        from mcp_server_langgraph.hitl.human_expert import HumanExpertRequest

        request = HumanExpertRequest(
            question="What is the correct approach?",
            context="Working on database migration",
        )

        assert request.question == "What is the correct approach?"

    def test_human_expert_request_has_context(self) -> None:
        """Test HumanExpertRequest has context field."""
        from mcp_server_langgraph.hitl.human_expert import HumanExpertRequest

        request = HumanExpertRequest(
            question="What is the correct approach?",
            context="Working on database migration",
        )

        assert request.context == "Working on database migration"

    def test_human_expert_request_has_optional_options(self) -> None:
        """Test HumanExpertRequest has optional options field."""
        from mcp_server_langgraph.hitl.human_expert import HumanExpertRequest

        request = HumanExpertRequest(
            question="Which approach?",
            context="Migration",
            options=["Option A", "Option B", "Option C"],
        )

        assert request.options == ["Option A", "Option B", "Option C"]

    def test_human_expert_request_has_optional_timeout(self) -> None:
        """Test HumanExpertRequest has optional timeout field."""
        from mcp_server_langgraph.hitl.human_expert import HumanExpertRequest

        request = HumanExpertRequest(
            question="What is the approach?",
            context="Migration",
            timeout_seconds=300,
        )

        assert request.timeout_seconds == 300


@pytest.mark.unit
@pytest.mark.xdist_group(name="human_expert_tool_response")
class TestHumanExpertToolResponse:
    """Tests for HumanExpertTool response handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_human_expert_response_exists(self) -> None:
        """Test HumanExpertResponse dataclass exists."""
        from mcp_server_langgraph.hitl.human_expert import HumanExpertResponse

        assert HumanExpertResponse is not None

    def test_human_expert_response_has_answer(self) -> None:
        """Test HumanExpertResponse has answer field."""
        from mcp_server_langgraph.hitl.human_expert import HumanExpertResponse

        response = HumanExpertResponse(
            answer="Use approach A",
            answered_by="user@example.com",
        )

        assert response.answer == "Use approach A"

    def test_human_expert_response_has_answered_by(self) -> None:
        """Test HumanExpertResponse has answered_by field."""
        from mcp_server_langgraph.hitl.human_expert import HumanExpertResponse

        response = HumanExpertResponse(
            answer="Use approach A",
            answered_by="user@example.com",
        )

        assert response.answered_by == "user@example.com"

    def test_human_expert_response_has_optional_selected_option(self) -> None:
        """Test HumanExpertResponse has optional selected_option field."""
        from mcp_server_langgraph.hitl.human_expert import HumanExpertResponse

        response = HumanExpertResponse(
            answer="Use approach A",
            answered_by="user@example.com",
            selected_option=0,
        )

        assert response.selected_option == 0

    def test_human_expert_response_has_optional_confidence(self) -> None:
        """Test HumanExpertResponse has optional confidence field."""
        from mcp_server_langgraph.hitl.human_expert import HumanExpertResponse

        response = HumanExpertResponse(
            answer="Use approach A",
            answered_by="user@example.com",
            confidence=0.95,
        )

        assert response.confidence == 0.95


@pytest.mark.unit
@pytest.mark.xdist_group(name="human_expert_tool_ask")
class TestHumanExpertToolAsk:
    """Tests for HumanExpertTool.ask() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ask_creates_pending_request(self) -> None:
        """Test ask() creates a pending request."""
        from mcp_server_langgraph.hitl.human_expert import (
            HumanExpertRequest,
            HumanExpertTool,
            RequestStatus,
        )

        tool = HumanExpertTool()
        request = HumanExpertRequest(
            question="What approach?",
            context="Migration",
        )

        request_id = await tool.ask(request, session_id="session-123")

        assert request_id is not None
        assert len(request_id) > 0
        status = tool.get_status(request_id)
        assert status == RequestStatus.PENDING

    @pytest.mark.asyncio
    async def test_ask_stores_request(self) -> None:
        """Test ask() stores the request for later retrieval."""
        from mcp_server_langgraph.hitl.human_expert import (
            HumanExpertRequest,
            HumanExpertTool,
        )

        tool = HumanExpertTool()
        request = HumanExpertRequest(
            question="What approach?",
            context="Migration",
        )

        request_id = await tool.ask(request, session_id="session-123")

        stored = tool.get_request(request_id)
        assert stored is request


@pytest.mark.unit
@pytest.mark.xdist_group(name="human_expert_tool_respond")
class TestHumanExpertToolRespond:
    """Tests for HumanExpertTool.respond() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_respond_updates_status(self) -> None:
        """Test respond() updates request status to ANSWERED."""
        from mcp_server_langgraph.hitl.human_expert import (
            HumanExpertRequest,
            HumanExpertResponse,
            HumanExpertTool,
            RequestStatus,
        )

        tool = HumanExpertTool()
        request = HumanExpertRequest(
            question="What approach?",
            context="Migration",
        )
        request_id = await tool.ask(request, session_id="session-123")

        response = HumanExpertResponse(
            answer="Use approach A",
            answered_by="user@example.com",
        )
        await tool.respond(request_id, response)

        status = tool.get_status(request_id)
        assert status == RequestStatus.ANSWERED

    @pytest.mark.asyncio
    async def test_respond_stores_response(self) -> None:
        """Test respond() stores the response for retrieval."""
        from mcp_server_langgraph.hitl.human_expert import (
            HumanExpertRequest,
            HumanExpertResponse,
            HumanExpertTool,
        )

        tool = HumanExpertTool()
        request = HumanExpertRequest(
            question="What approach?",
            context="Migration",
        )
        request_id = await tool.ask(request, session_id="session-123")

        response = HumanExpertResponse(
            answer="Use approach A",
            answered_by="user@example.com",
        )
        await tool.respond(request_id, response)

        stored = tool.get_response(request_id)
        assert stored is response


@pytest.mark.unit
@pytest.mark.xdist_group(name="request_status_enum")
class TestRequestStatusEnum:
    """Tests for RequestStatus enum."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_request_status_exists(self) -> None:
        """Test RequestStatus enum exists."""
        from mcp_server_langgraph.hitl.human_expert import RequestStatus

        assert RequestStatus is not None

    def test_request_status_has_pending(self) -> None:
        """Test RequestStatus has PENDING value."""
        from mcp_server_langgraph.hitl.human_expert import RequestStatus

        assert hasattr(RequestStatus, "PENDING")
        assert RequestStatus.PENDING.value == "pending"

    def test_request_status_has_answered(self) -> None:
        """Test RequestStatus has ANSWERED value."""
        from mcp_server_langgraph.hitl.human_expert import RequestStatus

        assert hasattr(RequestStatus, "ANSWERED")
        assert RequestStatus.ANSWERED.value == "answered"

    def test_request_status_has_timeout(self) -> None:
        """Test RequestStatus has TIMEOUT value."""
        from mcp_server_langgraph.hitl.human_expert import RequestStatus

        assert hasattr(RequestStatus, "TIMEOUT")
        assert RequestStatus.TIMEOUT.value == "timeout"

    def test_request_status_has_cancelled(self) -> None:
        """Test RequestStatus has CANCELLED value."""
        from mcp_server_langgraph.hitl.human_expert import RequestStatus

        assert hasattr(RequestStatus, "CANCELLED")
        assert RequestStatus.CANCELLED.value == "cancelled"


@pytest.mark.unit
@pytest.mark.xdist_group(name="human_expert_tool_pending")
class TestHumanExpertToolPending:
    """Tests for HumanExpertTool pending request management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_pending_returns_pending_requests(self) -> None:
        """Test list_pending returns only pending requests."""
        from mcp_server_langgraph.hitl.human_expert import (
            HumanExpertRequest,
            HumanExpertTool,
        )

        tool = HumanExpertTool()
        request1 = HumanExpertRequest(question="Q1?", context="C1")
        request2 = HumanExpertRequest(question="Q2?", context="C2")

        await tool.ask(request1, session_id="session-A")
        await tool.ask(request2, session_id="session-A")

        pending = tool.list_pending("session-A")

        assert len(pending) == 2

    @pytest.mark.asyncio
    async def test_list_pending_excludes_answered(self) -> None:
        """Test list_pending excludes answered requests."""
        from mcp_server_langgraph.hitl.human_expert import (
            HumanExpertRequest,
            HumanExpertResponse,
            HumanExpertTool,
        )

        tool = HumanExpertTool()
        request1 = HumanExpertRequest(question="Q1?", context="C1")
        request2 = HumanExpertRequest(question="Q2?", context="C2")

        id1 = await tool.ask(request1, session_id="session-A")
        await tool.ask(request2, session_id="session-A")

        # Answer first request
        response = HumanExpertResponse(answer="A1", answered_by="user")
        await tool.respond(id1, response)

        pending = tool.list_pending("session-A")

        assert len(pending) == 1
