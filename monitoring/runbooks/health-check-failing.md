# Health Check Failing Alert Runbook

## Overview

This alert fires when application health checks are failing, indicating service degradation.

## Symptoms

- Health endpoint returning non-200 status
- Kubernetes readiness/liveness probe failures
- Service removed from load balancer

---

## HealthCheckFailing

### Description
Application health check endpoint is failing.

### Impact
**Critical** - Service may be unhealthy and traffic may be affected.

### Resolution
1. Check pod status: `kubectl get pods -l app=mcp-server-langgraph`
2. Review health endpoint: `curl localhost:8000/health`
3. Check application logs for errors
4. Verify dependency connectivity (Redis, PostgreSQL, Keycloak)

### Escalation
Page on-call if service is degraded.
