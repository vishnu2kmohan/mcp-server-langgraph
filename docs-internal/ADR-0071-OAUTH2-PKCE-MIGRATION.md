# ADR-0071: OAuth2 Authorization Code + PKCE Migration

**Status**: Implemented
**Date**: 2025-12-15
**Author**: Claude Code (Opus 4.5) + Vishnu Mohan
**Related**: RFC 9700, OWASP Session Management, Keycloak Integration

---

## Context

Comprehensive security audit of Keycloak session management revealed several critical security gaps in the authentication flow. The most significant issue is the use of Resource Owner Password Credentials (ROPC) grant type, which is explicitly prohibited by RFC 9700 (OAuth 2.0 Security Best Current Practice).

### Problem Statement

**Critical Security Issues Identified:**

1. **ROPC Usage (RFC 9700 Violation)** - CRITICAL
   - Login endpoint (`POST /api/v1/user/login`) uses `grant_type: password`
   - RFC 9700 explicitly states: "The Resource Owner Password Credentials flow MUST NOT be used"
   - Security risk: Exposes user credentials to the application

2. **Missing Issuer (`iss`) Validation** - CRITICAL
   - JWT tokens were decoded without validating the issuer claim
   - Risk: Tokens from any Keycloak realm or other IdPs could be accepted

3. **Missing Issued-At (`iat`) Validation** - MEDIUM
   - Tokens with future `iat` timestamps could be accepted
   - Risk: Potential for token replay attacks

4. **No Token Denylist for Logout** - MEDIUM
   - Logout only revokes tokens with Keycloak, not locally
   - Risk: Token could be used during propagation delay

5. **Duplicate User Extraction Logic** - HIGH (DRY Violation)
   - Same JWT extraction code in `middleware.py` and `auth_request_middleware.py`
   - Risk: Maintenance burden and potential divergence

## Decision

Implement comprehensive security remediation following TDD principles:

1. **Migrate from ROPC to Authorization Code + PKCE flow**
2. **Add issuer and issued-at claim validation**
3. **Implement Redis-backed token denylist for immediate revocation**
4. **Consolidate user extraction logic into shared module**

## Solution Architecture

### Authentication Flow Comparison

```
BEFORE (ROPC - INSECURE):
┌─────────────┐     username/password     ┌─────────────┐
│   Frontend  │ ───────────────────────→  │   Backend   │
└─────────────┘                           └──────┬──────┘
                                                 │ ROPC grant
                                                 ↓
                                          ┌─────────────┐
                                          │  Keycloak   │
                                          └─────────────┘

AFTER (Authorization Code + PKCE - SECURE):
┌─────────────┐                           ┌─────────────┐
│   Frontend  │ ──→ GET /auth/login ───→  │   Backend   │
└──────┬──────┘                           └──────┬──────┘
       │                                         │ Redirect with PKCE
       ↓                                         ↓
┌─────────────┐  ←────── Auth + Code ─────────────┐
│  Keycloak   │                            │
└──────┬──────┘                            │
       │                                   │
       └────→ GET /auth/callback ──────────┘
              (exchange code with verifier)
```

### Implemented Components

#### 1. JWT Validation Enhancements (`auth/keycloak.py`)

```python
# Added issuer and iat validation
payload = jwt.decode(
    token,
    public_key,
    algorithms=["RS256"],
    audience=self.config.client_id,
    issuer=f"{self.config.server_url}/realms/{self.config.realm}",  # NEW
    options={
        "verify_signature": True,
        "verify_exp": True,
        "verify_aud": True,
        "verify_iss": True,  # NEW
        "verify_iat": True,  # NEW
    },
)

# Additional future iat check (30 second tolerance)
if iat > now + clock_skew_tolerance:
    raise jwt.ImmatureSignatureError("Token issued in the future")
```

#### 2. Shared JWT Utilities (`auth/jwt_utils.py`)

```python
def extract_user_from_jwt_payload(payload: dict) -> dict:
    """
    Single source of truth for user extraction from JWT.

    Handles:
    - Keycloak tokens (preferred_username, realm_access.roles)
    - InMemory tokens (username, roles)
    - Worker-safe ID patterns (test_gw*_username)

    Returns:
        user_id, keycloak_id, username, roles, email
    """
```

#### 3. Token Denylist (`auth/token_denylist.py`)

```python
class TokenDenylist(ABC):
    """Abstract interface for token denylist."""
    async def add(self, jti: str, expires_at: datetime) -> None: ...
    async def is_denied(self, jti: str) -> bool: ...

class InMemoryTokenDenylist(TokenDenylist):
    """Development/testing - data lost on restart."""

class RedisTokenDenylist(TokenDenylist):
    """Production - persistent with TTL-based cleanup."""
```

#### 4. OAuth2 PKCE Utilities (`auth/oauth2.py`)

```python
def generate_code_verifier() -> str:
    """Generate 86-char PKCE verifier (RFC 7636)."""

def generate_code_challenge(verifier: str) -> str:
    """Generate S256 challenge from verifier."""

def build_authorization_url(...) -> str:
    """Build Keycloak auth URL with PKCE params."""
```

#### 5. OAuth2 API Endpoints (`api/v1/auth.py`)

```
GET  /api/v1/auth/login     # Initiate OAuth2 + PKCE flow
GET  /api/v1/auth/callback  # Exchange code for tokens
POST /api/v1/auth/refresh   # Refresh access token
```

## Implementation Details

### Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `auth/jwt_utils.py` | Shared JWT extraction | ~80 |
| `auth/token_denylist.py` | Token denylist (InMemory + Redis) | ~200 |
| `auth/oauth2.py` | PKCE utilities | ~150 |
| `api/v1/auth.py` | OAuth2 endpoints | ~280 |
| `tests/unit/auth/test_jwt_utils.py` | JWT utils tests | ~120 |
| `tests/unit/auth/test_token_denylist.py` | Denylist tests | ~240 |
| `tests/unit/auth/test_oauth2.py` | PKCE tests | ~200 |

### Files Modified

| File | Changes |
|------|---------|
| `auth/keycloak.py` | Added iss/iat validation, Client Credentials grant for admin token |
| `auth/middleware.py` | Added denylist check, use shared jwt_utils |
| `api/auth_request_middleware.py` | Use shared jwt_utils |
| `api/v1/user.py` | Deprecated ROPC login, denylist on logout |
| `core/dependencies.py` | Added get_token_denylist |
| `core/config.py` | Added oauth2_auth_callback_uri, session_idle_seconds |
| `studio/frontend/LoginPage.tsx` | Added SSO login button for PKCE flow |
| `studio/frontend/AuthCallbackPage.tsx` | NEW: Handles PKCE callback |
| `studio/frontend/router/index.tsx` | Added /auth/callback route |

## Test Coverage

### Test Results

```
tests/unit/auth/test_keycloak.py - 89 passed
tests/unit/auth/test_jwt_utils.py - 11 passed
tests/unit/auth/test_token_denylist.py - 14 passed
tests/unit/auth/test_oauth2.py - 15 passed
tests/api/test_user_api.py - 11 passed (includes logout denylist tests)
```

### New Security Tests

- `test_verify_token_with_wrong_issuer_raises_error`
- `test_verify_token_with_correct_issuer_succeeds`
- `test_verify_token_with_future_iat_raises_error`
- `test_logout_adds_token_to_denylist`
- `test_generate_code_challenge_uses_sha256` (RFC 7636 test vector)

## Migration Guide

### For Frontend Developers

**Before (ROPC - deprecated):**
```javascript
// DO NOT USE
const response = await fetch('/api/v1/user/login', {
  method: 'POST',
  body: JSON.stringify({ username, password }),
});
```

**After (Authorization Code + PKCE):**
```javascript
// Redirect to initiate login
window.location.href = '/api/v1/auth/login';

// Handle callback (tokens returned as JSON)
// Store tokens securely (memory only, per OWASP)
```

### For Backend Services

**Token Refresh:**
```javascript
const response = await fetch('/api/v1/auth/refresh', {
  method: 'POST',
  body: JSON.stringify({ refresh_token }),
});
```

## Security References

- [RFC 9700: OAuth 2.0 Security Best Current Practice](https://datatracker.ietf.org/doc/rfc9700/)
- [RFC 7636: Proof Key for Code Exchange (PKCE)](https://datatracker.ietf.org/doc/rfc7636/)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)

## Consequences

### Positive

1. **RFC 9700 Compliant** - No more ROPC usage
2. **Token Revocation** - Immediate logout via denylist
3. **Stronger Validation** - Issuer and iat claims verified
4. **DRY Principle** - Single source of truth for JWT extraction
5. **Maintainability** - Clear separation of concerns

### Negative

1. **Breaking Change** - Frontend must migrate to new flow
2. **Complexity** - PKCE adds state management requirements
3. **Cookies** - PKCE flow uses secure httpOnly cookies

### Mitigations

1. **Gradual Migration** - ROPC endpoint deprecated but still functional
2. **Documentation** - Clear migration guide provided
3. **Backward Compatibility** - Both flows work during transition

## Deprecation Timeline

| Version | Action |
|---------|--------|
| Current | ROPC deprecated, OAuth2+PKCE available |
| v2.0 | ROPC removed, OAuth2+PKCE required |

## Verification

Run security tests:
```bash
uv run pytest tests/unit/auth/ -v -k "issuer or iat or denylist or oauth2 or pkce"
```

## Implementation Status (Updated 2025-12-15)

### Audit Summary

A comprehensive audit of all authentication methods across the codebase was performed:

| Component | Status | Notes |
|-----------|--------|-------|
| **Frontend (LoginPage.tsx)** | ✅ Compliant | Uses OAuth2+PKCE via SSO redirect |
| **Frontend (authSlice.ts)** | ✅ Compliant | Token management with proper cleanup |
| **Frontend (baseQueryWithReauth.ts)** | ✅ Compliant | 401 handling with token refresh |
| **Backend (/api/v1/auth/*)** | ✅ Compliant | OAuth2+PKCE endpoints implemented |
| **Backend (/api/v1/login)** | ⚠️ Deprecated | ROPC with deprecation warning, will be removed in v2.0 |
| **Keycloak (keycloak.py)** | ⚠️ Deprecated | `authenticate_user()` emits DeprecationWarning |
| **E2E Tests (journeys/*)** | ✅ Compliant | Use Token Exchange/PKCE with ROPC fallback |
| **Test Fixtures (conftest.py)** | ✅ Compliant | Auth hierarchy: Token Exchange → Client Credentials → ROPC |

### ROPC Deprecation Warnings Implemented

1. **`authenticate_user()` in `keycloak.py`**:
   ```python
   warnings.warn(
       "authenticate_user() uses ROPC which is deprecated per RFC 9700. "
       "Use Authorization Code + PKCE for user auth, or Client Credentials for "
       "service-to-service auth. This method will be removed in a future version.",
       DeprecationWarning,
       stacklevel=2,
   )
   ```

2. **`/api/v1/login` endpoint in `user.py`**:
   - FastAPI `deprecated=True` flag set
   - Logger warning emitted on every call

3. **`login()` in `real_clients.py` (E2E tests)**:
   - DeprecationWarning emitted with RFC 9700 reference

4. **`get_token()` in `test_keycloak_openfga_auth_flow.py`**:
   - DeprecationWarning suggesting Token Exchange alternative

### Remaining ROPC Usage (29 files identified)

Most ROPC usage is in:
- **Test code**: Using auth hierarchy with modern methods first
- **Setup scripts**: Administrative bootstrapping (acceptable)
- **Documentation**: Examples marked as deprecated

### Files with Deprecation Warnings

| File | Method | Deprecation Warning |
|------|--------|-------------------|
| `src/mcp_server_langgraph/auth/keycloak.py` | `authenticate_user()` | ✅ Added |
| `src/mcp_server_langgraph/api/v1/user.py` | `/login` endpoint | ✅ Present |
| `tests/e2e/real_clients.py` | `login()` | ✅ Present |
| `tests/e2e/journeys/test_keycloak_openfga_auth_flow.py` | `get_token()` | ✅ Present |

### Keycloak Client Configuration (Updated 2025-12-15)

**ROPC is now DISABLED** in `tests/e2e/default-realm.json`:

```json
{
  "clientId": "mcp-server",
  "directAccessGrantsEnabled": false,
  "authorizationServicesEnabled": true,
  "attributes": {
    "oauth2.device.authorization.grant.enabled": "true"
  }
}
```

**New Authentication Methods Available:**

| Method | RFC | Use Case |
|--------|-----|----------|
| **Token Exchange** | RFC 8693 | User impersonation without password |
| **Device Authorization** | RFC 8628 | CLI/headless authentication |
| **Client Credentials** | RFC 6749 | Service-to-service authentication |
| **Authorization Code + PKCE** | RFC 7636 | Browser-based user authentication |
| **DPoP (Token Binding)** | RFC 9449 | Sender-constrained tokens, replay protection |

**Authorization Settings for Token Exchange:**
- `authorizationServicesEnabled: true` - Required for token exchange
- Authorization policies configured for service account token exchange
- Scopes: `token-exchange`, `impersonate`

### Test Coverage

RFC 9700 compliance tests added to `tests/unit/auth/test_keycloak.py`:
- `test_authenticate_user_emits_deprecation_warning` ✅
- `test_authenticate_user_deprecation_warning_suggests_alternative` ✅
- `test_authenticate_user_still_works_despite_deprecation` ✅

### Device Authorization Grant (RFC 8628)

New module: `src/mcp_server_langgraph/auth/device_auth.py`

**Purpose:** Headless/CLI authentication without user interaction on the client device.

**Classes:**
- `DeviceAuthClient` - OAuth 2.0 Device Authorization client
- `DeviceAuthError`, `AuthorizationPending`, `SlowDown`, `ExpiredToken`, `AccessDenied` - Error classes

**Usage:**
```python
from mcp_server_langgraph.auth.device_auth import DeviceAuthClient, format_user_instructions

client = DeviceAuthClient(
    server_url="https://keycloak.example.com",
    realm="mcp-server",
    client_id="mcp-cli",
)

# Step 1: Request device code
device_response = await client.request_device_code()
print(format_user_instructions(device_response))

# Step 2: Wait for user authorization
tokens = await client.wait_for_authorization(
    device_response["device_code"],
    interval=device_response["interval"],
)
```

**Tests:** `tests/unit/auth/test_device_auth.py` (12 tests)

### DPoP Token Binding (RFC 9449)

New module: `src/mcp_server_langgraph/auth/dpop.py`

**Purpose:** Sender-constrained access tokens that prevent token theft and replay attacks.

**Classes:**
- `DPoPClient` - Generates DPoP proofs using ES256 (ECDSA with P-256)
- `DPoPReplayCache` - In-memory jti cache for replay protection

**Key Functions:**
- `verify_dpop_proof()` - Server-side DPoP proof verification
- `create_dpop_bound_token()` - Create tokens with cnf (confirmation) claim

**Usage (Client):**
```python
from mcp_server_langgraph.auth.dpop import DPoPClient

client = DPoPClient.generate()  # Generates new EC key pair
proof = client.generate_proof(
    http_method="POST",
    http_uri="https://api.example.com/token",
)
headers = {"DPoP": proof}
```

**Usage (Server):**
```python
from mcp_server_langgraph.auth.dpop import verify_dpop_proof, DPoPReplayCache

cache = DPoPReplayCache()
result = verify_dpop_proof(
    proof=request.headers["DPoP"],
    http_method="POST",
    http_uri="https://api.example.com/token",
    jti_cache=cache,
)
if result["valid"]:
    # Process request with verified token binding
    pass
```

**Tests:** `tests/unit/auth/test_dpop.py` (11 tests)

### DPoP Middleware Integration

**Location:** `src/mcp_server_langgraph/auth/middleware.py`

The DPoP verification is integrated into the authentication middleware via the `verify_token_with_dpop()` method:

```python
async def verify_token_with_dpop(
    self,
    token: str,
    dpop_proof: str | None,
    http_method: str,
    http_uri: str,
) -> TokenVerification:
    """
    Verify JWT token with optional DPoP sender-constraint verification.

    Behavior:
    - If token has cnf.jkt claim (DPoP-bound): DPoP proof is REQUIRED
    - If token has no cnf claim: DPoP proof is optional (verified if provided)
    """
```

**Verification Flow:**

1. Verify the base JWT token (signature, exp, aud, iss)
2. Check if token is DPoP-bound (has `cnf.jkt` claim)
3. If DPoP-bound and no proof provided → REJECT
4. If proof provided:
   - Verify DPoP proof signature (ES256)
   - Verify `htm` matches HTTP method
   - Verify `htu` matches HTTP URI
   - Verify `ath` matches token hash (for bound tokens)
   - Check replay cache for `jti`
   - Verify key thumbprint matches `cnf.jkt` (RFC 7638)
5. Return verification result

**Key Thumbprint Verification (RFC 7638):**

```python
# Calculate thumbprint of the proof's JWK
canonical = json.dumps(
    {"crv": proof_jwk["crv"], "kty": proof_jwk["kty"],
     "x": proof_jwk["x"], "y": proof_jwk["y"]},
    separators=(",", ":"), sort_keys=True,
)
thumbprint = hashlib.sha256(canonical.encode()).digest()
actual_jkt = base64.urlsafe_b64encode(thumbprint).rstrip(b"=").decode()

if actual_jkt != expected_jkt:
    return TokenVerification(valid=False, error="DPoP key thumbprint mismatch")
```

**Tests:** `tests/unit/auth/test_dpop_middleware.py` (8 tests)

| Test | Scenario |
|------|----------|
| `test_verify_token_without_dpop_succeeds_for_non_bound_token` | Non-DPoP tokens work without proof |
| `test_verify_dpop_bound_token_without_proof_fails` | DPoP-bound tokens require proof |
| `test_verify_token_with_valid_dpop_proof_succeeds` | Valid proof passes |
| `test_verify_token_with_wrong_dpop_key_fails` | Wrong key is rejected |
| `test_verify_token_with_wrong_http_method_fails` | Method mismatch rejected |
| `test_verify_token_with_wrong_http_uri_fails` | URI mismatch rejected |
| `test_verify_token_with_replayed_dpop_proof_fails` | Replay detection works |
| `test_verify_token_with_optional_dpop_for_non_bound_token` | Optional DPoP verified when provided |

### Device Authorization API Endpoints

**Location:** `src/mcp_server_langgraph/api/v1/auth.py`

Two new endpoints expose the Device Authorization Grant flow:

#### GET /api/v1/auth/device

**Purpose:** Request device authorization code for CLI/headless authentication.

**Response Model:**
```python
class DeviceCodeResponse(BaseModel):
    device_code: str       # Device verification code (for polling)
    user_code: str         # User code to enter at verification_uri
    verification_uri: str  # URL for user to visit
    verification_uri_complete: str | None  # URL with user_code embedded (for QR)
    expires_in: int        # Lifetime of device_code in seconds
    interval: int = 5      # Polling interval in seconds
```

**Example Response:**
```json
{
  "device_code": "GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNhszIySk9eS",
  "user_code": "WDJB-MJHT",
  "verification_uri": "https://keycloak.example.com/device",
  "verification_uri_complete": "https://keycloak.example.com/device?user_code=WDJB-MJHT",
  "expires_in": 600,
  "interval": 5
}
```

#### POST /api/v1/auth/device/token

**Purpose:** Poll for access token after device authorization.

**Request Model:**
```python
class DeviceTokenRequest(BaseModel):
    device_code: str  # Device code from GET /auth/device
```

**Success Response:** Returns `TokenResponse` (access_token, refresh_token, expires_in)

**Error Responses (HTTP 400):**

| Error Code | Description |
|------------|-------------|
| `authorization_pending` | User hasn't completed authorization yet |
| `slow_down` | Client is polling too frequently |
| `expired_token` | Device code has expired |
| `access_denied` | User denied the authorization request |

**Example Error Response:**
```json
{
  "error": "authorization_pending",
  "error_description": "Authorization pending"
}
```

**CLI Integration Pattern:**

```python
import asyncio
from mcp_server_langgraph.auth.device_auth import DeviceAuthClient

client = DeviceAuthClient(
    server_url="https://keycloak.example.com",
    realm="mcp-server",
    client_id="mcp-cli",
)

# Alternative: Use REST API directly
async def cli_login():
    # Step 1: Request device code
    response = await httpx.get("https://api.example.com/api/v1/auth/device")
    device_data = response.json()

    print(f"Visit: {device_data['verification_uri']}")
    print(f"Enter code: {device_data['user_code']}")

    # Step 2: Poll for tokens
    while True:
        await asyncio.sleep(device_data["interval"])
        token_response = await httpx.post(
            "https://api.example.com/api/v1/auth/device/token",
            json={"device_code": device_data["device_code"]},
        )

        if token_response.status_code == 200:
            tokens = token_response.json()
            print(f"Access token: {tokens['access_token'][:20]}...")
            break
        elif token_response.status_code == 400:
            error = token_response.json()
            if error["error"] == "authorization_pending":
                continue  # Keep polling
            elif error["error"] == "slow_down":
                await asyncio.sleep(5)  # Increase interval
                continue
            else:
                raise Exception(f"Auth failed: {error['error']}")
```

**Tests:** `tests/api/test_device_auth_api.py` (9 tests)

| Test | Scenario |
|------|----------|
| `test_device_auth_request_returns_device_code` | Device code returned |
| `test_device_auth_request_includes_verification_uri_complete` | QR-friendly URL included |
| `test_device_auth_request_includes_expires_in` | Expiration time provided |
| `test_device_token_poll_returns_tokens_when_authorized` | Successful token exchange |
| `test_device_token_poll_returns_authorization_pending` | Pending state handled |
| `test_device_token_poll_returns_slow_down` | Rate limiting handled |
| `test_device_token_poll_returns_expired_token` | Expiration handled |
| `test_device_token_poll_returns_access_denied` | Denial handled |
| `test_device_token_poll_validates_device_code` | Input validation |

### Frontend Support Summary

The Studio frontend fully supports all applicable Keycloak authentication capabilities:

| Capability | Frontend Support | Implementation |
|------------|------------------|----------------|
| **OAuth2 + PKCE** | ✅ Native | `LoginPage.tsx` redirects to `/api/v1/auth/login` |
| **Token Callback** | ✅ Native | `AuthCallbackPage.tsx` handles URL fragment tokens |
| **Token Refresh** | ✅ Native | `baseQueryWithReauth.ts` auto-refreshes on 401 |
| **Token Storage** | ✅ Native | `authSlice.ts` manages localStorage persistence |
| **Logout** | ✅ Native | `authSlice.ts` clears all auth storage keys |
| **Device Auth** | N/A | Backend-only (for CLI tools, not browser) |
| **DPoP** | Transparent | Handled in middleware (no frontend changes needed) |

**Note:** Device Authorization Grant is intentionally not exposed in the frontend as it's designed for CLI/headless scenarios where browser-based PKCE flow is not available
