# Authentication Alerts Runbook

## Overview

This runbook covers alerts related to authentication (Keycloak SSO) and authorization (OpenFGA).

---

## KeycloakDown

### Alert Definition
```yaml
alert: KeycloakDown
expr: up{job="keycloak"} == 0
for: 1m
severity: critical
```

### Severity
**CRITICAL** - Immediate response required

### Impact
- All new authentication attempts will fail
- Users cannot log in
- Token refresh will fail for existing sessions
- Complete authentication outage

### Diagnosis

1. **Check Keycloak pod status**
   ```bash
   kubectl get pods -l app=keycloak -n auth
   kubectl describe pod -l app=keycloak -n auth
   ```

2. **Check Keycloak logs**
   ```bash
   kubectl logs -l app=keycloak -n auth --tail=100
   ```

3. **Check database connectivity**
   ```bash
   # Keycloak depends on PostgreSQL
   kubectl exec -it keycloak-0 -n auth -- psql -h postgres -U keycloak -c "SELECT 1"
   ```

4. **Check Keycloak admin console**
   ```bash
   curl -k https://keycloak.example.com/health
   ```

### Resolution

1. **If pod is not running**
   ```bash
   kubectl rollout restart statefulset/keycloak -n auth
   ```

2. **If database connection is failing**
   - Check PostgreSQL pod status
   - Verify connection secrets
   - Check network policies

3. **If Keycloak is running but unhealthy**
   - Check realm configuration
   - Verify HTTPS certificates
   - Check Java heap memory

### Escalation
- **On-call SRE**: Slack #sre-oncall
- **Security Team**: If potential security incident

---

## AuthenticationFailureSpike

### Alert Definition
```yaml
alert: AuthenticationFailureSpike
expr: rate(auth_login_failures_total[5m]) > 10
for: 2m
severity: warning
```

### Severity
**WARNING** - Response within 15 minutes (potential security concern)

### Impact
- Many users unable to authenticate
- Could indicate credential stuffing attack
- Could indicate misconfiguration

### Diagnosis

1. **Check failure reasons**
   ```promql
   sum by (reason) (rate(auth_login_failures_total[5m]))
   ```

2. **Check for suspicious patterns**
   - Single user many failures (credential stuffing)
   - Many users from same IP (brute force)
   - Specific realm/client failing

3. **Review authentication logs**
   ```bash
   kubectl logs -l app=langgraph-agent -n mcp-server | grep -i "auth" | grep -i "fail"
   ```

4. **Check Keycloak events**
   - Keycloak Admin Console > Events > Login Events

### Resolution

1. **If credential stuffing attack**
   - Enable rate limiting on Keycloak
   - Block suspicious IPs at ingress level
   - Consider temporary account lockout

2. **If configuration issue**
   - Verify OIDC client configuration
   - Check redirect URIs
   - Verify client secret

3. **If JWKS refresh issue**
   - Check JWKS endpoint availability
   - Restart application to refresh JWKS cache

### Escalation
- **Security Team**: For suspected attacks
- **On-call SRE**: For configuration issues

---

## OpenFGADown

### Alert Definition
```yaml
alert: OpenFGADown
expr: up{job="openfga"} == 0
for: 1m
severity: critical
```

### Severity
**CRITICAL** - Immediate response required

### Impact
- All authorization checks will fail
- Users cannot access protected resources
- API requests will return 403 errors

### Diagnosis

1. **Check OpenFGA pod status**
   ```bash
   kubectl get pods -l app=openfga -n auth
   kubectl describe pod -l app=openfga -n auth
   ```

2. **Check OpenFGA logs**
   ```bash
   kubectl logs -l app=openfga -n auth --tail=100
   ```

3. **Check database connectivity**
   ```bash
   # OpenFGA uses PostgreSQL for tuple storage
   kubectl exec -it openfga-0 -n auth -- psql -h postgres -U openfga -c "SELECT 1"
   ```

4. **Check OpenFGA health**
   ```bash
   curl http://openfga:8080/healthz
   ```

### Resolution

1. **If pod is not running**
   ```bash
   kubectl rollout restart deployment/openfga -n auth
   ```

2. **If database connection is failing**
   - Check PostgreSQL pod status
   - Verify connection secrets
   - Check database exists

3. **If store initialization failed**
   - Check store_id in configuration
   - Verify authorization model is loaded
   - Re-run OpenFGA initialization

### Escalation
- **On-call SRE**: Slack #sre-oncall
- **Security Team**: For authorization model issues

---

## HighAuthorizationDenialRate

### Alert Definition
```yaml
alert: HighAuthorizationDenialRate
expr: rate(authz_check_total{result="denied"}[5m]) / rate(authz_check_total[5m]) > 0.3
for: 5m
severity: warning
```

### Severity
**WARNING** - Response within 30 minutes

### Impact
- Many users experiencing permission denied errors
- Could indicate misconfigured permissions
- Could indicate unauthorized access attempts

### Diagnosis

1. **Check denial patterns**
   ```promql
   sum by (relation, object_type) (rate(authz_check_total{result="denied"}[5m]))
   ```

2. **Identify affected users**
   - Check which user roles are being denied
   - Review recent permission changes

3. **Check OpenFGA tuples**
   ```bash
   # Query OpenFGA for user permissions
   curl -X POST http://openfga:8080/stores/{store_id}/read \
     -d '{"tuple_key": {"user": "user:example"}}'
   ```

### Resolution

1. **If permissions were recently changed**
   - Review recent tuple changes
   - Rollback if necessary
   - Verify authorization model

2. **If role sync is failing**
   - Check Keycloak-OpenFGA sync
   - Verify role mapper configuration
   - Re-run role synchronization

3. **If new feature deployment**
   - Verify new permissions were added
   - Check migration scripts ran

### Escalation
- **Security Team**: For permission model changes
- **On-call SRE**: For sync issues
