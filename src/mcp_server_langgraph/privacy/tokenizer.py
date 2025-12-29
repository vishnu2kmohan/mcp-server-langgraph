"""
PII Tokenizer

Replaces PII values with tokens before LLM exposure and restores
original values from tokens after processing.

Token format: <<PII_TYPE_hash>>
- PII_TYPE: The type of PII (EMAIL, PHONE, SSN, etc.)
- hash: Short unique identifier for the value

Usage:
    from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

    tokenizer = PIITokenizer()

    # Tokenize before sending to LLM
    tokenized_text, lookup = tokenizer.tokenize(
        "Contact john@example.com at 555-123-4567"
    )
    # tokenized_text: "Contact <<PII_EMAIL_a1b2c3>> at <<PII_PHONE_d4e5f6>>"

    # After LLM processing, restore original values
    original = tokenizer.untokenize(tokenized_text, lookup)
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, cast

from mcp_server_langgraph.privacy.detectors import detect_pii


class PIITokenizer:
    """Tokenizes PII for safe LLM processing.

    Replaces detected PII with tokens and provides a lookup table
    for restoring original values.
    """

    # Token format: <<PII_TYPE_HASH>>
    TOKEN_PREFIX = "<<"  # noqa: S105 - Token delimiter, not a password
    TOKEN_SUFFIX = ">>"  # noqa: S105 - Token delimiter, not a password
    TOKEN_PATTERN = re.compile(r"<<PII_[A-Z_]+_[a-f0-9]+>>")

    def __init__(self) -> None:
        """Initialize the tokenizer."""
        pass

    def _generate_token_id(self, value: str) -> str:
        """Generate a short hash for a value.

        Uses first 8 chars of SHA-256 for uniqueness.

        Args:
            value: The original PII value

        Returns:
            8-character hex hash
        """
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]

    def _create_token(self, pii_type: str, value: str) -> str:
        """Create a token for a PII value.

        Args:
            pii_type: Type of PII (EMAIL, PHONE, etc.)
            value: The original PII value

        Returns:
            Token string like <<PII_EMAIL_a1b2c3>>
        """
        token_id = self._generate_token_id(value)
        return f"{self.TOKEN_PREFIX}PII_{pii_type}_{token_id}{self.TOKEN_SUFFIX}"

    def tokenize(self, text: str | None) -> tuple[str, dict[str, str]]:
        """Replace PII in text with tokens.

        Args:
            text: Text potentially containing PII

        Returns:
            Tuple of (tokenized_text, lookup_table)
            - tokenized_text: Text with PII replaced by tokens
            - lookup_table: Mapping of tokens to original values
        """
        if not text:
            return "", {}

        detections = detect_pii(text)

        if not detections:
            return text, {}

        # Build lookup table and track replacements
        lookup_table: dict[str, str] = {}
        value_to_token: dict[str, str] = {}

        for detection in detections:
            value = detection.value
            if value not in value_to_token:
                token = self._create_token(detection.pii_type, value)
                value_to_token[value] = token
                lookup_table[token] = value

        # Sort detections by position (descending) to replace from end
        sorted_detections = sorted(detections, key=lambda d: d.start, reverse=True)

        # Replace PII with tokens
        result = text
        for detection in sorted_detections:
            token = value_to_token[detection.value]
            result = result[: detection.start] + token + result[detection.end :]

        return result, lookup_table

    def untokenize(
        self,
        text: str,
        lookup_table: dict[str, str] | Any,
    ) -> str:
        """Restore original PII values from tokens.

        Args:
            text: Text containing PII tokens
            lookup_table: Mapping of tokens to original values

        Returns:
            Text with tokens replaced by original PII values
        """
        if not text or not lookup_table:
            return text

        result = text
        for token, value in lookup_table.items():
            result = result.replace(token, value)

        return result

    def tokenize_dict(
        self,
        data: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Recursively tokenize string values in a dictionary.

        Args:
            data: Dictionary potentially containing PII in string values

        Returns:
            Tuple of (tokenized_dict, combined_lookup_table)
        """
        combined_lookup: dict[str, str] = {}

        def _tokenize_value(value: Any) -> Any:
            if isinstance(value, str):
                tokenized, lookup = self.tokenize(value)
                combined_lookup.update(lookup)
                return tokenized
            elif isinstance(value, dict):
                return {k: _tokenize_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [_tokenize_value(item) for item in value]
            return value

        tokenized_data = _tokenize_value(data)
        return tokenized_data, combined_lookup

    def untokenize_dict(
        self,
        data: dict[str, Any],
        lookup_table: dict[str, str],
    ) -> dict[str, Any]:
        """Recursively restore original values in a dictionary.

        Args:
            data: Dictionary containing tokenized strings
            lookup_table: Mapping of tokens to original values

        Returns:
            Dictionary with original values restored
        """

        def _untokenize_value(value: Any) -> Any:
            if isinstance(value, str):
                return self.untokenize(value, lookup_table)
            elif isinstance(value, dict):
                return {k: _untokenize_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [_untokenize_value(item) for item in value]
            return value

        return cast(dict[str, Any], _untokenize_value(data))
