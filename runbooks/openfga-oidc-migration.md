# OpenFGA OIDC Authentication Migration Runbook

**Status**: Production-Ready
**Last Updated**: 2025-12-15
**Severity**: Medium (Service Disruption During Migration)
**ETA**: 30-45 minutes for complete migration
**Reference**: ADR-0070 - OpenFGA OIDC Authentication Migration

---

## Overview

This runbook guides you through migrating OpenFGA authentication from preshared key to OIDC (OpenID Connect) for defense-in-depth security.

**Benefits**:
- ✅ Defense-in-depth: Token validation + network isolation
- ✅ Token expiration (1 hour default) limits exposure window
- ✅ Automatic token refresh (60-second buffer)
- ✅ Per-service credentials for audit attribution
- ✅ Production-ready security architecture

**Trade-offs**:
- ❌ OpenFGA Playground must be disabled (incompatible with OIDC)
- ❌ Additional Keycloak dependency (increased complexity)
- ❌ Token acquisition adds latency on first request (~100-200ms)

---

## Pre-Migration Checklist

### Requirements Verification

- [ ] **Keycloak is running** and accessible
  ```bash
  curl -f http://localhost/authn/realms/default/.well-known/openid-configuration
  # Should return 200 with JSON configuration
  ```

- [ ] **Keycloak Admin credentials** are available
  ```bash
  # Check environment or secrets manager
  echo $KEYCLOAK_ADMIN_USERNAME  # Should be: admin
  echo $KEYCLOAK_ADMIN_PASSWORD  # Should have value
  ```

- [ ] **OpenFGA data is backed up**
  ```bash
  # PostgreSQL backup (OpenFGA stores)
  pg_dump -h postgres-host -U postgres -d openfga_test > openfga_backup_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] **Rollback plan is understood** (see section below)

- [ ] **Team is notified** of planned downtime
  - Est. downtime: 5-10 minutes for services restart
  - Communication channel: [specify your channel]
  - Contact: [on-call engineer]

### Communication Template

```
🔧 PLANNED MAINTENANCE

Service: OpenFGA Authorization
Impact: Brief service disruption (5-10 minutes)
When: [date/time]
What: Migrating to OIDC authentication for improved security
Affected: All services using OpenFGA (authz-proxy, mcp-server)
Contact: [your-name]
```

---

## Migration Steps

### Phase 1: Create Keycloak Service Account

**Duration**: 5 minutes

#### 1.1 Login to Keycloak Admin Console

```bash
# Open Keycloak admin console
open http://localhost/authn/admin/

# Credentials:
Username: admin
Password: [from KEYCLOAK_ADMIN_PASSWORD]
Realm: master (use dropdown to switch)
```

#### 1.2 Create OpenFGA Service Account Client

1. Navigate to **Clients** → **Create client**
2. Fill in client settings:
   ```yaml
   Client ID: openfga-server
   Name: OpenFGA Server
   Description: Service account for OpenFGA server OIDC authentication
   Protocol: openid-connect
   ```
3. Click **Next**

4. **Capability config**:
   ```yaml
   Client authentication: ON (toggle to enable)
   Authorization: OFF
   Standard flow: OFF
   Direct access grants: OFF
   Service accounts roles: ON (toggle to enable)
   ```
5. Click **Save**

6. Go to **Credentials** tab → Copy **Client secret**
   ```bash
   # Save this value securely
   export OPENFGA_OIDC_CLIENT_SECRET="[paste-secret-here]"
   ```

#### 1.3 Verify Service Account

```bash
# Test token acquisition
curl -X POST http://localhost/authn/realms/default/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=openfga-server" \
  -d "client_secret=$OPENFGA_OIDC_CLIENT_SECRET"

# Should return:
# {
#   "access_token": "<JWT_TOKEN_WILL_APPEAR_HERE>",
#   "expires_in": 3600,
#   "token_type": "Bearer"
# }
```

---

### Phase 2: Update Environment Configuration

**Duration**: 5 minutes

#### 2.1 Update Environment Variables

**For Docker Compose (`.env.test` or `.env`):**
```bash
# Add OIDC credentials
OPENFGA_OIDC_CLIENT_ID=openfga-server
OPENFGA_OIDC_CLIENT_SECRET=[secret-from-step-1.2]

# Optional: Keep preshared key for rollback
# OPENFGA_PRESHARED_KEY=[existing-key]
```

**For Kubernetes (create/update secret):**
```bash
# Create Kubernetes secret
kubectl create secret generic openfga-oidc-creds \
  --from-literal=client-id=openfga-server \
  --from-literal=client-secret=$OPENFGA_OIDC_CLIENT_SECRET \
  --namespace=mcp-server-langgraph

# Update deployment to use secret
kubectl set env deployment/mcp-server \
  --from=secret/openfga-oidc-creds \
  --prefix=OPENFGA_OIDC_ \
  --namespace=mcp-server-langgraph
```

#### 2.2 Update OpenFGA Server Configuration

**Docker Compose (`docker-compose.test.yml`):**
```yaml
openfga-test:
  environment:
    # Change from 'none' or 'preshared' to 'oidc'
    - OPENFGA_AUTHN_METHOD=oidc
    - OPENFGA_AUTHN_OIDC_ISSUER=http://keycloak-test:8080/authn/realms/default
    - OPENFGA_AUTHN_OIDC_AUDIENCE=openfga-server
    # Disable Playground (incompatible with OIDC)
    - OPENFGA_PLAYGROUND_ENABLED=false
```

**Kubernetes (update ConfigMap or environment):**
```yaml
env:
  - name: OPENFGA_AUTHN_METHOD
    value: "oidc"
  - name: OPENFGA_AUTHN_OIDC_ISSUER
    value: "http://keycloak:8080/authn/realms/default"
  - name: OPENFGA_AUTHN_OIDC_AUDIENCE
    value: "openfga-server"
  - name: OPENFGA_PLAYGROUND_ENABLED
    value: "false"
```

---

### Phase 3: Deploy Updated Configuration

**Duration**: 10-15 minutes

#### 3.1 Stop Services (Graceful Shutdown)

```bash
# Docker Compose
docker compose -f docker-compose.test.yml down openfga-test authz-proxy-test mcp-server-test

# Kubernetes
kubectl scale deployment openfga authz-proxy mcp-server --replicas=0 --namespace=mcp-server-langgraph
```

#### 3.2 Start OpenFGA with OIDC

```bash
# Docker Compose
docker compose -f docker-compose.test.yml up -d openfga-test

# Kubernetes
kubectl apply -f deployments/kubernetes/base/openfga/deployment.yaml
kubectl wait --for=condition=ready pod -l app=openfga --timeout=120s
```

#### 3.3 Verify OpenFGA OIDC Authentication

```bash
# Test unauthenticated request (should fail)
curl -X GET http://localhost:9080/stores

# Expected: 401 Unauthorized

# Test with OIDC token (should succeed)
TOKEN=$(curl -X POST http://localhost/authn/realms/default/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=openfga-server" \
  -d "client_secret=$OPENFGA_OIDC_CLIENT_SECRET" \
  | jq -r '.access_token')

curl -X GET http://localhost:9080/stores \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK with JSON response
```

#### 3.4 Start Dependent Services

```bash
# Docker Compose
docker compose -f docker-compose.test.yml up -d authz-proxy-test mcp-server-test

# Kubernetes
kubectl scale deployment authz-proxy mcp-server --replicas=1 --namespace=mcp-server-langgraph
kubectl wait --for=condition=ready pod -l app=authz-proxy --timeout=120s
kubectl wait --for=condition=ready pod -l app=mcp-server --timeout=120s
```

---

### Phase 4: Verification

**Duration**: 5 minutes

#### 4.1 Check Service Logs

```bash
# authz-proxy logs (should see OIDC token acquisition)
docker compose -f docker-compose.test.yml logs authz-proxy-test | grep -i "oidc\|token"

# Expected output:
# INFO: OIDC access token obtained successfully
# INFO: OpenFGA store_id fetched: 01JFGM...

# mcp-server logs
docker compose -f docker-compose.test.yml logs mcp-server-test | grep -i "oidc\|openfga"
```

#### 4.2 Test End-to-End Flow

```bash
# Test authz-proxy can access OpenFGA
curl -X GET http://localhost:9004/api/authz-proxy/health

# Expected: {"status": "healthy", "service": "authz-proxy"}

# Test permission check (requires authenticated user)
# [Add your specific test based on your application]
```

#### 4.3 Monitor Metrics

```bash
# Check Grafana dashboard
open http://localhost/dashboards/

# Navigate to: Dashboards → OpenFGA OIDC
# Verify metrics:
# - openfga_oidc_tokens_acquired_total > 0
# - openfga_oidc_token_cache_hits_total increases over time
# - openfga_oidc_token_acquisition_seconds < 1s (P95)
```

---

## Rollback Plan

**If migration fails, follow these steps to restore service:**

### Immediate Rollback (< 5 minutes)

#### Step 1: Revert OpenFGA Configuration

```bash
# Docker Compose
docker compose -f docker-compose.test.yml down openfga-test

# Edit docker-compose.test.yml:
# OPENFGA_AUTHN_METHOD=none  # or preshared
# OPENFGA_PLAYGROUND_ENABLED=true

docker compose -f docker-compose.test.yml up -d openfga-test
```

#### Step 2: Restart Dependent Services

```bash
docker compose -f docker-compose.test.yml restart authz-proxy-test mcp-server-test
```

#### Step 3: Verify Services Recover

```bash
# Check health endpoints
curl http://localhost:9004/api/authz-proxy/health
curl http://localhost:8000/health/live
```

### Root Cause Analysis (After Rollback)

- [ ] Check Keycloak logs: `docker compose logs keycloak-test | tail -100`
- [ ] Check OpenFGA logs: `docker compose logs openfga-test | tail -100`
- [ ] Verify service account exists: Keycloak Admin Console → Clients → openfga-server
- [ ] Test OIDC token acquisition manually (see Phase 1.3)
- [ ] Review ADR-0070 for troubleshooting guidance

---

## Troubleshooting

### Issue 1: "Failed to obtain OIDC access token: HTTP 401"

**Symptoms**:
```
ERROR: Failed to obtain OIDC access token: HTTP 401
ERROR: Invalid client credentials
```

**Root Cause**: Invalid `OPENFGA_OIDC_CLIENT_SECRET`

**Fix**:
1. Verify secret in Keycloak: Admin Console → Clients → openfga-server → Credentials
2. Update environment variable with correct secret
3. Restart services

---

### Issue 2: "No access_token in Keycloak token response"

**Symptoms**:
```
ERROR: No access_token in Keycloak token response
```

**Root Cause**: Keycloak client misconfigured (service accounts disabled)

**Fix**:
1. Open Keycloak Admin Console → Clients → openfga-server
2. **Capability config** tab → Enable "Service accounts roles"
3. Click **Save**
4. Restart services

---

### Issue 3: OpenFGA Returns 401 for Valid Token

**Symptoms**:
```
# authz-proxy obtains token but OpenFGA rejects it
ERROR: HTTP 401 from OpenFGA API
```

**Root Cause**: Issuer or audience mismatch

**Fix**:
1. Check OpenFGA configuration:
   ```bash
   docker compose exec openfga-test env | grep OIDC
   ```
2. Verify issuer matches:
   ```bash
   # Should match:
   OPENFGA_AUTHN_OIDC_ISSUER=http://keycloak-test:8080/authn/realms/default
   ```
3. Check token claims:
   ```bash
   # Decode JWT token (use jwt.io or jwt-cli)
   echo $TOKEN | cut -d. -f2 | base64 -d | jq

   # Verify:
   # - "iss": "http://keycloak-test:8080/authn/realms/default"
   # - "azp" or "aud": "openfga-server"
   ```

---

### Issue 4: Services Can't Reach Keycloak

**Symptoms**:
```
ERROR: Failed to obtain OIDC token: ConnectionError
ERROR: Cannot connect to http://keycloak-test:8080
```

**Root Cause**: Network connectivity or Keycloak not running

**Fix**:
1. Verify Keycloak is running:
   ```bash
   docker compose ps keycloak-test
   # Should show: Up (healthy)
   ```
2. Test connectivity from service:
   ```bash
   docker compose exec mcp-server-test curl -f http://keycloak-test:8080/authn/realms/default
   ```
3. Check Docker network:
   ```bash
   docker network inspect mcp-test-network
   ```

---

## Post-Migration Tasks

### Documentation Updates

- [ ] Update deployment guides with OIDC configuration
- [ ] Update local development setup instructions
- [ ] Document Playground alternative (API calls with `curl` + OIDC token)

### Monitoring & Alerts

- [ ] Set up alert for `openfga_oidc_token_acquisition_failures_total > 10`
- [ ] Set up alert for `openfga_oidc_token_acquisition_seconds > 5s (P95)`
- [ ] Add OIDC metrics to observability dashboard

### Security

- [ ] **Remove preshared key** from configuration after 7 days of stable operation
- [ ] Rotate OIDC client secret quarterly
- [ ] Review audit logs for token acquisition patterns

---

## Success Criteria

Migration is complete when:

- [x] All services authenticate with OpenFGA using OIDC tokens
- [x] No authentication errors in logs (check for 30 minutes)
- [x] Health checks return 200 OK for all services
- [x] OIDC token metrics are being collected
- [x] Rollback plan is tested and documented
- [x] Team is trained on new authentication flow

---

## References

- **ADR-0070**: OpenFGA OIDC Authentication Migration
- **RFC 6749**: OAuth 2.0 Authorization Framework (Client Credentials Grant)
- **OpenFGA Docs**: [Authentication Configuration](https://openfga.dev/docs/getting-started/setup-openfga/configure-authentication)
- **Keycloak Docs**: [Service Account Client](https://www.keycloak.org/docs/latest/server_admin/#_service_accounts)
- **Runbook Template**: `.claude/templates/runbook-template.md`

---

## Appendix A: Quick Reference

### OIDC Token Acquisition (Manual)

```bash
# Obtain access token
TOKEN=$(curl -X POST http://localhost/authn/realms/default/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=openfga-server" \
  -d "client_secret=$OPENFGA_OIDC_CLIENT_SECRET" \
  | jq -r '.access_token')

# Use token with OpenFGA API
curl -X GET http://localhost:9080/stores \
  -H "Authorization: Bearer $TOKEN"
```

### Environment Variables Reference

```bash
# Required for OIDC
OPENFGA_OIDC_CLIENT_ID=openfga-server
OPENFGA_OIDC_CLIENT_SECRET=[from-keycloak]

# Keycloak configuration
KEYCLOAK_SERVER_URL=http://keycloak-test:8080/authn
KEYCLOAK_REALM=default

# OpenFGA server configuration
OPENFGA_AUTHN_METHOD=oidc
OPENFGA_AUTHN_OIDC_ISSUER=http://keycloak-test:8080/authn/realms/default
OPENFGA_AUTHN_OIDC_AUDIENCE=openfga-server
OPENFGA_PLAYGROUND_ENABLED=false
```

### Common Commands

```bash
# Restart all services
docker compose -f docker-compose.test.yml restart openfga-test authz-proxy-test mcp-server-test

# View logs (last 100 lines)
docker compose -f docker-compose.test.yml logs --tail=100 openfga-test

# Check service health
docker compose -f docker-compose.test.yml ps
```

---

**End of Runbook** | Last Updated: 2025-12-15 | Version: 1.0
