# Service Down Alert Runbook

## Overview

This alert fires when a core service is completely unavailable.

## Symptoms

- Complete service outage
- All health checks failing
- No traffic being processed

---

## ServiceDown

### Description
Service is not responding to any requests.

### Impact
**Critical** - Complete service outage.

### Resolution
1. Check pod status: `kubectl get pods -l app=<service>`
2. Review recent deployments
3. Check for infrastructure issues (node failures)
4. Consider immediate rollback

### Escalation
Page on-call immediately. This is a P1 incident.
