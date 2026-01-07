# Redis Down Alert Runbook

## Overview

This alert fires when the Redis service is unreachable.

## Symptoms

- Session storage failures
- Caching not working
- Checkpoint storage errors

---

## RedisDown

### Description
Redis is not responding to health checks.

### Impact
**Critical** - Session and checkpoint storage unavailable.

### Resolution
1. Check Redis pod status: `kubectl get pods -l app=redis`
2. Verify Redis connectivity: `redis-cli ping`
3. Check Redis logs for errors
4. Verify network connectivity

### Escalation
Page on-call immediately - Redis is critical infrastructure.
