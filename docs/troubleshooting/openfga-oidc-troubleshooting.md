# OpenFGA OIDC Authentication Troubleshooting Guide

**Last Updated**: 2025-12-15
**Reference**: ADR-0070 - OpenFGA OIDC Authentication Migration

---

## Table of Contents

1. [Quick Diagnosis](#quick-diagnosis)
2. [Common Issues](#common-issues)
3. [Debugging Tools](#debugging-tools)
4. [Error Messages Reference](#error-messages-reference)
5. [Performance Issues](#performance-issues)
6. [Security Considerations](#security-considerations)

---

## Quick Diagnosis

### Step 1: Check Service Health

```bash
# All services should return healthy
curl http://localhost:9004/api/authz-proxy/health
curl http://localhost:8000/health/live
curl http://localhost:9080/health
```

### Step 2: Check Logs for OIDC Errors

```bash
# Check authz-proxy logs
docker compose logs authz-proxy-test | grep -i "oidc\|token\|error" | tail -20

# Check mcp-server logs
docker compose logs mcp-server-test | grep -i "oidc\|token\|error" | tail -20

# Check OpenFGA logs
docker compose logs openfga-test | grep -i "auth\|oidc\|error" | tail -20
```

### Step 3: Verify OIDC Configuration

```bash
# Check environment variables
docker compose exec authz-proxy-test env | grep OPENFGA_OIDC
docker compose exec mcp-server-test env | grep OPENFGA_OIDC

# Expected output:
# OPENFGA_OIDC_CLIENT_ID=openfga-server
# OPENFGA_OIDC_CLIENT_SECRET=[should have value]
```

### Step 4: Test Token Acquisition

```bash
# Obtain token manually
curl -X POST http://localhost/authn/realms/default/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=openfga-server" \
  -d "client_secret=$OPENFGA_OIDC_CLIENT_SECRET"

# Expected: 200 OK with access_token
# If 401: Check client_secret
# If 404: Check realm name
# If 503: Keycloak is down
```

---

## Common Issues

### Issue 1: "Failed to obtain OIDC access token: HTTP 401"

#### Symptoms

```
ERROR: Failed to obtain OIDC access token: HTTP 401
ERROR: Invalid client credentials
```

#### Root Causes

1. **Invalid client secret**
2. **Client doesn't exist in Keycloak**
3. **Service accounts not enabled for client**

#### Diagnosis

```bash
# Step 1: Verify client exists in Keycloak
# Open http://localhost/authn/admin/
# Navigate to: Clients → Search for "openfga-server"
# Should exist and be enabled

# Step 2: Check client secret
# Clients → openfga-server → Credentials tab
# Compare with OPENFGA_OIDC_CLIENT_SECRET environment variable

# Step 3: Verify service accounts enabled
# Clients → openfga-server → Settings tab
# "Service accounts roles" should be ON
```

#### Fix

**Option A: Update client secret**
```bash
# Get correct secret from Keycloak Admin Console
# Update environment variable
export OPENFGA_OIDC_CLIENT_SECRET="correct-secret-here"

# Restart services
docker compose restart authz-proxy-test mcp-server-test
```

**Option B: Enable service accounts**
```yaml
# In Keycloak Admin Console:
1. Clients → openfga-server → Settings
2. Capability config → Service accounts roles: ON
3. Save
4. Restart services
```

#### Prevention

- Store secrets in secrets manager (Vault, AWS Secrets Manager)
- Use secret rotation automation
- Monitor for 401 errors with alerts

---

### Issue 2: "No access_token in Keycloak token response"

#### Symptoms

```
ERROR: No access_token in Keycloak token response
ERROR: Token response: {"error":"invalid_client"}
```

#### Root Cause

Client credentials grant not configured properly

#### Diagnosis

```bash
# Test token endpoint directly
curl -v -X POST http://localhost/authn/realms/default/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=openfga-server" \
  -d "client_secret=$OPENFGA_OIDC_CLIENT_SECRET"

# Check response:
# - If "invalid_client": Check client_id and client_secret
# - If "unauthorized_client": Service accounts not enabled
# - If missing access_token: Check grant_type is "client_credentials"
```

#### Fix

```yaml
# Keycloak Admin Console:
1. Clients → openfga-server
2. Settings tab:
   - Client authentication: ON
   - Authorization: OFF
   - Standard flow: OFF
   - Direct access grants: OFF
   - Service accounts roles: ON
3. Save
4. Restart services
```

---

### Issue 3: OpenFGA Rejects Valid OIDC Token (HTTP 401)

#### Symptoms

```
# authz-proxy successfully obtains token but OpenFGA returns 401
INFO: OIDC access token obtained successfully
ERROR: HTTP 401 from OpenFGA API
```

#### Root Causes

1. **Issuer mismatch**
2. **Audience mismatch**
3. **JWKS endpoint unreachable**
4. **Token expired** (clock skew)

#### Diagnosis

**Step 1: Check OpenFGA configuration**
```bash
docker compose exec openfga-test env | grep OIDC

# Expected:
# OPENFGA_AUTHN_METHOD=oidc
# OPENFGA_AUTHN_OIDC_ISSUER=http://keycloak-test:8080/authn/realms/default
# OPENFGA_AUTHN_OIDC_AUDIENCE=openfga-server
```

**Step 2: Decode and inspect JWT token**
```bash
# Get token
TOKEN=$(curl -X POST http://localhost/authn/realms/default/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=openfga-server" \
  -d "client_secret=$OPENFGA_OIDC_CLIENT_SECRET" \
  | jq -r '.access_token')

# Decode token (install jwt-cli: cargo install jwt-cli)
jwt decode $TOKEN

# Or use online tool: https://jwt.io
echo $TOKEN

# Verify claims:
# - "iss": Should match OPENFGA_AUTHN_OIDC_ISSUER exactly
# - "aud" or "azp": Should match OPENFGA_AUTHN_OIDC_AUDIENCE
# - "exp": Should be in the future (Unix timestamp)
```

**Step 3: Test JWKS endpoint**
```bash
# OpenFGA fetches public keys from this endpoint
curl -f http://keycloak-test:8080/authn/realms/default/protocol/openid-connect/certs

# Expected: 200 OK with JSON containing public keys
# If 404: Check issuer URL is correct
# If timeout: Check network connectivity
```

#### Fix

**Issuer mismatch:**
```yaml
# Ensure both use exact same URL (protocol, host, path, realm)
# In docker-compose.test.yml:
environment:
  # For OpenFGA
  - OPENFGA_AUTHN_OIDC_ISSUER=http://keycloak-test:8080/authn/realms/default

  # For services (issuer construction)
  - KEYCLOAK_SERVER_URL=http://keycloak-test:8080/authn
  - KEYCLOAK_REALM=default
```

**Audience mismatch:**
```yaml
# Update OpenFGA audience to match client_id
environment:
  - OPENFGA_AUTHN_OIDC_AUDIENCE=openfga-server  # Must match client_id
```

**Clock skew:**
```bash
# Check system clocks are synchronized
docker compose exec openfga-test date
docker compose exec keycloak-test date

# If different by > 5 minutes, sync clocks:
# On host: sudo ntpdate -s time.nist.gov
# Or use NTP daemon
```

---

### Issue 4: Token Acquisition is Slow (> 1 second)

#### Symptoms

```
WARN: OIDC token acquisition took 2.3 seconds
WARN: openfga_oidc_token_acquisition_seconds P95: 2.5s
```

#### Root Causes

1. **Keycloak is slow** (high load, resource constraints)
2. **Network latency** (services on different networks/datacenters)
3. **DNS resolution issues**

#### Diagnosis

**Step 1: Measure token acquisition time**
```bash
time curl -X POST http://localhost/authn/realms/default/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=openfga-server" \
  -d "client_secret=$OPENFGA_OIDC_CLIENT_SECRET"

# Expected: < 500ms
# If > 1s: Investigate Keycloak performance
```

**Step 2: Check Keycloak resource usage**
```bash
docker stats keycloak-test

# Check CPU and memory usage
# If CPU > 80% or memory near limit: Scale up
```

**Step 3: Check network latency**
```bash
# Measure latency from service to Keycloak
docker compose exec mcp-server-test sh -c "time curl -f http://keycloak-test:8080/authn/realms/default"

# Expected: < 100ms
# If > 500ms: Network issues
```

#### Fix

**Scale Keycloak:**
```yaml
# Increase resources in docker-compose.test.yml
deploy:
  resources:
    limits:
      cpus: '2.0'  # Increase from 1.0
      memory: 2048M  # Increase from 1792M
```

**Enable token caching:**
```python
# Already implemented - verify cache is working
# Check logs for "Using cached OIDC access token"
docker compose logs authz-proxy-test | grep "cached OIDC"
```

**Increase token TTL:**
```yaml
# In Keycloak Admin Console:
# Realm settings → Tokens → Access Token Lifespan
# Increase from 1h to 2h (reduces token acquisition frequency)
```

---

### Issue 5: "Clock skew too large" or Token Expired Immediately

#### Symptoms

```
ERROR: Token expired: exp=1702857600, now=1702861200
ERROR: Clock skew detected: 3600 seconds
```

#### Root Cause

System clocks not synchronized between Keycloak, OpenFGA, and services

#### Diagnosis

```bash
# Check all container clocks
docker compose exec keycloak-test date +%s
docker compose exec openfga-test date +%s
docker compose exec mcp-server-test date +%s

# Compare timestamps (should be within 5 seconds)
```

#### Fix

```bash
# Sync host clock with NTP
sudo ntpdate -s time.nist.gov

# Or install NTP daemon
sudo apt-get install ntp
sudo systemctl start ntp
sudo systemctl enable ntp

# Restart containers to inherit host time
docker compose restart
```

**Workaround (Temporary):**
```python
# Increase token refresh buffer (already set to 60s)
# In src/mcp_server_langgraph/auth/openfga.py
OIDC_TOKEN_REFRESH_BUFFER_SECONDS = 120  # Increase to 2 minutes
```

---

### Issue 6: Services Can't Reach Keycloak (Connection Refused)

#### Symptoms

```
ERROR: Failed to obtain OIDC token: ConnectionError
ERROR: Cannot connect to http://keycloak-test:8080
```

#### Root Causes

1. **Keycloak is not running**
2. **Network connectivity issues**
3. **Incorrect hostname in configuration**

#### Diagnosis

```bash
# Step 1: Check Keycloak is running
docker compose ps keycloak-test
# Should show: Up (healthy)

# Step 2: Test connectivity from service
docker compose exec mcp-server-test curl -f http://keycloak-test:8080/authn/realms/default
# Expected: 200 OK

# Step 3: Check Docker network
docker network inspect mcp-test-network | grep -A 10 keycloak
# Should show keycloak-test with IP address

# Step 4: DNS resolution
docker compose exec mcp-server-test nslookup keycloak-test
# Should resolve to container IP
```

#### Fix

**Start Keycloak:**
```bash
docker compose up -d keycloak-test
docker compose logs -f keycloak-test
# Wait for "Keycloak started successfully"
```

**Fix network configuration:**
```yaml
# Ensure services are on same network in docker-compose.test.yml
networks:
  - mcp-test-network

# Verify network exists
docker network ls | grep mcp-test
```

**Check hostname configuration:**
```yaml
# In environment variables, use service name (not localhost)
KEYCLOAK_SERVER_URL=http://keycloak-test:8080/authn  # ✓ Correct
# NOT: http://localhost:9082/authn  # ✗ Wrong (host port, not container)
```

---

## Debugging Tools

### JWT Token Inspector

```bash
# Install jwt-cli
cargo install jwt-cli

# Decode token
jwt decode $TOKEN

# Or use online: https://jwt.io
```

### OIDC Discovery Endpoint

```bash
# Get OIDC configuration
curl http://localhost/authn/realms/default/.well-known/openid-configuration | jq

# Important fields:
# - issuer: Should match OPENFGA_AUTHN_OIDC_ISSUER
# - token_endpoint: Where to obtain tokens
# - jwks_uri: Where OpenFGA fetches public keys
```

### OpenFGA Health Check

```bash
# Check OpenFGA is running and accessible
curl -f http://localhost:9080/health

# Expected: {"status":"serving"}
```

### Keycloak Admin API

```bash
# Get admin access token
ADMIN_TOKEN=$(curl -X POST http://localhost/authn/realms/master/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=admin123" \
  | jq -r '.access_token')

# Get client details
curl -X GET http://localhost/authn/admin/realms/default/clients \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq '.[] | select(.clientId=="openfga-server")'
```

---

## Error Messages Reference

### Python/FastAPI Errors

| Error Message | Cause | Fix |
|--------------|-------|-----|
| `Failed to obtain OIDC access token: HTTP 401` | Invalid credentials | Check client_id and client_secret |
| `No access_token in Keycloak token response` | Client misconfigured | Enable service accounts in Keycloak |
| `Failed to obtain OIDC token: ConnectionError` | Keycloak unreachable | Check Keycloak is running, verify network |
| `Token verification failed: Invalid issuer` | Issuer mismatch | Ensure OIDC_ISSUER matches token iss claim |
| `OpenFGAError: Unauthorized` | Token rejected by OpenFGA | Check audience, verify JWKS accessible |

### OpenFGA Server Errors

| Error Message | Cause | Fix |
|--------------|-------|-----|
| `authn: invalid token: invalid JWT format` | Malformed token | Check token is valid JWT (3 base64 segments) |
| `authn: invalid token: signature verification failed` | Invalid signature | Verify JWKS endpoint accessible, check issuer |
| `authn: invalid token: token is expired` | Expired token | Check clock skew, verify token TTL |
| `authn: invalid audience` | Audience mismatch | Set OPENFGA_AUTHN_OIDC_AUDIENCE=openfga-server |

### Keycloak Errors

| Error Message | Cause | Fix |
|--------------|-------|-----|
| `invalid_client` | Client doesn't exist or wrong secret | Verify client exists, check secret |
| `unauthorized_client` | Grant type not allowed | Enable service accounts in client settings |
| `unsupported_grant_type` | Wrong grant_type parameter | Use grant_type=client_credentials |

---

## Performance Issues

### Slow Token Acquisition (> 1s)

**Symptoms**: Token acquisition takes > 1 second

**Diagnosis**:
```bash
# Measure time
time curl -X POST http://localhost/authn/realms/default/protocol/openid-connect/token \
  -d "grant_type=client_credentials" \
  -d "client_id=openfga-server" \
  -d "client_secret=$OPENFGA_OIDC_CLIENT_SECRET"
```

**Fixes**:
1. Scale Keycloak resources (CPU, memory)
2. Enable connection pooling in HTTP client
3. Increase token cache TTL
4. Use token refresh buffer (already 60s)

### High Token Acquisition Rate

**Symptoms**: Many token acquisitions per second

**Diagnosis**:
```bash
# Check cache hit rate
docker compose logs authz-proxy-test | grep -c "cached OIDC"
docker compose logs authz-proxy-test | grep -c "Obtaining OIDC"
# Cache hits should be > 90% of total
```

**Fixes**:
1. Verify token caching is working
2. Increase token TTL in Keycloak
3. Increase refresh buffer (current: 60s)

---

## Security Considerations

### Token Expiration Too Long

**Risk**: Long-lived tokens increase exposure window

**Recommendation**:
- Access token TTL: 1 hour (default) ✓
- Refresh before expiration: 60 seconds ✓

### Insufficient Logging

**Risk**: Security incidents not detected

**Recommendation**:
```python
# Add audit logging for token acquisition
logger.info("OIDC token acquired", extra={
    "client_id": client_id,
    "expires_in": expires_in,
    "user": "service-account-openfga-server"
})
```

### Secrets in Logs

**Risk**: Client secret leaked in logs

**Prevention**:
```python
# Never log client_secret
logger.info("Token acquisition", extra={
    "client_id": client_id,
    # NO: "client_secret": client_secret
})
```

---

## References

- **ADR-0070**: OpenFGA OIDC Authentication Migration
- **RFC 6749**: OAuth 2.0 Authorization Framework
- **OpenFGA Docs**: [Authentication](https://openfga.dev/docs/getting-started/setup-openfga/configure-authentication)
- **Keycloak Docs**: [Service Accounts](https://www.keycloak.org/docs/latest/server_admin/#_service_accounts)
- **Migration Runbook**: `runbooks/openfga-oidc-migration.md`

---

**End of Troubleshooting Guide** | Last Updated: 2025-12-15 | Version: 1.0
