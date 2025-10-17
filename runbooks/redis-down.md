# Runbook: Redis Session Store Down

**Alert Name**: `RedisSessionStoreDown`
**Severity**: Critical
**Component**: redis

## Alert Description

The Redis session store service is down and unavailable. Session management operations will fail.

**Alert Rule**:
```yaml
expr: up{job="redis-session"} == 0
for: 2m
```

## Impact

- **User Impact**: HIGH - Session-based authentication will fail
- **Service Impact**: Cannot create, retrieve, or update sessions
- **Business Impact**: Users cannot maintain authenticated sessions

## Symptoms

- Health check endpoint fails for session store
- Application logs show Redis connection errors
- Users must re-authenticate on every request (if fallback not configured)
- Metric `up{job="redis-session"}` shows 0 for more than 2 minutes

## Diagnosis

### 1. Check Pod Status

```bash
kubectl get pods -n langgraph-agent -l app=redis-session
kubectl describe pod -n langgraph-agent -l app=redis-session
```

**Look for**:
- Pod status (CrashLoopBackOff, Error, Pending)
- Container restart count
- Recent events

### 2. Check Redis Logs

```bash
kubectl logs -n langgraph-agent -l app=redis-session --tail=100
kubectl logs -n langgraph-agent -l app=redis-session --previous
```

**Look for**:
- Out of memory errors
- Configuration errors
- Port binding failures
- AOF/RDB persistence errors

### 3. Check Service and Endpoints

```bash
kubectl get service redis-session -n langgraph-agent
kubectl get endpoints redis-session -n langgraph-agent
```

**Look for**:
- Service has correct selector
- Endpoints list shows pod IP

### 4. Check Resource Usage

```bash
kubectl top pod -n langgraph-agent -l app=redis-session
```

**Look for**:
- Memory usage near maxmemory limit
- CPU usage patterns

### 5. Test Redis Connectivity

```bash
# From application pod
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=langgraph-agent -o jsonpath='{.items[0].metadata.name}') -- sh -c 'nc -zv redis-session 6379'
```

### 6. Check Persistent Volume

If using PVC for persistence:

```bash
kubectl get pvc -n langgraph-agent | grep redis
kubectl describe pvc <redis-pvc-name> -n langgraph-agent
```

## Resolution

### Scenario 1: Pod CrashLoopBackOff

**Cause**: Redis failing to start

**Fix**:
1. Check logs for specific error
2. Verify Redis configuration:
   ```bash
   kubectl get configmap redis-session-config -n langgraph-agent -o yaml
   ```
3. Check for corrupt AOF file if using persistence:
   ```bash
   kubectl logs -n langgraph-agent -l app=redis-session --tail=50 | grep -i "AOF\|corrupt"
   ```
4. If AOF is corrupt, recover:
   ```bash
   # Delete and recreate pod (will lose session data)
   kubectl delete pod -n langgraph-agent -l app=redis-session
   ```

### Scenario 2: Out of Memory

**Cause**: Redis exceeding maxmemory limit

**Fix**:
1. Check current memory usage:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" INFO memory
   ```
2. Increase maxmemory in ConfigMap:
   ```bash
   kubectl patch configmap redis-session-config -n langgraph-agent -p '{"data":{"redis.conf":"maxmemory 1024mb\nmaxmemory-policy allkeys-lru\nappendonly yes\nappendfsync everysec"}}'
   ```
3. Increase pod memory limits:
   ```bash
   kubectl patch deployment redis-session -n langgraph-agent -p '{"spec":{"template":{"spec":{"containers":[{"name":"redis","resources":{"limits":{"memory":"1.5Gi"}}}]}}}}'
   ```
4. Restart Redis:
   ```bash
   kubectl rollout restart deployment/redis-session -n langgraph-agent
   ```

### Scenario 3: Password Authentication Failure

**Cause**: Redis password mismatch

**Fix**:
1. Verify secret exists and is correct:
   ```bash
   kubectl get secret langgraph-agent-secrets -n langgraph-agent -o jsonpath='{.data.redis-password}' | base64 -d
   ```
2. Test authentication:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "`<password>`" PING
   ```
3. If password is wrong, update secret and restart both Redis and application

### Scenario 4: Persistent Volume Issues

**Cause**: PVC mounting failures

**Fix**:
1. Check PVC status:
   ```bash
   kubectl get pvc -n langgraph-agent
   ```
2. If PVC is Pending, check storage class:
   ```bash
   kubectl get storageclass
   ```
3. Provision storage or use emptyDir as temporary fix:
   ```bash
   kubectl patch deployment redis-session -n langgraph-agent -p '{"spec":{"template":{"spec":{"volumes":[{"name":"redis-data","emptyDir":{}}]}}}}'
   ```

**Warning**: Using emptyDir will lose all session data on pod restart.

### Scenario 5: Port Binding Conflict

**Cause**: Port 6379 already in use

**Fix**:
1. Check for port conflicts:
   ```bash
   kubectl get pods -n langgraph-agent -o wide | grep redis
   ```
2. Ensure only one Redis session instance is running
3. Delete duplicate pods if found

### Scenario 6: Configuration Error

**Cause**: Invalid redis.conf settings

**Fix**:
1. Review ConfigMap:
   ```bash
   kubectl get configmap redis-session-config -n langgraph-agent -o yaml
   ```
2. Validate against Redis documentation
3. Apply minimal working configuration:
   ```bash
   kubectl patch configmap redis-session-config -n langgraph-agent -p '{"data":{"redis.conf":"maxmemory 512mb\nmaxmemory-policy allkeys-lru"}}'
   ```
4. Restart:
   ```bash
   kubectl rollout restart deployment/redis-session -n langgraph-agent
   ```

### Emergency Rollback

If recent deployment caused the issue:

```bash
kubectl rollout undo deployment/redis-session -n langgraph-agent
kubectl rollout status deployment/redis-session -n langgraph-agent
```

### Fallback: InMemory Sessions

As emergency workaround, switch to in-memory session storage:

1. Update application ConfigMap:
   ```bash
   kubectl patch configmap langgraph-agent-config -n langgraph-agent -p '{"data":{"session_backend":"memory"}}'
   ```
2. Restart application:
   ```bash
   kubectl rollout restart deployment/langgraph-agent -n langgraph-agent
   ```

**Warning**: This loses session persistence and doesn't work in multi-replica deployments.

## Verification

After fix, verify Redis is healthy:

```bash
# Check pod is running
kubectl get pods -n langgraph-agent -l app=redis-session

# Test Redis connectivity
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" PING

# Expected: PONG

# Check Redis info
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" INFO server

# Test session creation from application
kubectl logs -n langgraph-agent -l app=langgraph-agent --tail=20 | grep -i "session.*created"
```

## Prevention

- Configure pod disruption budgets
- Set up Redis replication for high availability
- Use Redis Sentinel for automatic failover
- Monitor memory usage proactively
- Set appropriate maxmemory and eviction policies
- Enable AOF persistence with proper fsync settings
- Regular backup of AOF/RDB files
- Implement health checks with proper timeouts

## High Availability Setup

For production, consider Redis Sentinel or Redis Cluster:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-session
spec:
  serviceName: redis-session
  replicas: 3  # Master + 2 replicas
  template:
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command:
        - redis-server
        - --replicaof
        - redis-session-0.redis-session
        - "6379"
```

## Related Alerts

- `RedisHighMemoryUsage` - Memory pressure
- `RedisConnectionPoolExhausted` - Connection limits
- `SessionStoreErrors` - Application-level session errors
- `SessionTTLViolations` - Session expiration issues

## Data Recovery

If session data is lost:

1. Users will need to re-authenticate
2. Check for AOF/RDB backups:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- ls -la /data/
   ```
3. Restore from backup if available:
   ```bash
   kubectl cp backup.aof langgraph-agent/redis-session-pod:/data/appendonly.aof
   kubectl delete pod -n langgraph-agent -l app=redis-session
   ```

## Escalation

If issue persists after 30 minutes:
- Page on-call SRE
- Consider invoking incident response
- Communicate session loss to users
- Prepare for mass re-authentication

## References

- [Redis Documentation](https://redis.io/documentation)
- [Deployment Configuration](../deployments/kubernetes/base/redis-session-deployment.yaml)
- [Session Management Code](../src/mcp_server_langgraph/auth/session.py)
- [Redis High Availability](https://redis.io/topics/sentinel)
