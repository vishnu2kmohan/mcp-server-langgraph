# Keycloak Token Refresh Alert Runbook

## Overview

This alert fires when token refresh operations are failing or experiencing issues.

## Symptoms

- Users being logged out unexpectedly
- Token refresh failures
- Session expiry issues

---

## KeycloakTokenRefreshFailures

### Description
Token refresh operations are failing at high rate.

### Impact
**Warning** - Users may experience authentication interruptions.

### Resolution
1. Check Keycloak token configuration
2. Verify client session settings
3. Review token lifetime configuration
4. Check for clock skew between services

### Escalation
Notify identity team if widespread.
