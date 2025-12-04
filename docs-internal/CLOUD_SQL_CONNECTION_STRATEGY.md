# Cloud SQL Connection Strategy

## Overview

This document describes the Cloud SQL connection strategies used across different environments in the MCP Server LangGraph deployment.

## Connection Methods

### 1. Cloud SQL Proxy (Sidecar Pattern)

**Used in:** Production GKE

**How it works:**
- Cloud SQL Proxy runs as a sidecar container alongside the application
- Application connects to `localhost:5432` (PostgreSQL)
- Proxy handles authentication via Workload Identity
- Proxy manages encrypted connections to Cloud SQL

**Configuration:**
```yaml
# Cloud SQL Proxy sidecar container
- name: cloud-sql-proxy
  image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.14.1
  args:
    - "--structured-logs"
    - "--port=5432"
    - "--private-ip"
    - "$(CLOUDSQL_CONNECTION_NAME)"
    - "--health-check"         # Enable health checks
    - "--http-port=9801"        # Health check port
    - "--http-address=0.0.0.0"  # Allow K8s probes
```

**Network Policy Requirements:**
```yaml
# Allow egress to PostgreSQL via Cloud SQL Proxy (localhost)
- to:
  - podSelector:
      matchLabels:
        app: mcp-server-langgraph
  ports:
  - protocol: TCP
    port: 5432  # PostgreSQL via proxy
```

**Advantages:**
- **Security**: Automatic IAM authentication, no passwords in config
- **Encryption**: Always uses encrypted connections
- **Connection pooling**: Proxy handles connection management
- **Multi-region**: Works across regions and projects
- **Cloud SQL Admin API**: Can use Cloud SQL Admin API features

**Disadvantages:**
- **Resource overhead**: Additional sidecar container (256-512Mi RAM, 250-500m CPU)
- **Complexity**: More moving parts to configure and monitor
- **Latency**: Additional hop through proxy (minimal, ~1-2ms)

**When to use:**
- ✅ Production deployments requiring high security
- ✅ Multi-region or multi-project setups
- ✅ When using Cloud SQL connection pooling
- ✅ When you need Cloud SQL Admin API features
- ✅ Cross-VPC or cross-network connections

---

### 2. Direct Private IP Connection

**Used in:** Staging GKE (configurable)

**How it works:**
- Application connects directly to Cloud SQL's private IP address
- Requires VPC peering between GKE and Cloud SQL
- Uses standard PostgreSQL connection string
- Authentication can use IAM or password-based

**Configuration:**
```yaml
# Direct connection in ConfigMap
postgres_host: "10.110.0.3"  # Cloud SQL private IP
postgres_port: "5432"
postgres_url: "postgresql://user@10.110.0.3:5432/database?sslmode=require"
```

**Network Policy Requirements:**
```yaml
# Allow Cloud SQL connection via private IP
- to:
  - ipBlock:
      cidr: 10.0.0.0/8  # GCP private IP range
  ports:
  - protocol: TCP
    port: 5432  # PostgreSQL standard port (NOT 3307!)
```

**Advantages:**
- **Performance**: Direct connection, no proxy overhead
- **Simplicity**: Standard PostgreSQL connection, fewer components
- **Resource efficiency**: No sidecar container needed
- **Debugging**: Easier to troubleshoot (standard psql tools work)

**Disadvantages:**
- **Security**: Requires network-level access (VPC peering)
- **Manual setup**: Must configure VPC peering and private IP
- **Limited to VPC**: Only works within the same VPC or peered VPCs
- **Connection limits**: No built-in connection pooling

**When to use:**
- ✅ Single-region deployments within same VPC
- ✅ Development/staging environments
- ✅ When minimizing resource overhead is important
- ✅ When you have VPC peering already configured
- ✅ Simple, straightforward deployments

---

## Current Configuration

### Production (production-gke)

**Method:** Cloud SQL Proxy (sidecar)

**Reason:** Production requires highest security, IAM authentication, and encryption guarantees.

**Configuration files:**
- `deployments/overlays/production-gke/deployment-patch.yaml` - Proxy sidecar configuration
- `deployments/overlays/production-gke/network-policy.yaml` - Network rules for proxy

**Health checks:**
```yaml
livenessProbe:
  httpGet:
    path: /liveness
    port: 9801  # Cloud SQL Proxy health endpoint

readinessProbe:
  httpGet:
    path: /readiness
    port: 9801  # Cloud SQL Proxy readiness endpoint
```

**Important:** Proxy args MUST include health check flags when probes are configured:
- `--health-check`
- `--http-port=9801`
- `--http-address=0.0.0.0`

---

### Staging (preview-gke)

**Method:** Hybrid (both methods configured)

**Current state:** Both Cloud SQL Proxy and direct IP connection are configured, allowing flexibility for testing.

**Configuration files:**
- `deployments/overlays/preview-gke/deployment-patch.yaml` - Proxy sidecar (commented/optional)
- `deployments/overlays/preview-gke/configmap-patch.yaml` - Direct IP connection strings
- `deployments/overlays/preview-gke/network-policy.yaml` - Network rules for both methods

**Recommendation:** Choose one method for staging to avoid confusion:

**Option A: Use Cloud SQL Proxy (recommended for prod parity)**
```bash
# Enable proxy in deployment-patch.yaml
# Update configmap to use localhost:5432
postgres_url: "postgresql://user@localhost:5432/database"
```

**Option B: Use Direct IP (simpler for staging)**
```bash
# Remove proxy sidecar from deployment-patch.yaml
# Keep existing direct IP configuration
postgres_url: "postgresql://user@10.110.0.3:5432/database"
```

---

## Migration Guide

### From Direct IP to Cloud SQL Proxy

1. **Add proxy sidecar to Deployment:**
   ```yaml
   containers:
   - name: cloud-sql-proxy
     image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.14.1
     args:
       - "--structured-logs"
       - "--port=5432"
       - "--private-ip"
       - "PROJECT:REGION:INSTANCE"
       - "--health-check"
       - "--http-port=9801"
       - "--http-address=0.0.0.0"
   ```

2. **Update connection strings to use localhost:**
   ```yaml
   postgres_host: "localhost"  # Changed from private IP
   postgres_url: "postgresql://user@localhost:5432/database"
   ```

3. **Update Network Policy:**
   ```yaml
   # Add rule for localhost communication
   - to:
     - podSelector:
         matchLabels:
           app: mcp-server-langgraph
     ports:
     - protocol: TCP
       port: 5432
   ```

4. **Configure Workload Identity:**
   ```yaml
   serviceAccount:
     annotations:
       iam.gke.io/gcp-service-account: app@project.iam.gserviceaccount.com
   ```

5. **Test connectivity:**
   ```bash
   kubectl exec -it <pod> -- psql -h localhost -p 5432 -U user -d database
   ```

### From Cloud SQL Proxy to Direct IP

1. **Remove proxy sidecar from Deployment**

2. **Update connection strings:**
   ```yaml
   postgres_host: "10.x.x.x"  # Cloud SQL private IP
   postgres_url: "postgresql://user@10.x.x.x:5432/database?sslmode=require"
   ```

3. **Update Network Policy:**
   ```yaml
   # Allow egress to GCP private IP range
   - to:
     - ipBlock:
         cidr: 10.0.0.0/8
     ports:
     - protocol: TCP
       port: 5432  # PostgreSQL port
   ```

4. **Configure VPC peering** (if not already done)

5. **Update authentication** (password or IAM)

---

## Common Issues & Troubleshooting

### Issue: "Connection refused" or "Connection timeout"

**Proxy method:**
- ✅ Check proxy logs: `kubectl logs <pod> -c cloud-sql-proxy`
- ✅ Verify health checks pass: `curl localhost:9801/liveness`
- ✅ Confirm CLOUDSQL_CONNECTION_NAME is correct
- ✅ Verify Workload Identity is properly configured

**Direct IP method:**
- ✅ Verify VPC peering exists
- ✅ Check Network Policy allows egress to private IP
- ✅ Confirm Cloud SQL instance has private IP enabled
- ✅ Test with `kubectl exec`: `nc -zv 10.x.x.x 5432`

### Issue: Wrong port (3307 instead of 5432)

**Problem:** Port 3307 is for MySQL, PostgreSQL uses 5432.

**Fix:**
```yaml
# WRONG
port: 3307  # MySQL port

# CORRECT
port: 5432  # PostgreSQL port
```

**Files to check:**
- `deployments/overlays/preview-gke/network-policy.yaml`
- `deployments/overlays/production-gke/network-policy.yaml`

### Issue: Proxy health checks failing

**Problem:** Liveness/readiness probes configured but proxy not exposing health endpoints.

**Fix:** Add health check flags to proxy args:
```yaml
args:
  - "--health-check"
  - "--http-port=9801"
  - "--http-address=0.0.0.0"
```

### Issue: "too many connections" to Cloud SQL

**Proxy method:**
- Adjust proxy's `--max-connections` flag
- Enable Cloud SQL connection pooling

**Direct IP method:**
- Implement application-level connection pooling (pgBouncer, PgPool)
- Increase Cloud SQL max_connections setting

---

## Performance Considerations

### Latency

| Method | Typical Latency | Notes |
|--------|----------------|-------|
| Cloud SQL Proxy | +1-2ms | Minimal overhead for localhost hop |
| Direct Private IP | Baseline | Direct VPC connection |

### Resource Usage

| Method | CPU | Memory | Notes |
|--------|-----|--------|-------|
| Cloud SQL Proxy | 250-500m | 256-512Mi | Per sidecar container |
| Direct Private IP | 0 | 0 | No additional containers |

### Connection Pooling

| Method | Built-in Pooling | External Pooling |
|--------|------------------|------------------|
| Cloud SQL Proxy | ✅ Yes (optional) | ✅ Can add PgBouncer |
| Direct Private IP | ❌ No | ✅ Requires PgBouncer/PgPool |

---

## Security Best Practices

### Cloud SQL Proxy
- ✅ Always use Workload Identity (never hardcode credentials)
- ✅ Use `--private-ip` flag for private network connections
- ✅ Enable structured logging (`--structured-logs`)
- ✅ Configure health checks for production
- ✅ Set resource limits on sidecar container
- ✅ Use read-only root filesystem when possible

### Direct Private IP
- ✅ Always use `sslmode=require` or `sslmode=verify-ca`
- ✅ Restrict Network Policy to specific IP ranges
- ✅ Use IAM authentication when possible
- ✅ Rotate passwords regularly if using password auth
- ✅ Limit VPC peering to necessary networks only
- ✅ Monitor connection attempts and failures

---

## Decision Matrix

| Requirement | Cloud SQL Proxy | Direct Private IP |
|------------|----------------|-------------------|
| Production security | ✅ Recommended | ⚠️ Requires careful setup |
| Multi-region | ✅ Yes | ❌ VPC peering required |
| Minimal latency | ⚠️ +1-2ms overhead | ✅ Direct connection |
| Minimal resources | ❌ Sidecar overhead | ✅ No extra containers |
| IAM authentication | ✅ Built-in | ⚠️ Requires Cloud SQL IAM connector |
| Connection pooling | ✅ Optional built-in | ⚠️ Requires external tool |
| Simple troubleshooting | ⚠️ More components | ✅ Standard PostgreSQL |
| Cloud SQL features | ✅ Full support | ⚠️ Limited |

---

## References

- [Cloud SQL Proxy Documentation](https://cloud.google.com/sql/docs/mysql/sql-proxy)
- [Cloud SQL Private IP](https://cloud.google.com/sql/docs/mysql/configure-private-ip)
- [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [VPC Peering](https://cloud.google.com/vpc/docs/vpc-peering)

---

**Last Updated:** 2025-11-07
**Reviewed By:** OpenAI Codex Validation (Phase 4)
