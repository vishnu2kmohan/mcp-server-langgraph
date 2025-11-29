# Deployment Quickstart Guide

Get the MCP Server with LangGraph up and running quickly across different platforms.

## Prerequisites

Before deploying, ensure you have:

- ✅ **LLM Provider API Key** (Anthropic, Google, or OpenAI)
- ✅ **Docker** installed (for local deployment)
- ✅ **kubectl** and access to a Kubernetes cluster (for K8s deployment)
- ✅ **Helm** 3.x installed (for Helm deployment)

## Database Architecture

The MCP Server uses a **multi-database architecture** with dedicated databases for each service:

| Database | Purpose | Tables | Environment Detection |
|----------|---------|--------|----------------------|
| **gdpr** / **gdpr_test** | GDPR compliance (user data, consents, audit logs) | 5 tables | `POSTGRES_DB` suffix |
| **openfga** / **openfga_test** | Authorization (relationship tuples, policies) | 3 tables | Auto-managed by OpenFGA |
| **keycloak** / **keycloak_test** | Authentication (users, realms, clients) | 3 tables | Auto-managed by Keycloak |

**Automatic Initialization**: All databases are created automatically via `migrations/000_init_databases.sh` when PostgreSQL starts. The script detects the environment from `POSTGRES_DB`:
- **Development/Production**: `POSTGRES_DB=postgres` → creates `gdpr`, `openfga`, `keycloak`
- **Test**: `POSTGRES_DB=gdpr_test` → creates `gdpr_test`, `openfga_test`, `keycloak_test`

**Validation**: After deployment, you can validate the database architecture:

```bash
# Docker Compose
docker compose exec agent python -c "
from mcp_server_langgraph.health.database_checks import validate_database_architecture
import asyncio
result = asyncio.run(validate_database_architecture(host='postgres'))
print(f'Valid: {result.is_valid}')
print(f'Databases: {list(result.databases.keys())}')
"

# Kubernetes
kubectl exec -it deployment/langgraph-agent -n langgraph-agent -- python -c "
from mcp_server_langgraph.health.database_checks import validate_database_architecture
import asyncio
result = asyncio.run(validate_database_architecture(host='postgres'))
print(f'Valid: {result.is_valid}')
print(f'Databases: {list(result.databases.keys())}')
"
```

**See**: [ADR-0060: Database Architecture](../adr/adr-0060-database-architecture-and-naming-convention.md) for complete architecture documentation.

## Quick Start Options

### 1. Local Development with Docker Compose (Fastest)

**Best for**: Local development and testing

```bash
# 1. Clone the repository
git clone https://github.com/vishnu2kmohan/mcp-server-langgraph.git
cd mcp-server-langgraph

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env and add your API key
# Set at minimum:
#   - GOOGLE_API_KEY or ANTHROPIC_API_KEY or OPENAI_API_KEY
#   - JWT_SECRET_KEY (generate with: openssl rand -base64 32)

# 4. Start all services
docker compose up -d

# 5. Check health
curl http://localhost:8000/health

# 6. View logs
docker compose logs -f agent
```

**Access Points**:
- Agent API: http://localhost:8000
- Jaeger UI: http://localhost:16686
- Prometheus: http://localhost:9090
- Keycloak: http://localhost:8080/admin (admin/admin)

### 2. Kubernetes with kubectl (Production-Ready)

**Best for**: Production deployments with full control

```bash
# 1. Set up prerequisites
export NAMESPACE=langgraph-agent

# 2. Create namespace
kubectl create namespace $NAMESPACE

# 3. Create secrets
kubectl create secret generic langgraph-agent-secrets \
  --from-literal=anthropic-api-key="YOUR_API_KEY" \
  --from-literal=jwt-secret-key="$(openssl rand -base64 32)" \
  --from-literal=redis-password="$(openssl rand -base64 32)" \
  --from-literal=postgres-password="$(openssl rand -base64 32)" \
  --from-literal=keycloak-client-secret="$(openssl rand -base64 32)" \
  --from-literal=keycloak-admin-password="$(openssl rand -base64 32)" \
  --from-literal=openfga-store-id="" \
  --from-literal=openfga-model-id="" \
  -n $NAMESPACE

# 4. Deploy all resources
kubectl apply -f deployments/kubernetes/base/ -n $NAMESPACE

# 5. Wait for deployments
kubectl wait --for=condition=available --timeout=300s \
  deployment/langgraph-agent \
  deployment/keycloak \
  deployment/redis-session \
  -n $NAMESPACE

# 6. Set up OpenFGA (required)
# Port-forward to OpenFGA
kubectl port-forward svc/openfga 8080:8080 -n $NAMESPACE &

# Run setup script
python3 scripts/setup/setup_openfga.py

# Update secrets with OpenFGA IDs
kubectl patch secret langgraph-agent-secrets \
  --type merge \
  -p '{"stringData":{"openfga-store-id":"YOUR_STORE_ID","openfga-model-id":"YOUR_MODEL_ID"}}' \
  -n $NAMESPACE

# 7. Restart deployment to pick up new secrets
kubectl rollout restart deployment/langgraph-agent -n $NAMESPACE

# 8. Check status
kubectl get pods -n $NAMESPACE
kubectl logs -f deployment/langgraph-agent -n $NAMESPACE
```

### 3. Kubernetes with Kustomize (Environment-Specific)

**Best for**: Multiple environments with different configurations

```bash
# Development environment
kubectl apply -k deployments/kustomize/overlays/dev

# Staging environment
kubectl apply -k deployments/kustomize/overlays/staging

# Production environment
kubectl apply -k deployments/kustomize/overlays/production
```

### 4. Helm Chart (Advanced)

**Best for**: Enterprise deployments with dependency management

```bash
# 1. Add Helm repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add openfga https://openfga.github.io/helm-charts
helm repo update

# 2. Install with Helm
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --set secrets.anthropicApiKey="YOUR_API_KEY" \
  --set secrets.jwtSecretKey="$(openssl rand -base64 32)" \
  --set secrets.redisPassword="$(openssl rand -base64 32)" \
  --set secrets.postgresPassword="$(openssl rand -base64 32)" \
  --set secrets.keycloakClientSecret="$(openssl rand -base64 32)" \
  --set secrets.keycloakAdminPassword="$(openssl rand -base64 32)"

# 3. Check status
helm status langgraph-agent -n langgraph-agent

# 4. Get service URL
kubectl get svc langgraph-agent -n langgraph-agent
```

## Post-Deployment Setup

### Initialize OpenFGA Authorization Model

Required for both inmemory and Keycloak authentication:

```bash
# 1. Port-forward to OpenFGA
kubectl port-forward svc/openfga 8080:8080 -n langgraph-agent &

# 2. Run setup script
python3 scripts/setup/setup_openfga.py

# 3. Note the Store ID and Model ID from the output
# 4. Update your secrets or environment variables with these IDs
```

### Configure Qdrant for Dynamic Context Loading (Optional)

**New in v2.6.0**: Qdrant vector database for Just-in-Time context loading

If using `ENABLE_DYNAMIC_CONTEXT_LOADING=true`:

```bash
# Qdrant is included in deployments but disabled by default
# To enable dynamic context loading with semantic search:

# 1. For Docker Compose - already included and running
curl http://localhost:6333/  # Check Qdrant health

# 2. For Kubernetes - ensure Qdrant is deployed
kubectl get pods -n langgraph-agent | grep qdrant

# 3. Enable dynamic context loading in your environment
# Docker Compose: Set in .env
ENABLE_DYNAMIC_CONTEXT_LOADING=true
QDRANT_URL=qdrant
QDRANT_PORT=6333

# Kubernetes: Update configmap
kubectl patch configmap langgraph-agent-config \
  --type merge \
  -p '{"data":{"enable_dynamic_context_loading":"true"}}' \
  -n langgraph-agent

# 4. Restart to apply changes
# Docker: docker compose restart agent
# Kubernetes: kubectl rollout restart deployment/langgraph-agent -n langgraph-agent

# 5. Verify Qdrant integration
curl http://localhost:8000/health/ready  # Should show qdrant in dependencies
```

**Qdrant Features**:
- **Semantic Search**: Dynamic context loading with 60% token reduction
- **Persistent Storage**: 10Gi PVC in Kubernetes (configurable)
- **Configurable**: Adjust DYNAMIC_CONTEXT_MAX_TOKENS, DYNAMIC_CONTEXT_TOP_K
- **Optional**: Leave disabled for standard operation

**See**: [Anthropic Best Practices Enhancement Plan](../reports/ANTHROPIC_BEST_PRACTICES_ENHANCEMENT_PLAN_20251017.md)

### Configure Keycloak (Optional)

If using `AUTH_PROVIDER=keycloak`:

```bash
# 1. Access Keycloak admin console
# For Docker Compose: http://localhost:8080/admin
# For Kubernetes: kubectl port-forward svc/keycloak 8080:8080 -n langgraph-agent

# 2. Login with admin credentials
# Docker: admin/admin (from .env or docker-compose.yml)
# Kubernetes: admin/[keycloak-admin-password from secrets]

# 3. Run Keycloak setup script
python3 scripts/setup/setup_keycloak.py

# This will:
# - Create the langgraph-agent realm
# - Create the langgraph-client client
# - Set up required scopes and roles
# - Output the client secret

# 4. Update your configuration with the client secret
```

## Verification

### Health Checks

```bash
# Overall health (includes dependencies)
curl http://localhost:8000/health

# Readiness (includes OpenFGA, Keycloak, Redis checks)
curl http://localhost:8000/health/ready

# Startup probe
curl http://localhost:8000/health/startup
```

### Test Authentication

```bash
# With inmemory provider (development)
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# With Keycloak provider (production)
# Use Keycloak's OAuth2 token endpoint
```

### View Metrics

```bash
# Prometheus metrics
curl http://localhost:8000/metrics/prometheus

# OpenTelemetry traces (in Jaeger UI)
# http://localhost:16686
```

## Environment-Specific Configurations

### Development
- **Authentication**: `inmemory` provider
- **Sessions**: `memory` backend
- **Replicas**: 1
- **Logging**: DEBUG level
- **Metrics**: Disabled (reduce noise)
- **TLS**: Disabled

### Staging
- **Authentication**: `keycloak` provider
- **Sessions**: `redis` backend (12-hour TTL)
- **Replicas**: 2
- **Logging**: INFO level
- **Metrics**: Enabled
- **TLS**: Optional

### Production
- **Authentication**: `keycloak` provider (required)
- **Sessions**: `redis` backend (24-hour TTL)
- **Replicas**: 3+ with autoscaling
- **Logging**: INFO level
- **Metrics**: Enabled with LangSmith
- **TLS**: Required (SSL verification enabled)

## Troubleshooting

### Common Issues

**Pods not starting**:
```bash
# Check pod status
kubectl describe pod <pod-name> -n langgraph-agent

# Check logs
kubectl logs <pod-name> -n langgraph-agent

# Common causes:
# - Missing secrets (check kubectl get secrets)
# - Init containers waiting for dependencies
# - Resource limits too low
```

**Health checks failing**:
```bash
# Check OpenFGA connectivity
kubectl exec -it <pod-name> -n langgraph-agent -- nc -zv openfga 8080

# Check Keycloak connectivity
kubectl exec -it <pod-name> -n langgraph-agent -- nc -zv keycloak 8080

# Check Redis connectivity
kubectl exec -it <pod-name> -n langgraph-agent -- nc -zv redis-session 6379
```

**Authentication errors**:
```bash
# Verify OpenFGA setup
python3 scripts/setup/setup_openfga.py --verify

# Verify Keycloak configuration
python3 scripts/setup/setup_keycloak.py --verify

# Check secret values
kubectl get secret langgraph-agent-secrets -n langgraph-agent -o yaml
```

## Scaling

### Horizontal Pod Autoscaling

```bash
# Enable HPA (automatically scales based on CPU/memory)
kubectl apply -f deployments/kubernetes/base/hpa.yaml -n langgraph-agent

# Check HPA status
kubectl get hpa -n langgraph-agent

# Manual scaling
kubectl scale deployment/langgraph-agent --replicas=5 -n langgraph-agent
```

### Resource Tuning

Edit deployment resource limits based on your workload:

```yaml
resources:
  requests:
    cpu: 500m      # Adjust based on usage
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi
```

## Next Steps

- 📚 Read the [complete deployment guide](README.md)
- 🔐 Set up [authentication with Keycloak](../docs/getting-started/authentication.mdx)
- 📊 Configure [observability and monitoring](../docs/guides/observability.mdx)
- 🔒 Review [security best practices](../docs/security/overview.mdx)
- 🚀 Explore [production deployment guide](../docs/deployment/production-checklist.mdx)

## Getting Help

- 📖 **Documentation**: `docs/` directory
- 🐛 **Issues**: [GitHub Issues](https://github.com/vishnu2kmohan/mcp-server-langgraph/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/vishnu2kmohan/mcp-server-langgraph/discussions)
