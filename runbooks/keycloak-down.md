# Runbook: Keycloak Service Down

**Alert Name**: `KeycloakDown`
**Severity**: Critical
**Component**: keycloak

## Alert Description

The Keycloak SSO service is down and unavailable. Authentication will fail for all users.

**Alert Rule**:
```yaml
expr: up{job="keycloak"} == 0
for: 2m
```

## Impact

- **User Impact**: HIGH - All authentication attempts will fail
- **Service Impact**: Complete authentication outage
- **Business Impact**: Users cannot log in or access the application

## Symptoms

- Health check endpoint `/health` returns 503 or times out
- Users receive "Service Unavailable" errors when attempting to log in
- Application logs show connection errors to Keycloak
- Metric `up{job="keycloak"}` shows 0 for more than 2 minutes

## Diagnosis

### 1. Check Pod Status

```bash
kubectl get pods -n langgraph-agent -l app=keycloak
kubectl describe pod -n langgraph-agent -l app=keycloak
```

**Look for**:
- Pod status (CrashLoopBackOff, ImagePullBackOff, Pending)
- Container restart count
- Events showing errors

### 2. Check Logs

```bash
kubectl logs -n langgraph-agent -l app=keycloak --tail=100
kubectl logs -n langgraph-agent -l app=keycloak --previous
```

**Look for**:
- Database connection errors
- Port binding failures
- Out of memory errors
- Configuration errors

### 3. Check PostgreSQL Dependency

```bash
kubectl get pods -n langgraph-agent -l app=postgres
kubectl logs -n langgraph-agent -l app=postgres --tail=50
```

Keycloak requires PostgreSQL. If PostgreSQL is down, Keycloak will fail.

### 4. Check Service and Endpoints

```bash
kubectl get service keycloak -n langgraph-agent
kubectl get endpoints keycloak -n langgraph-agent
```

**Look for**:
- Service has correct selector
- Endpoints list has healthy pod IPs

### 5. Check Resource Limits

```bash
kubectl top pod -n langgraph-agent -l app=keycloak
```

**Look for**:
- Memory usage near limits
- CPU throttling

## Resolution

### Scenario 1: Pod CrashLoopBackOff

**Cause**: Application failing to start

**Fix**:
1. Check logs for specific error
2. Verify database credentials in secrets:
   ```bash
   kubectl get secret langgraph-agent-secrets -n langgraph-agent -o jsonpath='{.data.postgres-password}' | base64 -d
   ```
3. Verify PostgreSQL is running and accessible
4. Check ConfigMap for correct database settings:
   ```bash
   kubectl get configmap langgraph-agent-config -n langgraph-agent -o yaml
   ```

### Scenario 2: ImagePullBackOff

**Cause**: Cannot pull container image

**Fix**:
1. Check image name and tag in deployment:
   ```bash
   kubectl get deployment keycloak -n langgraph-agent -o jsonpath='{.spec.template.spec.containers[0].image}'
   ```
2. Verify image exists: `quay.io/keycloak/keycloak:23.0`
3. Check image pull secrets if using private registry

### Scenario 3: PostgreSQL Connection Failure

**Cause**: Database unavailable or credentials incorrect

**Fix**:
1. Restart PostgreSQL if unhealthy
2. Verify database exists:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=postgres -o jsonpath='{.items[0].metadata.name}') -- psql -U postgres -c '\l'
   ```
3. Create keycloak database if missing:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=postgres -o jsonpath='{.items[0].metadata.name}') -- psql -U postgres -c 'CREATE DATABASE keycloak;'
   ```

### Scenario 4: Out of Memory

**Cause**: Pod exceeding memory limits

**Fix**:
1. Increase memory limits in deployment:
   ```bash
   kubectl patch deployment keycloak -n langgraph-agent -p '{"spec":{"template":{"spec":{"containers":[{"name":"keycloak","resources":{"limits":{"memory":"3Gi"}}}]}}}}'
   ```
2. Monitor memory usage after increase

### Scenario 5: Configuration Error

**Cause**: Invalid environment variables or settings

**Fix**:
1. Review ConfigMap and Secrets
2. Compare with `.env.example` for required variables
3. Update ConfigMap and restart:
   ```bash
   kubectl rollout restart deployment/keycloak -n langgraph-agent
   ```

### Emergency Rollback

If recent deployment caused the issue:

```bash
kubectl rollout undo deployment/keycloak -n langgraph-agent
kubectl rollout status deployment/keycloak -n langgraph-agent
```

### Fallback: InMemory Provider

As emergency workaround, switch to InMemory auth provider:

1. Update ConfigMap:
   ```bash
   kubectl patch configmap langgraph-agent-config -n langgraph-agent -p '{"data":{"auth_provider":"inmemory"}}'
   ```
2. Restart main application:
   ```bash
   kubectl rollout restart deployment/langgraph-agent -n langgraph-agent
   ```

**Note**: This loses all user sessions and uses hardcoded test users only.

## Verification

After fix, verify Keycloak is healthy:

```bash
# Check pod is running
kubectl get pods -n langgraph-agent -l app=keycloak

# Check logs show successful startup
kubectl logs -n langgraph-agent -l app=keycloak --tail=20

# Test health endpoint
kubectl port-forward -n langgraph-agent svc/keycloak 8080:8080 &
curl http://localhost:8080/health
```

Expected response: `{"status":"UP"}`

## Prevention

- Set up pod disruption budgets for Keycloak
- Configure horizontal pod autoscaling
- Monitor PostgreSQL health proactively
- Set resource requests/limits appropriately
- Enable persistent storage for PostgreSQL

## Related Alerts

- `KeycloakHighLatency` - Performance degradation
- `KeycloakTokenRefreshFailures` - Token refresh issues
- PostgreSQL alerts if database is root cause

## Escalation

If issue persists after 30 minutes:
- Page on-call SRE
- Consider invoking incident response
- Communicate outage to stakeholders

## References

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [Deployment Configuration](../deployments/base/keycloak-deployment.yaml)
- [Integration Guide](../integrations/keycloak.md)
