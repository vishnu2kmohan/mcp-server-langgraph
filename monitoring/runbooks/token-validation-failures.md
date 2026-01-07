# Token Validation Failures Alert Runbook

## Overview

This alert fires when JWT token validation failures are occurring at high rate.

## Symptoms

- Users receiving 401 Unauthorized errors
- Failed API requests
- Authentication issues

---

## TokenValidationFailures

### Description
High rate of JWT token validation failures.

### Impact
**Warning** - Users may be unable to access the service.

### Resolution
1. Check Keycloak JWKS endpoint availability
2. Verify token issuer configuration
3. Check for clock skew between services
4. Review token signing key rotation

### Escalation
Page on-call if affecting many users.
