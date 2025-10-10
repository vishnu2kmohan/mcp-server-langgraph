# Google Cloud Run Deployment Guide

Complete guide for deploying the MCP Server with LangGraph to Google Cloud Run.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Scaling](#scaling)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Cost Optimization](#cost-optimization)

---

## Overview

Google Cloud Run is a fully managed serverless platform that automatically scales your containers. This guide covers deploying the MCP Server with LangGraph as a Cloud Run service with:

- **Serverless autoscaling**: 0 to 100+ instances
- **Pay-per-use pricing**: Only pay when requests are being processed
- **Automatic HTTPS**: Free SSL certificates
- **Secret management**: Integrated with Google Secret Manager
- **Observability**: Built-in logging, monitoring, and tracing
- **Global deployment**: Deploy to multiple regions
- **High availability**: 99.95% SLA

### Architecture

```
Internet → Cloud Load Balancer → Cloud Run Service
                                      ↓
                                  Container
                                      ↓
                    ┌─────────────────┼─────────────────┐
                    ↓                 ↓                 ↓
              Secret Manager    Cloud Logging    Cloud Monitoring
```

### Why Cloud Run?

✅ **Pros**:
- No infrastructure management
- Automatic scaling (including to zero)
- Built-in traffic splitting for A/B testing
- Native GCP integration (IAM, Secret Manager, VPC)
- Fast cold starts (~1-2 seconds)
- Cost-effective for variable workloads

⚠️ **Considerations**:
- Request timeout limit (60 minutes max)
- Container size limit (32 GiB memory max)
- Stateless architecture required
- Cold start latency for infrequent requests

---

## Prerequisites

### Required Tools

1. **Google Cloud SDK** (gcloud CLI)
   ```bash
   # Install gcloud
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL

   # Initialize
   gcloud init
   ```

2. **Docker** (for local testing)
   ```bash
   # Verify Docker installation
   docker --version
   ```

3. **Git** (to clone repository)
   ```bash
   git --version
   ```

### Google Cloud Setup

1. **Create or select a GCP project**:
   ```bash
   # Create new project
   gcloud projects create PROJECT_ID --name="MCP Server with LangGraph"

   # Or select existing
   gcloud config set project PROJECT_ID
   ```

2. **Enable billing**:
   - Visit: https://console.cloud.google.com/billing
   - Link a billing account to your project

3. **Set environment variables**:
   ```bash
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   export REGION="us-central1"  # Or your preferred region
   ```

### API Keys

You'll need API keys for:
- **Anthropic** (for Claude models): https://console.anthropic.com/
- **OpenAI** (optional, for GPT models): https://platform.openai.com/api-keys
- **Google AI** (optional, for Gemini): https://aistudio.google.com/apikey

---

## Quick Start

### One-Command Deployment

```bash
# Clone repository
git clone https://github.com/vishnu2kmohan/mcp_server_langgraph.git
cd mcp_server_langgraph

# Run setup and deploy
cd cloudrun
./deploy.sh --setup
```

This script will:
1. Enable required Google Cloud APIs
2. Create service account with appropriate permissions
3. Build Docker image using Cloud Build
4. Deploy to Cloud Run
5. Output the service URL

### Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe mcp-server-langgraph \
  --region=$REGION \
  --format='value(status.url)')

# Test health endpoints
curl $SERVICE_URL/health/live
curl $SERVICE_URL/health/ready

# Expected response: {"status": "healthy"}
```

---

## Detailed Setup

### Step 1: Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  --project=$GOOGLE_CLOUD_PROJECT
```

### Step 2: Create Service Account

Create a dedicated service account for the Cloud Run service:

```bash
# Create service account
gcloud iam service-accounts create mcp-server-langgraph-sa \
  --display-name="MCP Server with LangGraph Service Account" \
  --project=$GOOGLE_CLOUD_PROJECT

# Grant necessary roles
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
  --member="serviceAccount:mcp-server-langgraph-sa@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Optional: If using Cloud SQL
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
  --member="serviceAccount:mcp-server-langgraph-sa@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

### Step 3: Configure Secrets

Use Google Secret Manager to store sensitive configuration:

#### Option A: Interactive Setup

```bash
cd cloudrun
./setup-secrets.sh
```

This script will prompt you for:
- JWT secret key
- Anthropic API key
- OpenAI API key
- OpenFGA credentials (optional)
- Infisical credentials (optional)

#### Option B: Manual Setup

```bash
# Create JWT secret
echo -n "your-super-secret-jwt-key-change-in-production" | \
  gcloud secrets create jwt-secret-key \
    --data-file=- \
    --replication-policy="automatic" \
    --project=$GOOGLE_CLOUD_PROJECT

# Create Anthropic API key secret
echo -n "sk-ant-..." | \
  gcloud secrets create anthropic-api-key \
    --data-file=- \
    --replication-policy="automatic" \
    --project=$GOOGLE_CLOUD_PROJECT

# Create OpenAI API key secret
echo -n "sk-..." | \
  gcloud secrets create openai-api-key \
    --data-file=- \
    --replication-policy="automatic" \
    --project=$GOOGLE_CLOUD_PROJECT

# Grant service account access to secrets
for secret in jwt-secret-key anthropic-api-key openai-api-key; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:mcp-server-langgraph-sa@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$GOOGLE_CLOUD_PROJECT
done
```

#### Verify Secrets

```bash
# List all secrets
gcloud secrets list --project=$GOOGLE_CLOUD_PROJECT

# View secret metadata (not the value)
gcloud secrets describe jwt-secret-key --project=$GOOGLE_CLOUD_PROJECT
```

### Step 4: Build Container Image

```bash
# Build using Cloud Build (recommended)
gcloud builds submit \
  --tag gcr.io/$GOOGLE_CLOUD_PROJECT/mcp-server-langgraph:latest \
  --project=$GOOGLE_CLOUD_PROJECT \
  .

# Or build locally and push
docker build -t gcr.io/$GOOGLE_CLOUD_PROJECT/mcp-server-langgraph:latest .
docker push gcr.io/$GOOGLE_CLOUD_PROJECT/mcp-server-langgraph:latest
```

### Step 5: Deploy to Cloud Run

#### Option A: Using gcloud CLI

```bash
gcloud run deploy mcp-server-langgraph \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/mcp-server-langgraph:latest \
  --platform managed \
  --region $REGION \
  --service-account mcp-server-langgraph-sa@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 100 \
  --cpu 2 \
  --memory 2Gi \
  --timeout 300 \
  --concurrency 80 \
  --set-env-vars="PORT=8000,ENVIRONMENT=production,LOG_LEVEL=INFO" \
  --set-secrets="JWT_SECRET_KEY=jwt-secret-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,OPENAI_API_KEY=openai-api-key:latest" \
  --project=$GOOGLE_CLOUD_PROJECT
```

#### Option B: Using YAML Configuration

```bash
# Update service.yaml with your project ID
sed -i "s/PROJECT_ID/$GOOGLE_CLOUD_PROJECT/g" cloudrun/service.yaml

# Deploy using YAML
gcloud run services replace cloudrun/service.yaml \
  --region $REGION \
  --project=$GOOGLE_CLOUD_PROJECT
```

#### Option C: Using Deployment Script

```bash
cd cloudrun
./deploy.sh
```

---

## Configuration

### Environment Variables

The service uses the following environment variables:

| Variable | Description | Source | Required |
|----------|-------------|--------|----------|
| `PORT` | HTTP port | Env | ✅ (set by Cloud Run) |
| `ENVIRONMENT` | Environment name | Env | ✅ |
| `LOG_LEVEL` | Logging level | Env | ✅ |
| `JWT_SECRET_KEY` | JWT signing secret | Secret Manager | ✅ |
| `ANTHROPIC_API_KEY` | Anthropic API key | Secret Manager | ✅ |
| `OPENAI_API_KEY` | OpenAI API key | Secret Manager | ⚠️ (if using OpenAI) |
| `MODEL_NAME` | Default LLM model | Env | ✅ |
| `OPENFGA_API_URL` | OpenFGA server URL | Env | ⚠️ (if using authz) |
| `OPENFGA_STORE_ID` | OpenFGA store ID | Secret Manager | ⚠️ (if using authz) |
| `OPENFGA_MODEL_ID` | OpenFGA model ID | Secret Manager | ⚠️ (if using authz) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry endpoint | Env | ⚠️ (if using OTel) |

### Update Environment Variables

```bash
# Update environment variables
gcloud run services update mcp-server-langgraph \
  --region $REGION \
  --update-env-vars "LOG_LEVEL=DEBUG,MODEL_NAME=claude-3-5-sonnet-20241022" \
  --project=$GOOGLE_CLOUD_PROJECT
```

### Update Secrets

```bash
# Create new secret version
echo -n "new-secret-value" | \
  gcloud secrets versions add jwt-secret-key \
    --data-file=- \
    --project=$GOOGLE_CLOUD_PROJECT

# Cloud Run automatically picks up new version on next deployment
# Or force update
gcloud run services update mcp-server-langgraph \
  --region $REGION \
  --project=$GOOGLE_CLOUD_PROJECT
```

### Resource Limits

Configure CPU and memory based on your workload:

```bash
gcloud run services update mcp-server-langgraph \
  --region $REGION \
  --cpu 4 \
  --memory 4Gi \
  --project=$GOOGLE_CLOUD_PROJECT
```

**Recommendations**:
- **Light workload** (< 100 req/min): 1 CPU, 1 GiB
- **Medium workload** (100-500 req/min): 2 CPU, 2 GiB (default)
- **Heavy workload** (> 500 req/min): 4 CPU, 4 GiB

---

## Deployment

### Initial Deployment

```bash
cd cloudrun
./deploy.sh --setup
```

### Update Deployment

```bash
# Update code, rebuild, and redeploy
./deploy.sh
```

### Rollback to Previous Revision

```bash
# List revisions
gcloud run revisions list \
  --service mcp-server-langgraph \
  --region $REGION \
  --project=$GOOGLE_CLOUD_PROJECT

# Rollback to specific revision
gcloud run services update-traffic mcp-server-langgraph \
  --region $REGION \
  --to-revisions REVISION_NAME=100 \
  --project=$GOOGLE_CLOUD_PROJECT
```

### Traffic Splitting (A/B Testing)

```bash
# Deploy new version without full traffic
gcloud run deploy mcp-server-langgraph \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/mcp-server-langgraph:v2 \
  --region $REGION \
  --no-traffic \
  --tag v2 \
  --project=$GOOGLE_CLOUD_PROJECT

# Gradually shift traffic: 90% old, 10% new
gcloud run services update-traffic mcp-server-langgraph \
  --region $REGION \
  --to-revisions CURRENT=90,REVISION-v2=10 \
  --project=$GOOGLE_CLOUD_PROJECT

# Full cutover
gcloud run services update-traffic mcp-server-langgraph \
  --region $REGION \
  --to-latest \
  --project=$GOOGLE_CLOUD_PROJECT
```

### Blue-Green Deployment

```bash
# Deploy green version with tag
gcloud run deploy mcp-server-langgraph \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/mcp-server-langgraph:green \
  --region $REGION \
  --no-traffic \
  --tag green \
  --project=$GOOGLE_CLOUD_PROJECT

# Test green version at: https://green---mcp-server-langgraph-....run.app

# Switch all traffic to green
gcloud run services update-traffic mcp-server-langgraph \
  --region $REGION \
  --to-tags green=100 \
  --project=$GOOGLE_CLOUD_PROJECT
```

---

## Monitoring

### View Logs

```bash
# Stream logs
gcloud run services logs tail mcp-server-langgraph \
  --region $REGION \
  --project=$GOOGLE_CLOUD_PROJECT

# View recent logs
gcloud run services logs read mcp-server-langgraph \
  --region $REGION \
  --limit 50 \
  --project=$GOOGLE_CLOUD_PROJECT

# Filter logs by severity
gcloud run services logs read mcp-server-langgraph \
  --region $REGION \
  --log-filter='severity>=ERROR' \
  --project=$GOOGLE_CLOUD_PROJECT
```

### Metrics and Monitoring

View metrics in Cloud Console:
- **Cloud Run Metrics**: https://console.cloud.google.com/run
  - Request count
  - Request latency
  - Container CPU/memory utilization
  - Instance count
  - Error rate

**Key Metrics to Monitor**:
- `Request count`: Total requests per second
- `Request latency (p95, p99)`: Response time percentiles
- `Container CPU utilization`: CPU usage percentage
- `Container memory utilization`: Memory usage
- `Billable instance time`: Cost tracking
- `Error rate`: Failed requests

### Set Up Alerts

```bash
# Create alert policy for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Error Rate - MCP Agent" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s \
  --project=$GOOGLE_CLOUD_PROJECT
```

### Cloud Trace Integration

The application includes OpenTelemetry instrumentation that automatically exports traces to Cloud Trace:

1. View traces: https://console.cloud.google.com/traces
2. Analyze latency breakdown by operation
3. Debug slow requests end-to-end

---

## Scaling

### Autoscaling Configuration

```bash
# Configure autoscaling
gcloud run services update mcp-server-langgraph \
  --region $REGION \
  --min-instances 0 \
  --max-instances 100 \
  --concurrency 80 \
  --cpu-throttling \
  --project=$GOOGLE_CLOUD_PROJECT
```

### Scaling Parameters

- **`min-instances`**: Minimum instances (0 for scale-to-zero, 1+ for warm pool)
- **`max-instances`**: Maximum concurrent instances
- **`concurrency`**: Requests per instance (default: 80)
- **`cpu-throttling`**: Throttle CPU when idle (saves cost)

### Scaling Strategies

#### Scale to Zero (Cost-Optimized)
```bash
--min-instances 0 \
--max-instances 100 \
--cpu-throttling
```
- **Pros**: Lowest cost, pay only for actual usage
- **Cons**: Cold start latency (1-2 seconds)
- **Use case**: Development, low-traffic applications

#### Warm Pool (Low Latency)
```bash
--min-instances 3 \
--max-instances 100 \
--no-cpu-throttling
```
- **Pros**: No cold starts, consistent latency
- **Cons**: Higher baseline cost
- **Use case**: Production, latency-sensitive applications

#### Hybrid (Balanced)
```bash
--min-instances 1 \
--max-instances 50 \
--cpu-throttling
```
- **Pros**: Balance cost and latency
- **Cons**: Some cold starts during traffic spikes
- **Use case**: Most production workloads

### Performance Tuning

**Optimize Cold Starts**:
1. Use startup CPU boost (enabled by default in service.yaml)
2. Minimize Docker image size (multi-stage build)
3. Lazy-load heavy dependencies
4. Use min-instances > 0 for critical paths

**Optimize Request Handling**:
1. Adjust concurrency based on workload (CPU-bound: 10-20, I/O-bound: 80-1000)
2. Enable HTTP/2 for connection reuse
3. Use connection pooling for databases
4. Implement request queuing and timeouts

---

## Security

### Authentication

#### Option 1: Require Authentication (Recommended for Production)

```bash
# Require authentication
gcloud run services update mcp-server-langgraph \
  --region $REGION \
  --no-allow-unauthenticated \
  --project=$GOOGLE_CLOUD_PROJECT

# Grant access to specific users
gcloud run services add-iam-policy-binding mcp-server-langgraph \
  --region $REGION \
  --member="user:user@example.com" \
  --role="roles/run.invoker" \
  --project=$GOOGLE_CLOUD_PROJECT

# Grant access to service account
gcloud run services add-iam-policy-binding mcp-server-langgraph \
  --region $REGION \
  --member="serviceAccount:caller@project.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --project=$GOOGLE_CLOUD_PROJECT
```

#### Option 2: Public Access (Use Application-Level Auth)

```bash
# Allow unauthenticated access
gcloud run services update mcp-server-langgraph \
  --region $REGION \
  --allow-unauthenticated \
  --project=$GOOGLE_CLOUD_PROJECT
```

**Note**: With public access, implement JWT-based authentication in the application (already included).

### Network Security

#### Ingress Control

```bash
# Restrict ingress to internal traffic only
gcloud run services update mcp-server-langgraph \
  --region $REGION \
  --ingress internal \
  --project=$GOOGLE_CLOUD_PROJECT

# Or allow only from Cloud Load Balancer
gcloud run services update mcp-server-langgraph \
  --region $REGION \
  --ingress internal-and-cloud-load-balancing \
  --project=$GOOGLE_CLOUD_PROJECT
```

#### VPC Connector (Private Resources)

If you need to access resources in a VPC (e.g., Cloud SQL, Redis):

```bash
# Create VPC connector
gcloud compute networks vpc-access connectors create mcp-connector \
  --region $REGION \
  --network default \
  --range 10.8.0.0/28 \
  --project=$GOOGLE_CLOUD_PROJECT

# Update service to use VPC connector
gcloud run services update mcp-server-langgraph \
  --region $REGION \
  --vpc-connector mcp-connector \
  --vpc-egress private-ranges-only \
  --project=$GOOGLE_CLOUD_PROJECT
```

Uncomment VPC settings in `cloudrun/service.yaml`:
```yaml
run.googleapis.com/vpc-access-connector: projects/PROJECT_ID/locations/REGION/connectors/mcp-connector
run.googleapis.com/vpc-egress: private-ranges-only
```

### Secret Rotation

```bash
# Rotate JWT secret
NEW_SECRET=$(openssl rand -base64 32)
echo -n "$NEW_SECRET" | gcloud secrets versions add jwt-secret-key \
  --data-file=- \
  --project=$GOOGLE_CLOUD_PROJECT

# Force service to pick up new secret
gcloud run services update mcp-server-langgraph \
  --region $REGION \
  --project=$GOOGLE_CLOUD_PROJECT
```

### Audit Logging

Enable Cloud Audit Logs:
```bash
# View audit logs
gcloud logging read "resource.type=cloud_run_revision" \
  --project=$GOOGLE_CLOUD_PROJECT \
  --limit 20
```

---

## Troubleshooting

### Common Issues

#### 1. Service Not Responding (502/503 Errors)

**Symptoms**: Service returns 502 Bad Gateway or 503 Service Unavailable

**Causes & Solutions**:
- **Container startup timeout**: Increase timeout or optimize startup
  ```bash
  gcloud run services update mcp-server-langgraph \
    --region $REGION \
    --timeout 600 \
    --project=$GOOGLE_CLOUD_PROJECT
  ```
- **Health check failures**: Check `/health/live` and `/health/ready` endpoints
- **Insufficient memory**: Increase memory allocation
  ```bash
  gcloud run services update mcp-server-langgraph \
    --region $REGION \
    --memory 4Gi \
    --project=$GOOGLE_CLOUD_PROJECT
  ```

#### 2. Secret Access Denied

**Symptoms**: Container logs show "Permission denied" for secrets

**Solution**: Grant service account access
```bash
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:mcp-server-langgraph-sa@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=$GOOGLE_CLOUD_PROJECT
```

#### 3. Cold Start Latency

**Symptoms**: First request after idle period is slow

**Solutions**:
- Use `--min-instances 1` or higher
- Enable startup CPU boost (default in service.yaml)
- Optimize Docker image size
- Use Cloud Run with CPU always allocated (more expensive)

#### 4. Out of Memory (OOM)

**Symptoms**: Container crashes with exit code 137

**Solutions**:
- Increase memory limit
  ```bash
  gcloud run services update mcp-server-langgraph \
    --region $REGION \
    --memory 4Gi \
    --project=$GOOGLE_CLOUD_PROJECT
  ```
- Profile memory usage and optimize code
- Reduce concurrency to limit memory per instance

#### 5. Request Timeout

**Symptoms**: Requests fail with 504 Gateway Timeout

**Solutions**:
- Increase timeout (max 60 minutes)
  ```bash
  gcloud run services update mcp-server-langgraph \
    --region $REGION \
    --timeout 3600 \
    --project=$GOOGLE_CLOUD_PROJECT
  ```
- Optimize slow operations
- Use async processing for long tasks

### Debugging Commands

```bash
# View service configuration
gcloud run services describe mcp-server-langgraph \
  --region $REGION \
  --project=$GOOGLE_CLOUD_PROJECT

# Check recent deployments
gcloud run revisions list \
  --service mcp-server-langgraph \
  --region $REGION \
  --project=$GOOGLE_CLOUD_PROJECT

# View environment variables
gcloud run services describe mcp-server-langgraph \
  --region $REGION \
  --format="value(spec.template.spec.containers[0].env)" \
  --project=$GOOGLE_CLOUD_PROJECT

# Test locally with secret
SECRET_VALUE=$(gcloud secrets versions access latest \
  --secret="jwt-secret-key" \
  --project=$GOOGLE_CLOUD_PROJECT)

docker run -p 8000:8000 \
  -e PORT=8000 \
  -e JWT_SECRET_KEY="$SECRET_VALUE" \
  gcr.io/$GOOGLE_CLOUD_PROJECT/mcp-server-langgraph:latest
```

---

## Cost Optimization

### Understanding Cloud Run Pricing

Cloud Run charges for:
1. **CPU allocation**: Per 100ms, only while processing requests
2. **Memory allocation**: Per 100ms, only while processing requests
3. **Request count**: $0.40 per million requests
4. **Networking**: Egress bandwidth

**Free Tier** (per month):
- 2 million requests
- 360,000 GB-seconds of memory
- 180,000 vCPU-seconds

### Cost Optimization Strategies

#### 1. Scale to Zero
```bash
--min-instances 0
```
- Saves ~$50/month per idle instance
- Accept 1-2 second cold start latency

#### 2. CPU Throttling
```bash
--cpu-throttling
```
- CPU only allocated during request processing
- Saves up to 50% on CPU costs

#### 3. Right-Size Resources
```bash
# Start small, increase if needed
--cpu 1 --memory 1Gi
```
- Monitor actual usage in Cloud Console
- Increase only if hitting limits

#### 4. Request Bundling
- Batch multiple operations per request
- Reduces request count charges

#### 5. Use Caching
- Implement Redis/Memcached for frequent queries
- Reduces LLM API calls (major cost driver)

#### 6. Optimize Concurrency
```bash
--concurrency 80  # Default, good for I/O-bound
--concurrency 200  # Higher for light workloads
```
- Fewer instances = lower costs
- Test to find optimal value

### Cost Monitoring

```bash
# View estimated costs
gcloud billing projects describe $GOOGLE_CLOUD_PROJECT

# Set budget alerts
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Cloud Run Budget" \
  --budget-amount=100 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90
```

### Cost Breakdown Example

**Scenario**: 1M requests/month, avg 500ms processing time, 2 CPU, 2 GiB

- **CPU**: 1M × 0.5s × 2 vCPU × $0.00002400/vCPU-sec = $24
- **Memory**: 1M × 0.5s × 2 GiB × $0.00000250/GiB-sec = $2.50
- **Requests**: 1M × $0.40/1M = $0.40
- **Total**: ~$27/month

**With optimizations** (1 CPU, 1 GiB, scale to zero):
- **Total**: ~$7/month (74% savings)

---

## Advanced Topics

### Custom Domain

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service mcp-server-langgraph \
  --domain api.yourdomain.com \
  --region $REGION \
  --project=$GOOGLE_CLOUD_PROJECT

# Add DNS records as instructed
```

### Multi-Region Deployment

```bash
# Deploy to multiple regions
for region in us-central1 europe-west1 asia-east1; do
  gcloud run deploy mcp-server-langgraph \
    --image gcr.io/$GOOGLE_CLOUD_PROJECT/mcp-server-langgraph:latest \
    --region $region \
    --project=$GOOGLE_CLOUD_PROJECT
done

# Set up global load balancer (requires Cloud Load Balancing)
```

### CI/CD Integration

Add to `.github/workflows/deploy-cloudrun.yml`:
```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy mcp-server-langgraph \
            --source . \
            --region us-central1 \
            --project ${{ secrets.GCP_PROJECT_ID }}
```

### Database Integration (Cloud SQL)

```bash
# Create Cloud SQL instance
gcloud sql instances create mcp-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT

# Connect Cloud Run to Cloud SQL
gcloud run services update mcp-server-langgraph \
  --region $REGION \
  --add-cloudsql-instances $GOOGLE_CLOUD_PROJECT:$REGION:mcp-db \
  --project=$GOOGLE_CLOUD_PROJECT
```

---

## Next Steps

✅ **You've successfully deployed to Cloud Run!**

**Recommended next steps**:

1. **Set up monitoring alerts**: Create alerts for errors and latency
2. **Configure custom domain**: Map your domain to the service
3. **Implement CI/CD**: Automate deployments with GitHub Actions
4. **Load testing**: Test performance under load
5. **Cost monitoring**: Set up budget alerts
6. **Backup and DR**: Plan disaster recovery strategy

**Resources**:
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Run Best Practices](https://cloud.google.com/run/docs/best-practices)
- [Cloud Run Pricing Calculator](https://cloud.google.com/products/calculator)
- [Cloud Run Samples](https://github.com/GoogleCloudPlatform/cloud-run-samples)

**Need help?**
- Cloud Run support: https://cloud.google.com/support
- Project issues: https://github.com/vishnu2kmohan/mcp_server_langgraph/issues

---

**Last Updated**: 2025-10-10
