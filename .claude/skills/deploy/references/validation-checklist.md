# Deployment Validation Checklist

Pre-deployment validation, post-deployment verification, and smoke tests.

---

## Pre-Deployment Validation

### Validation Checklist

```
  PRE-DEPLOYMENT VALIDATION

  Environment Checks:
  - Check kubectl installed and configured
  - Verify cluster context (correct cluster)
  - Check namespace exists
  - Verify required secrets exist
  - Validate RBAC permissions
  - Check resource quotas

  Manifest Validation:
  - Run kubectl --dry-run=client
  - Validate YAML syntax
  - Check image tags exist
  - Verify resource requests/limits
  - Validate environment variables

  Dependency Checks:
  - Redis availability
  - PostgreSQL availability
  - OpenFGA availability
  - Keycloak availability (if applicable)
  - External secrets configured (if applicable)
```

### Pre-Deployment Commands

```bash
# Check kubectl
kubectl version --client

# Check cluster context
kubectl config current-context

# Validate manifests
kubectl apply --dry-run=client -k deployments/<overlay>

# Check secrets
kubectl get secrets -n mcp-server-langgraph

# Check resource quotas
kubectl get resourcequota -n mcp-server-langgraph
```

---

## Post-Deployment Verification

### Verification Checklist

```
  POST-DEPLOYMENT VERIFICATION

  Application Health:
  - Pods are running (all replicas ready)
  - Health checks passing (/health endpoint)
  - Readiness probes passing
  - No CrashLoopBackOff errors

  Dependencies:
  - Redis connection successful
  - PostgreSQL connection successful
  - OpenFGA connection successful
  - Keycloak connection successful (if applicable)

  Observability:
  - Metrics being exported to Prometheus
  - Traces being sent to Jaeger/OTLP
  - Logs flowing to aggregation system
  - Grafana dashboards showing data

  Network & Ingress:
  - Service endpoints accessible
  - Ingress/Load balancer configured
  - TLS certificates valid
  - DNS resolving correctly

  Security:
  - Network policies in place
  - Pod security policies/standards enforced
  - Secrets properly mounted
  - RBAC configured correctly
```

### Verification Commands

```bash
# 1. Check pod status
kubectl get pods -n mcp-server-langgraph -l app=mcp-server-langgraph

# 2. Check pod logs
kubectl logs -n mcp-server-langgraph -l app=mcp-server-langgraph --tail=50

# 3. Test health endpoint
kubectl port-forward -n mcp-server-langgraph svc/mcp-server-langgraph 8000:8000 &
curl http://localhost:8000/health

# 4. Check service endpoints
kubectl get endpoints -n mcp-server-langgraph

# 5. Describe pod for events
kubectl describe pod -n mcp-server-langgraph -l app=mcp-server-langgraph

# 6. Check resource usage
kubectl top pods -n mcp-server-langgraph

# 7. Verify dependencies
kubectl exec -it -n mcp-server-langgraph <pod-name> -- \
  uv run --frozen python -c "import redis; r = redis.Redis(host='redis', port=6379); print(r.ping())"
```

---

## Smoke Tests

Run automated smoke tests after deployment:

```bash
#!/bin/bash
# smoke-test.sh

echo "Running smoke tests..."

# 1. Health check
curl -f http://<service-url>/health || exit 1

# 2. MCP server ping
curl -f http://<service-url>/v1/ping || exit 1

# 3. Authentication test (if applicable)
curl -H "Authorization: Bearer $TEST_TOKEN" \
     http://<service-url>/v1/sessions || exit 1

# 4. Agent invocation test
curl -X POST http://<service-url>/v1/agent/invoke \
     -H "Content-Type: application/json" \
     -d '{"input":"test"}' || exit 1

echo "All smoke tests passed!"
```
