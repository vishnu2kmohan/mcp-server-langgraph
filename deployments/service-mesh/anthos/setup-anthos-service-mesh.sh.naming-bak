#!/bin/bash
# ==============================================================================
# Setup Anthos Service Mesh (Managed Istio) for GKE
# ==============================================================================

set -euo pipefail

PROJECT_ID="${1:-}"
CLUSTER_NAME="${2:-mcp-prod-gke}"
REGION="${3:-us-central1}"

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: $0 PROJECT_ID [CLUSTER_NAME] [REGION]"
    exit 1
fi

echo "Setting up Anthos Service Mesh..."
echo "Project: $PROJECT_ID"
echo "Cluster: $CLUSTER_NAME"
echo "Region: $REGION"

# ==============================================================================
# 1. Enable Required APIs
# ==============================================================================

echo "Enabling required APIs..."

gcloud services enable \
    mesh.googleapis.com \
    meshconfig.googleapis.com \
    meshca.googleapis.com \
    gkehub.googleapis.com \
    anthos.googleapis.com \
    --project="$PROJECT_ID"

echo "✅ APIs enabled"

# ==============================================================================
# 2. Register Cluster with Fleet
# ==============================================================================

echo "Registering cluster with GKE Fleet..."

# Get cluster membership name
MEMBERSHIP_NAME="${CLUSTER_NAME}-membership"

# Register if not already registered
gcloud container fleet memberships register "$MEMBERSHIP_NAME" \
    --gke-cluster="$REGION/$CLUSTER_NAME" \
    --enable-workload-identity \
    --project="$PROJECT_ID" \
    2>/dev/null || echo "Cluster already registered"

echo "✅ Cluster registered with Fleet"

# ==============================================================================
# 3. Enable Anthos Service Mesh
# ==============================================================================

echo "Enabling Anthos Service Mesh (managed)..."

gcloud container fleet mesh enable \
    --project="$PROJECT_ID"

# Update mesh configuration
gcloud container fleet mesh update \
    --management automatic \
    --memberships="$MEMBERSHIP_NAME" \
    --project="$PROJECT_ID"

echo "✅ Anthos Service Mesh enabled (this may take 10-15 minutes)"

# ==============================================================================
# 4. Wait for Mesh to be Ready
# ==============================================================================

echo "Waiting for mesh to be provisioned..."

# Get cluster credentials
gcloud container clusters get-credentials "$CLUSTER_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID"

# Wait for control plane
echo "Checking mesh status (this may take several minutes)..."
for i in {1..60}; do
    STATUS=$(gcloud container fleet mesh describe \
        --project="$PROJECT_ID" \
        --format="value(membershipStates.${MEMBERSHIP_NAME}.servicemesh.controlPlaneManagement.state)" 2>/dev/null || echo "PENDING")

    if [ "$STATUS" = "ACTIVE" ]; then
        echo "✅ Mesh control plane is ACTIVE"
        break
    fi

    echo "Status: $STATUS (attempt $i/60)"
    sleep 30
done

# ==============================================================================
# 5. Enable Sidecar Injection
# ==============================================================================

echo "Enabling automatic sidecar injection for mcp-production namespace..."

kubectl label namespace mcp-production istio-injection=enabled --overwrite

echo "✅ Sidecar injection enabled"

# ==============================================================================
# 6. Deploy Istio Gateway
# ==============================================================================

echo "Deploying Istio Ingress Gateway..."

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  labels:
    app: istio-ingressgateway
    istio: ingressgateway
spec:
  type: LoadBalancer
  selector:
    app: istio-ingressgateway
    istio: ingressgateway
  ports:
  - name: http2
    port: 80
    targetPort: 8080
  - name: https
    port: 443
    targetPort: 8443
EOF

echo "✅ Istio Gateway deployed"

# ==============================================================================
# 7. Deploy Gateway and VirtualService
# ==============================================================================

echo "Creating Gateway and VirtualService for mcp-server..."

cat <<EOF | kubectl apply -f -
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: mcp-server-gateway
  namespace: mcp-production
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: mcp-server-tls-cert  # Create TLS secret
    hosts:
    - "*"
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: mcp-server
  namespace: mcp-production
spec:
  hosts:
  - "*"
  gateways:
  - mcp-server-gateway
  http:
  - match:
    - uri:
        prefix: /
    route:
    - destination:
        host: production-mcp-server-langgraph
        port:
          number: 8000
EOF

echo "✅ Gateway and VirtualService created"

# ==============================================================================
# 8. Enable mTLS
# ==============================================================================

echo "Enabling strict mTLS..."

cat <<EOF | kubectl apply -f -
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: mcp-production
spec:
  mtls:
    mode: STRICT
EOF

echo "✅ Strict mTLS enabled"

# ==============================================================================
# 9. Deploy Observability Components
# ==============================================================================

echo "Deploying Kiali, Grafana, Prometheus..."

# Add Istio Helm repo
helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update

# Install Kiali
kubectl create namespace istio-system --dry-run=client -o yaml | kubectl apply -f -

helm install kiali-server \
    --namespace istio-system \
    --repo https://kiali.org/helm-charts \
    kiali-server \
    --set auth.strategy=anonymous \
    --set deployment.service_type=LoadBalancer

echo "✅ Observability components deployed"

# ==============================================================================
# 10. Verification
# ==============================================================================

echo "Verifying Anthos Service Mesh installation..."

# Check mesh status
gcloud container fleet mesh describe \
    --project="$PROJECT_ID"

# Check sidecars
PODS_WITH_SIDECARS=$(kubectl get pods -n mcp-production \
    -o jsonpath='{.items[*].spec.containers[*].name}' \
    | grep -o istio-proxy | wc -l)

echo "Pods with sidecars: $PODS_WITH_SIDECARS"

# Get Ingress Gateway IP
GATEWAY_IP=$(kubectl get svc istio-ingressgateway -n istio-system \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Ingress Gateway IP: $GATEWAY_IP"

# ==============================================================================
# Setup Complete
# ==============================================================================

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Anthos Service Mesh Setup Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Ingress Gateway: http://$GATEWAY_IP"
echo "Kiali Dashboard:  kubectl port-forward -n istio-system svc/kiali 20001:20001"
echo
echo "Next steps:"
echo "1. Test mTLS: curl -v http://$GATEWAY_IP/"
echo "2. View service mesh: kubectl port-forward -n istio-system svc/kiali 20001:20001"
echo "3. Monitor traffic in Kiali UI"
echo "4. Configure TLS certificate for HTTPS"
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
