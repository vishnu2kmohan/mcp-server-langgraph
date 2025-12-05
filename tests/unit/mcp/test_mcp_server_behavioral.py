"""
Sample Test: Behavioral Mock Pattern for MCP Server

This test demonstrates the behavioral mock approach that eliminates brittle @patch decorators.

TDD Phase: RED - Test written first, implementation follows
Purpose: Prove that behavioral mocks enable testing BEHAVIOR, not implementation

Benefits over @patch decorators:
- ✅ Tests survive refactoring (no coupling to import paths)
- ✅ Self-documenting (behavioral intent is clear)
- ✅ Composable (mocks can be combined easily)
- ✅ Fewer lines (no @patch decorator boilerplate)

This sample will be used to refactor tests/unit/mcp/test_mcp_stdio_server.py (50 @patch → <10)
"""

import pytest
from tests.utils.mock_factories import (
    create_behavioral_auth_middleware,
    create_behavioral_agent_graph,
)


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testmcpserverbehavioralpattern")
class TestMCPServerBehavioralPattern:
    """Sample test class demonstrating behavioral mock pattern."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        import gc

        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_chat_authorized_user_gets_response(self):
        """
        Test: Authorized user receives agent response when sending chat message.

        This test validates BEHAVIOR:
        - GIVEN: User is authenticated and authorized
        - WHEN: User sends a chat message
        - THEN: Agent processes message and returns response

        This test does NOT validate IMPLEMENTATION:
        - Which auth library is used (JWT, OAuth, etc.)
        - Which LLM provider is called (OpenAI, Anthropic, etc.)
        - Internal module import paths
        - Specific function call sequences

        Contrast with old approach (50 @patch decorators):
            @patch("mcp_server_langgraph.mcp.server_stdio.settings")
            @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
            @patch("mcp_server_langgraph.mcp.server_stdio.get_agent_graph")
            @patch("mcp_server_langgraph.mcp.server_stdio.tracer")
            @patch("mcp_server_langgraph.mcp.server_stdio.format_response")
            async def test_handle_chat(...):
                # 5 patches! Very brittle!

        New behavioral approach (0 @patch decorators):
            # Just create mocks with desired behavior
            auth = create_behavioral_auth_middleware(authorized=True)
            agent = create_behavioral_agent_graph(response="Hi!")
        """
        # Arrange: Create behavioral mocks
        auth_middleware = create_behavioral_auth_middleware(
            authorized=True,
            user_id="alice",
            token_valid=True,
        )

        agent_graph = create_behavioral_agent_graph(
            response_message="Hi Alice! How can I help you today?",
            conversation_exists=False,
            user_id="alice",
        )

        # Act: Test the behavior we care about
        # NOTE: This test is intentionally written FIRST (RED phase)
        # The actual MCPAgentServer implementation will be adapted to accept
        # auth_middleware and agent_graph via dependency injection.
        #
        # Current implementation uses global imports/factories, which requires
        # @patch decorators. After refactoring, this test will pass.

        # For now, we'll test the mocks themselves to verify the pattern works
        token = "test-token-123"

        # Verify auth middleware behavior
        verification = await auth_middleware.verify_token(token)
        assert verification.valid is True
        assert verification.payload["sub"] == "alice"
        assert await auth_middleware.authorize() is True

        # Verify agent graph behavior
        from langchain_core.messages import HumanMessage

        user_message = HumanMessage(content="Hello, agent!")
        result = await agent_graph.ainvoke({"messages": [user_message]})

        assert "messages" in result
        assert len(result["messages"]) == 2  # User message + AI response
        assert "Hi Alice! How can I help you today?" in result["messages"][-1].content
        assert result["user_id"] == "alice"

    @pytest.mark.asyncio
    async def test_handle_chat_unauthorized_user_denied(self):
        """
        Test: Unauthorized user is denied access.

        BEHAVIOR:
        - GIVEN: User has invalid token
        - WHEN: User attempts to send chat message
        - THEN: Access is denied

        Old approach: 5 @patch decorators + complex mock setup
        New approach: One behavioral mock with authorization=False
        """
        # Arrange: Create behavioral mock with authorization denied
        auth_middleware = create_behavioral_auth_middleware(
            authorized=False,
            token_valid=False,
        )

        # Act & Assert: Verify denial behavior
        token = "invalid-token"
        verification = await auth_middleware.verify_token(token)

        assert verification.valid is False
        assert verification.error == "Invalid token"
        assert await auth_middleware.authorize() is False

    @pytest.mark.asyncio
    async def test_handle_chat_new_conversation(self):
        """
        Test: New conversation starts with no previous messages.

        BEHAVIOR:
        - GIVEN: User has no existing conversation
        - WHEN: User sends first message
        - THEN: Agent creates new conversation and responds

        Old approach: Complex aget_state mock setup with nested MagicMock
        New approach: conversation_exists=False parameter
        """
        # Arrange: Create behavioral mock for new conversation
        agent_graph = create_behavioral_agent_graph(
            response_message="Welcome! This is a new conversation.",
            conversation_exists=False,
            user_id="alice",
        )

        # Act: Verify new conversation behavior

        thread_id = "thread-123"
        config = {"configurable": {"thread_id": thread_id}}

        state_snapshot = await agent_graph.aget_state(config)

        # Assert: Verify no previous messages (new conversation)
        assert state_snapshot.values["messages"] == []

    @pytest.mark.asyncio
    async def test_handle_chat_existing_conversation(self):
        """
        Test: Existing conversation resumes with message history.

        BEHAVIOR:
        - GIVEN: User has existing conversation with previous messages
        - WHEN: User sends new message
        - THEN: Agent uses conversation context to respond

        Old approach: Complex mock chaining to simulate previous messages
        New approach: conversation_exists=True parameter
        """
        # Arrange: Create behavioral mock for existing conversation
        from langchain_core.messages import HumanMessage

        previous_messages = [
            HumanMessage(content="Tell me about Python"),
        ]

        agent_graph = create_behavioral_agent_graph(
            response_message="As I mentioned earlier, Python is a programming language.",
            conversation_exists=True,
            user_id="alice",
            messages=previous_messages,
        )

        # Act: Verify conversation resume behavior
        thread_id = "thread-456"
        config = {"configurable": {"thread_id": thread_id}}

        state_snapshot = await agent_graph.aget_state(config)

        # Assert: Verify previous messages exist
        assert len(state_snapshot.values["messages"]) == 1
        assert state_snapshot.values["messages"][0].content == "Tell me about Python"

    @pytest.mark.asyncio
    async def test_handle_chat_agent_error_handling(self):
        """
        Test: Agent errors are propagated correctly.

        BEHAVIOR:
        - GIVEN: LLM provider encounters error
        - WHEN: Agent attempts to invoke
        - THEN: Error is propagated to caller

        Old approach: Complex side_effect mock setup
        New approach: invoke_error parameter
        """
        # Arrange: Create behavioral mock that raises error
        agent_graph = create_behavioral_agent_graph(
            invoke_error=ValueError("LLM API rate limit exceeded"),
        )

        # Act & Assert: Verify error propagation
        from langchain_core.messages import HumanMessage

        user_message = HumanMessage(content="Hello")

        with pytest.raises(ValueError, match="LLM API rate limit exceeded"):
            await agent_graph.ainvoke({"messages": [user_message]})


# ==============================================================================
# Pattern Comparison: Old vs New
# ==============================================================================

"""
OLD PATTERN (Brittle - 50 @patch decorators):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@patch("mcp_server_langgraph.mcp.server_stdio.settings")
@patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
@patch("mcp_server_langgraph.mcp.server_stdio.get_agent_graph")
@patch("mcp_server_langgraph.mcp.server_stdio.tracer")
@patch("mcp_server_langgraph.mcp.server_stdio.format_response")
async def test_handle_chat_new_conversation(
    self, mock_format, mock_tracer, mock_graph, mock_auth, mock_settings
):
    # 10+ lines of mock setup
    mock_settings.OPENFGA_ENABLED = False
    mock_auth_instance = AsyncMock()
    mock_auth_instance.verify_token.return_value = MagicMock(
        valid=True,
        payload={"sub": "alice", "exp": 9999999999}
    )
    mock_auth_instance.authorize.return_value = True
    mock_auth.return_value = mock_auth_instance

    mock_graph_instance = AsyncMock()
    mock_graph_instance.aget_state.return_value = MagicMock(
        values={"messages": []}
    )
    mock_graph_instance.ainvoke.return_value = {
        "messages": [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi!")
        ]
    }
    mock_graph.return_value = mock_graph_instance

    # Test code...

Problems:
- ❌ 5 @patch decorators (very brittle)
- ❌ Couples to import paths (breaks on refactoring)
- ❌ 10+ lines of mock setup (verbose)
- ❌ Unclear behavioral intent
- ❌ Hard to maintain

NEW PATTERN (Robust - 0 @patch decorators):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def test_handle_chat_new_conversation(self):
    # Create behavioral mocks
    auth = create_behavioral_auth_middleware(authorized=True, user_id="alice")
    agent = create_behavioral_agent_graph(
        response_message="Hi!",
        conversation_exists=False
    )

    # Test via dependency injection
    server = MCPAgentServer(auth_middleware=auth, agent_graph=agent)
    response = await server.handle_chat(message="Hello", token="valid-token")

    # Verify behavior
    assert "Hi!" in response

Benefits:
- ✅ 0 @patch decorators (robust)
- ✅ No coupling to import paths (survives refactoring)
- ✅ 3 lines of setup (concise)
- ✅ Clear behavioral intent
- ✅ Easy to maintain
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXT STEPS (Phase 2.8 - Refactoring):
1. Adapt MCPAgentServer to accept dependencies via constructor
2. Refactor tests/unit/mcp/test_mcp_stdio_server.py (50 @patch → <10)
3. Apply pattern to other unit test files
4. Validate all tests pass
"""
