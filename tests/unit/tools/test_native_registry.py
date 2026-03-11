"""
Tests for tools/native_registry.py module.

TDD: These tests define the expected behavior for native tool definitions.
"""

import pytest

pytestmark = pytest.mark.unit


class TestNativeToolDef:
    """Tests for NativeToolDef dataclass."""

    def test_native_tool_def_is_frozen(self) -> None:
        """NativeToolDef should be a frozen dataclass."""
        from mcp_server_langgraph.tools.native_registry import NativeToolDef

        defn = NativeToolDef(
            name="web_search",
            provider="anthropic",
            provider_type="web_search_20250305",
            description="Search the web",
            fallback_builtin="web_search",
        )

        # Frozen dataclass should not allow modification
        with pytest.raises(Exception):  # FrozenInstanceError
            defn.name = "other"  # type: ignore

    def test_native_tool_def_has_required_fields(self) -> None:
        """NativeToolDef should have all required fields."""
        from mcp_server_langgraph.tools.native_registry import NativeToolDef

        defn = NativeToolDef(
            name="web_search",
            provider="anthropic",
            provider_type="web_search_20250305",
            description="Search the web using Anthropic's native tool",
            fallback_builtin="web_search",
        )

        assert defn.name == "web_search"
        assert defn.provider == "anthropic"
        assert defn.provider_type == "web_search_20250305"
        assert defn.description == "Search the web using Anthropic's native tool"
        assert defn.fallback_builtin == "web_search"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


class TestNativeTools:
    """Tests for NATIVE_TOOLS registry."""

    def test_native_tools_is_dict(self) -> None:
        """NATIVE_TOOLS should be a dict mapping (name, provider) to NativeToolDef."""
        from mcp_server_langgraph.tools.native_registry import NATIVE_TOOLS

        assert isinstance(NATIVE_TOOLS, dict)
        assert len(NATIVE_TOOLS) > 0

    def test_native_tools_has_anthropic_web_search(self) -> None:
        """NATIVE_TOOLS should contain Anthropic web_search."""
        from mcp_server_langgraph.tools.native_registry import NATIVE_TOOLS

        key = ("web_search", "anthropic")
        assert key in NATIVE_TOOLS
        defn = NATIVE_TOOLS[key]
        assert defn.name == "web_search"
        assert defn.provider == "anthropic"
        assert defn.provider_type == "web_search_20250305"

    def test_native_tools_has_google_web_search(self) -> None:
        """NATIVE_TOOLS should contain Google web search."""
        from mcp_server_langgraph.tools.native_registry import NATIVE_TOOLS

        key = ("web_search", "google")
        assert key in NATIVE_TOOLS
        defn = NATIVE_TOOLS[key]
        assert defn.name == "web_search"
        assert defn.provider == "google"
        assert defn.provider_type == "googleSearch"

    def test_native_tools_has_code_execution(self) -> None:
        """NATIVE_TOOLS should contain Anthropic code_execution."""
        from mcp_server_langgraph.tools.native_registry import NATIVE_TOOLS

        key = ("code_execution", "anthropic")
        assert key in NATIVE_TOOLS
        defn = NATIVE_TOOLS[key]
        assert defn.name == "code_execution"
        assert defn.provider == "anthropic"
        assert defn.fallback_builtin == "execute_python"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


class TestBuiltinToNative:
    """Tests for BUILTIN_TO_NATIVE mapping."""

    def test_builtin_to_native_maps_execute_python(self) -> None:
        """BUILTIN_TO_NATIVE should map execute_python to code_execution."""
        from mcp_server_langgraph.tools.native_registry import BUILTIN_TO_NATIVE

        assert BUILTIN_TO_NATIVE.get("execute_python") == "code_execution"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


class TestGetNativeForBuiltin:
    """Tests for get_native_for_builtin function."""

    def test_get_native_for_builtin_returns_native(self) -> None:
        """get_native_for_builtin should return native tool for known builtin."""
        from mcp_server_langgraph.tools.native_registry import get_native_for_builtin

        defn = get_native_for_builtin("web_search", "anthropic")
        assert defn is not None
        assert defn.name == "web_search"
        assert defn.provider == "anthropic"

    def test_get_native_for_builtin_maps_execute_python(self) -> None:
        """get_native_for_builtin should map execute_python to code_execution."""
        from mcp_server_langgraph.tools.native_registry import get_native_for_builtin

        defn = get_native_for_builtin("execute_python", "anthropic")
        assert defn is not None
        assert defn.name == "code_execution"
        assert defn.provider == "anthropic"

    def test_get_native_for_builtin_returns_none_for_unknown(self) -> None:
        """get_native_for_builtin should return None for unknown builtin."""
        from mcp_server_langgraph.tools.native_registry import get_native_for_builtin

        defn = get_native_for_builtin("calculator", "anthropic")
        assert defn is None

    def test_get_native_for_builtin_returns_none_for_unknown_provider(self) -> None:
        """get_native_for_builtin should return None for unknown provider."""
        from mcp_server_langgraph.tools.native_registry import get_native_for_builtin

        defn = get_native_for_builtin("web_search", "unknown_provider")
        assert defn is None

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
