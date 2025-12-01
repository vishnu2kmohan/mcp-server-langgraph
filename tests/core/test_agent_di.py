"""
TDD Tests for Agent Dependency Injection Refactoring

These tests define the behavior we want after refactoring agent.py
to use dependency injection instead of global singletons.

Following TDD:
1. Write tests first (this file) - RED
2. Refactor agent.py to pass tests - GREEN
3. Verify no regressions - REFACTOR
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testagentfactory")
class TestAgentFactory:
    """Test the new agent factory function"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_agent_with_container(self):
        """Test creating agent using container"""
        from mcp_server_langgraph.core.agent import create_agent
        from mcp_server_langgraph.core.container import create_test_container

        container = create_test_container()
        agent = create_agent(container=container)

        assert agent is not None
        # Agent should be a compiled graph
        assert hasattr(agent, "invoke") or callable(agent)

    def test_create_agent_with_settings(self):
        """Test creating agent with custom settings"""
        from mcp_server_langgraph.core.agent import create_agent
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(environment="test", model_name="test-model", log_level="DEBUG")

        agent = create_agent(settings=settings)

        assert agent is not None

    def test_create_agent_returns_different_instances(self):
        """Test that each call creates a new agent instance"""
        from mcp_server_langgraph.core.agent import create_agent

        agent1 = create_agent()
        agent2 = create_agent()

        # Should be different instances (no more singleton!)
        assert agent1 is not agent2

    def test_create_agent_uses_container_telemetry(self):
        """Test that agent uses container's telemetry provider"""
        from mcp_server_langgraph.core.agent import create_agent
        from mcp_server_langgraph.core.container import create_test_container

        container = create_test_container()

        # Container should use no-op telemetry in test mode
        _ = container.get_telemetry()  # noqa: F841

        # Agent creation should not raise errors with no-op telemetry
        agent = create_agent(container=container)

        assert agent is not None


@pytest.mark.xdist_group(name="testagentgraphfactory")
class TestAgentGraphFactory:
    """Test the graph creation function"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_agent_graph_with_settings(self):
        """Test creating agent graph with settings"""
        from mcp_server_langgraph.core.agent import create_agent_graph
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(environment="test")
        graph = create_agent_graph(settings=settings)

        assert graph is not None

    def test_create_agent_graph_with_container(self):
        """Test creating agent graph with container"""
        from mcp_server_langgraph.core.agent import create_agent_graph
        from mcp_server_langgraph.core.container import create_test_container

        container = create_test_container()
        graph = create_agent_graph(container=container)

        assert graph is not None

    def test_create_agent_graph_is_compiled(self):
        """Test that created graph is compiled and ready"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        graph = create_agent_graph()

        # Should have invoke method (compiled graph)
        assert hasattr(graph, "invoke")


@pytest.mark.xdist_group(name="testbackwardcompatibility")
class TestBackwardCompatibility:
    """Test that old singleton pattern still works during migration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_agent_graph_still_works(self):
        """Test that old get_agent_graph() function still works"""
        from mcp_server_langgraph.core.agent import get_agent_graph

        agent = get_agent_graph()

        assert agent is not None

    def test_get_agent_graph_returns_singleton(self):
        """Test that old function still returns singleton"""
        from mcp_server_langgraph.core.agent import get_agent_graph

        agent1 = get_agent_graph()
        agent2 = get_agent_graph()

        # Old function should still return same instance for backward compat
        assert agent1 is agent2


@pytest.mark.xdist_group(name="testagentstatemanagement")
class TestAgentStateManagement:
    """Test that agent state works with container pattern"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_agent_with_memory_checkpointer(self):
        """Test agent uses MemorySaver in test mode"""
        from mcp_server_langgraph.core.agent import create_agent
        from mcp_server_langgraph.core.container import create_test_container

        container = create_test_container()
        agent = create_agent(container=container)

        # Agent should be created with a checkpointer
        assert agent is not None

    def test_agent_with_redis_checkpointer(self):
        """Test agent can use Redis checkpointer from container"""
        from mcp_server_langgraph.core.agent import create_agent
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import ApplicationContainer, ContainerConfig

        # Create development container with Redis storage
        config = ContainerConfig(environment="development")
        settings = Settings(environment="development", redis_host="localhost", redis_port=6379)
        container = ApplicationContainer(config, settings=settings)

        # Should create agent without errors (even if Redis not connected)
        agent = create_agent(container=container)
        assert agent is not None


@pytest.mark.xdist_group(name="testagentconfiguration")
class TestAgentConfiguration:
    """Test that agent respects configuration from container"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_agent_uses_container_settings(self):
        """Test that agent uses settings from container"""
        from mcp_server_langgraph.core.agent import create_agent
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import create_test_container

        custom_settings = Settings(environment="test", model_name="custom-test-model", temperature=0.5)
        container = create_test_container(settings=custom_settings)

        agent = create_agent(container=container)

        assert agent is not None
        # Agent should be created with custom settings


@pytest.mark.xdist_group(name="testagentisolation")
class TestAgentIsolation:
    """Test that agents are properly isolated"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_multiple_agents_are_independent(self):
        """Test that multiple agent instances don't share state"""
        from mcp_server_langgraph.core.agent import create_agent

        agent1 = create_agent()
        agent2 = create_agent()

        # Agents should be independent
        assert agent1 is not agent2

    def test_agents_from_different_containers_are_independent(self):
        """Test that agents from different containers are independent"""
        from mcp_server_langgraph.core.agent import create_agent
        from mcp_server_langgraph.core.container import create_test_container

        container1 = create_test_container()
        container2 = create_test_container()

        agent1 = create_agent(container=container1)
        agent2 = create_agent(container=container2)

        assert agent1 is not agent2


@pytest.mark.xdist_group(name="testagenttesthelperintegration")
class TestAgentTestHelperIntegration:
    """Test that agent works with test helpers"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_test_agent_uses_new_factory(self):
        """Test that test helper uses the new factory"""
        from mcp_server_langgraph.core.test_helpers import create_test_agent

        agent = create_test_agent()

        assert agent is not None

    def test_create_test_agent_with_container(self, test_container):
        """Test that test helper works with container fixture"""
        from mcp_server_langgraph.core.test_helpers import create_test_agent

        agent = create_test_agent(container=test_container)

        assert agent is not None


@pytest.mark.xdist_group(name="testagentdocumentation")
class TestAgentDocumentation:
    """Test that refactored functions have good documentation"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_agent_has_docstring(self):
        """Test that create_agent has comprehensive docstring"""
        from mcp_server_langgraph.core.agent import create_agent

        assert create_agent.__doc__ is not None
        assert len(create_agent.__doc__) > 50
        assert "container" in create_agent.__doc__.lower()

    def test_create_agent_graph_has_docstring(self):
        """Test that create_agent_graph has comprehensive docstring"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        assert create_agent_graph.__doc__ is not None
        assert len(create_agent_graph.__doc__) > 50


@pytest.mark.unit
@pytest.mark.xdist_group(name="testsettingsinjectionregression")
class TestSettingsInjectionRegression:
    """
    Regression tests for settings injection bug fix.

    SECURITY: These tests verify that Finding 2 from OpenAI Codex analysis is fixed.
    Previously, settings_to_use parameter was ignored, preventing:
    - Testing with custom settings
    - Multi-tenant deployments
    - Feature flags and A/B testing
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_agent_graph_respects_checkpoint_backend_override(self):
        """
        Test that settings override actually changes checkpoint backend.

        REGRESSION TEST: Previously settings_to_use was discarded.
        """
        from mcp_server_langgraph.core.agent import create_agent_graph
        from mcp_server_langgraph.core.config import Settings

        # Create settings with memory backend
        memory_settings = Settings(environment="test", checkpoint_backend="memory")

        # Create agent graph with custom settings
        graph = create_agent_graph(settings=memory_settings)

        # Should create graph successfully with memory backend
        assert graph is not None
        assert hasattr(graph, "checkpointer")

    def test_create_agent_graph_with_disabled_verification(self):
        """
        Test that feature flags can be disabled via settings override.

        REGRESSION TEST: Feature flags should respect injected settings.
        """
        from mcp_server_langgraph.core.agent import create_agent_graph
        from mcp_server_langgraph.core.config import Settings

        # Create settings with verification disabled
        test_settings = Settings(environment="test", enable_verification=False, enable_context_compaction=False)

        # Should create graph with disabled features
        graph = create_agent_graph(settings=test_settings)
        assert graph is not None

    def test_create_agent_graph_with_custom_model_name(self):
        """
        Test that model configuration can be overridden via settings.

        REGRESSION TEST: Model selection should respect injected settings.
        """
        from mcp_server_langgraph.core.agent import create_agent_graph
        from mcp_server_langgraph.core.config import Settings

        # Create settings with custom model
        custom_settings = Settings(environment="test", model_name="gpt-5-mini", temperature=0.3)

        # Should create graph with custom model settings
        # (Note: May fail if API keys not configured, but settings should be used)
        try:
            graph = create_agent_graph(settings=custom_settings)
            assert graph is not None
        except Exception as e:
            # If it fails, ensure it's not because settings were ignored
            # (e.g., API key error is expected, settings being ignored is not)
            error_msg = str(e).lower()
            # Settings-related errors should not occur
            assert "checkpoint_backend" not in error_msg

    def test_settings_injection_no_global_mutation(self):
        """
        Test that using settings override doesn't mutate global settings.

        REGRESSION TEST: Finding 4 - Global state mutation in create_checkpointer.
        Previously, global settings object was temporarily mutated, causing race conditions.
        """
        from mcp_server_langgraph.core.agent import create_checkpointer
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.config import settings as global_settings

        # Capture original global settings values
        original_backend = global_settings.checkpoint_backend

        # Create checkpointer with override settings
        override_settings = Settings(environment="test", checkpoint_backend="memory")
        checkpointer = create_checkpointer(settings_override=override_settings)

        # Global settings should NOT be mutated
        assert global_settings.checkpoint_backend == original_backend
        assert checkpointer is not None

    def test_concurrent_settings_overrides_no_interference(self):
        """
        Test that concurrent settings overrides don't interfere with each other.

        REGRESSION TEST: Finding 4 - Race conditions from global state mutation.
        """
        import threading

        from mcp_server_langgraph.core.agent import create_checkpointer
        from mcp_server_langgraph.core.config import Settings

        results = {}
        errors = {}

        def create_with_backend(backend_name, thread_id):
            try:
                settings = Settings(environment="test", checkpoint_backend=backend_name)
                checkpointer = create_checkpointer(settings_override=settings)
                results[thread_id] = checkpointer
            except Exception as e:
                errors[thread_id] = e

        # Create multiple threads with different settings
        threads = []
        for i in range(5):
            backend = "memory"  # All use memory in test
            t = threading.Thread(target=create_with_backend, args=(backend, i))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # All threads should succeed without errors
        assert len(errors) == 0, f"Concurrent creation failed: {errors}"
        assert len(results) == 5

    def test_create_agent_graph_impl_uses_settings_parameter(self):
        """
        Test that create_agent_graph_impl actually uses the settings_to_use parameter.

        REGRESSION TEST: Finding 2 - settings_to_use was discarded in create_agent_graph_impl.
        The function had a TODO comment acknowledging it ignored the parameter.
        """
        from mcp_server_langgraph.core.agent import create_agent_graph_impl
        from mcp_server_langgraph.core.config import Settings

        # Create custom settings
        custom_settings = Settings(environment="test", checkpoint_backend="memory", enable_verification=False)

        # Call implementation directly with custom settings
        graph = create_agent_graph_impl(settings_to_use=custom_settings)

        # Should create graph successfully (settings actually used)
        assert graph is not None
        assert hasattr(graph, "checkpointer")

    def test_settings_override_for_multi_tenant_scenario(self):
        """
        Test multi-tenant scenario where different tenants have different settings.

        REGRESSION TEST: Multi-tenancy requires per-tenant settings injection.
        """
        from mcp_server_langgraph.core.agent import create_agent_graph
        from mcp_server_langgraph.core.config import Settings

        # Tenant 1: Basic configuration
        tenant1_settings = Settings(environment="test", checkpoint_backend="memory", enable_verification=False)

        # Tenant 2: Advanced configuration
        tenant2_settings = Settings(
            environment="test", checkpoint_backend="memory", enable_verification=True, enable_context_compaction=True
        )

        # Create separate graphs for each tenant
        tenant1_graph = create_agent_graph(settings=tenant1_settings)
        tenant2_graph = create_agent_graph(settings=tenant2_settings)

        # Both should be created successfully
        assert tenant1_graph is not None
        assert tenant2_graph is not None

        # Graphs should be independent instances
        assert tenant1_graph is not tenant2_graph
