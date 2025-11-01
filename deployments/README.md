# Deployment Configurations

This directory contains all deployment configurations for the MCP Server with LangGraph across different platforms and environments.

## Directory Structure

```
deployments/
├── helm/                    # Helm chart for Kubernetes
│   └── langgraph-agent/    # Main chart
├── kustomize/              # Kustomize overlays for Kubernetes
│   ├── base/               # Base configuration
│   └── overlays/           # Environment-specific overlays
│       ├── dev/            # Development environment
│       ├── staging/        # Staging environment
│       └── production/     # Production environment
├── kubernetes/             # Raw Kubernetes manifests
│   ├── base/               # Base manifests
│   └── kong/               # Kong API Gateway configs
├── cloudrun/               # Google Cloud Run deployment
├── kong/                   # Kong API Gateway standalone configs
└── langgraph-platform/     # LangGraph Platform (LangGraph Cloud)
```

## Deployment Options

### 1. Kubernetes with Helm (Recommended)

**Best for**: Production Kubernetes deployments with customization needs

```bash
# Install with default values
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace

# Install with custom values
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --values values-production.yaml

# Upgrade deployment
helm upgrade langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent
```

**Documentation**: See `helm/langgraph-agent/README.md`

### 2. Kubernetes with Kustomize

**Best for**: GitOps workflows, multiple environments

```bash
# Production deployment
kubectl apply -k deployments/kustomize/overlays/production

# Staging deployment
kubectl apply -k deployments/kustomize/overlays/staging

# Development deployment
kubectl apply -k deployments/kustomize/overlays/dev

# Check deployment
kubectl get all -n langgraph-agent
```

**Documentation**: See `kustomize/README.md`

### 3. Google Cloud Run

**Best for**: Serverless deployment on Google Cloud

```bash
# Deploy to Cloud Run
gcloud run deploy langgraph-agent \
  --source deployments/cloudrun \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated

# With environment variables from .env
gcloud run deploy langgraph-agent \
  --source deployments/cloudrun \
  --region us-central1 \
  --platform managed \
  --env-vars-file .env.cloudrun
```

**Documentation**: See `cloudrun/README.md`

### 4. LangGraph Platform (Cloud)

**Best for**: Quick deployment without infrastructure management

```bash
# Login to LangGraph Cloud
uvx langgraph-cli login

# Deploy agent
cd deployments/langgraph-platform
uvx langgraph-cli deploy

# Get deployment URL
uvx langgraph-cli deployment get <deployment-name>

# View logs
uvx langgraph-cli logs <deployment-name>
```

**Documentation**: See `langgraph-platform/README.md`

### 5. Kong API Gateway

**Best for**: Adding API management, rate limiting, authentication

```bash
# Install Kong with Helm
helm repo add kong https://charts.konghq.com
helm repo update
helm install kong kong/kong \
  --namespace kong \
  --create-namespace \
  --set ingressController.enabled=true

# Apply Kong configurations
kubectl apply -k deployments/kong/
```

**Documentation**: See `kong/README.md`

## Pre-Deployment Checklist

Before deploying to any environment:

### Secrets & Configuration
- ✅ **LLM provider API keys** (Anthropic, Google, or OpenAI)
- ✅ **JWT secret key** (generate: `openssl rand -base64 32`)
- ✅ **OpenFGA store and model IDs** (run `make setup-openfga`)
- ✅ **Keycloak configured** (if using AUTH_PROVIDER=keycloak)
  - Client ID and secret
  - Realm created
  - Admin credentials set
- ✅ **Redis password** (if using SESSION_BACKEND=redis)
- ✅ **PostgreSQL credentials** (for OpenFGA and Keycloak databases)

### Testing & Quality
- ✅ **All tests passing** (`make test` - 260+ unit tests)
- ✅ **Security scan clean** (`make security-check`)
- ✅ **Health checks working** (`/health`, `/health/ready`, `/health/startup`)

### Infrastructure
- ✅ **Resource limits set** in manifests (CPU/memory)
- ✅ **Persistent volumes configured** (for PostgreSQL, Redis)
- ✅ **Observability configured** (OpenTelemetry, Prometheus, LangSmith)
- ✅ **Autoscaling configured** (HPA for Kubernetes)
- ✅ **Network policies** in place (if using network isolation)
- ✅ **Monitoring alerts configured**

## Environment Variables

All deployment methods require the following environment variables:

### Required (Core)
- **LLM Provider**: `GOOGLE_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` (at least one)
- **Authentication**: `JWT_SECRET_KEY` (generate: `openssl rand -base64 32`)
- **Authorization**: `OPENFGA_STORE_ID`, `OPENFGA_MODEL_ID` (from `make setup-openfga`)

### Authentication & Authorization (New)
- `AUTH_PROVIDER` - Authentication provider: `inmemory` (default), `keycloak`
- `AUTH_MODE` - Authentication mode: `token` (JWT, default), `session`

**When using Keycloak (AUTH_PROVIDER=keycloak)**:
- `KEYCLOAK_SERVER_URL` - Keycloak server URL (e.g., `http://keycloak:8080`)
- `KEYCLOAK_REALM` - Realm name (default: `langgraph-agent`)
- `KEYCLOAK_CLIENT_ID` - Client ID (default: `langgraph-client`)
- `KEYCLOAK_CLIENT_SECRET` - Client secret (from Keycloak admin console)
- `KEYCLOAK_HOSTNAME` - Public hostname for token validation
- `KEYCLOAK_VERIFY_SSL` - Verify SSL certificates (default: `true`)
- `KEYCLOAK_TIMEOUT` - Connection timeout in seconds (default: `30`)

### Session Management (New)
**When using sessions (AUTH_MODE=session)**:
- `SESSION_BACKEND` - Backend: `memory` (default), `redis`
- `SESSION_TTL_SECONDS` - Session TTL in seconds (default: `86400` = 24 hours)
- `SESSION_SLIDING_WINDOW` - Refresh session on each request (default: `true`)
- `SESSION_MAX_CONCURRENT` - Max concurrent sessions per user (default: `5`)

**When using Redis (SESSION_BACKEND=redis)**:
- `REDIS_URL` - Redis connection URL (e.g., `redis://redis-session:6379/0`)
- `REDIS_PASSWORD` - Redis password (if authentication enabled)
- `REDIS_SSL` - Use SSL for Redis connection (default: `false`)

### LLM Configuration
- `LLM_PROVIDER` - Provider: `google`, `anthropic`, `openai`, `azure`, `bedrock`, `ollama` (default: `google`)
- `MODEL_NAME` - Model name (default: `gemini-2.5-flash`)
- `MODEL_TEMPERATURE` - Temperature (default: `0.7`)
- `MODEL_MAX_TOKENS` - Max tokens (default: `8192`)
- `MODEL_TIMEOUT` - Timeout in seconds (default: `60`)
- `ENABLE_FALLBACK` - Enable model fallback (default: `true`)

### Observability
- `ENABLE_TRACING` - Enable OpenTelemetry tracing (default: `true`)
- `ENABLE_METRICS` - Enable metrics (default: `true`)
- `ENABLE_CONSOLE_EXPORT` - Export to console (default: `false`)
- `OBSERVABILITY_BACKEND` - Backend: `opentelemetry`, `langsmith`, `both` (default: `opentelemetry`)
- `OTLP_ENDPOINT` - OpenTelemetry collector endpoint (default: `http://localhost:4317`)
- `LANGSMITH_API_KEY` - LangSmith API key (optional)
- `LANGSMITH_TRACING` - Enable LangSmith tracing (default: `false`)

### Agent Configuration
- `MAX_ITERATIONS` - Max agent iterations (default: `10`)
- `ENABLE_CHECKPOINTING` - Enable checkpointing (default: `true`)

**Security**: Never commit secrets to version control. Use:
- **Kubernetes**: Secrets, External Secrets Operator
- **Cloud Providers**: GCP Secret Manager, AWS Secrets Manager, Azure Key Vault
- **Third-party**: Infisical, HashiCorp Vault

## Monitoring and Observability

All deployments include:

- **Health Checks**: `/health` (liveness), `/health/ready` (readiness), `/health/startup` (startup)
- **OpenTelemetry**: Distributed tracing and metrics
- **Prometheus**: Metrics collection and scraping
- **Jaeger**: Trace visualization
- **Grafana**: Dashboard visualization
- **LangSmith** (optional): LLM-specific tracing and debugging

**Health Check Endpoints**:
- `/health` - Overall health status (includes dependencies)
- `/health/ready` - Readiness probe (includes OpenFGA, Keycloak, Redis checks)
- `/health/startup` - Startup probe (basic availability check)
- `/metrics/prometheus` - Prometheus metrics endpoint

**Access**:
- Jaeger UI: Port 16686
- Prometheus: Port 9090
- Grafana: Port 3000 (default credentials: admin/admin)
- OpenTelemetry Collector: Port 4317 (gRPC), 4318 (HTTP)

## Troubleshooting

### Common Issues

**Pod CrashLoopBackOff**:
- Check logs: `kubectl logs -f deployment/langgraph-agent -n langgraph-agent`
- Verify all secrets are set: `kubectl get secrets -n langgraph-agent`
- Check resource limits: `kubectl describe pod <pod-name> -n langgraph-agent`
- Verify init containers completed: Keycloak, Redis, OpenFGA must be ready

**Health check failures**:
- Ensure OpenFGA is accessible and initialized (store/model IDs set)
- Verify LLM provider API key is valid and has quota
- Check Keycloak is running (if AUTH_PROVIDER=keycloak)
- Verify Redis is accessible (if SESSION_BACKEND=redis)
- Check network policies allow pod-to-pod communication
- Review PostgreSQL database connectivity

**Authentication/Authorization issues**:
- **Keycloak**: Verify realm, client ID/secret match configuration
- **OpenFGA**: Run `make setup-openfga` to initialize authorization model
- **JWT tokens**: Ensure JWT_SECRET_KEY is consistent across all pods
- **Sessions**: Check Redis connectivity and password

**Performance issues**:
- Increase resource limits (CPU/memory) in deployment manifests
- Configure HPA for autoscaling (see Scaling section)
- Check OpenFGA connection pool size
- Monitor Redis memory usage (sessions can accumulate)
- Review LLM provider rate limits and quotas

### Debug Commands

```bash
# View application logs
kubectl logs -f deployment/langgraph-agent -n langgraph-agent

# View Keycloak logs
kubectl logs -f deployment/keycloak -n langgraph-agent

# View Redis logs
kubectl logs -f deployment/redis-session -n langgraph-agent

# View OpenFGA logs
kubectl logs -f deployment/openfga -n langgraph-agent

# Describe pod (shows events, resource usage, init container status)
kubectl describe pod <pod-name> -n langgraph-agent

# Shell into main application pod
kubectl exec -it <pod-name> -n langgraph-agent -- /bin/sh

# Check all secrets
kubectl get secrets -n langgraph-agent
kubectl describe secret langgraph-agent-secrets -n langgraph-agent

# View recent events
kubectl get events -n langgraph-agent --sort-by='.lastTimestamp'

# Check all deployments status
kubectl get deployments -n langgraph-agent

# Check service endpoints
kubectl get endpoints -n langgraph-agent

# Test service connectivity from within cluster
kubectl run -it --rm debug --image=busybox --restart=Never -n langgraph-agent -- sh
# Inside debug pod:
nc -zv keycloak 8080
nc -zv redis-session 6379
nc -zv openfga 8080
```

## Scaling

### Horizontal Pod Autoscaling (HPA)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: langgraph-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: langgraph-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Vertical Pod Autoscaling (VPA)

For automatic resource limit adjustments, install VPA:
```bash
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/download/vertical-pod-autoscaler-0.13.0/vertical-pod-autoscaler.yaml
```

## Security Best Practices

1. **Network Policies**: Restrict pod-to-pod communication
2. **RBAC**: Use least-privilege service accounts
3. **Pod Security Standards**: Enforce restricted or baseline policies
4. **Image Scanning**: Scan Docker images for vulnerabilities
5. **Secret Rotation**: Regularly rotate JWT secrets and API keys
6. **TLS/HTTPS**: Enable TLS for all external endpoints
7. **API Gateway**: Use Kong for authentication, rate limiting

## Additional Resources

- **Project Documentation**: `../docs/README.md`
- **Development Guide**: `../docs/development/development.md`
- **Production Guide**: `../docs/deployment/production-checklist.mdx`
- **Docker Deployment**: `../docs/deployment/docker.mdx`
- **Architecture Overview**: `../README.md#architecture`

**Last Updated**: 2025-10-12
