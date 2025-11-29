# Migration Guide: Security Fixes (November 2025)

## Overview

This guide helps you migrate existing deployments to incorporate critical security fixes released on November 5, 2025. Follow these steps carefully to ensure a smooth transition while maintaining security.

**Estimated Time**: 30-60 minutes per environment
**Downtime Required**: Yes (5-15 minutes)
**Breaking Changes**: Yes (4 areas)

---

## Pre-Migration Checklist

Before starting migration, complete these preparatory steps:

- [ ] **Backup Current Configuration**
  ```bash
  # Backup environment variables
  env | grep -E "AUTH_|JWT_|SCIM_|BUILDER_" > backup.env

  # Backup database (if using PostgreSQL)
  pg_dump -U postgres mcp_db > mcp_db_backup.sql

  # Backup Keycloak realm
  docker exec keycloak /opt/keycloak/bin/kc.sh export \
    --dir /tmp/export --realm your-realm
  ```

- [ ] **Review Current Service Principals**
  ```bash
  # Get list of all service principals
  curl -H "Authorization: Bearer $TOKEN" \
    http://your-server/api/v1/service-principals/ | jq .

  # Identify any that associate with users other than owner
  ```

- [ ] **Identify SCIM Clients**
  ```bash
  # List all SCIM integrations (Okta, Azure AD, etc.)
  # Note credentials that need updating
  ```

- [ ] **Schedule Maintenance Window**
  - Notify users of planned downtime
  - Schedule during low-traffic period
  - Prepare rollback plan

---

## Migration Steps

### Step 1: Update Application Code

```bash
# Pull latest changes
cd /path/to/mcp-server-langgraph
git fetch origin
git checkout main
git pull origin main

# Verify security commit is present
git log --oneline | grep "fix(security)"
# Should see: 455ad75 fix(security): address critical security vulnerabilities

# Install/update dependencies
uv sync

# Run tests to verify
uv run --frozen pytest tests/api/test_service_principals_security.py \
                tests/api/test_scim_security.py -v
```

**Expected Output**: All tests passing

---

### Step 2: Update Environment Configuration

#### For Production Deployments

Create/update your production environment file:

```bash
# /path/to/.env.production

# ============================================================================
# REQUIRED SECURITY UPDATES
# ============================================================================

# Environment (MUST be set to production)
ENVIRONMENT=production

# Authentication Provider (MUST NOT be inmemory in production)
AUTH_PROVIDER=keycloak

# JWT Secret (MUST be unique and secure)
JWT_SECRET_KEY=$(openssl rand -base64 64)

# GDPR Storage (MUST be postgres in production)
GDPR_STORAGE_BACKEND=postgres
GDPR_POSTGRES_URL=postgresql://user:pass@host:5432/gdpr_db

# Mock Authorization (MUST be false in production)
ENABLE_MOCK_AUTHORIZATION=false

# ============================================================================
# NEW SECURITY SETTINGS
# ============================================================================

# Visual Builder Authentication
BUILDER_AUTH_TOKEN=$(openssl rand -base64 32)
BUILDER_OUTPUT_DIR=/var/lib/mcp-server/workflows

# SCIM Endpoint Security
# (No new env vars needed - uses existing Keycloak roles)

# ============================================================================
# EXISTING CONFIGURATION
# ============================================================================

# Keycloak Settings
KEYCLOAK_SERVER_URL=https://keycloak.example.com
KEYCLOAK_REALM=mcp-production
KEYCLOAK_CLIENT_ID=mcp-server
KEYCLOAK_CLIENT_SECRET=your-keycloak-secret
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=your-admin-password

# ... rest of your configuration ...
```

**Validation**:
```bash
# Test configuration loads without errors
uv run --frozen python -c "from mcp_server_langgraph.core.config import Settings; s = Settings(); print('Config valid!')"
```

---

### Step 3: Migrate Service Principals

#### 3.1 Audit Existing Service Principals

```bash
# Create audit script
cat > audit_service_principals.sh <<'EOF'
#!/bin/bash
set -e

API_URL="http://your-server/api/v1/service-principals"
ADMIN_TOKEN="your-admin-token"

echo "Auditing Service Principals..."
echo "================================"

# Get all service principals
SPS=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$API_URL")

# Filter for potentially problematic associations
echo "$SPS" | jq -r '.[] | select(.associated_user_id != null and .associated_user_id != .owner_user_id) |
  "SP: \(.service_id) | Owner: \(.owner_user_id) | Acts As: \(.associated_user_id)"'

echo "================================"
echo "Review the above service principals."
echo "Non-admin users should only have SPs for themselves."
EOF

chmod +x audit_service_principals.sh
./audit_service_principals.sh
```

#### 3.2 Fix Unauthorized Service Principals

For each problematic service principal found:

**Option A - Delete and Recreate (Recommended)**:
```bash
# Delete the problematic SP
curl -X DELETE \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://your-server/api/v1/service-principals/problematic-sp"

# Recreate with admin account
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "legitimate-service",
    "description": "Proper service principal",
    "associated_user_id": "user:legitimate-user",
    "inherit_permissions": true
  }' \
  "http://your-server/api/v1/service-principals/"

# Save new client_secret securely
```

**Option B - Document as Admin-Approved**:
```bash
# If the association was legitimate but created by wrong user,
# document approval and leave as-is
# The SP will continue to work
```

---

### Step 4: Update SCIM Integration

#### 4.1 For SSO Providers (Okta, Azure AD, OneLogin, etc.)

**Create SCIM Provisioner Service Principal**:

```bash
# 1. Create service principal with admin account
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "scim-provisioner-okta",
    "description": "Okta SCIM 2.0 provisioning integration",
    "authentication_mode": "client_credentials"
  }' \
  "http://your-server/api/v1/service-principals/" \
  > scim_credentials.json

# 2. Extract client_secret (SAVE THIS SECURELY)
CLIENT_ID=$(jq -r '.service_id' scim_credentials.json)
CLIENT_SECRET=$(jq -r '.client_secret' scim_credentials.json)

# 3. Assign scim-provisioner role in Keycloak
# Option A: Via Keycloak Admin UI
#   - Go to Service Accounts → Client: scim-provisioner-okta
#   - Role Mappings → Add "scim-provisioner" role

# Option B: Via API
curl -X POST \
  "https://keycloak.example.com/admin/realms/mcp-production/users/$USER_ID/role-mappings/realm" \
  -H "Authorization: Bearer $KEYCLOAK_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[{"name":"scim-provisioner"}]'

# 4. Update SCIM provider configuration
# Example for Okta:
#   - SCIM Base URL: https://your-server/scim/v2
#   - Authentication: OAuth 2.0 Client Credentials
#   - Client ID: scim-provisioner-okta
#   - Client Secret: <from step 2>
#   - Token URL: https://keycloak.example.com/realms/mcp-production/protocol/openid-connect/token
```

#### 4.2 For Manual SCIM Operations

Users performing manual SCIM operations must have admin role:

```bash
# Assign admin role in Keycloak
# 1. Via Admin UI: Users → <user> → Role Mappings → Add "admin"

# 2. Via API:
curl -X POST \
  "https://keycloak.example.com/admin/realms/mcp-production/users/$USER_ID/role-mappings/realm" \
  -H "Authorization: Bearer $KEYCLOAK_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[{"name":"admin"}]'
```

---

### Step 5: Configure Visual Builder Security

#### 5.1 Set Up Authentication

```bash
# Generate secure token
export BUILDER_AUTH_TOKEN=$(openssl rand -base64 32)

# Add to environment configuration
echo "BUILDER_AUTH_TOKEN=$BUILDER_AUTH_TOKEN" >> /path/to/.env.production

# Store token in secret manager (Infisical, Vault, etc.)
# DO NOT commit token to git
```

#### 5.2 Configure Safe Output Directory

```bash
# Create dedicated directory for workflow outputs
sudo mkdir -p /var/lib/mcp-server/workflows
sudo chown mcp-server:mcp-server /var/lib/mcp-server/workflows
sudo chmod 755 /var/lib/mcp-server/workflows

# Set environment variable
export BUILDER_OUTPUT_DIR=/var/lib/mcp-server/workflows
echo "BUILDER_OUTPUT_DIR=/var/lib/mcp-server/workflows" >> /path/to/.env.production
```

#### 5.3 Update Client Applications

Update any applications using the builder API:

```javascript
// Before (insecure - no auth)
fetch('http://server/api/builder/save', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ workflow, output_path })
});

// After (secure - with auth)
const token = process.env.BUILDER_AUTH_TOKEN;
fetch('http://server/api/builder/save', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    workflow,
    output_path: `/var/lib/mcp-server/workflows/my_workflow.py`
  })
});
```

---

### Step 6: Deploy and Verify

#### 6.1 Deploy Application

**Kubernetes**:
```bash
# Update ConfigMap/Secret with new env vars
kubectl create configmap mcp-config \
  --from-env-file=.env.production \
  --dry-run=client -o yaml | kubectl apply -f -

# Update Deployment
kubectl set image deployment/mcp-server \
  mcp-server=your-registry/mcp-server:v2.8.0-security

# Verify rollout
kubectl rollout status deployment/mcp-server
kubectl get pods -l app=mcp-server
```

**Docker Compose**:
```bash
# Pull latest image
docker-compose pull mcp-server

# Restart with new configuration
docker-compose down
docker-compose up -d

# Verify logs
docker-compose logs -f mcp-server | grep -E "security|config"
```

**Systemd**:
```bash
# Update environment file
sudo cp .env.production /etc/mcp-server/environment

# Restart service
sudo systemctl restart mcp-server

# Check status
sudo systemctl status mcp-server
sudo journalctl -u mcp-server -f
```

#### 6.2 Verification Tests

**Test 1: Service Principal Authorization**:
```bash
# As regular user (should fail)
curl -X POST \
  -H "Authorization: Bearer $REGULAR_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-sp",
    "associated_user_id": "user:admin",
    "inherit_permissions": true
  }' \
  "http://your-server/api/v1/service-principals/"

# Expected: 403 Forbidden

# As admin (should succeed)
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-sp",
    "associated_user_id": "user:someuser",
    "inherit_permissions": true
  }' \
  "http://your-server/api/v1/service-principals/"

# Expected: 201 Created
```

**Test 2: SCIM Authorization**:
```bash
# As regular user (should fail)
curl -X POST \
  -H "Authorization: Bearer $REGULAR_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "userName": "test@example.com"
  }' \
  "http://your-server/scim/v2/Users"

# Expected: 403 Forbidden

# As admin or SCIM provisioner (should succeed)
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "userName": "test@example.com"
  }' \
  "http://your-server/scim/v2/Users"

# Expected: 201 Created
```

**Test 3: Builder Authentication**:
```bash
# Without auth (should fail)
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {...},
    "output_path": "/tmp/test.py"
  }' \
  "http://your-server/api/builder/save"

# Expected: 401 Unauthorized (in production)

# With auth (should succeed)
curl -X POST \
  -H "Authorization: Bearer $BUILDER_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {...},
    "output_path": "/var/lib/mcp-server/workflows/test.py"
  }' \
  "http://your-server/api/builder/save"

# Expected: 200 OK
```

**Test 4: Production Config Validation**:
```bash
# Check startup logs for validation
docker-compose logs mcp-server | grep -E "validate|security|config"

# Should see:
# - "Production configuration validated"
# - NO errors about inmemory auth provider
# - NO errors about missing JWT secrets
```

---

## Troubleshooting

### Issue: Application Won't Start

**Error**: `AUTH_PROVIDER=inmemory is not allowed in production`

**Solution**:
```bash
# Set proper auth provider
export AUTH_PROVIDER=keycloak
export KEYCLOAK_SERVER_URL=https://your-keycloak
export KEYCLOAK_CLIENT_SECRET=your-secret
```

---

### Issue: Service Principal Creation Fails with 403

**Error**: `You are not authorized to create service principals that act as...`

**Solution**:
```bash
# Option 1: Create SP for yourself only
curl -X POST ... -d '{
  "name": "my-service",
  "associated_user_id": "user:me",  # Same as current user
  "inherit_permissions": true
}'

# Option 2: Use admin account
# Get admin token first, then create SP
```

---

### Issue: SCIM Integration Broken

**Error**: Okta/Azure AD provisioning returns 403

**Solution**:
```bash
# 1. Create SCIM provisioner service principal (see Step 4.1)
# 2. Assign scim-provisioner role in Keycloak
# 3. Update SCIM provider with new credentials
# 4. Test with: curl -X POST ... /scim/v2/Users
```

---

### Issue: Builder Requests Return 401

**Error**: `Authentication required. Provide Bearer token`

**Solution**:
```bash
# 1. Set BUILDER_AUTH_TOKEN in environment
export BUILDER_AUTH_TOKEN=$(openssl rand -base64 32)

# 2. Update client to send token
curl -H "Authorization: Bearer $BUILDER_AUTH_TOKEN" ...

# 3. For development, can temporarily set ENVIRONMENT=development
#    (but NOT recommended for production)
```

---

## Rollback Procedure

If critical issues occur:

### Quick Rollback (Recommended for Production)

```bash
# 1. Revert to previous Docker image
docker-compose down
docker-compose pull mcp-server:v2.7.0  # Previous version
docker-compose up -d

# 2. Or rollback Kubernetes deployment
kubectl rollout undo deployment/mcp-server

# 3. Restore previous environment configuration
cp backup.env /path/to/.env.production
```

### Full Rollback (Last Resort)

```bash
# Revert git commit
git revert 455ad75027ea2c5e6a9912884a86783c545bf721
git push origin main

# Redeploy
# ... follow deployment steps ...
```

**⚠️ WARNING**: Rollback reintroduces critical security vulnerabilities. Only use as temporary measure while fixing issues.

---

## Post-Migration

### Monitor for Issues

```bash
# Watch application logs
tail -f /var/log/mcp-server/app.log | grep -E "403|401|security|auth"

# Monitor error rate
# Set up alerts for 403/401 spike

# Check Keycloak audit logs
# Verify no unauthorized access attempts
```

### Update Documentation

- [ ] Update internal wiki with new authentication requirements
- [ ] Notify team of SCIM credential changes
- [ ] Update runbooks with new environment variables
- [ ] Document builder authentication for developers

### Security Validation

- [ ] Run penetration tests against service principal endpoints
- [ ] Verify SCIM operations require proper roles
- [ ] Test builder path traversal protections
- [ ] Confirm production config validation works

---

## Support

**Issues**: Open GitHub Issue with `security-migration` label
**Questions**: GitHub Discussions → Security category
**Urgent**: Contact security@example.com

---

**Guide Version**: 1.0
**Last Updated**: November 5, 2025
**Compatible With**: mcp-server-langgraph v2.8.0+
