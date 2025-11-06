"""
Unit tests for server_streamable module initialization.

Tests verify that the module uses standard logging for module-level code
and observability logger only after lifespan initialization.

NOTE: These are simplified verification tests. Full module import testing
is complex due to dependency injection and is better validated via
integration tests and production deployment verification.
"""

import logging

import pytest


@pytest.mark.unit
def test_module_level_logger_uses_standard_logging():
    """
    Test that server_streamable.py uses standard logging.getLogger() for module-level code.

    This prevents RuntimeError when importing the module before observability is initialized.

    CRITICAL: Module-level code should NEVER use observability logger/tracer/metrics.
    """
    # Read the source file to verify it uses standard logging
    import pathlib

    source_file = pathlib.Path(__file__).parent.parent.parent / "src" / "mcp_server_langgraph" / "mcp" / "server_streamable.py"
    source_code = source_file.read_text()

    # Verify module-level logger is defined with standard logging
    assert (
        "_module_logger = logging.getLogger(__name__)" in source_code
    ), "Module should define _module_logger using standard logging.getLogger()"

    # Verify module-level code uses _module_logger, not observability logger
    # Look for the rate limiting try/except block
    rate_limit_section = source_code[source_code.find("# Rate limiting middleware") : source_code.find("class ChatInput")]

    assert "_module_logger.info" in rate_limit_section, "Module-level code should use _module_logger.info()"
    assert "_module_logger.warning" in rate_limit_section, "Module-level code should use _module_logger.warning()"

    # The observability logger import should still exist but not be used at module level
    assert "from mcp_server_langgraph.observability.telemetry import logger" in source_code


@pytest.mark.unit
def test_rate_limiting_logs_use_standard_logger():
    """
    Verify that rate limiting initialization uses standard logger, not observability logger.

    This is the specific fix for the production crash:
    RuntimeError: Observability not initialized at line 187
    """
    import pathlib

    source_file = pathlib.Path(__file__).parent.parent.parent / "src" / "mcp_server_langgraph" / "mcp" / "server_streamable.py"

    with open(source_file) as f:
        lines = f.readlines()

    # Find the rate limiting try/except block (around lines 173-197)
    rate_limit_start = None
    for i, line in enumerate(lines):
        if "# Rate limiting middleware" in line:
            rate_limit_start = i
            break

    assert rate_limit_start is not None, "Could not find rate limiting section"

    # Check the next ~30 lines for logger usage
    rate_limit_section = "".join(lines[rate_limit_start : rate_limit_start + 30])

    # Should use _module_logger, NOT observability logger
    if "logger.info" in rate_limit_section or "logger.warning" in rate_limit_section:
        # Make sure it's _module_logger, not the observability logger
        assert (
            "_module_logger" in rate_limit_section
        ), "Rate limiting section uses 'logger' directly - should use '_module_logger' instead"


@pytest.mark.unit
def test_observability_logger_not_used_at_module_level():
    """
    Verify that observability logger is not used at module level (outside functions).

    This prevents the RuntimeError that was causing production pod crashes.
    """
    import pathlib

    source_file = pathlib.Path(__file__).parent.parent.parent / "src" / "mcp_server_langgraph" / "mcp" / "server_streamable.py"
    source_code = source_file.read_text()

    # Split into module level (before any function definitions) and function level
    # Find the first function/async def
    first_function = min(
        source_code.find("def ") if "def " in source_code else len(source_code),
        source_code.find("async def ") if "async def " in source_code else len(source_code),
    )

    module_level_code = source_code[:first_function]

    # Check for problematic patterns at module level
    # Pattern: logger.info/warning/error (not _module_logger)
    import re

    # Find instances of logger. calls (not _module_logger.)
    bad_logger_usage = re.findall(r"^[^#]*\blogger\.(info|warning|error|debug)", module_level_code, re.MULTILINE)

    assert (
        len(bad_logger_usage) == 0
    ), f"Found {len(bad_logger_usage)} instances of observability logger usage at module level: {bad_logger_usage}"
