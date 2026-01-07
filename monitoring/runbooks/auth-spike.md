# Authentication Spike Alert Runbook

## Overview

This alert fires when there's an unusual spike in authentication attempts, which may indicate a brute force attack or system misconfiguration.

## Symptoms

- Sudden increase in authentication requests
- High rate of failed login attempts
- Increased load on Keycloak/auth services

---

## AuthenticationSpike

### Description
Authentication attempt rate has increased significantly above baseline.

### Impact
**Warning** - May indicate attack or misconfiguration.

### Resolution
1. Check authentication logs: `kubectl logs -l app=keycloak --tail=200`
2. Review source IPs of authentication attempts
3. Check for recent deployment changes
4. Verify client application behavior

### Escalation
If attack suspected, notify security team immediately.
