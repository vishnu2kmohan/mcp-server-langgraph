"""
TDD Tests for DPoPEnforcer class extraction.

This test module validates the DPoPEnforcer class which handles DPoP
(RFC 9449) sender-constraint verification as a standalone component.

RED-GREEN-REFACTOR: Start with failing tests to define expected behavior.
"""

import gc
import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="dpop_enforcer")
class TestDPoPEnforcer:
    """Test DPoPEnforcer class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_dpop_enforcer_can_be_imported(self) -> None:
        """Test that DPoPEnforcer can be imported from auth.dpop."""
        from mcp_server_langgraph.auth.dpop import DPoPEnforcer

        assert DPoPEnforcer is not None

    def test_dpop_enforcer_initialization(self) -> None:
        """Test DPoPEnforcer can be initialized with replay cache."""
        from mcp_server_langgraph.auth.dpop import DPoPEnforcer, DPoPReplayCache

        cache = DPoPReplayCache(max_size=100)
        enforcer = DPoPEnforcer(replay_cache=cache, required=False)

        assert enforcer.replay_cache is cache
        assert enforcer.required is False

    def test_dpop_enforcer_initialization_strict_mode(self) -> None:
        """Test DPoPEnforcer can be initialized in strict mode."""
        from mcp_server_langgraph.auth.dpop import DPoPEnforcer, DPoPReplayCache

        cache = DPoPReplayCache(max_size=100)
        enforcer = DPoPEnforcer(replay_cache=cache, required=True)

        assert enforcer.required is True

    def test_dpop_enforcer_verify_returns_result(self) -> None:
        """Test DPoPEnforcer.verify returns a DPoPVerificationResult."""
        from mcp_server_langgraph.auth.dpop import DPoPEnforcer, DPoPReplayCache

        cache = DPoPReplayCache(max_size=100)
        enforcer = DPoPEnforcer(replay_cache=cache, required=False)

        # Verify with no DPoP proof and non-bound token (should pass)
        result = enforcer.verify(
            token_payload={"sub": "user:alice"},  # No cnf claim
            dpop_proof=None,
            http_method="GET",
            http_uri="https://api.example.com/resource",
            access_token="dummy-token",
        )

        assert result.valid is True
        assert result.error is None

    def test_dpop_enforcer_rejects_missing_proof_when_required(self) -> None:
        """Test DPoPEnforcer rejects missing proof in strict mode."""
        from mcp_server_langgraph.auth.dpop import DPoPEnforcer, DPoPReplayCache

        cache = DPoPReplayCache(max_size=100)
        enforcer = DPoPEnforcer(replay_cache=cache, required=True)

        # Verify with no DPoP proof but required=True (should fail)
        result = enforcer.verify(
            token_payload={"sub": "user:alice"},
            dpop_proof=None,
            http_method="GET",
            http_uri="https://api.example.com/resource",
            access_token="dummy-token",
        )

        assert result.valid is False
        assert "required" in result.error.lower()

    def test_dpop_enforcer_rejects_missing_proof_for_bound_token(self) -> None:
        """Test DPoPEnforcer rejects missing proof for DPoP-bound token."""
        from mcp_server_langgraph.auth.dpop import DPoPEnforcer, DPoPReplayCache

        cache = DPoPReplayCache(max_size=100)
        enforcer = DPoPEnforcer(replay_cache=cache, required=False)

        # Token with cnf.jkt claim is DPoP-bound
        token_payload = {
            "sub": "user:alice",
            "cnf": {"jkt": "some-thumbprint"},
        }

        # Verify with no DPoP proof but token is bound (should fail)
        result = enforcer.verify(
            token_payload=token_payload,
            dpop_proof=None,
            http_method="GET",
            http_uri="https://api.example.com/resource",
            access_token="dummy-token",
        )

        assert result.valid is False
        assert "required" in result.error.lower()


@pytest.mark.xdist_group(name="dpop_enforcer")
class TestDPoPVerificationResult:
    """Test DPoPVerificationResult dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_dpop_verification_result_can_be_imported(self) -> None:
        """Test that DPoPVerificationResult can be imported."""
        from mcp_server_langgraph.auth.dpop import DPoPVerificationResult

        assert DPoPVerificationResult is not None

    def test_dpop_verification_result_success(self) -> None:
        """Test creating a successful verification result."""
        from mcp_server_langgraph.auth.dpop import DPoPVerificationResult

        result = DPoPVerificationResult(valid=True, error=None, dpop_bound=False)

        assert result.valid is True
        assert result.error is None
        assert result.dpop_bound is False

    def test_dpop_verification_result_failure(self) -> None:
        """Test creating a failed verification result."""
        from mcp_server_langgraph.auth.dpop import DPoPVerificationResult

        result = DPoPVerificationResult(
            valid=False,
            error="DPoP proof required",
            dpop_bound=True,
        )

        assert result.valid is False
        assert result.error == "DPoP proof required"
        assert result.dpop_bound is True
