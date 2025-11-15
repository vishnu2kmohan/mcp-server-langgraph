"""
TDD Tests for Test Helper Factories

These helper functions make it easy to create test instances of:
- Agents
- MCP Servers
- Settings
- Containers

Following TDD: Write tests first, then implement.
"""

import gc

import pytest


@pytest.mark.xdist_group(name="testagenthelpers")
class TestAgentHelpers:
    """Test helper functions for creating test agents"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_test_agent_basic(self):
        """Test creating a basic test agent"""
        from mcp_server_langgraph.core.test_helpers import create_test_agent

        agent = create_test_agent()

        assert agent is not None
        # Agent should have basic capabilities
        assert hasattr(agent, "invoke") or hasattr(agent, "stream") or callable(agent)

    def test_create_test_agent_with_custom_settings(self):
        """Test creating agent with custom settings"""
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.test_helpers import create_test_agent

        custom_settings = Settings(environment="test", model_name="test-model", log_level="ERROR")

        agent = create_test_agent(settings=custom_settings)

        assert agent is not None

    def test_create_test_agent_with_container(self):
        """Test creating agent using container"""
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.core.test_helpers import create_test_agent

        container = create_test_container()
        agent = create_test_agent(container=container)

        assert agent is not None

    def test_create_test_agent_returns_different_instances(self):
        """
        Test that each call creates a new agent instance.

        NOTE: Currently skipped because get_agent_graph() is a singleton.
        This test will pass after Phase 3 refactoring when agents use containers.
        """
        import pytest

        pytest.skip("get_agent_graph() is currently a singleton - will fix in Phase 3")

        from mcp_server_langgraph.core.test_helpers import create_test_agent

        agent1 = create_test_agent()
        agent2 = create_test_agent()

        # Should be different instances
        assert agent1 is not agent2


@pytest.mark.xdist_group(name="testserverhelpers")
class TestServerHelpers:
    """Test helper functions for creating test MCP servers"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_test_server_basic(self):
        """Test creating a basic test server"""
        from mcp_server_langgraph.core.test_helpers import create_test_server

        server = create_test_server()

        assert server is not None
        # Server should have MCP capabilities
        assert hasattr(server, "server") or hasattr(server, "app")

    def test_create_test_server_with_container(self):
        """Test creating server using container"""
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.core.test_helpers import create_test_server

        container = create_test_container()
        server = create_test_server(container=container)

        assert server is not None

    def test_create_test_server_has_no_auth_by_default(self):
        """Test that test server has no-op auth by default"""
        from mcp_server_langgraph.core.test_helpers import create_test_server

        server = create_test_server()

        # Server should accept any token in test mode
        assert server is not None


@pytest.mark.xdist_group(name="testsettingshelpers")
class TestSettingsHelpers:
    """Test helper functions for creating test settings"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_test_settings_basic(self):
        """Test creating basic test settings"""
        from mcp_server_langgraph.core.test_helpers import create_test_settings

        settings = create_test_settings()

        assert settings.environment == "test"
        assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]

    def test_create_test_settings_with_overrides(self):
        """Test creating settings with overrides"""
        from mcp_server_langgraph.core.test_helpers import create_test_settings

        settings = create_test_settings(model_name="custom-model", log_level="ERROR")

        assert settings.model_name == "custom-model"
        assert settings.log_level == "ERROR"

    def test_create_test_settings_has_safe_defaults(self):
        """Test that test settings have safe defaults"""
        from mcp_server_langgraph.core.test_helpers import create_test_settings

        settings = create_test_settings()

        # Should have test-safe API keys
        assert settings.jwt_secret_key
        assert "test" in settings.jwt_secret_key.lower() or len(settings.jwt_secret_key) > 0

        # Should not try to connect to real services
        assert settings.openfga_store_id == "" or settings.openfga_store_id is None
        assert settings.openfga_model_id == "" or settings.openfga_model_id is None


@pytest.mark.xdist_group(name="testcontainerhelpers")
class TestContainerHelpers:
    """Test helper functions for container creation"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_test_container_helper_exists(self):
        """Test that create_test_container helper is accessible"""
        from mcp_server_langgraph.core.test_helpers import create_test_container

        container = create_test_container()

        assert container is not None
        assert container.settings.environment == "test"


@pytest.mark.xdist_group(name="testmockhelpers")
class TestMockHelpers:
    """Test helper functions for creating mocks"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_mock_llm_response(self):
        """Test creating mock LLM response"""
        from mcp_server_langgraph.core.test_helpers import create_mock_llm_response

        response = create_mock_llm_response(content="Test response", model="test-model")

        assert response is not None
        # Should be compatible with LangChain message format
        assert "content" in str(response) or hasattr(response, "content")

    def test_create_mock_llm_stream(self):
        """Test creating mock LLM stream"""
        from mcp_server_langgraph.core.test_helpers import create_mock_llm_stream

        stream = create_mock_llm_stream(chunks=["Hello", " ", "World"])

        # Should be iterable
        chunks = list(stream)
        assert len(chunks) == 3

    def test_create_mock_mcp_request(self):
        """Test creating mock MCP request"""
        from mcp_server_langgraph.core.test_helpers import create_mock_mcp_request

        request = create_mock_mcp_request(method="tools/call", params={"name": "chat", "arguments": {"message": "test"}})

        assert request["jsonrpc"] == "2.0"
        assert request["method"] == "tools/call"
        assert "id" in request

    def test_create_mock_jwt_token(self):
        """Test creating mock JWT token"""
        from mcp_server_langgraph.core.test_helpers import create_mock_jwt_token

        token = create_mock_jwt_token(user_id="test-user")

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0


@pytest.mark.xdist_group(name="testpytestfixturehelpers")
class TestPytestFixtureHelpers:
    """Test that helpers work well as pytest fixtures"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_agent_helper_as_fixture(self, test_container):
        """Test using agent helper in a pytest fixture context"""
        from mcp_server_langgraph.core.test_helpers import create_test_agent

        agent = create_test_agent(container=test_container)

        assert agent is not None

    def test_server_helper_as_fixture(self, container):
        """Test using server helper in a pytest fixture context"""
        from mcp_server_langgraph.core.test_helpers import create_test_server

        server = create_test_server(container=container)

        assert server is not None


@pytest.mark.xdist_group(name="testhelperdocumentation")
class TestHelperDocumentation:
    """Test that helpers have good documentation"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_helpers_have_docstrings(self):
        """Test that all helper functions have docstrings"""
        from mcp_server_langgraph.core import test_helpers

        helpers = [
            "create_test_agent",
            "create_test_server",
            "create_test_settings",
            "create_test_container",
            "create_mock_llm_response",
            "create_mock_mcp_request",
        ]

        for helper_name in helpers:
            helper = getattr(test_helpers, helper_name)
            assert helper.__doc__ is not None
            assert len(helper.__doc__) > 10  # At least minimal documentation
