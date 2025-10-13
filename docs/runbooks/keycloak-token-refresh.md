# Runbook: Keycloak Token Refresh Failures

**Alert Name**: `KeycloakTokenRefreshFailures`
**Severity**: Warning
**Component**: keycloak

## Alert Description

Keycloak is experiencing token refresh failures. More than 0.5 token refresh operations per second are failing.

**Alert Rule**:
```yaml
expr: |
  rate(keycloak_token_refresh_failed_total[5m]) > 0.5
for: 3m
```

## Impact

- **User Impact**: MEDIUM - Users may be logged out unexpectedly
- **Service Impact**: Session continuity issues
- **Business Impact**: Disrupted user workflows, re-authentication required

## Symptoms

- Users receive "Token expired" errors during active sessions
- Application logs show token refresh errors
- Increased authentication failure rates
- Users complain about being logged out frequently

## Diagnosis

### 1. Check Token Refresh Failure Rate

```bash
# Query Prometheus
curl -s 'http://localhost:9090/api/v1/query?query=rate(keycloak_token_refresh_failed_total[5m])'
```

### 2. Check Application Logs

```bash
kubectl logs -n langgraph-agent -l app=langgraph-agent --tail=100 | grep -i "token.*refresh\|refresh.*fail"
```

**Look for**:
- "Invalid refresh token" errors
- "Refresh token expired" messages
- HTTP 401/403 responses from Keycloak

### 3. Check Keycloak Logs

```bash
kubectl logs -n langgraph-agent -l app=keycloak --tail=100 | grep -i "refresh\|token"
```

**Look for**:
- Token validation errors
- Session expiration messages
- Client authentication failures

### 4. Check Keycloak Realm Settings

Access Keycloak admin console and verify realm token settings:

```bash
kubectl port-forward -n langgraph-agent svc/keycloak 8080:8080
# Navigate to: http://localhost:8080/admin/master/console/#/langgraph-agent/realm-settings
```

**Check**:
- Access Token Lifespan
- Refresh Token Lifespan
- SSO Session Idle
- SSO Session Max

### 5. Check Client Configuration

In Keycloak admin console, check client settings:

```bash
# Navigate to: Clients > langgraph-client
```

**Verify**:
- Client authentication is enabled
- Valid redirect URIs are configured
- Client secret matches application configuration

### 6. Check System Time Sync

```bash
# Check Keycloak pod time
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=keycloak -o jsonpath='{.items[0].metadata.name}') -- date

# Check application pod time
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=langgraph-agent -o jsonpath='{.items[0].metadata.name}') -- date
```

Time skew can cause token validation failures.

## Resolution

### Scenario 1: Refresh Token Expired

**Cause**: Refresh token lifetime too short for usage pattern

**Fix**:
1. Access Keycloak admin console
2. Navigate to Realm Settings > Tokens
3. Increase "Refresh Token Lifespan":
   - Recommended: 1800 seconds (30 minutes)
   - Current default: 900 seconds (15 minutes)
4. Increase "SSO Session Idle":
   - Recommended: 3600 seconds (1 hour)
5. Save changes

### Scenario 2: Client Secret Mismatch

**Cause**: Application using wrong client secret

**Fix**:
1. Get correct client secret from Keycloak:
   ```bash
   # Navigate to Clients > langgraph-client > Credentials
   ```
2. Update Kubernetes secret:
   ```bash
   kubectl create secret generic langgraph-agent-secrets \
     -n langgraph-agent \
     --from-literal=keycloak-client-secret='<new-secret>' \
     --dry-run=client -o yaml | kubectl apply -f -
   ```
3. Restart application:
   ```bash
   kubectl rollout restart deployment/langgraph-agent -n langgraph-agent
   ```

### Scenario 3: Invalid Refresh Token Format

**Cause**: Token parsing or validation errors

**Fix**:
1. Check application token handling code
2. Verify JWT library compatibility
3. Update application dependencies if needed
4. Review token validation logic in `src/mcp_server_langgraph/auth/keycloak.py`

### Scenario 4: Time Synchronization Issues

**Cause**: Clock skew between services

**Fix**:
1. Ensure NTP is running on nodes:
   ```bash
   kubectl get nodes -o wide
   # SSH to nodes and verify: timedatectl status
   ```
2. Allow time skew tolerance in token validation:
   ```bash
   kubectl patch configmap langgraph-agent-config -n langgraph-agent -p '{"data":{"keycloak_token_clock_skew":"60"}}'
   ```
3. Restart application:
   ```bash
   kubectl rollout restart deployment/langgraph-agent -n langgraph-agent
   ```

### Scenario 5: Session Store Issues

**Cause**: Redis session store errors preventing token storage

**Fix**:
1. Check Redis health:
   ```bash
   kubectl get pods -n langgraph-agent -l app=redis-session
   kubectl logs -n langgraph-agent -l app=redis-session --tail=50
   ```
2. Verify Redis connectivity from application:
   ```bash
   kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=langgraph-agent -o jsonpath='{.items[0].metadata.name}') -- sh -c 'nc -zv redis-session 6379'
   ```
3. Check for Redis memory issues (see `redis-memory.md` runbook)

### Scenario 6: Concurrent Refresh Requests

**Cause**: Multiple clients refreshing same token simultaneously

**Fix**:
1. Implement token refresh locking in application
2. Add retry logic with exponential backoff
3. Review refresh token rotation settings in Keycloak

### Scenario 7: Keycloak Session Eviction

**Cause**: Keycloak evicting sessions due to memory pressure

**Fix**:
1. Check Keycloak memory usage:
   ```bash
   kubectl top pod -n langgraph-agent -l app=keycloak
   ```
2. Increase memory limits:
   ```bash
   kubectl patch deployment keycloak -n langgraph-agent -p '{"spec":{"template":{"spec":{"containers":[{"name":"keycloak","resources":{"limits":{"memory":"3Gi"}}}]}}}}'
   ```
3. Configure external session storage (Infinispan, Redis)

## Verification

After fix, verify token refresh is working:

```bash
# Test token refresh flow
ACCESS_TOKEN="<token>"
REFRESH_TOKEN="<refresh-token>"

curl -X POST http://localhost:8080/realms/langgraph-agent/protocol/openid-connect/token \
  -d "grant_type=refresh_token" \
  -d "client_id=langgraph-client" \
  -d "client_secret=<secret>" \
  -d "refresh_token=$REFRESH_TOKEN" \
  --write-out "\nStatus: %{http_code}\n"
```

Expected: HTTP 200 with new tokens

Check failure rate decreased:
```bash
curl -s 'http://localhost:9090/api/v1/query?query=rate(keycloak_token_refresh_failed_total[5m])'
```

## Prevention

- Set appropriate token lifetimes for usage patterns
- Implement automatic token refresh before expiration
- Monitor token refresh success rate
- Use refresh token rotation for security
- Implement proper error handling and retry logic
- Regular time synchronization verification
- Session store health monitoring

## Recommended Token Lifetimes

```yaml
# For interactive applications
Access Token Lifespan: 300 seconds (5 minutes)
Refresh Token Lifespan: 1800 seconds (30 minutes)
SSO Session Idle: 3600 seconds (1 hour)
SSO Session Max: 28800 seconds (8 hours)

# For long-running background jobs
Access Token Lifespan: 3600 seconds (1 hour)
Refresh Token Lifespan: 86400 seconds (24 hours)
SSO Session Idle: 86400 seconds (24 hours)
SSO Session Max: 604800 seconds (7 days)
```

## Application Code Review

Check token refresh implementation:

**File**: `src/mcp_server_langgraph/auth/keycloak.py`

**Look for**:
- Proper refresh token storage
- Retry logic for transient failures
- Token expiration checking before requests
- Error handling for refresh failures

## Related Alerts

- `SessionStoreErrors` - Session storage issues
- `KeycloakDown` - Service availability
- `KeycloakHighLatency` - Performance issues
- `AuthenticationFailureSpike` - Overall auth problems

## Escalation

If failures persist after 1 hour:
- Review Keycloak configuration with security team
- Check for recent Keycloak version updates
- Review application code changes
- Consider rolling back recent deployments

## References

- [Keycloak Token Documentation](https://www.keycloak.org/docs/latest/server_admin/#_timeouts)
- [OAuth 2.0 Refresh Token Flow](https://datatracker.ietf.org/doc/html/rfc6749#section-6)
- [Integration Guide](../integrations/keycloak.md)
- [Session Management](../../src/mcp_server_langgraph/auth/session.py)
