# Keycloak Slow Alert Runbook

## Overview

This alert fires when Keycloak authentication service response times are elevated.

## Symptoms

- Slow login/logout operations
- Token refresh delays
- Increased authentication latency

---

## KeycloakSlow

### Description
Keycloak response times exceed acceptable thresholds.

### Impact
**Warning** - Authentication operations delayed.

### Resolution
1. Check Keycloak pod resources: `kubectl top pod -l app=keycloak`
2. Review Keycloak database performance
3. Check for excessive session count
4. Consider Keycloak horizontal scaling

### Escalation
Notify identity team for investigation.
