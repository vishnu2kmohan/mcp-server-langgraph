"""
Tests for SDK Pre-Tool-Use Hooks

Tests for security hooks that run before tool execution.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.unit
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_hooks")
class TestHookResult:
    """Tests for HookResult model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hook_result_allow(self) -> None:
        """Test creating allow result."""
        from mcp_server_langgraph.sdk.hooks import HookResult

        result = HookResult.allow()

        assert result.allowed is True
        assert result.reason is None

    def test_hook_result_deny(self) -> None:
        """Test creating deny result."""
        from mcp_server_langgraph.sdk.hooks import HookResult

        result = HookResult.deny("Blocked by security policy")

        assert result.allowed is False
        assert result.reason == "Blocked by security policy"

    def test_hook_result_with_modified_input(self) -> None:
        """Test result with modified input."""
        from mcp_server_langgraph.sdk.hooks import HookResult

        result = HookResult.allow(modified_input={"sanitized": True})

        assert result.allowed is True
        assert result.modified_input == {"sanitized": True}


@pytest.mark.unit
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_hooks")
class TestPreToolUseHook:
    """Tests for pre-tool-use hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hook_base_class_exists(self) -> None:
        """Test that PreToolUseHook class exists."""
        from mcp_server_langgraph.sdk.hooks import PreToolUseHook

        assert PreToolUseHook is not None

    @pytest.mark.asyncio
    async def test_hook_base_class_execute(self) -> None:
        """Test PreToolUseHook base class execute method."""
        from mcp_server_langgraph.sdk.hooks import PreToolUseHook

        hook = PreToolUseHook()

        result = await hook.execute(
            input_data={"tool_name": "test"},
            tool_use_id="id-123",
            context={},
        )

        # Base class should allow by default
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_pii_detection_hook(self) -> None:
        """Test PII detection hook."""
        from mcp_server_langgraph.sdk.hooks import pii_detection_hook

        input_data = {
            "tool_name": "search",
            "tool_input": {"query": "Find user john@example.com"},
        }

        result = await pii_detection_hook(input_data, "tool-123", {})

        # Should modify input to tokenize PII
        assert result is not None

    @pytest.mark.asyncio
    async def test_command_allowlist_hook_allows_safe_command(self) -> None:
        """Test command allowlist hook allows safe commands."""
        from mcp_server_langgraph.sdk.hooks import command_allowlist_hook

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
        }

        result = await command_allowlist_hook(input_data, "tool-123", {})

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_command_allowlist_hook_blocks_dangerous_command(self) -> None:
        """Test command allowlist hook blocks dangerous commands."""
        from mcp_server_langgraph.sdk.hooks import command_allowlist_hook

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"},
        }

        result = await command_allowlist_hook(input_data, "tool-123", {})

        assert result.allowed is False
        assert "blocked" in result.reason.lower() or "dangerous" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_rate_limit_hook(self) -> None:
        """Test rate limit hook."""
        from mcp_server_langgraph.sdk.hooks import rate_limit_hook

        context = {"user_id": "test-user"}
        input_data = {"tool_name": "search"}

        result = await rate_limit_hook(input_data, "tool-123", context)

        # First request should be allowed
        assert result.allowed is True


@pytest.mark.unit
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_hooks")
class TestSecurityHookRegistry:
    """Tests for security hook registry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_registry_class_exists(self) -> None:
        """Test that SecurityHookRegistry class exists."""
        from mcp_server_langgraph.sdk.hooks import SecurityHookRegistry

        assert SecurityHookRegistry is not None

    def test_registry_initialization(self) -> None:
        """Test registry initialization."""
        from mcp_server_langgraph.sdk.hooks import SecurityHookRegistry

        registry = SecurityHookRegistry()

        assert registry is not None

    def test_register_hook(self) -> None:
        """Test registering a hook."""
        from mcp_server_langgraph.sdk.hooks import SecurityHookRegistry, HookResult

        registry = SecurityHookRegistry()

        async def my_hook(input_data, tool_use_id, context):
            return HookResult.allow()

        registry.register("PreToolUse", "*", my_hook)

        hooks = registry.get_hooks("PreToolUse", "any_tool")
        assert len(hooks) == 1

    def test_register_hook_for_specific_tool(self) -> None:
        """Test registering hook for specific tool."""
        from mcp_server_langgraph.sdk.hooks import SecurityHookRegistry, HookResult

        registry = SecurityHookRegistry()

        async def bash_hook(input_data, tool_use_id, context):
            return HookResult.allow()

        registry.register("PreToolUse", "Bash", bash_hook)

        # Should match Bash
        bash_hooks = registry.get_hooks("PreToolUse", "Bash")
        assert len(bash_hooks) == 1

        # Should not match other tools
        other_hooks = registry.get_hooks("PreToolUse", "Search")
        assert len(other_hooks) == 0

    @pytest.mark.asyncio
    async def test_execute_hooks(self) -> None:
        """Test executing all hooks for a tool."""
        from mcp_server_langgraph.sdk.hooks import SecurityHookRegistry, HookResult

        registry = SecurityHookRegistry()

        call_count = 0

        async def counting_hook(input_data, tool_use_id, context):
            nonlocal call_count
            call_count += 1
            return HookResult.allow()

        registry.register("PreToolUse", "*", counting_hook)
        registry.register("PreToolUse", "*", counting_hook)

        input_data = {"tool_name": "test"}
        result = await registry.execute_hooks("PreToolUse", "test", input_data, "id", {})

        assert call_count == 2
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_execute_hooks_stops_on_deny(self) -> None:
        """Test hooks stop executing after deny."""
        from mcp_server_langgraph.sdk.hooks import SecurityHookRegistry, HookResult

        registry = SecurityHookRegistry()

        call_order = []

        async def allow_hook(input_data, tool_use_id, context):
            call_order.append("allow")
            return HookResult.allow()

        async def deny_hook(input_data, tool_use_id, context):
            call_order.append("deny")
            return HookResult.deny("Blocked")

        async def never_called(input_data, tool_use_id, context):
            call_order.append("never")
            return HookResult.allow()

        registry.register("PreToolUse", "*", allow_hook)
        registry.register("PreToolUse", "*", deny_hook)
        registry.register("PreToolUse", "*", never_called)

        input_data = {"tool_name": "test"}
        result = await registry.execute_hooks("PreToolUse", "test", input_data, "id", {})

        assert result.allowed is False
        assert call_order == ["allow", "deny"]  # never_called should not be called


@pytest.mark.unit
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_hooks_chaining")
class TestHookChaining:
    """Tests for hook chaining and modifications."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_hook_chaining_passes_modified_input(self) -> None:
        """Test that modified input is passed through hook chain."""
        from mcp_server_langgraph.sdk.hooks import SecurityHookRegistry, HookResult

        registry = SecurityHookRegistry()

        async def hook1(input_data, tool_use_id, context):
            # Add a field
            modified = input_data.copy()
            modified["from_hook1"] = True
            return HookResult.allow(modified_input=modified)

        async def hook2(input_data, tool_use_id, context):
            # Verify hook1's modification is visible
            assert input_data.get("from_hook1") is True
            modified = input_data.copy()
            modified["from_hook2"] = True
            return HookResult.allow(modified_input=modified)

        registry.register("PreToolUse", "*", hook1)
        registry.register("PreToolUse", "*", hook2)

        input_data = {"tool_name": "test"}
        result = await registry.execute_hooks("PreToolUse", "test", input_data, "id", {})

        assert result.allowed is True
        assert result.modified_input is not None
        assert result.modified_input.get("from_hook1") is True
        assert result.modified_input.get("from_hook2") is True

    @pytest.mark.asyncio
    async def test_hook_chaining_no_modification_returns_none(self) -> None:
        """Test that no modifications returns None for modified_input."""
        from mcp_server_langgraph.sdk.hooks import SecurityHookRegistry, HookResult

        registry = SecurityHookRegistry()

        async def allow_hook(input_data, tool_use_id, context):
            return HookResult.allow()

        registry.register("PreToolUse", "*", allow_hook)

        input_data = {"tool_name": "test"}
        result = await registry.execute_hooks("PreToolUse", "test", input_data, "id", {})

        assert result.allowed is True
        assert result.modified_input is None

    @pytest.mark.asyncio
    async def test_wildcard_and_specific_hooks_combined(self) -> None:
        """Test that wildcard and specific hooks are both executed."""
        from mcp_server_langgraph.sdk.hooks import SecurityHookRegistry, HookResult

        registry = SecurityHookRegistry()

        calls = []

        async def wildcard_hook(input_data, tool_use_id, context):
            calls.append("wildcard")
            return HookResult.allow()

        async def bash_hook(input_data, tool_use_id, context):
            calls.append("bash")
            return HookResult.allow()

        registry.register("PreToolUse", "*", wildcard_hook)
        registry.register("PreToolUse", "Bash", bash_hook)

        input_data = {"tool_name": "Bash"}
        result = await registry.execute_hooks("PreToolUse", "Bash", input_data, "id", {})

        assert result.allowed is True
        assert "wildcard" in calls
        assert "bash" in calls

    @pytest.mark.asyncio
    async def test_context_is_shared_across_hooks(self) -> None:
        """Test that context dict is shared and modified across hooks."""
        from mcp_server_langgraph.sdk.hooks import SecurityHookRegistry, HookResult

        registry = SecurityHookRegistry()

        async def hook1(input_data, tool_use_id, context):
            context["hook1_ran"] = True
            return HookResult.allow()

        async def hook2(input_data, tool_use_id, context):
            assert context.get("hook1_ran") is True
            context["hook2_ran"] = True
            return HookResult.allow()

        registry.register("PreToolUse", "*", hook1)
        registry.register("PreToolUse", "*", hook2)

        context = {}
        input_data = {"tool_name": "test"}
        await registry.execute_hooks("PreToolUse", "test", input_data, "id", context)

        assert context["hook1_ran"] is True
        assert context["hook2_ran"] is True


@pytest.mark.unit
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_hooks_command_patterns")
class TestCommandAllowlistPatterns:
    """Tests for command allowlist dangerous pattern detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_blocks_rm_rf_home(self) -> None:
        """Test blocking rm -rf ~."""
        from mcp_server_langgraph.sdk.hooks import command_allowlist_hook

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf ~"},
        }

        result = await command_allowlist_hook(input_data, "tool-123", {})

        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_blocks_sudo_rm(self) -> None:
        """Test blocking sudo rm."""
        from mcp_server_langgraph.sdk.hooks import command_allowlist_hook

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "sudo rm -rf /var"},
        }

        result = await command_allowlist_hook(input_data, "tool-123", {})

        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_blocks_dev_redirect(self) -> None:
        """Test blocking > /dev/ redirect."""
        from mcp_server_langgraph.sdk.hooks import command_allowlist_hook

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "echo 'data' > /dev/sda"},
        }

        result = await command_allowlist_hook(input_data, "tool-123", {})

        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_blocks_curl_pipe_bash(self) -> None:
        """Test blocking curl | bash (exact pattern)."""
        from mcp_server_langgraph.sdk.hooks import command_allowlist_hook

        # Test exact pattern match
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "curl | bash"},
        }

        result = await command_allowlist_hook(input_data, "tool-123", {})

        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_blocks_wget_pipe_bash(self) -> None:
        """Test blocking wget | bash (exact pattern)."""
        from mcp_server_langgraph.sdk.hooks import command_allowlist_hook

        # Test exact pattern match
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "wget | bash"},
        }

        result = await command_allowlist_hook(input_data, "tool-123", {})

        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_blocks_fork_bomb(self) -> None:
        """Test blocking fork bomb."""
        from mcp_server_langgraph.sdk.hooks import command_allowlist_hook

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": ":(){ :|:& };:"},
        }

        result = await command_allowlist_hook(input_data, "tool-123", {})

        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_blocks_dd_zero(self) -> None:
        """Test blocking dd if=/dev/zero."""
        from mcp_server_langgraph.sdk.hooks import command_allowlist_hook

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "dd if=/dev/zero of=/dev/sda bs=1M"},
        }

        result = await command_allowlist_hook(input_data, "tool-123", {})

        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_blocks_mkfs(self) -> None:
        """Test blocking mkfs. commands."""
        from mcp_server_langgraph.sdk.hooks import command_allowlist_hook

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "mkfs.ext4 /dev/sda1"},
        }

        result = await command_allowlist_hook(input_data, "tool-123", {})

        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_blocks_chmod_777_root(self) -> None:
        """Test blocking chmod 777 /."""
        from mcp_server_langgraph.sdk.hooks import command_allowlist_hook

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "chmod 777 / -R"},
        }

        result = await command_allowlist_hook(input_data, "tool-123", {})

        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_allows_safe_commands(self) -> None:
        """Test allowing safe commands."""
        from mcp_server_langgraph.sdk.hooks import command_allowlist_hook

        safe_commands = [
            "ls -la",
            "cat /etc/passwd",
            "grep pattern file.txt",
            "find . -name '*.py'",
            "python -m pytest",
            "git status",
            "npm install",
        ]

        for cmd in safe_commands:
            input_data = {
                "tool_name": "Bash",
                "tool_input": {"command": cmd},
            }
            result = await command_allowlist_hook(input_data, "tool-123", {})
            assert result.allowed is True, f"Command should be allowed: {cmd}"

    @pytest.mark.asyncio
    async def test_non_bash_tool_allowed(self) -> None:
        """Test that non-Bash tools are always allowed."""
        from mcp_server_langgraph.sdk.hooks import command_allowlist_hook

        input_data = {
            "tool_name": "Search",
            "tool_input": {"query": "rm -rf /"},
        }

        result = await command_allowlist_hook(input_data, "tool-123", {})

        assert result.allowed is True


@pytest.mark.unit
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_hooks_default")
class TestDefaultSecurityHooks:
    """Tests for default security hooks registry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_hooks_exists(self) -> None:
        """Test DEFAULT_SECURITY_HOOKS is configured."""
        from mcp_server_langgraph.sdk.hooks import DEFAULT_SECURITY_HOOKS

        assert DEFAULT_SECURITY_HOOKS is not None

    def test_default_hooks_has_wildcard_hooks(self) -> None:
        """Test DEFAULT_SECURITY_HOOKS has wildcard hooks."""
        from mcp_server_langgraph.sdk.hooks import DEFAULT_SECURITY_HOOKS

        hooks = DEFAULT_SECURITY_HOOKS.get_hooks("PreToolUse", "AnyTool")
        # Should have at least pii_detection_hook and rate_limit_hook
        assert len(hooks) >= 2

    def test_default_hooks_has_bash_specific_hooks(self) -> None:
        """Test DEFAULT_SECURITY_HOOKS has Bash-specific hooks."""
        from mcp_server_langgraph.sdk.hooks import DEFAULT_SECURITY_HOOKS

        hooks = DEFAULT_SECURITY_HOOKS.get_hooks("PreToolUse", "Bash")
        # Should have wildcard hooks PLUS bash-specific hook
        assert len(hooks) >= 3

    @pytest.mark.asyncio
    async def test_default_hooks_executes_for_bash(self) -> None:
        """Test DEFAULT_SECURITY_HOOKS blocks dangerous Bash commands."""
        from mcp_server_langgraph.sdk.hooks import DEFAULT_SECURITY_HOOKS

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"},
        }

        result = await DEFAULT_SECURITY_HOOKS.execute_hooks("PreToolUse", "Bash", input_data, "id", {})

        assert result.allowed is False


@pytest.mark.unit
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_hooks_rate_limit")
class TestRateLimitHook:
    """Tests for rate limit hook behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_rate_limit_hook_allows_requests(self) -> None:
        """Test rate limit hook allows requests (placeholder implementation)."""
        from mcp_server_langgraph.sdk.hooks import rate_limit_hook

        # Make multiple requests
        for i in range(10):
            context = {"user_id": f"user-{i}"}
            input_data = {"tool_name": "search"}
            result = await rate_limit_hook(input_data, f"tool-{i}", context)
            assert result.allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_hook_without_user_id(self) -> None:
        """Test rate limit hook works without user_id in context."""
        from mcp_server_langgraph.sdk.hooks import rate_limit_hook

        context = {}  # No user_id
        input_data = {"tool_name": "test"}

        result = await rate_limit_hook(input_data, "tool-123", context)

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_hook_different_tools(self) -> None:
        """Test rate limit hook works for different tool types."""
        from mcp_server_langgraph.sdk.hooks import rate_limit_hook

        tools = ["Bash", "Search", "Read", "Write", "custom_tool"]
        context = {"user_id": "test-user"}

        for tool in tools:
            input_data = {"tool_name": tool}
            result = await rate_limit_hook(input_data, f"tool-{tool}", context)
            assert result.allowed is True


@pytest.mark.unit
@pytest.mark.sdk
@pytest.mark.xdist_group(name="sdk_hooks_pii")
class TestPIIDetectionHook:
    """Tests for PII detection hook."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_pii_hook_disabled_allows_all(self) -> None:
        """Test PII hook allows all when feature flag is disabled."""
        from mcp_server_langgraph.sdk.hooks import pii_detection_hook

        input_data = {
            "tool_name": "search",
            "tool_input": {"query": "john@example.com 555-123-4567"},
        }

        # Feature flag is disabled by default
        result = await pii_detection_hook(input_data, "tool-123", {})

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_pii_hook_handles_empty_input(self) -> None:
        """Test PII hook handles empty tool input."""
        from mcp_server_langgraph.sdk.hooks import pii_detection_hook

        input_data = {
            "tool_name": "test",
            "tool_input": {},
        }

        result = await pii_detection_hook(input_data, "tool-123", {})

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_pii_hook_handles_non_string_values(self) -> None:
        """Test PII hook handles non-string values in tool input."""
        from mcp_server_langgraph.sdk.hooks import pii_detection_hook

        input_data = {
            "tool_name": "test",
            "tool_input": {
                "count": 42,
                "enabled": True,
                "items": ["a", "b", "c"],
            },
        }

        result = await pii_detection_hook(input_data, "tool-123", {})

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_pii_hook_handles_missing_tool_input(self) -> None:
        """Test PII hook handles missing tool_input key."""
        from mcp_server_langgraph.sdk.hooks import pii_detection_hook

        input_data = {
            "tool_name": "test",
        }

        result = await pii_detection_hook(input_data, "tool-123", {})

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_pii_hook_enabled_tokenizes_email(self) -> None:
        """Test PII hook tokenizes email when feature flag enabled."""
        from mcp_server_langgraph.sdk.hooks import pii_detection_hook

        # Mock the feature flag to be enabled (patching in the module where it's imported)
        with patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags:
            mock_flags.enable_pii_tokenization = True

            # Mock the PIITokenizer in the privacy module
            with patch("mcp_server_langgraph.privacy.PIITokenizer") as mock_tokenizer_class:
                # Setup tokenizer mock - tokenize returns (tokenized_text, lookup)
                mock_tokenizer = MagicMock()
                mock_tokenizer.tokenize.return_value = (
                    "Find [TOKEN_EMAIL_1]",
                    {"[TOKEN_EMAIL_1]": "john@example.com"},
                )
                mock_tokenizer_class.return_value = mock_tokenizer

                input_data = {
                    "tool_name": "search",
                    "tool_input": {"query": "Find john@example.com"},
                }
                context: dict[str, Any] = {}

                result = await pii_detection_hook(input_data, "tool-123", context)

                # Should return modified input with tokenized PII
                assert result.allowed is True
                assert result.modified_input is not None
                assert "[TOKEN_EMAIL_1]" in result.modified_input["tool_input"]["query"]
                # Lookup table should be stored in context
                assert "pii_lookup" in context
                assert "[TOKEN_EMAIL_1]" in context["pii_lookup"]

    @pytest.mark.asyncio
    async def test_pii_hook_enabled_no_pii_found(self) -> None:
        """Test PII hook returns unmodified input when no PII found."""
        from mcp_server_langgraph.sdk.hooks import pii_detection_hook

        with patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags:
            mock_flags.enable_pii_tokenization = True

            with patch("mcp_server_langgraph.privacy.PIITokenizer") as mock_tokenizer_class:
                # Setup tokenizer mock - returns empty lookup (no PII found)
                mock_tokenizer = MagicMock()
                mock_tokenizer.tokenize.return_value = ("Find weather in NYC", {})
                mock_tokenizer_class.return_value = mock_tokenizer

                input_data = {
                    "tool_name": "search",
                    "tool_input": {"query": "Find weather in NYC"},
                }
                context: dict[str, Any] = {}

                result = await pii_detection_hook(input_data, "tool-123", context)

                # Should allow without modification (empty lookup means no PII)
                assert result.allowed is True
                assert result.modified_input is None
                # Tokenizer should be called but return empty lookup
                mock_tokenizer.tokenize.assert_called_once()

    @pytest.mark.asyncio
    async def test_pii_hook_enabled_multiple_fields(self) -> None:
        """Test PII hook tokenizes multiple fields."""
        from mcp_server_langgraph.sdk.hooks import pii_detection_hook

        with patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags:
            mock_flags.enable_pii_tokenization = True

            with patch("mcp_server_langgraph.privacy.PIITokenizer") as mock_tokenizer_class:
                # Each call to tokenize returns different token
                call_count = [0]

                def tokenize_side_effect(text):
                    call_count[0] += 1
                    token = f"[TOKEN_{call_count[0]}]"
                    return (token, {token: text})

                mock_tokenizer = MagicMock()
                mock_tokenizer.tokenize.side_effect = tokenize_side_effect
                mock_tokenizer_class.return_value = mock_tokenizer

                input_data = {
                    "tool_name": "email",
                    "tool_input": {
                        "to": "alice@example.com",
                        "from": "bob@example.com",
                        "count": 5,  # Non-string - should be skipped
                    },
                }
                context: dict[str, Any] = {}

                result = await pii_detection_hook(input_data, "tool-123", context)

                assert result.allowed is True
                assert result.modified_input is not None
                # Both string fields should be tokenized
                assert "pii_lookup" in context
                assert len(context["pii_lookup"]) == 2

    @pytest.mark.asyncio
    async def test_pii_hook_import_error_handled(self) -> None:
        """Test PII hook handles ImportError gracefully."""
        from mcp_server_langgraph.sdk.hooks import pii_detection_hook

        with patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags:
            mock_flags.enable_pii_tokenization = True

            # Patch PIITokenizer to raise ImportError when instantiated
            with patch(
                "mcp_server_langgraph.privacy.PIITokenizer",
                side_effect=ImportError("Privacy module not available"),
            ):
                input_data = {
                    "tool_name": "search",
                    "tool_input": {"query": "john@example.com"},
                }

                result = await pii_detection_hook(input_data, "tool-123", {})

                # Should allow even when import fails
                assert result.allowed is True
