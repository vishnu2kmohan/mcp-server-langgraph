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

- ✅ **Secrets configured** (JWT_SECRET_KEY, API keys)
- ✅ **OpenFGA store and model IDs** set (run `make setup-openfga`)
- ✅ **LLM provider API key** valid with sufficient quota
- ✅ **All tests passing** (`make test`)
- ✅ **Security scan clean** (`make security-check`)
- ✅ **Health checks working** (`/health/live`, `/health/ready`)
- ✅ **Resource limits set** in manifests
- ✅ **Observability configured** (Jaeger, Prometheus, LangSmith)
- ✅ **Autoscaling configured** (HPA for Kubernetes)
- ✅ **Monitoring alerts configured**

## Environment Variables

All deployment methods require the following environment variables:

### Required
- `GOOGLE_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` - At least one LLM provider
- `JWT_SECRET_KEY` - Generate with `openssl rand -base64 32`
- `OPENFGA_STORE_ID` - From `scripts/setup/setup_openfga.py`
- `OPENFGA_MODEL_ID` - From `scripts/setup/setup_openfga.py`

### Optional
- `LLM_PROVIDER` - Default: `google`
- `MODEL_NAME` - Default: `gemini-2.5-flash-002`
- `LANGSMITH_API_KEY` - For LangSmith tracing
- `LANGSMITH_TRACING` - Enable LangSmith (default: `false`)
- `ENABLE_TRACING` - Enable OpenTelemetry (default: `true`)
- `ENABLE_METRICS` - Enable metrics (default: `true`)

**Security**: Never commit secrets to version control. Use:
- Kubernetes Secrets
- Cloud provider secret managers (GCP Secret Manager, AWS Secrets Manager)
- Infisical for centralized secret management

## Monitoring and Observability

All deployments include:

- **Health Checks**: `/health/live` (liveness), `/health/ready` (readiness)
- **OpenTelemetry**: Distributed tracing and metrics
- **Prometheus**: Metrics collection
- **Jaeger**: Trace visualization
- **Grafana**: Dashboard visualization
- **LangSmith** (optional): LLM-specific tracing

**Access**:
- Jaeger UI: Port 16686
- Prometheus: Port 9090
- Grafana: Port 3000 (default credentials: admin/admin)

## Troubleshooting

### Common Issues

**Pod CrashLoopBackOff**:
- Check logs: `kubectl logs -f deployment/langgraph-agent -n langgraph-agent`
- Verify secrets are set: `kubectl get secrets -n langgraph-agent`
- Check resource limits: `kubectl describe pod <pod-name> -n langgraph-agent`

**Health check failures**:
- Ensure OpenFGA is accessible
- Verify LLM provider API key is valid
- Check network policies

**Performance issues**:
- Increase resource limits (CPU/memory)
- Configure HPA for autoscaling
- Check OpenFGA connection pool size

### Debug Commands

```bash
# View logs
kubectl logs -f deployment/langgraph-agent -n langgraph-agent

# Describe pod
kubectl describe pod <pod-name> -n langgraph-agent

# Shell into pod
kubectl exec -it <pod-name> -n langgraph-agent -- /bin/bash

# Check secrets
kubectl get secrets -n langgraph-agent
kubectl describe secret langgraph-agent-secrets -n langgraph-agent

# View events
kubectl get events -n langgraph-agent --sort-by='.lastTimestamp'
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
- **Production Guide**: `../docs/deployment/production.md`
- **Docker Deployment**: `../docs/deployment/docker.mdx`
- **Architecture Overview**: `../README.md#architecture`

**Last Updated**: 2025-10-12
