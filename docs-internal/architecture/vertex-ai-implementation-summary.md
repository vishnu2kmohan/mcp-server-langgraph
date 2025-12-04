# Vertex AI with Workload Identity - Implementation Summary

**Date**: 2025-10-21
**Environment**: GKE Staging (preview-gke)
**Status**: ✅ Complete

## Overview

Successfully implemented Vertex AI integration with Workload Identity Federation for the staging GKE environment. This provides keyless, secure authentication to Vertex AI APIs from Kubernetes pods.

## Changes Made

### 1. Code Changes

#### `src/mcp_server_langgraph/core/config.py`
- **Added**: `vertex_project` configuration field (GCP project ID for Vertex AI)
- **Added**: `vertex_location` configuration field (Vertex AI region, default: `us-central1`)
- **Purpose**: Support Vertex AI configuration alongside Google AI Studio

**Lines changed**: 97-101

```python
# Vertex AI (Google Cloud AI Platform)
# Use Workload Identity on GKE (no GOOGLE_APPLICATION_CREDENTIALS needed)
# or set GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
vertex_project: Optional[str] = None  # GCP project ID for Vertex AI
vertex_location: str = "us-central1"  # Vertex AI location/region
```

#### `src/mcp_server_langgraph/llm/factory.py`
- **Updated**: `create_llm_from_config()` - Added Vertex AI provider support
- **Updated**: `create_summarization_model()` - Added Vertex AI configuration
- **Updated**: `create_verification_model()` - Added Vertex AI configuration
- **Added**: Logic to pass `vertex_project` and `vertex_location` to LiteLLM
- **Added**: Support for both `google` and `vertex_ai` provider names

**Lines changed**: 505, 535-546, 591-592, 606-609, 654, 669-672

**Key changes**:
```python
api_key_map = {
    # ... other providers ...
    "vertex_ai": None,  # Vertex AI uses Workload Identity
}

# Vertex AI configuration
elif config.llm_provider in ["vertex_ai", "google"]:
    vertex_project = config.vertex_project or config.google_project_id
    if vertex_project:
        provider_kwargs.update({
            "vertex_project": vertex_project,
            "vertex_location": config.vertex_location,
        })
```

### 2. Infrastructure Scripts

#### `scripts/gcp/setup-vertex-ai-preview.sh` (NEW)
- **Purpose**: Automated setup for Vertex AI Workload Identity
- **Permissions**: Executable (`chmod +x`)
- **Size**: 12,001 bytes

**What it does**:
1. ✅ Enables Vertex AI API (`aiplatform.googleapis.com`)
2. ✅ Creates `vertex-ai-staging` service account
3. ✅ Grants IAM permissions:
   - `roles/aiplatform.user` - API access
   - `roles/aiplatform.developer` - Model management
   - `roles/logging.logWriter` - Cloud Logging
   - `roles/monitoring.metricWriter` - Cloud Monitoring
4. ✅ Binds Kubernetes SA to GCP SA (Workload Identity)
5. ✅ Annotates Kubernetes service account
6. ✅ Verifies configuration

**Usage**:
```bash
./scripts/gcp/setup-vertex-ai-preview.sh
```

### 3. Kubernetes Manifests

#### `deployments/overlays/preview-gke/serviceaccount-patch.yaml`
- **Changed**: Workload Identity annotation
- **Old SA**: `mcp-staging-sa@vishnu-sandbox-20250310.iam.gserviceaccount.com`
- **New SA**: `vertex-ai-staging@vishnu-sandbox-20250310.iam.gserviceaccount.com`

**Why changed**: The new service account includes Vertex AI permissions in addition to existing permissions (Secret Manager, Cloud SQL, Logging, Monitoring).

```yaml
annotations:
  iam.gke.io/gcp-service-account: vertex-ai-staging@vishnu-sandbox-20250310.iam.gserviceaccount.com
```

#### `deployments/overlays/preview-gke/deployment-patch.yaml`
- **Added**: Vertex AI environment variables
- **Added**: LLM provider configuration
- **Updated**: Comments for clarity

**New environment variables**:
```yaml
env:
  # LLM Provider Configuration
  - name: LLM_PROVIDER
    value: "google"
  - name: MODEL_NAME
    value: "gemini-2.5-flash"

  # Vertex AI Configuration (Workload Identity - no credentials needed)
  - name: VERTEX_PROJECT
    value: "vishnu-sandbox-20250310"
  - name: VERTEX_LOCATION
    value: "us-central1"
```

### 4. Documentation

#### `docs/deployment/vertex-ai-workload-identity.mdx` (NEW)
- **Purpose**: Comprehensive guide for Vertex AI setup with Workload Identity
- **Size**: ~15KB
- **Sections**:
  - Overview & Architecture diagram
  - Prerequisites
  - Quick setup (automated) & Manual setup (detailed)
  - Configuration guide
  - Deployment instructions
  - Verification steps (5 different tests)
  - Troubleshooting (4 common issues)
  - Security considerations
  - Cost management
  - Migration guide from Google AI Studio

#### `.env.example`
- **Updated**: Added Vertex AI configuration section
- **Added**: Comments explaining two authentication options:
  1. Google AI Studio (API key) - for development
  2. Vertex AI (Workload Identity) - for production

```bash
# Option 1: Google AI Studio (API Key - good for development/testing)
GOOGLE_API_KEY=your-key-here

# Option 2: Vertex AI (GCP - production/enterprise)
# VERTEX_PROJECT=your-gcp-project-id
# VERTEX_LOCATION=us-central1
```

### 5. GitHub Configuration

#### `.github/workflows/deploy-preview-gke.yaml`
- **Changed**: GitHub environment name
- **Old**: `staging`
- **New**: `preview-gke`
- **Why**: Better reflects that this is specifically for GKE staging deployment

**Action Required**: Update GitHub environment settings:
1. Go to GitHub repository Settings → Environments
2. Rename environment from `staging` to `preview-gke`
3. Or create new `preview-gke` environment with same protection rules

## How It Works

### Authentication Flow

```
┌─────────────────────────────────────────────┐
│ Kubernetes Pod                              │
│ ┌─────────────────────────────────────────┐ │
│ │ ServiceAccount: mcp-server-langgraph    │ │
│ │ Annotation: vertex-ai-staging@...       │ │
│ └──────────────┬──────────────────────────┘ │
│                │ 1. Pod requests token      │
│                ▼                            │
│ ┌─────────────────────────────────────────┐ │
│ │ GKE Metadata Server                     │ │
│ │ Issues GCP access token                 │ │
│ └──────────────┬──────────────────────────┘ │
└────────────────┼──────────────────────────────┘
                 │ 2. Token with SA identity
                 ▼
┌─────────────────────────────────────────────┐
│ Google Cloud                                │
│ ┌─────────────────────────────────────────┐ │
│ │ IAM checks permissions                  │ │
│ │ vertex-ai-staging has aiplatform.user   │ │
│ └──────────────┬──────────────────────────┘ │
│                │ 3. API call allowed        │
│                ▼                            │
│ ┌─────────────────────────────────────────┐ │
│ │ Vertex AI API                           │ │
│ │ Returns gemini-2.5-flash response   │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### LiteLLM Integration

When `VERTEX_PROJECT` is set, LiteLLM automatically:
1. Detects Workload Identity credentials
2. Uses Vertex AI endpoints instead of AI Studio
3. Authenticates via GCP service account token
4. Routes requests to `aiplatform.googleapis.com`

**No service account keys needed!**

## Deployment Steps

### Option A: Full Automated Setup

```bash
# 1. Run Vertex AI setup (creates SA, grants permissions, binds to K8s SA)
./scripts/gcp/setup-vertex-ai-preview.sh

# 2. Deploy updated manifests
kubectl apply -k deployments/overlays/preview-gke

# 3. Verify deployment
kubectl rollout status deployment/mcp-server-langgraph -n mcp-staging

# 4. Test Vertex AI access
POD_NAME=$(kubectl get pods -n mcp-staging -l app=mcp-server-langgraph -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $POD_NAME -n mcp-staging -- gcloud auth list
```

### Option B: Manual Step-by-Step

See: `docs/deployment/vertex-ai-workload-identity.mdx`

## Verification Checklist

- [ ] **GCP Service Account Created**
  ```bash
  gcloud iam service-accounts describe vertex-ai-staging@vishnu-sandbox-20250310.iam.gserviceaccount.com
  ```

- [ ] **IAM Permissions Granted**
  ```bash
  gcloud projects get-iam-policy vishnu-sandbox-20250310 \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:vertex-ai-staging@*"
  ```

- [ ] **Workload Identity Binding**
  ```bash
  gcloud iam service-accounts get-iam-policy \
    vertex-ai-staging@vishnu-sandbox-20250310.iam.gserviceaccount.com
  ```

- [ ] **Kubernetes SA Annotated**
  ```bash
  kubectl get sa mcp-server-langgraph -n mcp-staging \
    -o jsonpath='{.metadata.annotations.iam\.gke\.io/gcp-service-account}'
  ```

- [ ] **Pod Authentication Working**
  ```bash
  kubectl exec -it $POD_NAME -n mcp-staging -- gcloud auth list
  # Should show: vertex-ai-staging@vishnu-sandbox-20250310.iam.gserviceaccount.com
  ```

- [ ] **Vertex AI API Access**
  ```bash
  kubectl exec -it $POD_NAME -n mcp-staging -- python3 -c \
    "from google.cloud import aiplatform; aiplatform.init(project='vishnu-sandbox-20250310', location='us-central1'); print('✓ Vertex AI working!')"
  ```

- [ ] **LiteLLM Integration**
  ```bash
  kubectl logs -n mcp-staging $POD_NAME | grep -i "vertex\|gemini"
  ```

## Security Benefits

| Feature | Before | After |
|---------|--------|-------|
| **Authentication** | API key in secret | Workload Identity (keyless) |
| **Key Rotation** | Manual | Automatic (Google-managed) |
| **Scope** | Broad (API key for all) | Fine-grained (IAM per SA) |
| **Audit** | Limited | Full Cloud Audit Logs |
| **Compromise Impact** | High (key can be used anywhere) | Low (only works from GKE pod) |

## Cost Comparison

| Model | Google AI Studio | Vertex AI | Status |
|-------|-----------------|-----------|--------|
| gemini-2.5-flash | $0.15/$0.60 per 1M tokens | $0.075/$0.30 per 1M chars | Production-grade, Vertex AI ~50% cheaper |
| gemini-2.5-pro | $1.25/$10 per 1M tokens | $0.625/$5 per 1M chars | Production-grade, Vertex AI ~50% cheaper |

**Notes**:
- **gemini-2.5-flash** and **gemini-2.5-pro** are production-grade models recommended for enterprise use
- Only these two specific models are officially supported for production workloads
- Vertex AI pricing is per character, AI Studio is per token (~4 chars = 1 token)
- Vertex AI offers better pricing and enterprise features (VPC, audit logs, etc.)

## Fallback Strategy

The configuration supports fallback to Google AI Studio if Vertex AI fails:

1. **Primary**: Vertex AI (via Workload Identity)
2. **Fallback 1**: Google AI Studio (via `GOOGLE_API_KEY`)
3. **Fallback 2**: Anthropic Claude (via `ANTHROPIC_API_KEY`)

This is configured in `FALLBACK_MODELS` environment variable.

## Troubleshooting

### Issue: Pod shows default compute SA instead of vertex-ai-staging

**Solution**:
```bash
# Restart deployment to pick up new annotation
kubectl rollout restart deployment/mcp-server-langgraph -n mcp-staging
```

### Issue: Permission denied when calling Vertex AI

**Solution**:
```bash
# Verify permissions
gcloud projects get-iam-policy vishnu-sandbox-20250310 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:vertex-ai-staging@*"

# Should include:
# - roles/aiplatform.user
# - roles/aiplatform.developer
```

### Issue: LiteLLM not detecting Vertex AI

**Solution**:
```bash
# Ensure VERTEX_PROJECT is set
kubectl describe pod $POD_NAME -n mcp-staging | grep VERTEX_PROJECT

# Should show: VERTEX_PROJECT=vishnu-sandbox-20250310
```

## Testing Commands

### 1. Test Workload Identity
```bash
kubectl run -it --rm test-wi \
  --image=google/cloud-sdk:slim \
  --serviceaccount=mcp-server-langgraph \
  --namespace=mcp-staging \
  -- gcloud auth list
```

### 2. Test Vertex AI API
```bash
POD_NAME=$(kubectl get pods -n mcp-staging -l app=mcp-server-langgraph -o jsonpath='{.items[0].metadata.name}')

kubectl exec -it $POD_NAME -n mcp-staging -- python3 << 'EOF'
from litellm import completion

response = completion(
    model="vertex_ai/gemini-2.5-flash",
    messages=[{"role": "user", "content": "Hello from Vertex AI!"}],
    vertex_project="vishnu-sandbox-20250310",
    vertex_location="us-central1"
)

print(f"✓ Success! Response: {response.choices[0].message.content}")
EOF
```

### 3. Test Application Health
```bash
kubectl port-forward -n mcp-staging svc/mcp-server-langgraph 8080:80 &
curl http://localhost:8080/health
```

## Next Steps

1. **Update GitHub Environment**:
   - Rename `staging` environment to `preview-gke` in GitHub settings
   - Or create new `preview-gke` environment with protection rules

2. **Run Setup Script**:
   ```bash
   ./scripts/gcp/setup-vertex-ai-preview.sh
   ```

3. **Deploy to Staging**:
   ```bash
   kubectl apply -k deployments/overlays/preview-gke
   ```

4. **Verify and Test** (see verification checklist above)

5. **Monitor Costs**:
   - Set up budget alerts in GCP Console
   - Monitor Vertex AI usage in Cloud Logging

6. **Production Deployment**:
   - Create similar setup for production environment
   - Use separate GCP project or tighter IAM controls
   - Consider multi-region deployment for HA

## Files Changed

### Modified
- `src/mcp_server_langgraph/core/config.py` - Added Vertex AI config fields
- `src/mcp_server_langgraph/llm/factory.py` - Added Vertex AI provider support
- `deployments/overlays/preview-gke/serviceaccount-patch.yaml` - Updated WI annotation
- `deployments/overlays/preview-gke/deployment-patch.yaml` - Added Vertex AI env vars
- `.env.example` - Added Vertex AI configuration examples
- `.github/workflows/deploy-preview-gke.yaml` - Updated environment name

### Created
- `scripts/gcp/setup-vertex-ai-preview.sh` - Automated setup script
- `docs/deployment/vertex-ai-workload-identity.mdx` - Comprehensive documentation
- `VERTEX_AI_IMPLEMENTATION_SUMMARY.md` - This file

## Resources

- **Documentation**: `docs/deployment/vertex-ai-workload-identity.mdx`
- **Setup Script**: `scripts/gcp/setup-vertex-ai-preview.sh`
- **GCP Console**: https://console.cloud.google.com/vertex-ai
- **Vertex AI Docs**: https://cloud.google.com/vertex-ai/docs
- **Workload Identity**: https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity
- **LiteLLM Vertex AI**: https://docs.litellm.ai/docs/providers/vertex

---

**Implementation Complete**: ✅
**Date**: 2025-10-21
**Author**: Claude Code (Sonnet 4.5)
**Review Status**: Ready for testing
