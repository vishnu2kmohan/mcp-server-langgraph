# Runbook: Session Store Errors

**Alert Name**: `SessionStoreErrors`
**Severity**: Warning
**Component**: sessions

## Alert Description

Session store is experiencing errors during create, read, update, or delete operations. More than 0.1 errors per second detected.

**Alert Rule**:
```yaml
expr: |
  rate(session_store_errors_total[5m]) > 0.1
for: 3m
```

## Impact

- **User Impact**: MEDIUM - Session operations may fail
- **Service Impact**: Degraded session management
- **Business Impact**: Authentication issues, user frustration

## Symptoms

- Application logs show session operation errors
- Users report login failures
- Intermittent "session not found" errors
- Session creation or refresh failures

## Diagnosis

### 1. Check Error Rate and Type

```bash
# Check application logs for session errors
kubectl logs -n langgraph-agent -l app=langgraph-agent --tail=200 | grep -i "session.*error\|session.*fail"
```

**Look for**:
- Connection errors to Redis
- Serialization/deserialization errors
- Timeout errors
- Key not found errors
- Permission errors

### 2. Check Session Store Backend

```bash
# Determine which backend is in use
kubectl get configmap langgraph-agent-config -n langgraph-agent -o jsonpath='{.data.session_backend}'
```

Expected: `redis` or `memory`

### 3. Check Redis Health (if using Redis backend)

```bash
# Check Redis pod status
kubectl get pods -n langgraph-agent -l app=redis-session

# Check Redis logs
kubectl logs -n langgraph-agent -l app=redis-session --tail=50

# Test Redis connectivity
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=langgraph-agent -o jsonpath='{.items[0].metadata.name}') -- sh -c 'nc -zv redis-session 6379'
```

### 4. Check Prometheus Metrics

```bash
# Query error breakdown by operation type
curl -s 'http://localhost:9090/api/v1/query?query=rate(session_store_errors_total[5m])' | jq '.data.result[] | {operation: .metric.operation, error_type: .metric.error_type, rate: .value[1]}'
```

### 5. Check Session Store Code

Review implementation for issues:

```bash
# Check session.py for recent changes
git log --oneline -10 src/mcp_server_langgraph/auth/session.py
```

### 6. Test Session Operations Manually

```bash
# Port forward to access application directly
kubectl port-forward -n langgraph-agent svc/langgraph-agent 8000:8000 &

# Test session creation
curl -X POST http://localhost:8000/api/sessions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "testuser"}'
```

## Resolution

### Scenario 1: Redis Connection Errors

**Cause**: Cannot connect to Redis session store

**Fix**:
1. Verify Redis is running:
   ```bash
   kubectl get pods -n langgraph-agent -l app=redis-session
   ```
2. Check service exists:
   ```bash
   kubectl get svc redis-session -n langgraph-agent
   ```
3. Test connectivity:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=langgraph-agent -o jsonpath='{.items[0].metadata.name}') -- nc -zv redis-session 6379
   ```
4. If Redis is down, see `redis-down.md` runbook
5. If connection timing out, check network policies:
   ```bash
   kubectl get networkpolicies -n langgraph-agent
   ```

### Scenario 2: Serialization Errors

**Cause**: Cannot serialize/deserialize session data

**Fix**:
1. Check logs for specific serialization error:
   ```bash
   kubectl logs -n langgraph-agent -l app=langgraph-agent --tail=100 | grep -i "serializ\|pickle\|json"
   ```
2. Common causes:
   - Session data contains non-serializable objects
   - Version mismatch in pickle protocol
   - Corrupted session data
3. Update session data structure to use serializable types only
4. Clear corrupted sessions:
   ```bash
   # For Redis backend
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" --scan --pattern "session:*" | while read key; do
     redis-cli -a "${REDIS_PASSWORD}" GET "$key" > /dev/null || redis-cli -a "${REDIS_PASSWORD}" DEL "$key"
   done
   ```

### Scenario 3: Timeout Errors

**Cause**: Redis operations timing out

**Fix**:
1. Check Redis performance:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" --latency
   ```
2. Increase timeout in application:
   ```bash
   kubectl patch configmap langgraph-agent-config -n langgraph-agent -p '{"data":{"redis_socket_timeout":"10"}}'
   ```
3. Check for Redis performance issues (see `keycloak-slow.md` runbook)
4. Restart application:
   ```bash
   kubectl rollout restart deployment/langgraph-agent -n langgraph-agent
   ```

### Scenario 4: Permission Errors

**Cause**: Redis authentication or ACL issues

**Fix**:
1. Verify Redis password:
   ```bash
   kubectl get secret langgraph-agent-secrets -n langgraph-agent -o jsonpath='{.data.redis-password}' | base64 -d
   ```
2. Test authentication:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "`<password>`" PING
   ```
3. Check Redis ACL if enabled:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" ACL LIST
   ```
4. Update password if needed and restart both services

### Scenario 5: Memory Backend Errors (if using InMemory)

**Cause**: Memory issues with in-memory session store

**Fix**:
1. Check application memory usage:
   ```bash
   kubectl top pod -n langgraph-agent -l app=langgraph-agent
   ```
2. InMemory store doesn't persist across restarts - verify this is acceptable
3. For production, switch to Redis:
   ```bash
   kubectl patch configmap langgraph-agent-config -n langgraph-agent -p '{"data":{"session_backend":"redis"}}'
   kubectl rollout restart deployment/langgraph-agent -n langgraph-agent
   ```

### Scenario 6: Concurrent Access Errors

**Cause**: Race conditions in session updates

**Fix**:
1. Review session update logic in code
2. Implement optimistic locking for session updates:
   ```python
   # Use Redis WATCH for transactional updates
   async def update_session(self, session_id: str, data: dict):
       async with self.redis_client.pipeline(transaction=True) as pipe:
           await pipe.watch(f"session:{session_id}")
           await pipe.multi()
           await pipe.set(f"session:{session_id}", json.dumps(data))
           await pipe.execute()
   ```
3. Deploy updated code

### Scenario 7: Invalid Session IDs

**Cause**: Malformed or invalid session IDs

**Fix**:
1. Check session ID generation:
   ```bash
   grep -A 10 "def create_session" src/mcp_server_langgraph/auth/session.py
   ```
2. Ensure using cryptographically secure random IDs
3. Add validation for session ID format:
   ```python
   import re

   def validate_session_id(session_id: str) -> bool:
       # Session IDs should be URL-safe base64
       return bool(re.match(r'^[A-Za-z0-9_-]{32,}$', session_id))
   ```
4. Add validation to all session operations

## Code Review Checklist

Review `src/mcp_server_langgraph/auth/session.py` for:

- [ ] Proper error handling in all methods
- [ ] Connection pooling for Redis operations
- [ ] Timeout configuration
- [ ] Retry logic for transient errors
- [ ] Input validation for session IDs
- [ ] Proper serialization/deserialization
- [ ] Logging of all errors
- [ ] Metrics emission for errors

## Verification

After fix, verify errors have stopped:

```bash
# Check error rate
curl -s 'http://localhost:9090/api/v1/query?query=rate(session_store_errors_total[5m])'

# Test session operations
# 1. Create session
curl -X POST http://localhost:8000/api/sessions \
  -H "Authorization: Bearer <token>" \
  -d '{"user_id": "testuser"}'

# 2. Get session
curl -X GET http://localhost:8000/api/sessions/<session-id> \
  -H "Authorization: Bearer <token>"

# 3. Delete session
curl -X DELETE http://localhost:8000/api/sessions/<session-id> \
  -H "Authorization: Bearer <token>"

# Check logs for errors
kubectl logs -n langgraph-agent -l app=langgraph-agent --tail=50 | grep -i error
```

## Prevention

- Implement comprehensive error handling
- Add retry logic with exponential backoff
- Monitor session store health proactively
- Regular load testing of session operations
- Circuit breaker pattern for Redis calls
- Validate all inputs before operations
- Use connection pooling best practices
- Set appropriate timeouts

## Error Handling Best Practices

```python
# In src/mcp_server_langgraph/auth/session.py

class RedisSessionStore(SessionStore):
    async def get_session(self, session_id: str) -> Optional[Session]:
        try:
            # Validate input
            if not self._validate_session_id(session_id):
                logger.warning(f"Invalid session ID format: {session_id}")
                return None

            # Operation with timeout
            data = await asyncio.wait_for(
                self.redis_client.get(f"session:{session_id}"),
                timeout=5.0
            )

            if not data:
                return None

            # Deserialize with error handling
            try:
                session_dict = json.loads(data)
                return Session(**session_dict)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"Session deserialization failed: {e}")
                # Optionally delete corrupted session
                await self.delete_session(session_id)
                return None

        except asyncio.TimeoutError:
            logger.error(f"Session fetch timeout for {session_id}")
            record_session_operation("get", "timeout")
            return None
        except redis.RedisError as e:
            logger.error(f"Redis error fetching session: {e}")
            record_session_operation("get", "redis_error")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error fetching session: {e}")
            record_session_operation("get", "unknown_error")
            return None
```

## Monitoring

Add detailed metrics for session operations:

```python
# Metrics by operation type and error type
session_store_errors = Counter(
    "session_store_errors_total",
    "Total session store errors",
    ["operation", "error_type"]
)

# Usage
record_session_operation(operation="create", error_type="timeout")
record_session_operation(operation="get", error_type="not_found")
record_session_operation(operation="update", error_type="redis_error")
```

## Related Alerts

- `RedisSessionStoreDown` - Complete Redis outage
- `RedisHighMemoryUsage` - Memory pressure
- `RedisConnectionPoolExhausted` - Connection limits
- `SessionTTLViolations` - Session expiration issues

## Escalation

If errors persist after 30 minutes:
- Review recent code changes
- Check for infrastructure issues
- Consider rolling back recent deployments
- Engage development team for code review

## References

- [Session Management Implementation](../src/mcp_server_langgraph/auth/session.py)
- [Redis Documentation](https://redis.io/documentation)
- [Error Handling Best Practices](https://docs.python.org/3/tutorial/errors.html)
- [Deployment Configuration](../deployments/base/deployment.yaml)
