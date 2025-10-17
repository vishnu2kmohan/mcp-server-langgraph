# Runbook: Redis Connection Pool Exhausted

**Alert Name**: `RedisConnectionPoolExhausted`
**Severity**: Warning
**Component**: redis

## Alert Description

Redis connection pool is more than 95% utilized. New session operations may be delayed or fail.

**Alert Rule**:
```yaml
expr: |
  redis_client_pool_connections_in_use{job="langgraph-agent"}
  /
  redis_client_pool_max_connections{job="langgraph-agent"}
  > 0.95
for: 3m
```

## Impact

- **User Impact**: MEDIUM - Slow or failing session operations
- **Service Impact**: Connection timeouts, degraded performance
- **Business Impact**: Poor user experience, potential authentication delays

## Symptoms

- Application logs show "connection pool exhausted" or "connection timeout" errors
- Slow response times for authenticated requests
- Intermittent session creation failures
- Users experience delays during login

## Diagnosis

### 1. Check Connection Pool Status

```bash
# Check application logs for pool metrics
kubectl logs -n langgraph-agent -l app=langgraph-agent --tail=100 | grep -i "redis.*pool\|connection.*pool"
```

**Look for**:
- "Connection pool exhausted" errors
- "Waiting for connection" messages
- Pool size and utilization metrics

### 2. Check Active Connections

```bash
# Check Redis server connections
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" CLIENT LIST | wc -l
```

Shows total number of active connections to Redis.

### 3. Check Application Pod Count

```bash
kubectl get pods -n langgraph-agent -l app=langgraph-agent
```

More pods = more connections needed.

### 4. Check for Connection Leaks

```bash
# Monitor connection count over time
watch -n 2 'kubectl exec -n langgraph-agent $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" CLIENT LIST | wc -l'
```

If count continuously increases, there may be a connection leak.

### 5. Check Application Code

Review session store implementation:

```bash
# Check for proper connection handling
grep -r "redis.Redis\|redis.ConnectionPool" src/mcp_server_langgraph/auth/session.py
```

**Look for**:
- Connections opened but not closed
- Missing context managers (with statements)
- Connection pool configuration

### 6. Check Redis Max Clients

```bash
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" CONFIG GET maxclients
```

Default is 10,000. Ensure pool size doesn't approach this limit.

## Resolution

### Scenario 1: Insufficient Pool Size

**Cause**: Pool size too small for concurrent load

**Fix**:
1. Update application configuration to increase pool size:
   ```bash
   kubectl patch configmap langgraph-agent-config -n langgraph-agent -p '{"data":{"redis_pool_max_connections":"50"}}'  # Increase from default 10
   ```
2. Restart application to apply:
   ```bash
   kubectl rollout restart deployment/langgraph-agent -n langgraph-agent
   ```

**Recommended pool sizes**:
- Low traffic (< 100 req/s): 10-20 connections
- Medium traffic (100-500 req/s): 20-50 connections
- High traffic (> 500 req/s): 50-100 connections

### Scenario 2: Connection Leaks

**Cause**: Connections not being returned to pool

**Fix**:
1. Review code in `src/mcp_server_langgraph/auth/session.py:349` (RedisSessionStore)
2. Ensure all Redis operations use connection pooling:
   ```python
   # Correct pattern
   async def get_session(self, session_id: str):
       async with self.redis_client as conn:
           data = await conn.get(f"session:{session_id}")
       return data

   # Incorrect (leaks connection)
   async def get_session(self, session_id: str):
       conn = await self.redis_client.get_connection()
       data = await conn.get(f"session:{session_id}")
       # Missing: await conn.close() or context manager
       return data
   ```
3. Deploy fix if code issue found

### Scenario 3: Slow Operations Blocking Connections

**Cause**: Long-running Redis operations holding connections

**Fix**:
1. Check for slow Redis commands:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" SLOWLOG GET 10
   ```
2. Add connection timeout to prevent hanging:
   ```bash
   kubectl patch configmap langgraph-agent-config -n langgraph-agent -p '{"data":{"redis_socket_timeout":"5","redis_socket_connect_timeout":"5"}}'
   ```
3. Optimize slow queries or operations

### Scenario 4: Too Many Application Replicas

**Cause**: Each pod creates its own connection pool

**Fix**:

**Calculate total connections**:
```
total_connections = pod_count × pool_size_per_pod
```

If exceeding Redis maxclients or causing congestion:

**Option A - Reduce pool size per pod**:
```bash
kubectl patch configmap langgraph-agent-config -n langgraph-agent -p '{"data":{"redis_pool_max_connections":"20"}}'
```

**Option B - Reduce replica count** (if over-provisioned):
```bash
kubectl scale deployment langgraph-agent -n langgraph-agent --replicas=3
```

**Option C - Increase Redis capacity**:
- Deploy Redis Cluster for horizontal scaling
- Use connection multiplexing (Redis Proxy)

### Scenario 5: Connection Pool Misconfiguration

**Cause**: Incorrect pool parameters

**Fix**:
1. Review current configuration:
   ```bash
   kubectl get configmap langgraph-agent-config -n langgraph-agent -o jsonpath='{.data}' | grep redis
   ```
2. Apply recommended settings:
   ```bash
   kubectl patch configmap langgraph-agent-config -n langgraph-agent -p '{"data":{
     "redis_pool_max_connections":"50",
     "redis_pool_min_idle":"10",
     "redis_socket_keepalive":"true",
     "redis_socket_timeout":"5",
     "redis_health_check_interval":"30"
   }}'
   ```
3. Restart:
   ```bash
   kubectl rollout restart deployment/langgraph-agent -n langgraph-agent
   ```

### Scenario 6: Redis Server Connection Limits

**Cause**: Redis hitting maxclients limit

**Fix**:
1. Check current limit:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" CONFIG GET maxclients
   ```
2. Increase if needed:
   ```bash
   kubectl patch configmap redis-session-config -n langgraph-agent -p '{"data":{"redis.conf":"maxclients 20000\nmaxmemory 512mb\nmaxmemory-policy allkeys-lru"}}'
   ```
3. Restart Redis:
   ```bash
   kubectl rollout restart deployment/redis-session -n langgraph-agent
   ```

## Immediate Mitigation

If pool exhaustion is causing outage:

```bash
# Restart application pods to reset connection pools
kubectl rollout restart deployment/langgraph-agent -n langgraph-agent

# Or kill specific problematic pods
kubectl delete pod -n langgraph-agent <pod-name>
```

## Verification

After fix, verify pool utilization has decreased:

```bash
# Check application logs for pool metrics
kubectl logs -n langgraph-agent -l app=langgraph-agent --tail=50 | grep -i pool

# Monitor Redis connections
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" INFO clients

# Check Prometheus metrics
curl -s 'http://localhost:9090/api/v1/query?query=redis_client_pool_connections_in_use/redis_client_pool_max_connections'
```

Expected: Ratio < 0.80 (80% utilization)

## Prevention

- Set appropriate pool size for expected load
- Implement connection pool monitoring
- Use connection pooling best practices
- Set connection timeouts to prevent hanging
- Enable connection health checks
- Load test to determine optimal pool size
- Monitor connection count trends

## Recommended Connection Pool Settings

```python
# In src/mcp_server_langgraph/auth/session.py
redis_client = redis.asyncio.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    password=settings.redis_password,
    max_connections=50,  # Pool size
    socket_timeout=5.0,  # Prevent hanging
    socket_connect_timeout=5.0,
    socket_keepalive=True,  # Keep connections alive
    health_check_interval=30,  # Check connection health
    retry_on_timeout=True,
    decode_responses=True,
)
```

## Capacity Planning

**Calculate required pool size**:

```
avg_request_duration = 0.1 seconds  # Average Redis operation time
requests_per_second = 100
connections_needed = requests_per_second × avg_request_duration
safety_factor = 2.0
pool_size = connections_needed × safety_factor
```

**Example**:
- 100 req/s
- 100ms avg operation time
- Required: 100 × 0.1 = 10 connections
- With 2x safety: **20 connections per pod**

## Monitoring

Add connection pool metrics to application:

```python
# In src/mcp_server_langgraph/auth/metrics.py
redis_pool_size = Gauge(
    "redis_client_pool_max_connections",
    "Maximum Redis connection pool size",
)

redis_pool_in_use = Gauge(
    "redis_client_pool_connections_in_use",
    "Current Redis connections in use",
)

# Update periodically
redis_pool_in_use.set(len(redis_client.connection_pool._in_use_connections))
```

## Load Testing

Test connection pool under load:

```bash
# Use Apache Bench or similar
ab -n 10000 -c 100 http://localhost:8000/health

# Monitor connections during test
watch -n 1 'kubectl exec -n langgraph-agent $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}" CLIENT LIST | wc -l'
```

## Related Alerts

- `RedisSessionStoreDown` - Complete service outage
- `RedisHighMemoryUsage` - Memory pressure
- `SessionStoreErrors` - Application session errors
- `HighResponseTime` - Performance degradation

## Alternative Solutions

### 1. Redis Proxy (Twemproxy/Envoy)

Deploy proxy for connection multiplexing:
- Multiple application connections → single Redis connection
- Reduces total connection count

### 2. Redis Cluster

Shard connections across multiple Redis instances:
- Horizontal scaling
- Distributes connection load

### 3. Stateless Sessions

Use JWT tokens instead of Redis sessions:
- No Redis connections needed
- Trade-off: can't revoke tokens easily

## Escalation

If issue persists after tuning:
- Review application architecture
- Consider Redis Cluster deployment
- Evaluate alternative session storage
- Engage performance engineering team

## References

- [Redis Connection Pooling](https://redis.io/docs/manual/clients/)
- [redis-py Documentation](https://redis-py.readthedocs.io/en/stable/connections.html)
- [Session Store Implementation](../src/mcp_server_langgraph/auth/session.py)
- [Deployment Configuration](../deployments/kubernetes/base/deployment.yaml)
