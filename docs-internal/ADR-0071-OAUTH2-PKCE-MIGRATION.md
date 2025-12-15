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
