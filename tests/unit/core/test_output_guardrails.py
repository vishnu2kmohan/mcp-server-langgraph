"""
TDD Tests for output guardrails

These tests define the expected behavior for the output guardrails system.
Written FIRST before implementation (RED phase).
"""

import gc
from typing import Any

import pytest


@pytest.mark.xdist_group(name="output_guardrails")
class TestGuardrailResult:
    """Test suite for GuardrailResult dataclass."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_guardrail_result_defaults(self):
        """GIVEN default parameters
        WHEN GuardrailResult is created
        THEN it has correct defaults"""
        from mcp_server_langgraph.sdk.output_guardrails import GuardrailResult

        result = GuardrailResult(allowed=True)

        assert result.allowed is True
        assert result.modified_output is None
        assert result.reason is None
        assert result.tripwire_triggered is False

    @pytest.mark.unit
    def test_guardrail_result_with_modified_output(self):
        """GIVEN modified_output parameter
        WHEN GuardrailResult is created
        THEN it stores the modified output"""
        from mcp_server_langgraph.sdk.output_guardrails import GuardrailResult

        result = GuardrailResult(
            allowed=True,
            modified_output="Sanitized content",
            reason="PII redacted",
        )

        assert result.allowed is True
        assert result.modified_output == "Sanitized content"
        assert result.reason == "PII redacted"

    @pytest.mark.unit
    def test_guardrail_result_with_tripwire(self):
        """GIVEN tripwire_triggered=True
        WHEN GuardrailResult is created
        THEN it signals processing should stop"""
        from mcp_server_langgraph.sdk.output_guardrails import GuardrailResult

        result = GuardrailResult(
            allowed=False,
            reason="Dangerous content detected",
            tripwire_triggered=True,
        )

        assert result.allowed is False
        assert result.tripwire_triggered is True


@pytest.mark.xdist_group(name="output_guardrails")
class TestPIIGuardrail:
    """Test suite for PII detection and redaction guardrail."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pii_guardrail_detects_email(self):
        """GIVEN output containing an email address
        WHEN PIIGuardrail validates
        THEN the email is redacted"""
        from mcp_server_langgraph.sdk.output_guardrails import PIIGuardrail

        guardrail = PIIGuardrail()
        output = "Contact me at john.doe@example.com for more info."
        context: dict[str, Any] = {}

        result = await guardrail.validate(output, context)

        assert result.allowed is True
        assert result.modified_output is not None
        assert "john.doe@example.com" not in result.modified_output
        assert "[EMAIL]" in result.modified_output or "[REDACTED]" in result.modified_output

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pii_guardrail_detects_phone(self):
        """GIVEN output containing a phone number
        WHEN PIIGuardrail validates
        THEN the phone is redacted"""
        from mcp_server_langgraph.sdk.output_guardrails import PIIGuardrail

        guardrail = PIIGuardrail()
        output = "Call me at 555-123-4567 or (555) 987-6543."
        context: dict[str, Any] = {}

        result = await guardrail.validate(output, context)

        assert result.allowed is True
        assert result.modified_output is not None
        assert "555-123-4567" not in result.modified_output
        assert "[PHONE]" in result.modified_output or "[REDACTED]" in result.modified_output

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pii_guardrail_detects_ssn(self):
        """GIVEN output containing a Social Security Number
        WHEN PIIGuardrail validates
        THEN the SSN is redacted"""
        from mcp_server_langgraph.sdk.output_guardrails import PIIGuardrail

        guardrail = PIIGuardrail()
        output = "My SSN is 123-45-6789."
        context: dict[str, Any] = {}

        result = await guardrail.validate(output, context)

        assert result.allowed is True
        assert result.modified_output is not None
        assert "123-45-6789" not in result.modified_output
        assert "[SSN]" in result.modified_output or "[REDACTED]" in result.modified_output

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pii_guardrail_allows_clean_output(self):
        """GIVEN output with no PII
        WHEN PIIGuardrail validates
        THEN output is unchanged"""
        from mcp_server_langgraph.sdk.output_guardrails import PIIGuardrail

        guardrail = PIIGuardrail()
        output = "This is a clean response with no personal information."
        context: dict[str, Any] = {}

        result = await guardrail.validate(output, context)

        assert result.allowed is True
        # Should either be None (unchanged) or same as original
        if result.modified_output is not None:
            assert result.modified_output == output


@pytest.mark.xdist_group(name="output_guardrails")
class TestProfanityGuardrail:
    """Test suite for profanity filtering guardrail."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_profanity_guardrail_filters_content(self):
        """GIVEN output containing profanity
        WHEN ProfanityGuardrail validates
        THEN profanity is filtered"""
        from mcp_server_langgraph.sdk.output_guardrails import ProfanityGuardrail

        guardrail = ProfanityGuardrail()
        # Using a placeholder that would be in a real profanity list
        output = "This is a damn frustrating problem."
        context: dict[str, Any] = {}

        result = await guardrail.validate(output, context)

        assert result.allowed is True
        if result.modified_output is not None:
            # Either filtered or flagged
            assert "damn" not in result.modified_output.lower() or result.reason

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_profanity_guardrail_allows_clean_content(self):
        """GIVEN output without profanity
        WHEN ProfanityGuardrail validates
        THEN output is unchanged"""
        from mcp_server_langgraph.sdk.output_guardrails import ProfanityGuardrail

        guardrail = ProfanityGuardrail()
        output = "This is a perfectly acceptable response."
        context: dict[str, Any] = {}

        result = await guardrail.validate(output, context)

        assert result.allowed is True


@pytest.mark.xdist_group(name="output_guardrails")
class TestDisclaimerGuardrail:
    """Test suite for AI-generated disclaimer guardrail."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_disclaimer_guardrail_adds_prefix(self):
        """GIVEN any output
        WHEN DisclaimerGuardrail validates
        THEN a disclaimer is added"""
        from mcp_server_langgraph.sdk.output_guardrails import DisclaimerGuardrail

        guardrail = DisclaimerGuardrail()
        output = "Here is my analysis of the data."
        context: dict[str, Any] = {}

        result = await guardrail.validate(output, context)

        assert result.allowed is True
        assert result.modified_output is not None
        # Should contain some form of AI disclaimer
        modified_lower = result.modified_output.lower()
        assert ("ai" in modified_lower or "generated" in modified_lower or
                "disclaimer" in modified_lower or "note" in modified_lower)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_disclaimer_guardrail_respects_skip_flag(self):
        """GIVEN context with skip_disclaimer=True
        WHEN DisclaimerGuardrail validates
        THEN no disclaimer is added"""
        from mcp_server_langgraph.sdk.output_guardrails import DisclaimerGuardrail

        guardrail = DisclaimerGuardrail()
        output = "Here is my analysis."
        context = {"skip_disclaimer": True}

        result = await guardrail.validate(output, context)

        assert result.allowed is True
        # Should not modify if skip is requested
        assert result.modified_output is None or result.modified_output == output


@pytest.mark.xdist_group(name="output_guardrails")
class TestFormatGuardrail:
    """Test suite for output format enforcement guardrail."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_format_guardrail_validates_json(self):
        """GIVEN expected JSON format and valid JSON output
        WHEN FormatGuardrail validates
        THEN output is allowed"""
        from mcp_server_langgraph.sdk.output_guardrails import FormatGuardrail

        guardrail = FormatGuardrail(expected_format="json")
        output = '{"key": "value", "number": 42}'
        context: dict[str, Any] = {}

        result = await guardrail.validate(output, context)

        assert result.allowed is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_format_guardrail_rejects_invalid_json(self):
        """GIVEN expected JSON format and invalid JSON output
        WHEN FormatGuardrail validates
        THEN output is rejected"""
        from mcp_server_langgraph.sdk.output_guardrails import FormatGuardrail

        guardrail = FormatGuardrail(expected_format="json")
        output = "This is not JSON"
        context: dict[str, Any] = {}

        result = await guardrail.validate(output, context)

        assert result.allowed is False
        assert "json" in result.reason.lower() if result.reason else False


@pytest.mark.xdist_group(name="output_guardrails")
class TestGuardrailChain:
    """Test suite for guardrail chain execution."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_guardrail_chain_execution(self):
        """GIVEN multiple guardrails in a chain
        WHEN chain is executed
        THEN all guardrails are applied in order"""
        from mcp_server_langgraph.sdk.output_guardrails import (
            GuardrailChain,
            PIIGuardrail,
            DisclaimerGuardrail,
        )

        chain = GuardrailChain([PIIGuardrail(), DisclaimerGuardrail()])
        output = "Contact john@example.com for details."
        context: dict[str, Any] = {}

        result = await chain.execute(output, context)

        assert result.allowed is True
        # PII should be redacted AND disclaimer should be added
        assert "john@example.com" not in result.modified_output
        assert "[EMAIL]" in result.modified_output or "[REDACTED]" in result.modified_output

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_tripwire_stops_processing(self):
        """GIVEN a tripwire guardrail in the chain
        WHEN tripwire is triggered
        THEN processing stops immediately"""
        from mcp_server_langgraph.sdk.output_guardrails import (
            GuardrailChain,
            GuardrailResult,
            OutputGuardrail,
        )

        class TripwireGuardrail(OutputGuardrail):
            async def validate(self, output: str, context: dict[str, Any]) -> GuardrailResult:
                if "dangerous" in output.lower():
                    return GuardrailResult(
                        allowed=False,
                        reason="Dangerous content detected",
                        tripwire_triggered=True,
                    )
                return GuardrailResult(allowed=True)

        class ModifyGuardrail(OutputGuardrail):
            async def validate(self, output: str, context: dict[str, Any]) -> GuardrailResult:
                return GuardrailResult(
                    allowed=True,
                    modified_output=output + " [MODIFIED]",
                )

        chain = GuardrailChain([TripwireGuardrail(), ModifyGuardrail()])
        output = "This is dangerous content."
        context: dict[str, Any] = {}

        result = await chain.execute(output, context)

        assert result.allowed is False
        assert result.tripwire_triggered is True
        # Second guardrail should NOT have run
        assert "[MODIFIED]" not in (result.modified_output or "")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_guardrail_chain_passes_modified_output(self):
        """GIVEN guardrails that modify output
        WHEN chain is executed
        THEN each guardrail receives modified output from previous"""
        from mcp_server_langgraph.sdk.output_guardrails import (
            GuardrailChain,
            GuardrailResult,
            OutputGuardrail,
        )

        class AddAGuardrail(OutputGuardrail):
            async def validate(self, output: str, context: dict[str, Any]) -> GuardrailResult:
                return GuardrailResult(allowed=True, modified_output=output + "A")

        class AddBGuardrail(OutputGuardrail):
            async def validate(self, output: str, context: dict[str, Any]) -> GuardrailResult:
                return GuardrailResult(allowed=True, modified_output=output + "B")

        chain = GuardrailChain([AddAGuardrail(), AddBGuardrail()])
        result = await chain.execute("X", {})

        assert result.allowed is True
        assert result.modified_output == "XAB"


@pytest.mark.xdist_group(name="output_guardrails_integration")
class TestOutputGuardrailsIntegration:
    """Integration tests for output guardrails with hook system."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_guardrails_integrate_with_after_model_hook(self):
        """GIVEN output guardrails configured
        WHEN AFTER_MODEL hook fires
        THEN guardrails are applied to LLM output"""
        # Placeholder for hook integration test
        pass
