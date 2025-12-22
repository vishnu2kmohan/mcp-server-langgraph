"""
Output guardrails for validating and filtering LLM outputs.

Provides a protocol-based system for post-LLM response validation,
following the OpenAI Agents SDK guardrails pattern.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from mcp_server_langgraph.observability.telemetry import logger


@dataclass
class GuardrailResult:
    """Result from a guardrail validation."""

    allowed: bool
    """Whether the output is allowed to proceed."""

    modified_output: str | None = None
    """Modified output if the guardrail made changes. None if unchanged."""

    reason: str | None = None
    """Reason for the decision (especially useful for rejections)."""

    tripwire_triggered: bool = False
    """If True, processing should stop immediately."""


class OutputGuardrail(Protocol):
    """Protocol for output guardrails following OpenAI pattern."""

    async def validate(
        self,
        output: str,
        context: dict[str, Any],
    ) -> GuardrailResult:
        """
        Validate LLM output and optionally modify it.

        Args:
            output: The LLM output to validate
            context: Additional context (user info, session, etc.)

        Returns:
            GuardrailResult indicating whether output is allowed,
            optionally with modifications.
        """
        ...


class PIIGuardrail:
    """Detect and redact PII from outputs."""

    # Email pattern
    EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    )

    # Phone patterns (US format)
    PHONE_PATTERNS = [
        re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),  # 555-123-4567
        re.compile(r"\(\d{3}\)\s*\d{3}[-.\s]?\d{4}"),      # (555) 123-4567
    ]

    # SSN pattern
    SSN_PATTERN = re.compile(r"\b\d{3}[-]?\d{2}[-]?\d{4}\b")

    # Credit card pattern (basic)
    CREDIT_CARD_PATTERN = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")

    def __init__(self, redact_emails: bool = True, redact_phones: bool = True,
                 redact_ssn: bool = True, redact_credit_cards: bool = True):
        """Initialize PII guardrail with options."""
        self.redact_emails = redact_emails
        self.redact_phones = redact_phones
        self.redact_ssn = redact_ssn
        self.redact_credit_cards = redact_credit_cards

    async def validate(
        self,
        output: str,
        context: dict[str, Any],
    ) -> GuardrailResult:
        """Detect and redact PII from output."""
        modified = output
        redactions_made = []

        # Redact emails
        if self.redact_emails:
            new_output = self.EMAIL_PATTERN.sub("[EMAIL]", modified)
            if new_output != modified:
                redactions_made.append("email")
                modified = new_output

        # Redact phone numbers
        if self.redact_phones:
            for pattern in self.PHONE_PATTERNS:
                new_output = pattern.sub("[PHONE]", modified)
                if new_output != modified:
                    if "phone" not in redactions_made:
                        redactions_made.append("phone")
                    modified = new_output

        # Redact SSN
        if self.redact_ssn:
            new_output = self.SSN_PATTERN.sub("[SSN]", modified)
            if new_output != modified:
                redactions_made.append("SSN")
                modified = new_output

        # Redact credit cards
        if self.redact_credit_cards:
            new_output = self.CREDIT_CARD_PATTERN.sub("[CREDIT_CARD]", modified)
            if new_output != modified:
                redactions_made.append("credit_card")
                modified = new_output

        if redactions_made:
            logger.info(
                "PII redacted from output",
                extra={"redaction_types": redactions_made}
            )
            return GuardrailResult(
                allowed=True,
                modified_output=modified,
                reason=f"PII redacted: {', '.join(redactions_made)}",
            )

        return GuardrailResult(allowed=True)


class ProfanityGuardrail:
    """Filter profanity from outputs."""

    # Basic word list - in production, use a more comprehensive list
    DEFAULT_PROFANITY = {
        "damn", "darn", "crap", "hell", "heck",
        # Additional words would be added in production
    }

    def __init__(self, word_list: set[str] | None = None, replacement: str = "****"):
        """Initialize profanity guardrail."""
        self.word_list = word_list or self.DEFAULT_PROFANITY
        self.replacement = replacement

    async def validate(
        self,
        output: str,
        context: dict[str, Any],
    ) -> GuardrailResult:
        """Filter profanity from output."""
        modified = output
        words_filtered = []

        # Case-insensitive word replacement
        for word in self.word_list:
            pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
            new_output = pattern.sub(self.replacement, modified)
            if new_output != modified:
                words_filtered.append(word)
                modified = new_output

        if words_filtered:
            logger.info(
                "Profanity filtered from output",
                extra={"words_filtered": len(words_filtered)}
            )
            return GuardrailResult(
                allowed=True,
                modified_output=modified,
                reason=f"Filtered {len(words_filtered)} word(s)",
            )

        return GuardrailResult(allowed=True)


class DisclaimerGuardrail:
    """Add AI-generated disclaimers to outputs."""

    DEFAULT_DISCLAIMER = (
        "[Note: This response was generated by AI and may contain errors. "
        "Please verify important information independently.]\n\n"
    )

    def __init__(self, disclaimer: str | None = None, position: str = "prefix"):
        """
        Initialize disclaimer guardrail.

        Args:
            disclaimer: Custom disclaimer text (uses default if None)
            position: "prefix" to add at start, "suffix" to add at end
        """
        self.disclaimer = disclaimer or self.DEFAULT_DISCLAIMER
        self.position = position

    async def validate(
        self,
        output: str,
        context: dict[str, Any],
    ) -> GuardrailResult:
        """Add disclaimer to output."""
        # Check for skip flag in context
        if context.get("skip_disclaimer"):
            return GuardrailResult(allowed=True)

        if self.position == "prefix":
            modified = self.disclaimer + output
        else:
            modified = output + "\n\n" + self.disclaimer

        return GuardrailResult(
            allowed=True,
            modified_output=modified,
            reason="Disclaimer added",
        )


class FormatGuardrail:
    """Enforce output format requirements."""

    SUPPORTED_FORMATS = {"json", "xml", "markdown"}

    def __init__(self, expected_format: str):
        """
        Initialize format guardrail.

        Args:
            expected_format: Expected output format (json, xml, markdown)
        """
        if expected_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {expected_format}")
        self.expected_format = expected_format

    async def validate(
        self,
        output: str,
        context: dict[str, Any],
    ) -> GuardrailResult:
        """Validate output format."""
        if self.expected_format == "json":
            return await self._validate_json(output)
        elif self.expected_format == "xml":
            return await self._validate_xml(output)
        elif self.expected_format == "markdown":
            # Markdown is generally permissive
            return GuardrailResult(allowed=True)

        return GuardrailResult(allowed=True)

    async def _validate_json(self, output: str) -> GuardrailResult:
        """Validate JSON format."""
        try:
            # Try to parse as JSON
            json.loads(output.strip())
            return GuardrailResult(allowed=True)
        except json.JSONDecodeError as e:
            return GuardrailResult(
                allowed=False,
                reason=f"Invalid JSON format: {e}",
            )

    async def _validate_xml(self, output: str) -> GuardrailResult:
        """Validate XML format."""
        try:
            import xml.etree.ElementTree as ET
            ET.fromstring(output.strip())
            return GuardrailResult(allowed=True)
        except ET.ParseError as e:
            return GuardrailResult(
                allowed=False,
                reason=f"Invalid XML format: {e}",
            )


class GuardrailChain:
    """Execute multiple guardrails in sequence."""

    def __init__(self, guardrails: list[OutputGuardrail]):
        """
        Initialize guardrail chain.

        Args:
            guardrails: List of guardrails to execute in order
        """
        self.guardrails = guardrails

    async def execute(
        self,
        output: str,
        context: dict[str, Any],
    ) -> GuardrailResult:
        """
        Execute all guardrails in sequence.

        Each guardrail receives the (possibly modified) output from the previous one.
        If any guardrail triggers a tripwire, processing stops immediately.

        Args:
            output: Initial output to validate
            context: Context passed to all guardrails

        Returns:
            Final GuardrailResult after all guardrails have run
        """
        current_output = output
        all_reasons: list[str] = []

        for guardrail in self.guardrails:
            result = await guardrail.validate(current_output, context)

            # If tripwire triggered, stop immediately
            if result.tripwire_triggered:
                logger.warning(
                    "Guardrail tripwire triggered",
                    extra={
                        "guardrail": type(guardrail).__name__,
                        "reason": result.reason,
                    }
                )
                return result

            # If not allowed, stop
            if not result.allowed:
                logger.warning(
                    "Guardrail rejected output",
                    extra={
                        "guardrail": type(guardrail).__name__,
                        "reason": result.reason,
                    }
                )
                return result

            # Update output if modified
            if result.modified_output is not None:
                current_output = result.modified_output

            # Collect reasons
            if result.reason:
                all_reasons.append(result.reason)

        # All guardrails passed
        return GuardrailResult(
            allowed=True,
            modified_output=current_output if current_output != output else None,
            reason="; ".join(all_reasons) if all_reasons else None,
        )


# Factory function for common guardrail configurations
def create_default_guardrails() -> GuardrailChain:
    """Create a default guardrail chain with common protections."""
    return GuardrailChain([
        PIIGuardrail(),
        ProfanityGuardrail(),
    ])


def create_strict_guardrails() -> GuardrailChain:
    """Create a strict guardrail chain with all protections."""
    return GuardrailChain([
        PIIGuardrail(),
        ProfanityGuardrail(),
        DisclaimerGuardrail(),
    ])
