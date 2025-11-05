#!/bin/bash
# ==============================================================================
# Setup ArgoCD for GCP GKE Multi-Cluster Management
# ==============================================================================

set -euo pipefail

PROJECT_ID="${1:-}"
if [ -z "$PROJECT_ID" ]; then
    echo "Usage: $0 PROJECT_ID"
    exit 1
fi

echo "Setting up ArgoCD for GCP project: $PROJECT_ID"

# ==============================================================================
# 1. Install ArgoCD on Management Cluster
# ==============================================================================

echo "Installing ArgoCD..."

# Create namespace
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
echo "Waiting for ArgoCD to be ready..."
kubectl wait --for=condition=available --timeout=300s \
    deployment/argocd-server \
    deployment/argocd-repo-server \
    deployment/argocd-applicationset-controller \
    -n argocd

echo "✅ ArgoCD installed"

# ==============================================================================
# 2. Install ArgoCD Image Updater
# ==============================================================================

echo "Installing ArgoCD Image Updater..."

kubectl apply -n argocd \
    -f https://raw.githubusercontent.com/argoproj-labs/argocd-image-updater/stable/manifests/install.yaml

kubectl wait --for=condition=available --timeout=120s \
    deployment/argocd-image-updater \
    -n argocd

echo "✅ ArgoCD Image Updater installed"

# ==============================================================================
# 3. Configure Workload Identity for ArgoCD
# ==============================================================================

echo "Configuring Workload Identity for ArgoCD..."

# Create GCP service account
gcloud iam service-accounts create argocd-sa \
    --display-name="ArgoCD Service Account" \
    --project="$PROJECT_ID" \
    2>/dev/null || echo "Service account already exists"

# Grant permissions
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:argocd-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/container.developer" \
    2>/dev/null || echo "Permission already granted"

# Grant Artifact Registry reader role
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:argocd-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.reader" \
    2>/dev/null || echo "Permission already granted"

# Bind Kubernetes SA to GCP SA
kubectl annotate serviceaccount argocd-server \
    -n argocd \
    iam.gke.io/gcp-service-account=argocd-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --overwrite

kubectl annotate serviceaccount argocd-image-updater \
    -n argocd \
    iam.gke.io/gcp-service-account=argocd-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --overwrite

# Bind GCP SA to Kubernetes SA
gcloud iam service-accounts add-iam-policy-binding \
    argocd-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:${PROJECT_ID}.svc.id.goog[argocd/argocd-server]" \
    --project="$PROJECT_ID"

gcloud iam service-accounts add-iam-policy-binding \
    argocd-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:${PROJECT_ID}.svc.id.goog[argocd/argocd-image-updater]" \
    --project="$PROJECT_ID"

echo "✅ Workload Identity configured"

# ==============================================================================
# 4. Get Admin Password
# ==============================================================================

echo "Getting ArgoCD admin password..."

ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
    -o jsonpath="{.data.password}" | base64 -d)

echo "✅ ArgoCD admin password retrieved"

# ==============================================================================
# 5. Expose ArgoCD UI
# ==============================================================================

echo "Exposing ArgoCD UI..."

kubectl patch svc argocd-server -n argocd \
    --patch '{"spec": {"type": "LoadBalancer"}}'

echo "Waiting for Load Balancer IP..."
sleep 30

ARGOCD_URL=$(kubectl get svc argocd-server -n argocd \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "✅ ArgoCD UI exposed"

# ==============================================================================
# 6. Apply Multi-Cluster Configuration
# ==============================================================================

echo "Applying multi-cluster configuration..."

# Update cluster endpoints in the YAML
# Note: This requires manual update with actual cluster endpoints

echo "⚠️  Update gcp-multi-cluster-setup.yaml with actual cluster endpoints before applying"
echo "   Then run: kubectl apply -f deployments/argocd/gcp-multi-cluster-setup.yaml"

# ==============================================================================
# 7. Setup Complete
# ==============================================================================

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ArgoCD Setup Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "ArgoCD URL:      https://$ARGOCD_URL"
echo "Username:        admin"
echo "Password:        $ARGOCD_PASSWORD"
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Next Steps"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "1. Access ArgoCD UI:"
echo "   https://$ARGOCD_URL"
echo
echo "2. Login with admin credentials (shown above)"
echo
echo "3. Add cluster credentials:"
echo "   # Get dev cluster credentials"
echo "   gcloud container clusters get-credentials mcp-dev-gke --zone=us-central1-a"
echo "   argocd cluster add gke_${PROJECT_ID}_us-central1-a_mcp-dev-gke --name=gcp-dev"
echo
echo "   # Get staging cluster credentials"
echo "   gcloud container clusters get-credentials mcp-staging-cluster --region=us-central1"
echo "   argocd cluster add gke_${PROJECT_ID}_us-central1_mcp-staging-cluster --name=gcp-staging"
echo
echo "   # Get production cluster credentials"
echo "   gcloud container clusters get-credentials mcp-prod-gke --region=us-central1"
echo "   argocd cluster add gke_${PROJECT_ID}_us-central1_mcp-prod-gke --name=gcp-production"
echo
echo "4. Apply application definitions:"
echo "   kubectl apply -f deployments/argocd/gcp-production-app.yaml"
echo "   kubectl apply -f deployments/argocd/gcp-multi-cluster-setup.yaml"
echo
echo "5. Sync applications:"
echo "   argocd app sync mcp-server-production-gke"
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
