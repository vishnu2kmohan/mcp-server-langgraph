# Redis Pool Alert Runbook

## Overview

This alert fires when Redis connection pool is near saturation.

## Symptoms

- Connection timeout errors
- Increased latency
- Failed cache operations

---

## RedisPoolSaturation

### Description
Redis connection pool utilization exceeds threshold.

### Impact
**Warning** - New connections may be queued or fail.

### Resolution
1. Check for connection leaks in application
2. Review connection pool configuration
3. Increase pool size if needed
4. Check for long-running commands blocking connections

### Escalation
Create ticket for pool optimization.
