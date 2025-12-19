"""
Token Validator

Extracted from AuthMiddleware (Phase 2.2 SRP decomposition).
Handles JWT token verification with denylist and DPoP support.

Responsibilities:
- Basic JWT token verification via user provider
- Token denylist checking (OWASP Session Management)
- DPoP (RFC 9449) sender-constraint verification
"""

import base64
import hashlib
import json
from typing import Any

from mcp_server_langgraph.auth.dpop import DPoPReplayCache, verify_dpop_proof
from mcp_server_langgraph.auth.token_denylist import TokenDenylist
from mcp_server_langgraph.auth.user_provider import TokenVerification, UserProvider
from mcp_server_langgraph.observability.telemetry import logger


class TokenValidator:
    """
    Validates JWT tokens with optional DPoP support.

    Extracted from AuthMiddleware to follow Single Responsibility Principle.
    This class focuses solely on token verification logic.

    Features:
    - Delegates basic JWT verification to UserProvider
    - Checks token denylist for revoked tokens
    - Supports DPoP (RFC 9449) sender-constraint verification
    - Configurable enforcement modes (optional vs required DPoP)
    """

    def __init__(
        self,
        user_provider: UserProvider,
        token_denylist: TokenDenylist | None = None,
        dpop_required: bool = False,
        dpop_replay_cache: DPoPReplayCache | None = None,
    ) -> None:
        """
        Initialize TokenValidator.

        Args:
            user_provider: Provider for JWT verification (InMemory, Keycloak, etc.)
            token_denylist: Optional denylist for immediate token revocation
            dpop_required: If True, ALL tokens require DPoP proof (strict mode)
            dpop_replay_cache: Cache for preventing DPoP proof replay attacks
        """
        self.user_provider = user_provider
        self.token_denylist = token_denylist
        self.dpop_required = dpop_required
        self.dpop_replay_cache = dpop_replay_cache

    async def verify_token(self, token: str) -> TokenVerification:
        """
        Verify and decode JWT token.

        Supports both self-issued tokens (InMemoryUserProvider) and
        Keycloak-issued tokens (KeycloakUserProvider).

        Security:
        - Checks token denylist for immediate revocation (OWASP best practice)
        - Tokens added to denylist on logout are rejected here

        Args:
            token: JWT token to verify

        Returns:
            TokenVerification with validation result
        """
        # Delegate to user provider (returns Pydantic TokenVerification)
        result = await self.user_provider.verify_token(token)

        if result.valid and result.payload:
            # Check token denylist for immediate revocation (OWASP Session Management)
            if self.token_denylist:
                jti = result.payload.get("jti")
                if jti and await self.token_denylist.is_denied(jti):
                    logger.warning(
                        "Token rejected (in denylist)",
                        extra={"jti": jti[:8] + "..." if len(jti) > 8 else jti},
                    )
                    return TokenVerification(valid=False, error="Token has been revoked")

            logger.info("Token verified", extra={"sub": result.payload.get("sub")})
        else:
            logger.warning("Token verification failed", extra={"error": result.error})

        return result

    async def verify_token_with_dpop(
        self,
        token: str,
        dpop_proof: str | None,
        http_method: str,
        http_uri: str,
    ) -> TokenVerification:
        """
        Verify JWT token with optional DPoP (RFC 9449) sender-constraint verification.

        DPoP provides token binding by requiring clients to prove possession of a
        private key. This prevents token theft and replay attacks.

        Behavior (depends on self.dpop_required):
        - If dpop_required=True: ALL tokens require DPoP proof (strict mode)
        - If dpop_required=False (default):
          - Tokens with cnf.jkt claim (DPoP-bound): DPoP proof is REQUIRED
          - Tokens without cnf claim: DPoP proof is optional (verified if provided)

        Args:
            token: JWT access token to verify
            dpop_proof: DPoP proof JWT from request header (may be None)
            http_method: HTTP method of the request (GET, POST, etc.)
            http_uri: Full HTTP URI of the request

        Returns:
            TokenVerification with validation result
        """
        # First, verify the token itself
        result = await self.verify_token(token)
        if not result.valid or not result.payload:
            return result

        # Check if token is DPoP-bound (has cnf.jkt claim)
        cnf = result.payload.get("cnf")
        is_dpop_bound = cnf is not None and "jkt" in cnf

        # Check if DPoP is required (either by enforcement mode or token binding)
        dpop_required_for_this_request = self.dpop_required or is_dpop_bound

        if dpop_required_for_this_request and not dpop_proof:
            # DPoP is required (by enforcement or token binding) but no proof provided - reject
            reason = "enforcement mode" if self.dpop_required else "sender-constrained token"
            logger.warning(
                f"DPoP proof required ({reason}) but not provided",
                extra={
                    "sub": result.payload.get("sub"),
                    "dpop_required": self.dpop_required,
                    "is_dpop_bound": is_dpop_bound,
                },
            )
            return TokenVerification(
                valid=False,
                error=f"DPoP proof required ({reason})",
            )

        if dpop_proof:
            # Verify the DPoP proof
            dpop_result = verify_dpop_proof(
                proof=dpop_proof,
                http_method=http_method,
                http_uri=http_uri,
                access_token=token if is_dpop_bound else None,
                jti_cache=self.dpop_replay_cache,
            )

            if not dpop_result["valid"]:
                logger.warning(
                    "DPoP proof verification failed",
                    extra={
                        "error": dpop_result.get("error"),
                        "sub": result.payload.get("sub"),
                    },
                )
                return TokenVerification(
                    valid=False,
                    error=f"DPoP verification failed: {dpop_result.get('error', 'Unknown error')}",
                )

            # If token is DPoP-bound, verify the key thumbprint matches
            if is_dpop_bound and cnf:
                expected_jkt = cnf["jkt"]
                proof_jwk = dpop_result.get("jwk")

                if proof_jwk:
                    # Calculate thumbprint of the proof's JWK
                    actual_jkt = self._calculate_jwk_thumbprint(proof_jwk)

                    if actual_jkt != expected_jkt:
                        logger.warning(
                            "DPoP key thumbprint mismatch",
                            extra={
                                "expected": expected_jkt[:8] + "...",
                                "actual": actual_jkt[:8] + "...",
                                "sub": result.payload.get("sub"),
                            },
                        )
                        return TokenVerification(
                            valid=False,
                            error="DPoP key thumbprint does not match token binding",
                        )

            logger.info(
                "Token verified with DPoP",
                extra={
                    "sub": result.payload.get("sub"),
                    "dpop_bound": is_dpop_bound,
                },
            )

        return result

    def _calculate_jwk_thumbprint(self, jwk: dict[str, Any]) -> str:
        """
        Calculate the JWK thumbprint (RFC 7638) for a given JWK.

        Args:
            jwk: JSON Web Key dictionary

        Returns:
            Base64url-encoded SHA-256 thumbprint
        """
        # Create canonical representation for EC key
        canonical = json.dumps(
            {
                "crv": jwk["crv"],
                "kty": jwk["kty"],
                "x": jwk["x"],
                "y": jwk["y"],
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        thumbprint = hashlib.sha256(canonical.encode()).digest()
        return base64.urlsafe_b64encode(thumbprint).rstrip(b"=").decode()
