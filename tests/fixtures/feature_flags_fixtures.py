"""
Feature flags test fixtures.

Provides a shared MockFeatureFlags class for testing feature-gated functionality.
This ensures consistent behavior across all test modules that need to mock feature flags.

Usage:
    from tests.fixtures.feature_flags_fixtures import MockFeatureFlags

    @pytest.fixture(autouse=True)
    def mock_feature_flags(monkeypatch):
        mock_flags = MockFeatureFlags()
        ff_module = sys.modules["mcp_server_langgraph.core.feature_flags"]
        monkeypatch.setattr(ff_module, "feature_flags", mock_flags)
"""

from __future__ import annotations


class MockFeatureFlags:
    """Mock feature flags for testing.

    This class mimics the real FeatureFlags behavior while allowing
    tests to control feature flag values. By default, is_test_mode=True
    which bypasses all feature checks (matching the real FF_TEST_MODE behavior).

    Attributes:
        is_test_mode: When True, all feature checks are bypassed.
        All feature flags default to False unless explicitly set.

    Example:
        # Create with defaults (test mode enabled)
        mock_flags = MockFeatureFlags()

        # Create with specific flags enabled
        mock_flags = MockFeatureFlags(
            enable_multi_agent_orchestration=True,
            enable_agentic_memory=True,
        )

        # Test feature flag blocking
        mock_flags.is_test_mode = False
        mock_flags.enable_skills_system = False
        # Now require_feature("enable_skills_system") will raise FeatureDisabledError
    """

    def __init__(
        self,
        *,
        # Test mode
        is_test_mode: bool = True,
        # Multi-agent flags
        enable_multi_agent_orchestration: bool = False,
        enable_agentic_memory: bool = False,
        enable_sdk_agent_definition: bool = False,
        max_subagents: int = 10,
        # Model capabilities routing (Phase 1)
        enable_model_capabilities_routing: bool = True,
        # Cost tracking flags
        enable_cost_tracking: bool = False,
        orchestration_cost_limit: float = 0.50,
        session_cost_limit: float = 5.00,
        cost_alert_thresholds: list[float] | None = None,
        # Thinking budget flags
        enable_thinking_budget: bool = False,
        default_thinking_level: str = "medium",
        # Dynamic context splitting flags
        enable_dynamic_context_splitting: bool = False,
        context_split_threshold: float = 0.8,
        # Orchestrator resilience flags (Phase 10)
        enable_orchestrator_resilience: bool = True,
        orchestrator_timeout_seconds: int = 300,
        orchestrator_max_concurrent: int = 5,
        orchestrator_circuit_breaker_threshold: int = 3,
        # AI UX Service Migration (Phase 11)
        enable_orchestrated_ai_ux: bool = False,
        # Alert Recommendations Migration (Phase 12)
        enable_orchestrated_alert_analysis: bool = False,
        # Execution flags
        enable_programmatic_tools: bool = False,
        # Skills flags
        enable_skills_system: bool = False,
        enable_skills_marketplace: bool = False,
        # Privacy flags
        enable_pii_tokenization: bool = False,
        # Tool flags
        enable_tool_examples: bool = True,
        enable_think_tool: bool = True,
        enable_defer_loading: bool = False,
        # Conversation/suggestion flags (AI API)
        enable_conversation_history_validation: bool = True,
        max_conversation_history_messages: int = 5,
        max_input_length: int = 10000,
        enable_llm_suggestions: bool = True,
        enable_suggestion_quality_tracking: bool = True,
        # HITL (Human-in-the-Loop) flags
        enable_agent_hitl: bool = True,
        agent_hitl_confidence_threshold: float = 0.7,
        enable_agent_hitl_push_notifications: bool = True,
        # AI Explanation flags (Plan Section 10.2)
        enable_ai_explanations: bool = False,
        ai_explanation_strategy: str = "lazy",
        ai_explanation_model: str = "gpt-4o-mini",
        # Orchestration MCP flags (Plan Section 10.4)
        enable_orchestration_mcp_tools: bool = False,
        enable_orchestration_mcp_resources: bool = False,
        # Hooks MCP extension (Plan Section 10.5)
        enable_hooks_mcp_extension: bool = False,
        # Rate limiting flags
        enable_distributed_rate_limiting: bool = False,
    ) -> None:
        """Initialize MockFeatureFlags with configurable defaults.

        Args:
            is_test_mode: When True, bypasses all feature checks (default: True)
            enable_multi_agent_orchestration: Enable multi-agent features
            enable_agentic_memory: Enable notes and checkpoints
            enable_sdk_agent_definition: Enable SDK AgentDefinition support
            max_subagents: Maximum number of subagents (default: 10)
            enable_cost_tracking: Enable cost tracking for orchestration
            orchestration_cost_limit: Cost limit per orchestration (default: 0.50)
            session_cost_limit: Cost limit per session (default: 5.00)
            cost_alert_thresholds: Thresholds for cost alerts (default: [0.5, 0.75, 0.9])
            enable_thinking_budget: Enable thinking budget management
            default_thinking_level: Default thinking level (default: "medium")
            enable_dynamic_context_splitting: Enable dynamic context splitting
            context_split_threshold: Threshold for context splitting (default: 0.8)
            enable_programmatic_tools: Enable sandbox tool calling
            enable_skills_system: Enable skills loading
            enable_skills_marketplace: Enable marketplace integration
            enable_pii_tokenization: Enable PII detection/tokenization
            enable_tool_examples: Enable tool input examples
            enable_think_tool: Enable think tool for reasoning
            enable_defer_loading: Enable deferred tool loading
            enable_conversation_history_validation: Enable history validation
            max_conversation_history_messages: Max history messages
            max_input_length: Max input length
            enable_llm_suggestions: Enable LLM-powered suggestions
            enable_suggestion_quality_tracking: Enable quality tracking
        """
        # Test mode flag - when True, bypasses all feature checks
        self.is_test_mode = is_test_mode

        # Multi-agent flags
        self.enable_multi_agent_orchestration = enable_multi_agent_orchestration
        self.enable_agentic_memory = enable_agentic_memory
        self.enable_sdk_agent_definition = enable_sdk_agent_definition
        self.max_subagents = max_subagents

        # Model capabilities routing (Phase 1)
        self.enable_model_capabilities_routing = enable_model_capabilities_routing

        # Cost tracking flags
        self.enable_cost_tracking = enable_cost_tracking
        self.orchestration_cost_limit = orchestration_cost_limit
        self.session_cost_limit = session_cost_limit
        self.cost_alert_thresholds = cost_alert_thresholds or [0.5, 0.75, 0.9]

        # Thinking budget flags
        self.enable_thinking_budget = enable_thinking_budget
        self.default_thinking_level = default_thinking_level

        # Dynamic context splitting flags
        self.enable_dynamic_context_splitting = enable_dynamic_context_splitting
        self.context_split_threshold = context_split_threshold

        # Orchestrator resilience flags (Phase 10)
        self.enable_orchestrator_resilience = enable_orchestrator_resilience
        self.orchestrator_timeout_seconds = orchestrator_timeout_seconds
        self.orchestrator_max_concurrent = orchestrator_max_concurrent
        self.orchestrator_circuit_breaker_threshold = orchestrator_circuit_breaker_threshold

        # AI UX Service Migration (Phase 11)
        self.enable_orchestrated_ai_ux = enable_orchestrated_ai_ux

        # Alert Recommendations Migration (Phase 12)
        self.enable_orchestrated_alert_analysis = enable_orchestrated_alert_analysis

        # Execution flags
        self.enable_programmatic_tools = enable_programmatic_tools

        # Skills flags
        self.enable_skills_system = enable_skills_system
        self.enable_skills_marketplace = enable_skills_marketplace

        # Privacy flags
        self.enable_pii_tokenization = enable_pii_tokenization

        # Tool flags
        self.enable_tool_examples = enable_tool_examples
        self.enable_think_tool = enable_think_tool
        self.enable_defer_loading = enable_defer_loading

        # Conversation/suggestion flags (AI API)
        self.enable_conversation_history_validation = enable_conversation_history_validation
        self.max_conversation_history_messages = max_conversation_history_messages
        self.max_input_length = max_input_length
        self.enable_llm_suggestions = enable_llm_suggestions
        self.enable_suggestion_quality_tracking = enable_suggestion_quality_tracking

        # HITL (Human-in-the-Loop) flags
        self.enable_agent_hitl = enable_agent_hitl
        self.agent_hitl_confidence_threshold = agent_hitl_confidence_threshold
        self.enable_agent_hitl_push_notifications = enable_agent_hitl_push_notifications

        # AI Explanation flags (Plan Section 10.2)
        self.enable_ai_explanations = enable_ai_explanations
        self.ai_explanation_strategy = ai_explanation_strategy
        self.ai_explanation_model = ai_explanation_model

        # Orchestration MCP flags (Plan Section 10.4)
        self.enable_orchestration_mcp_tools = enable_orchestration_mcp_tools
        self.enable_orchestration_mcp_resources = enable_orchestration_mcp_resources

        # Hooks MCP extension (Plan Section 10.5)
        self.enable_hooks_mcp_extension = enable_hooks_mcp_extension

        # Rate limiting flags
        self.enable_distributed_rate_limiting = enable_distributed_rate_limiting

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled.

        Args:
            feature_name: Name of the feature flag attribute

        Returns:
            True if the feature is enabled, False otherwise
        """
        return getattr(self, feature_name, False)

    def require_feature(self, feature_name: str, display_name: str | None = None) -> None:
        """Require a feature to be enabled, raising FeatureDisabledError if not.

        Mimics the real FeatureFlags.require_feature behavior, including
        test mode bypass.

        Args:
            feature_name: Name of the feature flag attribute
            display_name: Human-readable feature name for error message

        Raises:
            FeatureDisabledError: If feature is disabled and not in test mode
        """
        # Test mode bypasses all feature flag checks
        if self.is_test_mode:
            return

        if not self.is_feature_enabled(feature_name):
            from mcp_server_langgraph.core.exceptions import FeatureDisabledError

            raise FeatureDisabledError(
                feature_name=display_name or feature_name.replace("enable_", "").replace("_", " ").title(),
                flag_name=f"FF_{feature_name.upper()}",
            )

    def get_feature_value(self, feature_name: str, default: object = None) -> object:
        """Get feature flag value with fallback.

        Args:
            feature_name: Name of the feature flag attribute
            default: Default value if attribute not found

        Returns:
            Feature flag value or default
        """
        return getattr(self, feature_name, default)
