# Runbook: Session TTL Violations

**Alert Name**: `SessionTTLViolations`
**Severity**: Info
**Component**: sessions

## Alert Description

Sessions are expiring before their expected TTL (Time To Live). This may indicate configuration issues or unexpected eviction.

**Alert Rule**:
```yaml
expr: |
  rate(session_ttl_violations_total[10m]) > 0
for: 5m
```

## Impact

- **User Impact**: LOW-MEDIUM - Users may be logged out earlier than expected
- **Service Impact**: Session management not meeting SLA
- **Business Impact**: User inconvenience, potential confusion

## Symptoms

- Users report being logged out sooner than expected
- Session lifetime shorter than configured TTL
- Application logs show session expiration warnings
- Metrics show sessions missing before TTL expiration

## Diagnosis

### 1. Check Configured TTL

```bash
# Check application configuration
kubectl get configmap langgraph-agent-config -n langgraph-agent -o jsonpath='{.data.session_ttl_seconds}'
```

Expected values:
- Development: 3600 (1 hour)
- Staging: 43200 (12 hours)
- Production: 86400 (24 hours)

### 2. Check Actual Session TTLs in Redis

```bash
# Sample session keys and check their TTL
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" --scan --pattern "session:*" | head -10 | while read key; do
  echo "$key: $(redis-cli -a "${REDIS_PASSWORD}" TTL "$key")s"
done
```

**Look for**:
- TTL significantly shorter than expected
- Negative TTL (-1 = no expiration, -2 = key doesn't exist)
- Inconsistent TTLs across sessions

### 3. Check Redis Memory Usage

```bash
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" INFO memory
```

**Look for**:
- High memory usage (>90%)
- Eviction policy: `maxmemory-policy`
- Evicted keys count

If memory is high, sessions may be evicted early (see `redis-memory.md` runbook).

### 4. Check Session Creation Code

```bash
# Review session creation in code
grep -A 20 "async def create_session" src/mcp_server_langgraph/auth/session.py
```

**Verify**:
- Sessions created with SETEX (not SET + EXPIRE)
- TTL value correctly passed
- No manual expiration overrides

### 5. Check for Session Refresh Logic

```bash
# Check if sliding window is enabled
kubectl get configmap langgraph-agent-config -n langgraph-agent -o jsonpath='{.data.session_sliding_window}'
```

If `true`, sessions should refresh on each access. If `false`, sessions expire at original TTL.

### 6. Monitor Session Lifetime

```bash
# Create test session and monitor
SESSION_ID=$(curl -s -X POST http://localhost:8000/api/sessions \
  -H "Authorization: Bearer <token>" \
  -d '{"user_id": "testuser"}' | jq -r '.session_id')

# Monitor TTL every 30 seconds
watch -n 30 "kubectl exec -n langgraph-agent $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a '${REDIS_PASSWORD}' TTL session:$SESSION_ID"
```

## Resolution

### Scenario 1: Redis Memory Eviction

**Cause**: Redis evicting sessions due to memory pressure

**Fix**:
1. Check eviction policy:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" CONFIG GET maxmemory-policy
   ```
2. If policy is `allkeys-lru` or `allkeys-lfu`, sessions can be evicted before TTL
3. Change to `volatile-lru` (only evict keys with TTL, prefer oldest):
   ```bash
   kubectl patch configmap redis-session-config -n langgraph-agent -p '{"data":{"redis.conf":"maxmemory 512mb\nmaxmemory-policy volatile-lru\nappendonly yes"}}'
   ```
4. Or increase maxmemory (see `redis-memory.md` runbook)
5. Restart Redis:
   ```bash
   kubectl rollout restart deployment/redis-session -n langgraph-agent
   ```

### Scenario 2: Incorrect TTL Configuration

**Cause**: TTL not being set correctly in code

**Fix**:
1. Review session creation code:
   ```python
   # Correct implementation (RedisSessionStore)
   async def create_session(self, session: Session) -> None:
       await self.redis_client.setex(
           f"session:{session.session_id}",
           self.ttl_seconds,  # TTL in seconds
           session.json()
       )

   # Incorrect - uses SET without TTL
   # await self.redis_client.set(f"session:{session.session_id}", session.json())
   ```
2. Ensure using `SETEX` or `SET` with `EX` parameter
3. Deploy fix if code issue found

### Scenario 3: Sliding Window Not Working

**Cause**: Session refresh not updating TTL on access

**Fix**:
1. Verify sliding window is enabled:
   ```bash
   kubectl get configmap langgraph-agent-config -n langgraph-agent -o jsonpath='{.data.session_sliding_window}'
   ```
2. If disabled but should be enabled:
   ```bash
   kubectl patch configmap langgraph-agent-config -n langgraph-agent -p '{"data":{"session_sliding_window":"true"}}'
   ```
3. Review refresh logic in code:
   ```python
   async def refresh_session(self, session_id: str) -> None:
       if self.sliding_window:
           # Refresh TTL on access
           await self.redis_client.expire(
               f"session:{session_id}",
               self.ttl_seconds
           )
   ```
4. Restart application:
   ```bash
   kubectl rollout restart deployment/langgraph-agent -n langgraph-agent
   ```

### Scenario 4: Manual Session Deletion

**Cause**: Sessions being deleted programmatically before TTL

**Fix**:
1. Check for session cleanup jobs or scripts
2. Review session deletion logic:
   ```bash
   grep -r "delete_session\|revoke_session" src/mcp_server_langgraph/auth/
   ```
3. Check for bulk deletion operations:
   ```bash
   kubectl logs -n langgraph-agent -l app=langgraph-agent --tail=200 | grep -i "session.*delet\|session.*revok"
   ```
4. Verify deletion is intentional (e.g., logout, security revocation)
5. If unintentional, fix deletion logic

### Scenario 5: Clock Skew Issues

**Cause**: Time synchronization issues between nodes

**Fix**:
1. Check system time on Redis pod:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- date
   ```
2. Check application pod time:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=langgraph-agent -o jsonpath='{.items[0].metadata.name}') -- date
   ```
3. Ensure NTP is running on all nodes
4. Verify time is synchronized across cluster

### Scenario 6: Configuration Mismatch

**Cause**: Application using different TTL than configured

**Fix**:
1. Check if environment variable is being read correctly:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=langgraph-agent -o jsonpath='{.items[0].metadata.name}') -- env | grep SESSION_TTL
   ```
2. Verify ConfigMap is mounted:
   ```bash
   kubectl describe pod -n langgraph-agent -l app=langgraph-agent | grep -A 10 "Environment Variables from"
   ```
3. Check for hardcoded TTL in code:
   ```bash
   grep -r "ttl.*=.*[0-9]" src/mcp_server_langgraph/auth/session.py
   ```
4. Restart application to reload config:
   ```bash
   kubectl rollout restart deployment/langgraph-agent -n langgraph-agent
   ```

### Scenario 7: AOF Rewrite During High Load

**Cause**: Redis AOF rewrite causing temporary performance issues

**Fix**:
1. Check Redis logs for AOF activity:
   ```bash
   kubectl logs -n langgraph-agent -l app=redis-session --tail=100 | grep -i AOF
   ```
2. Tune AOF settings to reduce rewrites:
   ```bash
   kubectl patch configmap redis-session-config -n langgraph-agent -p '{"data":{"redis.conf":"maxmemory 512mb\nappendonly yes\nauto-aof-rewrite-percentage 100\nauto-aof-rewrite-min-size 128mb"}}'
   ```
3. Restart Redis:
   ```bash
   kubectl rollout restart deployment/redis-session -n langgraph-agent
   ```

## Verification

After fix, verify sessions maintain expected TTL:

```bash
# Create test session
SESSION_ID=$(curl -s -X POST http://localhost:8000/api/sessions \
  -H "Authorization: Bearer <token>" \
  -d '{"user_id": "testuser"}' | jq -r '.session_id')

# Check initial TTL
INITIAL_TTL=$(kubectl exec -n langgraph-agent $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" TTL "session:$SESSION_ID")
echo "Initial TTL: $INITIAL_TTL seconds"

# Wait 1 minute
sleep 60

# Check TTL again
CURRENT_TTL=$(kubectl exec -n langgraph-agent $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" TTL "session:$SESSION_ID")
echo "TTL after 60s: $CURRENT_TTL seconds"

# Should be approximately initial_ttl - 60
EXPECTED=$((INITIAL_TTL - 60))
echo "Expected TTL: ~$EXPECTED seconds"

# Test sliding window (if enabled)
curl -s http://localhost:8000/api/sessions/$SESSION_ID \
  -H "Authorization: Bearer <token>"

# Check if TTL refreshed
REFRESHED_TTL=$(kubectl exec -n langgraph-agent $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" TTL "session:$SESSION_ID")
echo "TTL after access: $REFRESHED_TTL seconds"
```

## Prevention

- Set appropriate eviction policies in Redis
- Monitor Redis memory usage proactively
- Implement comprehensive logging for session operations
- Regular validation of TTL behavior
- Load testing with session lifecycle scenarios
- Monitor session metrics over time
- Document expected session lifetime behavior

## Expected Session Lifetime Behavior

### Without Sliding Window

```
Session created at T=0 with TTL=3600s
T=0:    TTL = 3600s
T=600:  TTL = 3000s  (10 min later)
T=1800: TTL = 1800s  (30 min later)
T=3600: Session expires
```

### With Sliding Window

```
Session created at T=0 with TTL=3600s
T=0:    TTL = 3600s
T=600:  Access → TTL = 3600s (refreshed)
T=1200: Access → TTL = 3600s (refreshed)
T=4800: No access since T=1200 → Session expires
```

## Monitoring

Add metrics for session lifetime tracking:

```python
# In src/mcp_server_langgraph/auth/metrics.py

session_lifetime = Histogram(
    "session_actual_lifetime_seconds",
    "Actual session lifetime before expiration",
    buckets=[300, 600, 1800, 3600, 7200, 14400, 28800, 86400]
)

session_ttl_violations = Counter(
    "session_ttl_violations_total",
    "Sessions expiring before expected TTL",
    ["reason"]
)

# Usage
# When session expires
actual_lifetime = time.time() - session.created_at
expected_lifetime = session.ttl_seconds

if actual_lifetime < expected_lifetime * 0.9:  # Expired >10% early
    session_ttl_violations.labels(reason="early_expiration").inc()
    logger.warning(
        f"Session {session.session_id} expired early: "
        f"expected={expected_lifetime}s, actual={actual_lifetime}s"
    )

session_lifetime.observe(actual_lifetime)
```

## Related Alerts

- `RedisHighMemoryUsage` - Memory pressure causing eviction
- `SessionStoreErrors` - Session operation failures
- `RedisSessionStoreDown` - Complete Redis outage

## Configuration Reference

**Recommended TTL values**:

```yaml
# Development
session_ttl_seconds: 3600  # 1 hour
session_sliding_window: true

# Staging
session_ttl_seconds: 43200  # 12 hours
session_sliding_window: true

# Production - Interactive
session_ttl_seconds: 86400  # 24 hours
session_sliding_window: true

# Production - API/Background
session_ttl_seconds: 604800  # 7 days
session_sliding_window: false
```

## Escalation

This is typically a low-priority issue unless users are actively complaining. If sessions are expiring significantly early (>50% shorter than expected):

- Review recent configuration changes
- Check for infrastructure issues
- Engage development team
- Consider temporary TTL increase

## References

- [Session Management Implementation](../../src/mcp_server_langgraph/auth/session.py)
- [Redis TTL Documentation](https://redis.io/commands/ttl)
- [Redis Eviction Policies](https://redis.io/docs/manual/eviction/)
- [Configuration Guide](../../deployments/README.md)
