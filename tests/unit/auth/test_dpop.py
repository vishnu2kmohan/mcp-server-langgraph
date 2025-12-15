"""
Tests for DPoP (Demonstrating Proof of Possession) - RFC 9449.

DPoP provides token binding by requiring clients to prove possession of a
private key. This prevents token theft and replay attacks.

TDD Tests - Written FIRST before implementation.
"""

import gc
import json

import pytest

# Markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
]


@pytest.fixture
def dpop_key_pair():
    """Generate ES256 key pair for DPoP proofs."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    return {
        "private_key": private_key,
        "public_key": public_key,
        "private_pem": private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        "public_pem": public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ),
    }


@pytest.mark.xdist_group(name="dpop_tests")
class TestDPoPProofGeneration:
    """Test DPoP proof generation (RFC 9449 Section 4)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_generate_dpop_proof_returns_jwt(self, dpop_key_pair):
        """
        GIVEN: DPoP client with valid key pair
        WHEN: generate_proof() is called with HTTP method and URL
        THEN: Should return a valid JWT string
        """
        from mcp_server_langgraph.auth.dpop import DPoPClient

        client = DPoPClient(private_key=dpop_key_pair["private_key"])

        proof = client.generate_proof(
            http_method="POST",
            http_uri="https://api.example.com/token",
        )

        # Should be a JWT (three base64url-encoded parts separated by dots)
        assert isinstance(proof, str)
        parts = proof.split(".")
        assert len(parts) == 3, "DPoP proof should be a JWT with header.payload.signature"

    def test_generate_dpop_proof_header_contains_typ_dpop(self, dpop_key_pair):
        """
        GIVEN: DPoP client generating a proof
        WHEN: The JWT header is decoded
        THEN: Should contain typ: dpop+jwt and alg: ES256
        """
        import base64

        from mcp_server_langgraph.auth.dpop import DPoPClient

        client = DPoPClient(private_key=dpop_key_pair["private_key"])

        proof = client.generate_proof(
            http_method="POST",
            http_uri="https://api.example.com/token",
        )

        # Decode header (first part of JWT)
        header_b64 = proof.split(".")[0]
        # Add padding if needed
        header_b64 += "=" * (4 - len(header_b64) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_b64))

        assert header.get("typ") == "dpop+jwt"
        assert header.get("alg") == "ES256"
        assert "jwk" in header, "Header must contain public key as JWK"

    def test_generate_dpop_proof_payload_contains_required_claims(self, dpop_key_pair):
        """
        GIVEN: DPoP client generating a proof
        WHEN: The JWT payload is decoded
        THEN: Should contain required claims: jti, htm, htu, iat
        """
        import base64

        from mcp_server_langgraph.auth.dpop import DPoPClient

        client = DPoPClient(private_key=dpop_key_pair["private_key"])

        proof = client.generate_proof(
            http_method="POST",
            http_uri="https://api.example.com/token",
        )

        # Decode payload (second part of JWT)
        payload_b64 = proof.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        assert "jti" in payload, "Payload must contain unique identifier (jti)"
        assert payload.get("htm") == "POST", "Payload must contain HTTP method (htm)"
        assert payload.get("htu") == "https://api.example.com/token", "Payload must contain HTTP URI (htu)"
        assert "iat" in payload, "Payload must contain issued at time (iat)"

    def test_generate_dpop_proof_with_access_token_includes_ath(self, dpop_key_pair):
        """
        GIVEN: DPoP client generating a proof for resource access
        WHEN: access_token is provided
        THEN: Payload should contain ath (access token hash) claim
        """
        import base64

        from mcp_server_langgraph.auth.dpop import DPoPClient

        client = DPoPClient(private_key=dpop_key_pair["private_key"])

        proof = client.generate_proof(
            http_method="GET",
            http_uri="https://api.example.com/resource",
            access_token="test-access-token-xyz",
        )

        # Decode payload
        payload_b64 = proof.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        assert "ath" in payload, "Payload must contain access token hash (ath) when access_token is provided"

    def test_generate_dpop_proof_jti_is_unique(self, dpop_key_pair):
        """
        GIVEN: DPoP client generating multiple proofs
        WHEN: generate_proof() is called multiple times
        THEN: Each proof should have a unique jti
        """
        import base64

        from mcp_server_langgraph.auth.dpop import DPoPClient

        client = DPoPClient(private_key=dpop_key_pair["private_key"])

        proofs = [client.generate_proof(http_method="POST", http_uri="https://api.example.com/token") for _ in range(5)]

        jtis = []
        for proof in proofs:
            payload_b64 = proof.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            jtis.append(payload["jti"])

        # All JTIs should be unique
        assert len(set(jtis)) == 5, "Each DPoP proof must have a unique jti"


@pytest.mark.xdist_group(name="dpop_tests")
class TestDPoPProofVerification:
    """Test DPoP proof verification (RFC 9449 Section 4.3)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_verify_dpop_proof_valid_proof(self, dpop_key_pair):
        """
        GIVEN: Valid DPoP proof for a request
        WHEN: verify_proof() is called with matching method and URI
        THEN: Should return True and decoded claims
        """
        from mcp_server_langgraph.auth.dpop import DPoPClient, verify_dpop_proof

        client = DPoPClient(private_key=dpop_key_pair["private_key"])

        proof = client.generate_proof(
            http_method="POST",
            http_uri="https://api.example.com/token",
        )

        result = verify_dpop_proof(
            proof=proof,
            http_method="POST",
            http_uri="https://api.example.com/token",
        )

        assert result["valid"] is True
        assert "claims" in result

    def test_verify_dpop_proof_wrong_method(self, dpop_key_pair):
        """
        GIVEN: DPoP proof generated for POST
        WHEN: verify_proof() is called with GET method
        THEN: Should return False with method mismatch error
        """
        from mcp_server_langgraph.auth.dpop import DPoPClient, verify_dpop_proof

        client = DPoPClient(private_key=dpop_key_pair["private_key"])

        proof = client.generate_proof(
            http_method="POST",
            http_uri="https://api.example.com/token",
        )

        result = verify_dpop_proof(
            proof=proof,
            http_method="GET",  # Different method!
            http_uri="https://api.example.com/token",
        )

        assert result["valid"] is False
        assert "method" in result.get("error", "").lower()

    def test_verify_dpop_proof_wrong_uri(self, dpop_key_pair):
        """
        GIVEN: DPoP proof generated for /token endpoint
        WHEN: verify_proof() is called with /resource endpoint
        THEN: Should return False with URI mismatch error
        """
        from mcp_server_langgraph.auth.dpop import DPoPClient, verify_dpop_proof

        client = DPoPClient(private_key=dpop_key_pair["private_key"])

        proof = client.generate_proof(
            http_method="POST",
            http_uri="https://api.example.com/token",
        )

        result = verify_dpop_proof(
            proof=proof,
            http_method="POST",
            http_uri="https://api.example.com/other",  # Different URI!
        )

        assert result["valid"] is False
        assert "uri" in result.get("error", "").lower()

    def test_verify_dpop_proof_expired(self, dpop_key_pair):
        """
        GIVEN: DPoP proof with old iat timestamp
        WHEN: verify_proof() is called after max_age
        THEN: Should return False with expired error
        """
        import time

        import jwt

        from mcp_server_langgraph.auth.dpop import DPoPClient, verify_dpop_proof

        client = DPoPClient(private_key=dpop_key_pair["private_key"])

        # Generate a proof manually with an old iat timestamp (10 minutes ago)
        old_iat = int(time.time()) - 600  # 10 minutes ago

        header = {
            "typ": "dpop+jwt",
            "alg": "ES256",
            "jwk": client.get_public_jwk(),
        }

        payload = {
            "jti": "test-expired-jti",
            "htm": "POST",
            "htu": "https://api.example.com/token",
            "iat": old_iat,  # 10 minutes ago
        }

        # Sign with ES256
        proof = jwt.encode(
            payload,
            dpop_key_pair["private_key"],
            algorithm="ES256",
            headers=header,
        )

        # Verify with max_age=300 (5 minutes) - should fail since proof is 10 min old
        result = verify_dpop_proof(
            proof=proof,
            http_method="POST",
            http_uri="https://api.example.com/token",
            max_age_seconds=300,  # 5 minutes
        )

        # Proof should be INVALID because iat is older than max_age
        assert result["valid"] is False
        assert "expired" in result.get("error", "").lower()


@pytest.mark.xdist_group(name="dpop_tests")
class TestDPoPJtiReplayProtection:
    """Test DPoP jti replay protection (RFC 9449 Section 11.1)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_jti_replay_detection_rejects_reused_jti(self, dpop_key_pair):
        """
        GIVEN: DPoP proof that was already used
        WHEN: Same proof is presented again
        THEN: Should be rejected as replay attack
        """
        from mcp_server_langgraph.auth.dpop import DPoPClient, DPoPReplayCache, verify_dpop_proof

        client = DPoPClient(private_key=dpop_key_pair["private_key"])
        cache = DPoPReplayCache()

        proof = client.generate_proof(
            http_method="POST",
            http_uri="https://api.example.com/token",
        )

        # First use should succeed
        result1 = verify_dpop_proof(
            proof=proof,
            http_method="POST",
            http_uri="https://api.example.com/token",
            jti_cache=cache,
        )
        assert result1["valid"] is True

        # Second use should fail (replay)
        result2 = verify_dpop_proof(
            proof=proof,
            http_method="POST",
            http_uri="https://api.example.com/token",
            jti_cache=cache,
        )
        assert result2["valid"] is False
        assert "replay" in result2.get("error", "").lower()


@pytest.mark.xdist_group(name="dpop_tests")
class TestDPoPKeyBinding:
    """Test DPoP key binding for access tokens."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_dpop_bound_access_token_contains_cnf_claim(self, dpop_key_pair):
        """
        GIVEN: Access token bound to DPoP key
        WHEN: Token is inspected
        THEN: Should contain cnf (confirmation) claim with jwk thumbprint
        """
        from mcp_server_langgraph.auth.dpop import DPoPClient, create_dpop_bound_token

        client = DPoPClient(private_key=dpop_key_pair["private_key"])

        # Create a mock access token with DPoP binding
        bound_token = create_dpop_bound_token(
            original_claims={"sub": "alice", "aud": "api"},
            dpop_jwk=client.get_public_jwk(),
        )

        assert "cnf" in bound_token
        assert "jkt" in bound_token["cnf"], "cnf must contain JWK thumbprint (jkt)"
