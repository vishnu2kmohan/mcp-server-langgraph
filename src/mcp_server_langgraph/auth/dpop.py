"""
DPoP (Demonstrating Proof of Possession) - RFC 9449.

DPoP provides token binding by requiring clients to prove possession of a
private key. This prevents token theft and replay attacks.

Key Features:
- Sender-constrained access tokens bound to client's public key
- Protection against token theft and replay attacks
- Replay protection via jti (JWT ID) tracking
- Compatible with OAuth 2.0 authorization code and client credentials flows

Usage:
    from mcp_server_langgraph.auth.dpop import DPoPClient, verify_dpop_proof

    # Client side: Generate DPoP proof
    client = DPoPClient.generate()  # Generates new key pair
    proof = client.generate_proof(
        http_method="POST",
        http_uri="https://api.example.com/token",
    )

    # Include DPoP header in request
    headers = {"DPoP": proof}

    # Server side: Verify DPoP proof
    result = verify_dpop_proof(
        proof=proof,
        http_method="POST",
        http_uri="https://api.example.com/token",
    )

References:
- RFC 9449: OAuth 2.0 Demonstrating Proof of Possession (DPoP)
  https://datatracker.ietf.org/doc/rfc9449/
"""

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, cast

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey, EllipticCurvePublicKey
import jwt
from jwt.algorithms import ECAlgorithm

from mcp_server_langgraph.observability.telemetry import logger


class DPoPClient:
    """
    DPoP client for generating proof tokens.

    Generates and signs DPoP proofs using ES256 (ECDSA with P-256 and SHA-256).
    Each proof includes the HTTP method, URI, and a unique jti to prevent replay.
    """

    def __init__(
        self,
        private_key: EllipticCurvePrivateKey,
        algorithm: str = "ES256",
    ) -> None:
        """
        Initialize DPoP client with existing key pair.

        Args:
            private_key: EC private key for signing
            algorithm: JWT algorithm (default: ES256)
        """
        self.private_key = private_key
        self.public_key = private_key.public_key()
        self.algorithm = algorithm

    @classmethod
    def generate(cls) -> "DPoPClient":
        """
        Generate new DPoP client with fresh key pair.

        Returns:
            DPoPClient with new EC key pair
        """
        private_key = ec.generate_private_key(ec.SECP256R1())
        return cls(private_key=private_key)

    def get_public_jwk(self) -> dict[str, Any]:
        """
        Get public key as JWK for inclusion in DPoP proof header.

        Returns:
            JWK dictionary with kty, crv, x, y
        """
        return ECAlgorithm.to_jwk(self.public_key, as_dict=True)

    def get_jwk_thumbprint(self) -> str:
        """
        Calculate JWK thumbprint (RFC 7638) for key binding.

        Returns:
            Base64url-encoded SHA-256 thumbprint
        """
        jwk = self.get_public_jwk()

        # Per RFC 7638: Sort keys alphabetically and remove optional members
        # For EC keys: crv, kty, x, y
        canonical = json.dumps(
            {"crv": jwk["crv"], "kty": jwk["kty"], "x": jwk["x"], "y": jwk["y"]},
            separators=(",", ":"),
            sort_keys=True,
        )

        digest = hashlib.sha256(canonical.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    def generate_proof(
        self,
        http_method: str,
        http_uri: str,
        access_token: str | None = None,
        nonce: str | None = None,
    ) -> str:
        """
        Generate DPoP proof for a request.

        Args:
            http_method: HTTP method (GET, POST, etc.)
            http_uri: Full URI of the request
            access_token: Access token (for resource requests, adds ath claim)
            nonce: Server-provided nonce (if required)

        Returns:
            DPoP proof as JWT string
        """
        # Build header with public key
        header = {
            "typ": "dpop+jwt",
            "alg": self.algorithm,
            "jwk": self.get_public_jwk(),
        }

        # Build payload with required claims
        payload = {
            "jti": secrets.token_urlsafe(16),  # Unique identifier
            "htm": http_method.upper(),  # HTTP method
            "htu": http_uri,  # HTTP URI
            "iat": int(datetime.now(UTC).timestamp()),  # Issued at
        }

        # Add access token hash if binding to access token
        if access_token:
            ath = hashlib.sha256(access_token.encode()).digest()
            payload["ath"] = base64.urlsafe_b64encode(ath).rstrip(b"=").decode()

        # Add nonce if provided by server
        if nonce:
            payload["nonce"] = nonce

        # Sign with ES256
        token = jwt.encode(
            payload,
            self.private_key,
            algorithm=self.algorithm,
            headers=header,
        )

        return token


class DPoPReplayCache:
    """
    In-memory cache for DPoP jti replay protection.

    Production deployments should use Redis or similar distributed cache.
    """

    def __init__(self, max_size: int = 10000) -> None:
        """
        Initialize replay cache.

        Args:
            max_size: Maximum number of jti values to store
        """
        self._cache: set[str] = set()
        self._max_size = max_size

    def has_been_used(self, jti: str) -> bool:
        """Check if jti has been used before."""
        return jti in self._cache

    def mark_used(self, jti: str) -> None:
        """Mark jti as used."""
        # Simple eviction: clear half when full
        if len(self._cache) >= self._max_size:
            # In production, use LRU or TTL-based eviction
            self._cache.clear()
            logger.warning("DPoP replay cache cleared due to size limit")

        self._cache.add(jti)


def verify_dpop_proof(
    proof: str,
    http_method: str,
    http_uri: str,
    access_token: str | None = None,
    jti_cache: DPoPReplayCache | None = None,
    max_age_seconds: int = 300,
) -> dict[str, Any]:
    """
    Verify DPoP proof.

    Args:
        proof: DPoP proof JWT string
        http_method: Expected HTTP method
        http_uri: Expected HTTP URI
        access_token: Access token (for ath verification)
        jti_cache: Cache for replay protection
        max_age_seconds: Maximum age of proof in seconds

    Returns:
        Dict with:
            - valid: bool
            - claims: dict (if valid)
            - error: str (if invalid)
    """
    try:
        # Decode without verification to get header
        unverified_header = jwt.get_unverified_header(proof)

        # Validate header
        if unverified_header.get("typ") != "dpop+jwt":
            return {"valid": False, "error": "Invalid typ: must be dpop+jwt"}

        if unverified_header.get("alg") != "ES256":
            return {"valid": False, "error": "Invalid alg: only ES256 supported"}

        jwk = unverified_header.get("jwk")
        if not jwk:
            return {"valid": False, "error": "Missing jwk in header"}

        # Reconstruct public key from JWK
        public_key = cast(EllipticCurvePublicKey, ECAlgorithm.from_jwk(jwk))

        # Verify signature and decode
        payload = jwt.decode(
            proof,
            public_key,
            algorithms=["ES256"],
            options={"verify_aud": False},  # DPoP doesn't use aud
        )

        # Validate required claims
        if "jti" not in payload:
            return {"valid": False, "error": "Missing jti claim"}

        if "htm" not in payload:
            return {"valid": False, "error": "Missing htm claim"}

        if "htu" not in payload:
            return {"valid": False, "error": "Missing htu claim"}

        if "iat" not in payload:
            return {"valid": False, "error": "Missing iat claim"}

        # Validate htm (HTTP method)
        if payload["htm"].upper() != http_method.upper():
            return {"valid": False, "error": f"HTTP method mismatch: expected {http_method}, got {payload['htm']}"}

        # Validate htu (HTTP URI)
        if payload["htu"] != http_uri:
            return {"valid": False, "error": f"HTTP URI mismatch: expected {http_uri}, got {payload['htu']}"}

        # Validate iat (not too old)
        now = int(datetime.now(UTC).timestamp())
        if now - payload["iat"] > max_age_seconds:
            return {"valid": False, "error": f"Proof expired (iat too old, max_age={max_age_seconds}s)"}

        # Validate ath if access_token provided
        if access_token:
            expected_ath = hashlib.sha256(access_token.encode()).digest()
            expected_ath_b64 = base64.urlsafe_b64encode(expected_ath).rstrip(b"=").decode()
            if payload.get("ath") != expected_ath_b64:
                return {"valid": False, "error": "Access token hash (ath) mismatch"}

        # Check for replay if cache provided
        if jti_cache:
            if jti_cache.has_been_used(payload["jti"]):
                return {"valid": False, "error": "Replay attack detected: jti already used"}
            jti_cache.mark_used(payload["jti"])

        return {"valid": True, "claims": payload, "jwk": jwk}

    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "Proof signature expired"}
    except jwt.InvalidTokenError as e:
        return {"valid": False, "error": f"Invalid proof: {e}"}
    except Exception as e:
        logger.error(f"DPoP verification error: {e}", exc_info=True)
        return {"valid": False, "error": f"Verification error: {e}"}


def create_dpop_bound_token(
    original_claims: dict[str, Any],
    dpop_jwk: dict[str, Any],
) -> dict[str, Any]:
    """
    Create DPoP-bound token claims with cnf (confirmation) claim.

    This is used by authorization servers to bind access tokens
    to the client's DPoP public key.

    Args:
        original_claims: Original token claims (sub, aud, etc.)
        dpop_jwk: DPoP public key as JWK

    Returns:
        Token claims with cnf.jkt (JWK thumbprint) added
    """
    # Calculate JWK thumbprint (RFC 7638)
    # For EC keys: crv, kty, x, y
    canonical = json.dumps(
        {
            "crv": dpop_jwk["crv"],
            "kty": dpop_jwk["kty"],
            "x": dpop_jwk["x"],
            "y": dpop_jwk["y"],
        },
        separators=(",", ":"),
        sort_keys=True,
    )

    thumbprint = hashlib.sha256(canonical.encode()).digest()
    jkt = base64.urlsafe_b64encode(thumbprint).rstrip(b"=").decode()

    # Add confirmation claim
    claims = {**original_claims}
    claims["cnf"] = {"jkt": jkt}

    return claims


# ============================================================================
# DPoP Enforcement (RFC 9449) - Extracted from AuthMiddleware
# ============================================================================


@dataclass
class DPoPVerificationResult:
    """
    Result of DPoP verification.

    Returned from DPoPEnforcer.verify() operations.
    """

    valid: bool
    """Whether the DPoP verification passed."""

    error: str | None
    """Error message if verification failed, None otherwise."""

    dpop_bound: bool = False
    """Whether the token was DPoP-bound (had cnf.jkt claim)."""


class DPoPEnforcer:
    """
    DPoP (RFC 9449) sender-constraint verification enforcer.

    Extracted from AuthMiddleware to follow Single Responsibility Principle.
    Handles DPoP proof verification and token binding validation.

    Behavior (depends on self.required):
    - If required=True: ALL tokens require DPoP proof (strict mode)
    - If required=False (default):
      - Tokens with cnf.jkt claim (DPoP-bound): DPoP proof is REQUIRED
      - Tokens without cnf claim: DPoP proof is optional (verified if provided)

    Usage:
        enforcer = DPoPEnforcer(replay_cache=cache, required=False)
        result = enforcer.verify(
            token_payload={"sub": "user:alice", "cnf": {"jkt": "..."}},
            dpop_proof=proof,
            http_method="POST",
            http_uri="https://api.example.com/resource",
            access_token=token,
        )
        if not result.valid:
            raise AuthenticationError(result.error)
    """

    def __init__(
        self,
        replay_cache: "DPoPReplayCache | None" = None,
        required: bool = False,
    ) -> None:
        """
        Initialize DPoPEnforcer.

        Args:
            replay_cache: DPoP jti replay cache for replay protection (RFC 9449)
            required: If True, ALL tokens require DPoP proof (strict mode).
                     If False (default), only tokens with cnf.jkt claim require DPoP.
        """
        self.replay_cache = replay_cache
        self.required = required

    def verify(
        self,
        token_payload: dict[str, Any],
        dpop_proof: str | None,
        http_method: str,
        http_uri: str,
        access_token: str,
    ) -> DPoPVerificationResult:
        """
        Verify DPoP proof for a token.

        Args:
            token_payload: Decoded JWT payload (must include cnf claim if DPoP-bound)
            dpop_proof: DPoP proof JWT from request header (may be None)
            http_method: HTTP method of the request (GET, POST, etc.)
            http_uri: Full HTTP URI of the request
            access_token: The access token being verified (for ath claim)

        Returns:
            DPoPVerificationResult with validation result
        """
        # Check if token is DPoP-bound (has cnf.jkt claim)
        cnf = token_payload.get("cnf")
        is_dpop_bound = cnf is not None and "jkt" in cnf

        # Check if DPoP is required (either by enforcement mode or token binding)
        dpop_required_for_this_request = self.required or is_dpop_bound

        if dpop_required_for_this_request and not dpop_proof:
            # DPoP is required (by enforcement or token binding) but no proof provided
            reason = "enforcement mode" if self.required else "sender-constrained token"
            logger.warning(
                f"DPoP proof required ({reason}) but not provided",
                extra={
                    "sub": token_payload.get("sub"),
                    "dpop_required": self.required,
                    "is_dpop_bound": is_dpop_bound,
                },
            )
            return DPoPVerificationResult(
                valid=False,
                error=f"DPoP proof required ({reason})",
                dpop_bound=is_dpop_bound,
            )

        if dpop_proof:
            # Verify the DPoP proof
            dpop_result = verify_dpop_proof(
                proof=dpop_proof,
                http_method=http_method,
                http_uri=http_uri,
                access_token=access_token if is_dpop_bound else None,
                jti_cache=self.replay_cache,
            )

            if not dpop_result["valid"]:
                logger.warning(
                    "DPoP proof verification failed",
                    extra={
                        "error": dpop_result.get("error"),
                        "sub": token_payload.get("sub"),
                    },
                )
                return DPoPVerificationResult(
                    valid=False,
                    error=f"DPoP verification failed: {dpop_result.get('error', 'Unknown error')}",
                    dpop_bound=is_dpop_bound,
                )

            # If token is DPoP-bound, verify the key thumbprint matches
            if is_dpop_bound and cnf:
                expected_jkt = cnf["jkt"]
                proof_jwk = dpop_result.get("jwk")

                if proof_jwk:
                    # Calculate thumbprint of the proof's JWK
                    canonical = json.dumps(
                        {
                            "crv": proof_jwk["crv"],
                            "kty": proof_jwk["kty"],
                            "x": proof_jwk["x"],
                            "y": proof_jwk["y"],
                        },
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                    thumbprint_bytes = hashlib.sha256(canonical.encode()).digest()
                    actual_jkt = base64.urlsafe_b64encode(thumbprint_bytes).rstrip(b"=").decode()

                    if actual_jkt != expected_jkt:
                        logger.warning(
                            "DPoP key thumbprint mismatch",
                            extra={
                                "expected": expected_jkt[:8] + "...",
                                "actual": actual_jkt[:8] + "...",
                                "sub": token_payload.get("sub"),
                            },
                        )
                        return DPoPVerificationResult(
                            valid=False,
                            error="DPoP key thumbprint does not match token binding",
                            dpop_bound=is_dpop_bound,
                        )

            logger.info(
                "DPoP verification successful",
                extra={
                    "sub": token_payload.get("sub"),
                    "dpop_bound": is_dpop_bound,
                },
            )

        return DPoPVerificationResult(
            valid=True,
            error=None,
            dpop_bound=is_dpop_bound,
        )
