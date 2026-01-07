# Infisical Down Alert Runbook

## Overview

This alert fires when the Infisical secrets management service is unreachable.

## Symptoms

- Secret retrieval failures
- Application startup failures
- Configuration refresh errors

---

## InfisicalDown

### Description
Infisical service is not responding to health checks.

### Impact
**Critical** - Secrets cannot be retrieved, new deployments may fail.

### Resolution
1. Check Infisical pod status: `kubectl get pods -l app=infisical`
2. Verify network connectivity to Infisical
3. Check Infisical logs for errors
4. Fallback to environment variables if configured

### Escalation
Page on-call for secrets infrastructure issues.
