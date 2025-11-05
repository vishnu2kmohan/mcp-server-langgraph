# Infrastructure Deployment Checklist

## Overview

This checklist ensures reproducible and idempotent infrastructure deployments following the standardized naming convention: `{environment}-mcp-server-langgraph-{resource-type}`.

**Last Updated:** 2025-11-05
**Status:** ✅ Validated with staging rebuild

---

## Pre-Deployment Validation

### 1. Naming Convention Compliance

Run this validation before any infrastructure changes:

```bash
# Check for legacy naming patterns
! grep -r "mcp-staging-cluster\|mcp-prod-gke\|mcp-dev-cluster" \
  terraform/environments/ .github/workflows/deploy-*.yaml deployments/overlays/ || \
  echo "❌ FAIL: Legacy naming found"

# Verify new naming in active configs
grep -r "staging-mcp-server-langgraph-gke\|production-mcp-server-langgraph-gke" \
  .github/workflows/deploy-*.yaml terraform/environments/gcp-*/main.tf && \
  echo "✅ PASS: New naming present"
```

### 2. GitHub Variables Check

```bash
gh variable list | grep -E "GKE_.*_CLUSTER|NAMESPACE"
# Should show:
# - GKE_STAGING_CLUSTER: staging-mcp-server-langgraph-gke
# - GKE_PROD_CLUSTER: production-mcp-server-langgraph-gke
# - STAGING_NAMESPACE: staging-mcp-server-langgraph
# - PRODUCTION_NAMESPACE: production-mcp-server-langgraph
```

---

## Staging Environment Deployment

### Phase 1: Terraform Infrastructure

```bash
cd terraform/environments/gcp-staging

# 1. Initialize Terraform
terraform init \
  -backend-config=bucket=mcp-langgraph-terraform-state-staging \
  -backend-config=prefix=gcp-staging \
  -reconfigure

# 2. Plan (review for new naming)
terraform plan -out=tfplan

# Expected resources with new naming:
# - GKE: staging-mcp-server-langgraph-gke
# - VPC: staging-mcp-slg-vpc
# - Cloud SQL: staging-mcp-slg-postgres
# - Redis: staging-mcp-slg-redis

# 3. Apply (only VPC typically succeeds due to module bugs)
terraform apply tfplan
```

**Known Terraform Issues** (handle manually for now):
- Cloud SQL database flags validation errors
- GKE cluster may already exist
- WIF pool and SAs may need import

### Phase 2: Manual Resource Creation (Until Terraform Modules Fixed)

```bash
# 1. Create GKE cluster if not exists
gcloud container clusters create-auto staging-mcp-server-langgraph-gke \
  --region=us-central1 \
  --release-channel=regular \
  --async

# Wait for cluster
gcloud container clusters describe staging-mcp-server-langgraph-gke \
  --region=us-central1 --format="value(status)"
# Should show: RUNNING

# 2. Create Cloud SQL (with VPC peering from Terraform)
gcloud sql instances create staging-mcp-slg-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-custom-2-7680 \
  --region=us-central1 \
  --network=projects/vishnu-sandbox-20250310/global/networks/staging-mcp-slg-vpc \
  --no-assign-ip \
  --async

# 3. Create Redis
gcloud redis instances create staging-mcp-slg-redis \
  --size=5 \
  --region=us-central1 \
  --network=projects/vishnu-sandbox-20250310/global/networks/staging-mcp-slg-vpc \
  --redis-version=redis_7_0 \
  --tier=standard \
  --async

# 4. Wait for databases
gcloud sql instances describe staging-mcp-slg-postgres --format="value(state)"
# Should show: RUNNABLE

gcloud redis instances describe staging-mcp-slg-redis --region=us-central1 --format="value(state)"
# Should show: READY
```

### Phase 3: Database Setup

```bash
# 1. Create required databases
gcloud sql databases create mcp_langgraph_staging --instance=staging-mcp-slg-postgres
gcloud sql databases create openfga --instance=staging-mcp-slg-postgres
gcloud sql databases create keycloak --instance=staging-mcp-slg-postgres

# 2. Create database users
gcloud sql users create postgres --instance=staging-mcp-slg-postgres --password=<PASSWORD>
gcloud sql users create openfga --instance=staging-mcp-slg-postgres --password=<PASSWORD>
gcloud sql users create keycloak --instance=staging-mcp-slg-postgres --password=<PASSWORD>

# 3. Verify
gcloud sql databases list --instance=staging-mcp-slg-postgres
# Should show: mcp_langgraph_staging, openfga, keycloak, postgres
```

### Phase 4: Kubernetes Configuration

```bash
# 1. Get cluster credentials
gcloud container clusters get-credentials staging-mcp-server-langgraph-gke --region=us-central1

# 2. Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm repo update
kubectl create namespace external-secrets-system
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets-system \
  --set installCRDs=true \
  --wait

# 3. CRITICAL: Fix Workload Identity for External Secrets
#    This is the #1 cause of pod crashes
gcloud iam service-accounts add-iam-policy-binding \
  external-secrets-staging@vishnu-sandbox-20250310.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:vishnu-sandbox-20250310.svc.id.goog[staging-mcp-server-langgraph/staging-external-secrets-operator]"

# 4. Create Redis service (ExternalName to Memorystore)
REDIS_IP=$(gcloud redis instances describe staging-mcp-slg-redis --region=us-central1 --format="value(host)")

kubectl create service externalname redis-session \
  --external-name=${REDIS_IP} \
  -n staging-mcp-server-langgraph

kubectl patch service redis-session -n staging-mcp-server-langgraph \
  -p '{"spec":{"ports":[{"port":6379,"targetPort":6379,"protocol":"TCP","name":"redis"}]}}'

# 5. Verify naming correctness
kubectl get namespace staging-mcp-server-langgraph  # Should exist
kubectl get service redis-session -n staging-mcp-server-langgraph  # Should exist
```

### Phase 5: Deploy Application

```bash
# Deploy via GitHub Actions (IaC best practice)
gh workflow run deploy-staging-gke.yaml

# Monitor deployment
gh run list --workflow=deploy-staging-gke.yaml --limit=1

# Or deploy manually with kubectl
kubectl apply -k deployments/overlays/staging-gke

# Monitor rollout
kubectl rollout status deployment/staging-mcp-server-langgraph \
  -n staging-mcp-server-langgraph --timeout=10m
```

---

## Validation Checklist

### Infrastructure Resources

```bash
# GKE Cluster
gcloud container clusters describe staging-mcp-server-langgraph-gke \
  --region=us-central1 --format="value(name,status)"
# Expected: staging-mcp-server-langgraph-gke RUNNING

# Cloud SQL
gcloud sql instances describe staging-mcp-slg-postgres \
  --format="value(name,state)"
# Expected: staging-mcp-slg-postgres RUNNABLE

# Redis
gcloud redis instances describe staging-mcp-slg-redis \
  --region=us-central1 --format="value(name,state)"
# Expected: staging-mcp-slg-redis READY

# VPC
gcloud compute networks describe staging-mcp-slg-vpc --format="value(name)"
# Expected: staging-mcp-slg-vpc
```

### Kubernetes Resources

```bash
# Namespace
kubectl get namespace staging-mcp-server-langgraph
# Expected: Active

# Deployments
kubectl get deployment -n staging-mcp-server-langgraph
# Expected names:
# - staging-mcp-server-langgraph
# - staging-keycloak
# - staging-openfga
# - staging-qdrant

# Services
kubectl get svc -n staging-mcp-server-langgraph
# Expected:
# - staging-mcp-server-langgraph
# - staging-keycloak
# - staging-openfga
# - staging-qdrant
# - redis-session

# External Secrets
kubectl get secretstore,externalsecret -n staging-mcp-server-langgraph
# Expected:
# - SecretStore: staging-gcp-secret-store (Ready: True)
# - ExternalSecret: mcp-server-langgraph-secrets (Ready: True)
# - Secret: staging-mcp-server-langgraph-secrets (should exist)
```

### Workload Identity Bindings

```bash
# External Secrets SA
gcloud iam service-accounts get-iam-policy \
  external-secrets-staging@vishnu-sandbox-20250310.iam.gserviceaccount.com

# Should include:
# member: serviceAccount:vishnu-sandbox-20250310.svc.id.goog[staging-mcp-server-langgraph/staging-external-secrets-operator]

# Application SA (if using Workload Identity)
gcloud iam service-accounts list --filter="email:staging-mcp-slg-*"
# Expected:
# - staging-mcp-slg-app-sa
# - staging-mcp-slg-worker-sa
```

---

## Common Issues & Resolutions

### Issue 1: Pods Crashing - "cannot connect to database"

**Symptoms:**
- OpenFGA/Keycloak pods in CrashLoopBackOff
- Logs show database connection errors

**Root Causes:**
1. Missing databases (`openfga`, `keycloak`)
2. Wrong database instance name in Kustomize patches
3. Missing database users/passwords

**Fix:**
```bash
# Create databases
gcloud sql databases create openfga --instance=staging-mcp-slg-postgres
gcloud sql databases create keycloak --instance=staging-mcp-slg-postgres

# Verify Kustomize patches use correct instance
grep "staging-mcp-slg-postgres" deployments/overlays/staging-gke/*-patch.yaml
# Should find references in deployment-patch.yaml, keycloak-patch.yaml, openfga-patch.yaml

# Create users
gcloud sql users create openfga --instance=staging-mcp-slg-postgres
gcloud sql users create keycloak --instance=staging-mcp-slg-postgres
```

### Issue 2: External Secrets Not Syncing

**Symptoms:**
- SecretStore shows "InvalidProviderConfig"
- ExternalSecret shows "SecretSyncedError"
- No secrets exist in namespace

**Root Causes:**
1. Wrong namespace in Workload Identity binding
2. Wrong cluster name in SecretStore spec
3. Wrong namespace in external-secrets.yaml

**Fix:**
```bash
# 1. Check external-secrets.yaml
cat deployments/overlays/staging-gke/external-secrets.yaml | grep -E "namespace:|clusterName:"
# namespace: staging-mcp-server-langgraph (NOT mcp-server-langgraph-staging)
# clusterName: staging-mcp-server-langgraph-gke (NOT staging-mcp-server-langgraph-cluster)

# 2. Fix Workload Identity binding
gcloud iam service-accounts add-iam-policy-binding \
  external-secrets-staging@vishnu-sandbox-20250310.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:vishnu-sandbox-20250310.svc.id.goog[staging-mcp-server-langgraph/staging-external-secrets-operator]"

# 3. Restart External Secrets Operator
kubectl delete pods -n external-secrets-system -l app.kubernetes.io/name=external-secrets

# 4. Verify
kubectl get secretstore staging-gcp-secret-store -n staging-mcp-server-langgraph
# Status should become Ready: True
```

### Issue 3: MCP Server Stuck in Init - "waiting for redis"

**Symptoms:**
- Pods stuck in Init:0/3 or Init:1/3
- Init container logs show "nc: bad address 'redis-session'"

**Root Cause:**
- Redis service doesn't exist

**Fix:**
```bash
# Get Redis IP
REDIS_IP=$(gcloud redis instances describe staging-mcp-slg-redis \
  --region=us-central1 --format="value(host)")

# Create service
kubectl create service externalname redis-session \
  --external-name=${REDIS_IP} \
  -n staging-mcp-server-langgraph

# Add port
kubectl patch service redis-session -n staging-mcp-server-langgraph \
  -p '{"spec":{"ports":[{"port":6379,"targetPort":6379,"protocol":"TCP","name":"redis"}]}}'
```

### Issue 4: Legacy Naming in Deployed Resources

**Symptoms:**
- Resources exist with old names (mcp-staging-*, mcp-production-*, etc.)
- Kustomize/workflows reference old names

**Fix:**
```bash
# Audit all code
grep -r "mcp-staging-cluster\|mcp-prod-gke\|mcp-staging\>" \
  terraform/ .github/ deployments/ scripts/ \
  --include="*.tf" --include="*.yaml" --include="*.sh" \
  | grep -v ".git\|.naming-bak\|NAMING-CONVENTIONS"

# Any matches should be updated per NAMING-CONVENTIONS.md

# Commit fixes immediately
git add -A
git commit -m "fix: update remaining naming convention violations"
git push origin main
```

---

## Post-Deployment Verification

### 1. Infrastructure State

```bash
# Run comprehensive check
cat > /tmp/verify-infra.sh << 'EOF'
#!/bin/bash
echo "=== Infrastructure Verification ==="

echo -e "\n✓ GKE Cluster:"
gcloud container clusters describe staging-mcp-server-langgraph-gke \
  --region=us-central1 --format="value(name,status)" || echo "❌ MISSING"

echo -e "\n✓ Cloud SQL:"
gcloud sql instances describe staging-mcp-slg-postgres \
  --format="value(name,state,ipAddresses[0].ipAddress)" || echo "❌ MISSING"

echo -e "\n✓ Redis:"
gcloud redis instances describe staging-mcp-slg-redis \
  --region=us-central1 --format="value(name,state,host)" || echo "❌ MISSING"

echo -e "\n✓ VPC:"
gcloud compute networks describe staging-mcp-slg-vpc \
  --format="value(name)" || echo "❌ MISSING"

echo -e "\n✓ Kubernetes Namespace:"
kubectl get namespace staging-mcp-server-langgraph || echo "❌ MISSING"

echo -e "\n✓ Deployments:"
kubectl get deployment -n staging-mcp-server-langgraph || echo "❌ MISSING"

echo -e "\n✓ Secrets:"
kubectl get secret staging-mcp-server-langgraph-secrets \
  -n staging-mcp-server-langgraph || echo "❌ MISSING (check External Secrets)"

echo -e "\n✅ Verification complete"
EOF

chmod +x /tmp/verify-infra.sh
/tmp/verify-infra.sh
```

### 2. Naming Compliance Audit

```bash
# Automated audit script
cat > /tmp/naming-audit.sh << 'EOF'
#!/bin/bash
VIOLATIONS=0

echo "=== NAMING CONVENTION AUDIT ==="

echo -e "\n1. Checking Terraform..."
if grep -r "name_prefix.*=.*staging-mcp-server-langgraph" terraform/environments/gcp-staging/main.tf >/dev/null; then
  echo "✅ Terraform: staging full prefix correct"
else
  echo "❌ Terraform: staging prefix incorrect"
  VIOLATIONS=$((VIOLATIONS+1))
fi

if grep -r "short_prefix.*=.*staging-mcp-slg" terraform/environments/gcp-staging/main.tf >/dev/null; then
  echo "✅ Terraform: staging short prefix correct"
else
  echo "❌ Terraform: staging short prefix incorrect"
  VIOLATIONS=$((VIOLATIONS+1))
fi

echo -e "\n2. Checking Kustomization..."
if grep "namespace: staging-mcp-server-langgraph" deployments/overlays/staging-gke/kustomization.yaml >/dev/null; then
  echo "✅ Kustomization: namespace correct"
else
  echo "❌ Kustomization: namespace incorrect"
  VIOLATIONS=$((VIOLATIONS+1))
fi

echo -e "\n3. Checking External Secrets..."
if grep "clusterName: staging-mcp-server-langgraph-gke" deployments/overlays/staging-gke/external-secrets.yaml >/dev/null; then
  echo "✅ External Secrets: cluster name correct"
else
  echo "❌ External Secrets: cluster name incorrect"
  VIOLATIONS=$((VIOLATIONS+1))
fi

echo -e "\n4. Checking Cloud SQL references..."
if grep "staging-mcp-slg-postgres" deployments/overlays/staging-gke/deployment-patch.yaml >/dev/null; then
  echo "✅ Deployment patch: Cloud SQL name correct"
else
  echo "❌ Deployment patch: Cloud SQL name incorrect"
  VIOLATIONS=$((VIOLATIONS+1))
fi

echo -e "\n5. Checking GitHub workflows..."
if grep 'GKE_CLUSTER.*staging-mcp-server-langgraph-gke' .github/workflows/deploy-staging-gke.yaml >/dev/null; then
  echo "✅ Workflow: cluster name correct"
else
  echo "❌ Workflow: cluster name incorrect"
  VIOLATIONS=$((VIOLATIONS+1))
fi

echo -e "\n========================================="
if [ $VIOLATIONS -eq 0 ]; then
  echo "✅ PASS: All naming conventions compliant"
  exit 0
else
  echo "❌ FAIL: $VIOLATIONS violations found"
  exit 1
fi
EOF

chmod +x /tmp/naming-audit.sh
/tmp/naming-audit.sh
```

---

## Production Environment Deployment

Follow same steps as staging but use `production` prefix:

**Resources:**
- Cluster: `production-mcp-server-langgraph-gke`
- VPC: `production-mcp-slg-vpc`
- Cloud SQL: `production-mcp-slg-postgres`
- Redis: `production-mcp-slg-redis`
- Namespace: `production-mcp-server-langgraph`

**Terraform:**
```bash
cd terraform/environments/gcp-prod
terraform init -backend-config=bucket=mcp-langgraph-terraform-state-prod \
  -backend-config=prefix=gcp-prod -reconfigure
terraform plan -out=tfplan
terraform apply tfplan
```

---

## Development Environment Deployment

**Resources:**
- Cluster: `dev-mcp-server-langgraph-gke`
- VPC: `dev-mcp-slg-vpc`
- Cloud SQL: `dev-mcp-slg-postgres`
- Redis: `dev-mcp-slg-redis`
- Namespace: `dev-mcp-server-langgraph`

---

## Terraform State Management

### Import Manually-Created Resources

If resources were created manually (via gcloud), import into Terraform:

```bash
cd terraform/environments/gcp-staging

# Import Cloud SQL
terraform import module.cloudsql.google_sql_database_instance.main \
  staging-mcp-slg-postgres

# Import Redis
terraform import module.memorystore.google_redis_instance.main \
  projects/vishnu-sandbox-20250310/locations/us-central1/instances/staging-mcp-slg-redis

# Import GKE cluster (if created manually)
terraform import module.gke.google_container_cluster.autopilot \
  staging-mcp-server-langgraph-gke

# Import VPC
terraform import module.vpc.google_compute_network.main \
  staging-mcp-slg-vpc

# Verify state
terraform plan
# Should show: No changes (if all resources imported correctly)
```

---

## Idempotency Testing

### Test 1: Terraform Plan Should Show No Changes

```bash
cd terraform/environments/gcp-staging
terraform plan

# Expected output:
# "No changes. Your infrastructure matches the configuration."
```

### Test 2: Kubectl Apply Should Be Idempotent

```bash
kubectl apply -k deployments/overlays/staging-gke

# Expected output:
# "unchanged" for all resources (or "configured" if recently changed)
```

### Test 3: GitHub Actions Deploy Should Be Idempotent

```bash
# Trigger deployment twice
gh workflow run deploy-staging-gke.yaml
# Wait for completion
sleep 300
gh workflow run deploy-staging-gke.yaml

# Both should succeed with same result
# No pods should be unnecessarily restarted
```

---

## Pre-Commit Validation Hook

Add to `.github/workflows/validate-naming.yaml`:

```yaml
name: Validate Naming Conventions

on:
  pull_request:
    paths:
      - 'terraform/**'
      - 'deployments/**'
      - '.github/workflows/**'

jobs:
  validate-naming:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check for legacy naming
        run: |
          if grep -r "mcp-staging-cluster\|mcp-prod-gke\|mcp-dev-cluster" \
            terraform/ .github/workflows/ deployments/overlays/; then
            echo "❌ Legacy naming found"
            exit 1
          fi
          echo "✅ No legacy naming patterns found"

      - name: Verify new naming present
        run: |
          grep -q "staging-mcp-server-langgraph-gke" \
            .github/workflows/deploy-staging-gke.yaml || exit 1
          grep -q "production-mcp-server-langgraph-gke" \
            .github/workflows/deploy-production-gke.yaml || exit 1
          echo "✅ New naming conventions verified"
```

---

## Reference Documentation

- **Naming Conventions**: See `NAMING-CONVENTIONS.md`
- **Terraform Modules**: See `terraform/modules/*/README.md`
- **Deployment Workflows**: See `.github/workflows/deploy-*.yaml`
- **Troubleshooting**: See `docs/infrastructure/gke-cluster-requirements.mdx`

---

## Reproducibility Guarantee

This checklist ensures:
- ✅ **Reproducible**: Same steps produce identical infrastructure
- ✅ **Idempotent**: Running twice has no additional effect
- ✅ **Versioned**: All configuration in git
- ✅ **Validated**: Automated checks prevent regressions
- ✅ **Documented**: Clear instructions for all steps

**Last Validated:** 2025-11-05 (Staging rebuild from scratch succeeded)
