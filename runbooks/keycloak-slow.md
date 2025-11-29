# Runbook: Keycloak High Latency

**Alert Name**: `KeycloakHighLatency`
**Severity**: Warning
**Component**: keycloak

## Alert Description

Keycloak SSO service is experiencing high response times. The 95th percentile latency exceeds 2 seconds.

**Alert Rule**:
```yaml
expr: |
  histogram_quantile(0.95,
    rate(keycloak_request_duration_bucket[5m])
  ) > 2000
for: 5m
```

## Impact

- **User Impact**: MEDIUM - Slow login/authentication experience
- **Service Impact**: Degraded authentication performance
- **Business Impact**: User frustration, potential timeouts

## Symptoms

- Login pages take 2+ seconds to respond
- Token validation requests are slow
- Application logs show Keycloak timeout warnings
- Users report slow authentication

## Diagnosis

### 1. Check Current Response Times

```bash
# Port forward to access metrics
kubectl port-forward -n langgraph-agent svc/keycloak 8080:8080 &

# Query Prometheus for latency
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(keycloak_request_duration_bucket[5m]))'
```

### 2. Check Resource Usage

```bash
kubectl top pod -n langgraph-agent -l app=keycloak
```

**Look for**:
- CPU usage near 90%+
- Memory usage near limits
- CPU throttling

### 3. Check Pod Count

```bash
kubectl get pods -n langgraph-agent -l app=keycloak
```

**Look for**:
- Number of ready pods vs desired replicas
- Any pods in non-Ready state

### 4. Check PostgreSQL Performance

```bash
kubectl logs -n langgraph-agent -l app=postgres --tail=50 | grep -i slow
```

Keycloak performance is tied to PostgreSQL. Slow database queries will cause high latency.

### 5. Check Network Latency

```bash
# Test network latency from application pod
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=langgraph-agent -o jsonpath='{.items[0].metadata.name}') -- sh -c 'time nc -zv keycloak 8080'
```

### 6. Check for High Request Rate

```bash
# Check request rate
kubectl logs -n langgraph-agent -l app=keycloak --tail=200 | grep -c "GET\|POST"
```

High traffic may be overwhelming the service.

## Resolution

### Scenario 1: High CPU Usage

**Cause**: Insufficient CPU resources

**Fix**:
1. Scale horizontally:
   ```bash
   kubectl scale deployment keycloak -n langgraph-agent --replicas=3
   ```
2. Or increase CPU limits:
   ```bash
   kubectl patch deployment keycloak -n langgraph-agent -p '{"spec":{"template":{"spec":{"containers":[{"name":"keycloak","resources":{"limits":{"cpu":"3000m"},"requests":{"cpu":"1000m"}}}]}}}}'
   ```

### Scenario 2: High Memory Usage

**Cause**: Insufficient memory causing GC pressure

**Fix**:
1. Increase memory limits:
   ```bash
   kubectl patch deployment keycloak -n langgraph-agent -p '{"spec":{"template":{"spec":{"containers":[{"name":"keycloak","resources":{"limits":{"memory":"3Gi"},"requests":{"memory":"1.5Gi"}}}]}}}}'
   ```
2. Tune JVM heap settings via environment variables

### Scenario 3: Insufficient Replicas

**Cause**: Too few pods to handle load

**Fix**:
1. Scale deployment:
   ```bash
   kubectl scale deployment keycloak -n langgraph-agent --replicas=3
   ```
2. Enable horizontal pod autoscaling:
   ```bash
   kubectl autoscale deployment keycloak -n langgraph-agent --min=2 --max=5 --cpu-percent=70
   ```

### Scenario 4: PostgreSQL Performance

**Cause**: Slow database queries

**Fix**:
1. Check PostgreSQL slow query log
2. Add database indexes for frequently queried tables
3. Scale PostgreSQL resources:
   ```bash
   kubectl patch deployment postgres -n langgraph-agent -p '{"spec":{"template":{"spec":{"containers":[{"name":"postgres","resources":{"limits":{"cpu":"2000m","memory":"4Gi"}}}]}}}}'
   ```
4. Consider PostgreSQL connection pooling (PgBouncer)

### Scenario 5: JWKS Cache Issues

**Cause**: Frequent JWKS fetches causing overhead

**Fix**:
1. Check application logs for JWKS cache hit rate
2. Increase JWKS cache TTL in application ConfigMap:
   ```bash
   kubectl patch configmap langgraph-agent-config -n langgraph-agent -p '{"data":{"keycloak_jwks_cache_ttl":"3600"}}'
   ```
3. Restart application to apply:
   ```bash
   kubectl rollout restart deployment/langgraph-agent -n langgraph-agent
   ```

### Scenario 6: Session Overhead

**Cause**: Too many active sessions

**Fix**:
1. Review session configuration in Keycloak admin console
2. Reduce session timeout values
3. Enable session eviction policies

### Scenario 7: Network Congestion

**Cause**: Network latency between services

**Fix**:
1. Verify pods are scheduled on same node/zone when possible
2. Check node network performance
3. Review service mesh configuration if applicable

## Verification

After fix, verify latency has improved:

```bash
# Check Prometheus metrics
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(keycloak_request_duration_bucket[5m]))'

# Test login flow manually
curl -X POST http://localhost:8080/realms/langgraph-agent/protocol/openid-connect/token \
  -d "grant_type=password" \
  -d "client_id=langgraph-client" \
  -d "client_secret=<secret>" \
  -d "username=testuser" \
  -d "password=testpass" \
  --write-out "\nTime: %{time_total}s\n"
```

Expected time: < 1 second for token endpoint

## Prevention

- Configure horizontal pod autoscaling (HPA)
- Set appropriate resource requests and limits
- Monitor request rate and scale proactively
- Implement caching strategies (JWKS, sessions)
- Regular performance testing and capacity planning
- Database query optimization and indexing
- Use Redis for session storage instead of PostgreSQL

## Related Alerts

- `KeycloakDown` - Complete service outage
- `HighCPUUsage` - CPU resource exhaustion
- `HighMemoryUsage` - Memory pressure
- PostgreSQL performance alerts

## Performance Tuning

### Recommended Keycloak Settings

```yaml
env:
- name: JAVA_OPTS
  value: "-Xms1024m -Xmx2048m -XX:+UseG1GC -XX:MaxGCPauseMillis=100"
- name: KC_CACHE
  value: "ispn"  # Infinispan caching
- name: KC_CACHE_STACK
  value: "kubernetes"  # Kubernetes discovery
```

### Recommended HPA Configuration

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: keycloak-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: keycloak
  minReplicas: 2
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Escalation

If latency remains above 2s after 1 hour:
- Notify application team
- Review recent changes
- Consider temporary traffic reduction
- Plan capacity upgrade

## References

- [Keycloak Performance Tuning](https://www.keycloak.org/high-availability/concepts-memory-and-cpu-sizing)
- [Deployment Configuration](../deployments/base/keycloak-deployment.yaml)
- [Integration Guide](../integrations/keycloak.md)
