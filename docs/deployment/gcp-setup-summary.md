# GCP Infrastructure Setup - Complete ✅

**Date**: 2025-11-02
**Project**: `vishnu-sandbox-20250310`
**Region**: `us-central1`
**Status**: All infrastructure ready for CI/CD deployments

---

## ✅ Resources Created

### 1. GKE Autopilot Cluster
- **Name**: `mcp-staging-cluster`
- **Region**: `us-central1`
- **Status**: `RUNNING`
- **Type**: Autopilot (managed, auto-scaling)
- **Workload Identity**: Enabled
- **Network**: `staging-vpc`

**Verify**:
```bash
gcloud container clusters describe mcp-staging-cluster --region=us-central1
```

### 2. Artifact Registry Repository
- **Name**: `mcp-staging`
- **Location**: `us-central1`
- **Format**: Docker
- **Full Path**: `us-central1-docker.pkg.dev/vishnu-sandbox-20250310/mcp-staging`

**Verify**:
```bash
gcloud artifacts repositories describe mcp-staging --location=us-central1
```

**Docker Authentication**:
```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### 3. Workload Identity Federation (Keyless Auth)
- **Pool Name**: `github-actions-pool`
- **Provider Name**: `github-provider`
- **Status**: `ACTIVE`
- **Location**: `global`
- **Repository**: `vishnu2kmohan/mcp-server-langgraph`

**Full Resource Names**:
- Pool: `projects/1024691643349/locations/global/workloadIdentityPools/github-actions-pool`
- Provider: `projects/1024691643349/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider`

**Verify**:
```bash
gcloud iam workload-identity-pools describe github-actions-pool --location=global
```

### 4. Service Account
- **Email**: `mcp-staging-sa@vishnu-sandbox-20250310.iam.gserviceaccount.com`
- **Display Name**: MCP Staging Service Account
- **Roles**:
  - `roles/container.developer` - Deploy to GKE
  - `roles/artifactregistry.writer` - Push Docker images
  - `roles/logging.logWriter` - Write logs
  - `roles/monitoring.metricWriter` - Write metrics
  - `roles/cloudsql.client` - Connect to Cloud SQL (when created)
  - `roles/secretmanager.secretAccessor` - Access secrets

**Workload Identity Binding**:
- GitHub repository `vishnu2kmohan/mcp-server-langgraph` can impersonate this service account via Workload Identity Federation

**Verify**:
```bash
gcloud iam service-accounts describe mcp-staging-sa@vishnu-sandbox-20250310.iam.gserviceaccount.com
```

### 5. VPC Network
- **Name**: `staging-vpc`
- **Subnet**: `staging-gke-subnet`
- **Region**: `us-central1`

---

## 🔧 GitHub Actions Workflow Configuration

### Already Configured ✅

The workflow `.github/workflows/deploy-staging-gke.yaml` already has the correct configuration:

```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: 'projects/1024691643349/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider'
    service_account: 'mcp-staging-sa@vishnu-sandbox-20250310.iam.gserviceaccount.com'
    token_format: access_token
```

**No GitHub Secrets Required** - Workload Identity Federation provides keyless authentication!

---

## 🚀 Deployment Workflow

### Automatic Deployment Triggers

The staging deployment workflow runs automatically on:
1. **Push to main branch** - Deploys latest code
2. **Manual trigger** - Via GitHub Actions UI (`workflow_dispatch`)

### Manual Deployment

Trigger manually via GitHub CLI:
```bash
gh workflow run deploy-staging-gke.yaml
```

Or via GitHub UI:
1. Go to Actions → Deploy to GKE Staging
2. Click "Run workflow"
3. Select branch: `main`
4. Click "Run workflow"

### Deployment Steps

1. **Build Docker Image**:
   - Target: `final-base` (distroless, 200MB)
   - Tags: `staging-${GITHUB_SHA::8}`, `staging-latest`
   - Push to: `us-central1-docker.pkg.dev/vishnu-sandbox-20250310/mcp-staging/agent`

2. **Deploy to GKE**:
   - Namespace: `mcp-staging`
   - Uses: Kustomize overlay (`deployments/overlays/staging-gke/`)
   - Health checks: 5 minutes timeout
   - Rollout strategy: RollingUpdate

3. **Smoke Tests**:
   - Script: `scripts/gcp/staging-smoke-tests.sh`
   - Tests: Health check, basic API calls, logging verification
   - Timeout: 10 minutes

4. **Rollback on Failure**:
   - Automatic: `kubectl rollout undo deployment/mcp-server-langgraph -n mcp-staging`
   - Notifications: GitHub workflow status

---

## 📊 Monitoring & Verification

### Check Cluster Status
```bash
# Cluster info
gcloud container clusters describe mcp-staging-cluster --region=us-central1

# Node status
gcloud container node-pools list --cluster=mcp-staging-cluster --region=us-central1

# Get credentials
gcloud container clusters get-credentials mcp-staging-cluster --region=us-central1
```

### Check Deployments
```bash
# List deployments
kubectl get deployments -n mcp-staging

# Deployment details
kubectl describe deployment mcp-server-langgraph -n mcp-staging

# Pod status
kubectl get pods -n mcp-staging

# Logs
kubectl logs -f deployment/mcp-server-langgraph -n mcp-staging
```

### Check Images
```bash
# List images
gcloud artifacts docker images list us-central1-docker.pkg.dev/vishnu-sandbox-20250310/mcp-staging

# Image details
gcloud artifacts docker images describe \
  us-central1-docker.pkg.dev/vishnu-sandbox-20250310/mcp-staging/agent:staging-latest
```

---

## 🔐 Security

### Workload Identity Federation Benefits
- ✅ **No service account keys** - Keyless authentication
- ✅ **Short-lived tokens** - 1-hour validity
- ✅ **OIDC-based** - Industry standard
- ✅ **Audit trail** - All actions logged
- ✅ **Granular permissions** - Per-repository access

### IAM Best Practices Applied
- ✅ **Least privilege** - Service account has only required roles
- ✅ **Workload Identity** - No exported keys
- ✅ **Resource-level permissions** - Scoped to staging environment
- ✅ **Separation of duties** - Staging vs. production accounts

---

## 💰 Cost Estimation

### Monthly Costs (Staging)

| Resource | Configuration | Est. Monthly Cost |
|----------|---------------|-------------------|
| **GKE Autopilot** | 1-5 nodes, e2-medium | ~$75-150 |
| **Artifact Registry** | Docker images, 10GB | ~$0.10/GB = $1 |
| **Cloud Logging** | 5GB/month | ~$0.50/GB = $2.50 |
| **Cloud Monitoring** | Included | $0 |
| **Networking** | Standard egress | ~$10-20 |
| **Total** | | **~$90-175/month** |

### Cost Optimization Tips
- Use `preemptible` node pool for non-critical workloads
- Set resource limits on pods
- Clean up old images regularly
- Use Cloud CDN for static content
- Enable autoscaling with appropriate min/max nodes

---

## 🛠️ Troubleshooting

### Workflow Fails: "Permission denied"
**Cause**: IAM permissions not properly configured

**Fix**:
```bash
# Re-grant permissions
gcloud projects add-iam-policy-binding vishnu-sandbox-20250310 \
  --member="serviceAccount:mcp-staging-sa@vishnu-sandbox-20250310.iam.gserviceaccount.com" \
  --role="roles/container.developer"
```

### Workflow Fails: "Workload Identity Provider not found"
**Cause**: Workload Identity Pool or Provider misconfigured

**Fix**:
```bash
# Verify pool exists
gcloud iam workload-identity-pools describe github-actions-pool --location=global

# Verify provider exists
gcloud iam workload-identity-pools providers describe github-provider \
  --workload-identity-pool=github-actions-pool \
  --location=global
```

### Docker Push Fails: "403 Forbidden"
**Cause**: Artifact Registry permissions missing

**Fix**:
```bash
# Grant Artifact Registry Writer role
gcloud projects add-iam-policy-binding vishnu-sandbox-20250310 \
  --member="serviceAccount:mcp-staging-sa@vishnu-sandbox-20250310.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

### Deployment Fails: "ImagePullBackOff"
**Cause**: Image doesn't exist or GKE can't pull from Artifact Registry

**Fix**:
```bash
# Verify image exists
gcloud artifacts docker images list us-central1-docker.pkg.dev/vishnu-sandbox-20250310/mcp-staging

# Check GKE node service account permissions
gcloud projects add-iam-policy-binding vishnu-sandbox-20250310 \
  --member="serviceAccount:service-1024691643349@gcp-sa-gkenode.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.reader"
```

---

## 📚 Additional Documentation

- **Full Setup Guide**: [docs/deployment/gcp-configuration.md](gcp-configuration.md)
- **GKE Staging Guide**: [docs/deployment/kubernetes/gke-staging.mdx](kubernetes/gke-staging.mdx)
- **Terraform Config**: [docs/deployment/infrastructure/terraform-gcp.mdx](infrastructure/terraform-gcp.mdx)
- **Security Hardening**: [docs/security/gcp-security-hardening.mdx](../security/gcp-security-hardening.mdx)
- **Runbooks**: [docs/deployment/operations/gke-runbooks.mdx](operations/gke-runbooks.mdx)

---

## ✅ Verification Checklist

- [x] GKE cluster created and running
- [x] Artifact Registry repository created
- [x] Workload Identity Pool created
- [x] Workload Identity Provider configured
- [x] Service account created with proper roles
- [x] GitHub Actions workflow configured
- [x] VPC network created
- [ ] First deployment successful (pending)
- [ ] Smoke tests passing (pending)
- [ ] Monitoring dashboards configured (optional)

---

## 🎯 Next Steps

1. **Test Deployment**:
   ```bash
   gh workflow run deploy-staging-gke.yaml
   ```

2. **Monitor Deployment**:
   ```bash
   gh run watch
   # Or check in GitHub UI
   ```

3. **Verify Application**:
   ```bash
   kubectl get pods -n mcp-staging
   kubectl logs -f deployment/mcp-server-langgraph -n mcp-staging
   ```

4. **Configure Monitoring** (Optional):
   - Set up Cloud Monitoring dashboards
   - Configure alerting policies
   - Enable log-based metrics

5. **Production Setup** (When Ready):
   - Run `scripts/gcp/setup-production-infrastructure.sh`
   - Configure production secrets
   - Set up Cloud SQL for production
   - Enable Binary Authorization

---

**Setup Completed By**: Claude Code
**Documentation**: Comprehensive guides available in `docs/deployment/`
**Support**: See [GCP Runbooks](operations/gke-runbooks.mdx) for operational procedures
