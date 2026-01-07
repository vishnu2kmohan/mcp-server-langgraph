# Redis Memory Alert Runbook

## Overview

This alert fires when Redis memory utilization is high.

## Symptoms

- Eviction of cached items
- Performance degradation
- Risk of OOM

---

## RedisHighMemory

### Description
Redis memory usage exceeds warning threshold.

### Impact
**Warning** - Cache evictions may affect performance.

### Resolution
1. Check Redis memory stats: `redis-cli info memory`
2. Review key expiration policies
3. Identify large keys: `redis-cli --bigkeys`
4. Consider memory limit increase

### Escalation
Create infrastructure ticket for capacity planning.
