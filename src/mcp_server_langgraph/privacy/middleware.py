"""
PII MCP Middleware

Middleware that automatically tokenizes PII in MCP request/response flows
before LLM exposure and restores original values after processing.

Required for GDPR, HIPAA, and SOC2 compliance.

Usage:
    from mcp_server_langgraph.privacy.middleware import PIIMiddleware

    middleware = PIIMiddleware()

    # Process incoming request (tokenize PII)
    processed_request, context = await middleware.process_request(request)

    # ... LLM processes the request ...

    # Process outgoing response (restore PII)
    final_response = await middleware.process_response(response, context)
"""

from __future__ import annotations

import json
from typing import Any, cast

from mcp_server_langgraph.privacy.tokenizer import PIITokenizer


def _safe_is_feature_enabled(flag_name: str) -> bool:
    """Safely check if a feature flag is enabled."""
    try:
        from mcp_server_langgraph.core.feature_flags import is_feature_enabled

        result: bool = is_feature_enabled(flag_name)
        return result
    except (ImportError, RuntimeError):
        return True


# Expose for mocking in tests
def is_feature_enabled(flag_name: str) -> bool:
    """Check if a feature flag is enabled."""
    return _safe_is_feature_enabled(flag_name)


# MCP methods that should be processed for PII
# These methods contain user-provided content that may include PII
PII_SENSITIVE_METHODS = {
    "tools/call",
    "prompts/get",
    "resources/read",
    "sampling/createMessage",
    "completion/complete",
}

# MCP methods that should skip PII processing
# These are metadata methods without user content
PII_SKIP_METHODS = {
    "tools/list",
    "prompts/list",
    "resources/list",
    "resources/templates/list",
    "ping",
    "initialize",
}


class PIIMiddleware:
    """Middleware for PII tokenization in MCP flows.

    Tokenizes PII in requests before LLM exposure and
    restores original values in responses.
    """

    def __init__(self) -> None:
        """Initialize the middleware with a tokenizer."""
        self._tokenizer = PIITokenizer()

    def _should_process(self, method: str | None) -> bool:
        """Check if a method should be processed for PII.

        Args:
            method: MCP method name

        Returns:
            True if the method should be processed for PII
        """
        if not method:
            return False

        # Skip known metadata methods
        if method in PII_SKIP_METHODS:
            return False

        # Process known sensitive methods
        if method in PII_SENSITIVE_METHODS:
            return True

        # Default: process if it might contain user content
        # This is conservative - better to over-tokenize than expose PII
        return True

    def _tokenize_value(
        self,
        value: Any,
        lookup: dict[str, str],
    ) -> Any:
        """Recursively tokenize string values.

        Args:
            value: Value to process
            lookup: Lookup table to update with new mappings

        Returns:
            Processed value with PII tokenized
        """
        if isinstance(value, str):
            tokenized, new_lookup = self._tokenizer.tokenize(value)
            lookup.update(new_lookup)
            return tokenized
        elif isinstance(value, dict):
            return {k: self._tokenize_value(v, lookup) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._tokenize_value(item, lookup) for item in value]
        return value

    def _untokenize_value(
        self,
        value: Any,
        lookup: dict[str, str],
    ) -> Any:
        """Recursively untokenize string values.

        Args:
            value: Value to process
            lookup: Lookup table with token-to-value mappings

        Returns:
            Processed value with original PII restored
        """
        if isinstance(value, str):
            return self._tokenizer.untokenize(value, lookup)
        elif isinstance(value, dict):
            return {k: self._untokenize_value(v, lookup) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._untokenize_value(item, lookup) for item in value]
        return value

    async def process_request(
        self,
        request: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Process an MCP request, tokenizing any PII.

        Args:
            request: The MCP request dictionary

        Returns:
            Tuple of (processed_request, context)
            - processed_request: Request with PII tokenized
            - context: Context dict with pii_lookup for untokenization
        """
        # Check feature flag
        if not is_feature_enabled("pii_tokenization"):
            return request, {"pii_lookup": {}}

        method = request.get("method")

        # Skip methods that don't contain user content
        if not self._should_process(method):
            return request, {"pii_lookup": {}}

        # Tokenize PII in the request
        lookup: dict[str, str] = {}
        processed = self._tokenize_value(request, lookup)

        return processed, {"pii_lookup": lookup}

    async def process_response(
        self,
        response: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Process an MCP response, restoring tokenized PII.

        Args:
            response: The MCP response dictionary
            context: Context from process_request containing pii_lookup

        Returns:
            Response with original PII values restored
        """
        lookup = context.get("pii_lookup", {})

        if not lookup:
            return response

        # Restore original PII values
        return cast(dict[str, Any], self._untokenize_value(response, lookup))

    def tokenize_text(self, text: str) -> tuple[str, dict[str, str]]:
        """Convenience method to tokenize a single text string.

        Args:
            text: Text to tokenize

        Returns:
            Tuple of (tokenized_text, lookup_table)
        """
        return self._tokenizer.tokenize(text)

    def untokenize_text(self, text: str, lookup: dict[str, str]) -> str:
        """Convenience method to untokenize a single text string.

        Args:
            text: Tokenized text
            lookup: Lookup table from tokenize_text

        Returns:
            Text with original values restored
        """
        return self._tokenizer.untokenize(text, lookup)

    def log_safe_request(self, request: dict[str, Any]) -> str:
        """Generate a log-safe version of a request (all PII tokenized).

        Args:
            request: The MCP request to log

        Returns:
            JSON string safe for logging
        """
        lookup: dict[str, str] = {}
        processed = self._tokenize_value(request, lookup)
        return json.dumps(processed, default=str)
