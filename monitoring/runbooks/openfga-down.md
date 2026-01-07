# OpenFGA Down Alert Runbook

## Overview

This alert fires when the OpenFGA authorization service is unreachable.

## Symptoms

- Authorization check failures
- Access denied errors
- Permission evaluation timeouts

---

## OpenFGADown

### Description
OpenFGA service is not responding to health checks.

### Impact
**Critical** - Authorization checks failing, access control compromised.

### Resolution
1. Check OpenFGA pod status: `kubectl get pods -l app=openfga`
2. Review OpenFGA logs: `kubectl logs -l app=openfga --tail=100`
3. Verify PostgreSQL connectivity (OpenFGA backend)
4. Check network policies

### Escalation
Page on-call immediately - authorization is critical.
