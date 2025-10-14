# Runbook: Redis High Memory Usage

**Alert Name**: `RedisHighMemoryUsage`
**Severity**: Warning
**Component**: redis

## Alert Description

Redis session store is using more than 90% of allocated memory. Sessions may be evicted before TTL expiration.

**Alert Rule**:
```yaml
expr: |
  (
    redis_memory_used_bytes{job="redis-session"}
    /
    redis_memory_max_bytes{job="redis-session"}
  ) > 0.90
for: 5m
```

## Impact

- **User Impact**: MEDIUM - Users may be logged out unexpectedly
- **Service Impact**: Session eviction, degraded performance
- **Business Impact**: Disrupted workflows, frequent re-authentication

## Symptoms

- Users report being logged out during active sessions
- Application logs show "session not found" errors
- Redis logs show eviction notices
- Session creation becomes slower

## Diagnosis

### 1. Check Current Memory Usage

```bash
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" INFO memory
```

**Look for**:
- `used_memory_human`: Current memory usage
- `maxmemory_human`: Memory limit
- `evicted_keys`: Number of evicted keys
- `mem_fragmentation_ratio`: Memory fragmentation

### 2. Check Key Count

```bash
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" DBSIZE
```

High key count may indicate session accumulation.

### 3. Check Session TTLs

```bash
# Sample session keys and check TTL
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" --scan --pattern "session:*" | head -10 | while read key; do
  echo "$key: $(redis-cli -a "${REDIS_PASSWORD}" TTL "$key")s"
done
```

**Look for**:
- Keys with very long TTL
- Keys with -1 TTL (no expiration)

### 4. Check Eviction Policy

```bash
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" CONFIG GET maxmemory-policy
```

Should be: `allkeys-lru` for session store

### 5. Analyze Key Sizes

```bash
# Check size of sample keys
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" --scan --pattern "session:*" | head -5 | while read key; do
  echo "$key: $(redis-cli -a "${REDIS_PASSWORD}" DEBUG OBJECT "$key" | grep -o 'serializedlength:[0-9]*' | cut -d: -f2) bytes"
done
```

### 6. Check Memory Fragmentation

```bash
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" INFO memory | grep mem_fragmentation_ratio
```

**Fragmentation ratio**:
- < 1.0: Memory swapping (bad)
- 1.0-1.5: Normal
- > 1.5: High fragmentation

## Resolution

### Scenario 1: Too Many Active Sessions

**Cause**: Session accumulation exceeding expected load

**Fix Option A - Increase Memory Limit**:
```bash
# Update ConfigMap
kubectl patch configmap redis-session-config -n langgraph-agent -p '{"data":{"redis.conf":"maxmemory 1024mb\nmaxmemory-policy allkeys-lru\nappendonly yes\nappendfsync everysec"}}'

# Update pod memory limits
kubectl patch deployment redis-session -n langgraph-agent -p '{"spec":{"template":{"spec":{"containers":[{"name":"redis","resources":{"limits":{"memory":"1.5Gi"},"requests":{"memory":"1Gi"}}}]}}}}'
```

**Fix Option B - Reduce Session TTL**:
```bash
# Update application ConfigMap
kubectl patch configmap langgraph-agent-config -n langgraph-agent -p '{"data":{"session_ttl_seconds":"43200"}}'  # 12 hours instead of 24

# Restart application
kubectl rollout restart deployment/langgraph-agent -n langgraph-agent
```

**Fix Option C - Reduce Concurrent Session Limit**:
```bash
# Limit sessions per user
kubectl patch configmap langgraph-agent-config -n langgraph-agent -p '{"data":{"session_max_concurrent":"3"}}'  # 3 instead of 5

# Restart application
kubectl rollout restart deployment/langgraph-agent -n langgraph-agent
```

### Scenario 2: Memory Leak

**Cause**: Sessions not being cleaned up properly

**Fix**:
1. Check for sessions without TTL:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" --scan --pattern "session:*" | while read key; do
     TTL=$(redis-cli -a "${REDIS_PASSWORD}" TTL "$key")
     if [ "$TTL" -eq "-1" ]; then
       echo "No TTL: $key"
     fi
   done
   ```
2. Review session creation code in `src/mcp_server_langgraph/auth/session.py`
3. Ensure all session keys are created with SETEX (not SET + EXPIRE)
4. Clean up orphaned sessions:
   ```bash
   # Manually expire old sessions (use with caution)
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" --scan --pattern "session:*" | while read key; do
     redis-cli -a "${REDIS_PASSWORD}" EXPIRE "$key" 86400
   done
   ```

### Scenario 3: Large Session Objects

**Cause**: Sessions storing too much data

**Fix**:
1. Analyze session content size
2. Review what's being stored in sessions
3. Move large data to separate storage (database, object store)
4. Store only session ID and essential claims in Redis
5. Implement session data compression if needed

### Scenario 4: High Memory Fragmentation

**Cause**: Memory fragmentation from key churn

**Fix**:
1. Restart Redis to defragment:
   ```bash
   kubectl delete pod -n langgraph-agent -l app=redis-session
   ```
2. Enable automatic memory defragmentation:
   ```bash
   kubectl patch configmap redis-session-config -n langgraph-agent -p '{"data":{"redis.conf":"maxmemory 512mb\nmaxmemory-policy allkeys-lru\nactivedefrag yes\nactive-defrag-cycle-min 1\nactive-defrag-cycle-max 25"}}'
   ```
3. Restart:
   ```bash
   kubectl rollout restart deployment/redis-session -n langgraph-agent
   ```

### Scenario 5: Eviction Policy Ineffective

**Cause**: Wrong eviction policy for workload

**Fix**:
1. Change to volatile-lru (only evict keys with TTL):
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" CONFIG SET maxmemory-policy volatile-lru
   ```
2. Make persistent in ConfigMap:
   ```bash
   kubectl patch configmap redis-session-config -n langgraph-agent -p '{"data":{"redis.conf":"maxmemory 512mb\nmaxmemory-policy volatile-lru\nappendonly yes"}}'
   ```

### Scenario 6: Stale User Sessions

**Cause**: Users not logging out properly

**Fix**:
1. Implement sliding window expiration:
   ```bash
   kubectl patch configmap langgraph-agent-config -n langgraph-agent -p '{"data":{"session_sliding_window":"true"}}'
   ```
2. This refreshes TTL on each access, allowing active sessions to stay longer
3. Restart application:
   ```bash
   kubectl rollout restart deployment/langgraph-agent -n langgraph-agent
   ```

## Immediate Mitigation

If memory is critically high (>95%):

```bash
# Flush least recently used sessions
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" --scan --pattern "session:*" | head -100 | xargs redis-cli -a "${REDIS_PASSWORD}" DEL
```

**Warning**: This will log out affected users.

## Verification

After fix, verify memory usage has decreased:

```bash
# Check memory usage
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" INFO memory | grep used_memory_human

# Check eviction rate
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" INFO stats | grep evicted_keys

# Monitor over time
watch -n 5 'kubectl exec -n langgraph-agent $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" INFO memory | grep -E "used_memory_human|maxmemory_human"'
```

## Prevention

- Set appropriate maxmemory limits based on expected load
- Configure proper session TTL values
- Implement session cleanup on logout
- Monitor key count and memory usage
- Use sliding window expiration for active sessions
- Limit concurrent sessions per user
- Regular capacity planning
- Set up alerting at 80% threshold

## Capacity Planning

**Calculate required memory**:

```
sessions = max_concurrent_users × sessions_per_user
session_size = avg_session_data_size (bytes)
overhead = 1.2  # 20% overhead for fragmentation
maxmemory = sessions × session_size × overhead
```

**Example**:
- 10,000 concurrent users
- 3 sessions per user
- 2 KB per session
- Required: 10,000 × 3 × 2048 × 1.2 = ~73 MB

Add safety margin (2-3x) for peak load: **200-300 MB**

## Monitoring

Set up Prometheus alerts at multiple thresholds:

```yaml
- alert: RedisMemoryWarning
  expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.80
  for: 10m

- alert: RedisMemoryCritical
  expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.90
  for: 5m

- alert: RedisHighEvictionRate
  expr: rate(redis_evicted_keys_total[5m]) > 10
  for: 5m
```

## Related Alerts

- `RedisSessionStoreDown` - Complete service outage
- `RedisConnectionPoolExhausted` - Connection limits
- `SessionStoreErrors` - Application errors
- `SessionTTLViolations` - Early session expiration

## Long-term Solutions

1. **Redis Cluster**: Shard sessions across multiple Redis instances
2. **Redis Enterprise**: Use commercial Redis with better memory management
3. **Alternative Stores**: Consider Memcached, Hazelcast, or database-backed sessions
4. **Stateless Tokens**: Use JWT tokens instead of server-side sessions

## References

- [Redis Memory Optimization](https://redis.io/topics/memory-optimization)
- [Redis Eviction Policies](https://redis.io/docs/manual/eviction/)
- [Deployment Configuration](../../deployments/kubernetes/base/redis-session-deployment.yaml)
- [Session Management Code](../../src/mcp_server_langgraph/auth/session.py)
