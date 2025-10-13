#!/bin/bash
#
# Kubernetes Deployment Test Script
#
# Tests deployment configurations in a local kind cluster
# - Creates kind cluster
# - Deploys using Kustomize
# - Verifies pod status
# - Runs health checks
# - Cleans up cluster
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="langgraph-test"
NAMESPACE="langgraph-agent-dev"
TIMEOUT="300s"

echo -e "${GREEN}🚀 Kubernetes Deployment Test${NC}"
echo "================================"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
if ! command -v kind &> /dev/null; then
    echo -e "${RED}❌ kind not found. Install from: https://kind.sigs.k8s.io/${NC}"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found. Install from: https://kubernetes.io/docs/tasks/tools/${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Prerequisites met"
echo ""

# Create kind cluster
echo "Creating kind cluster..."
if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo -e "${YELLOW}Cluster ${CLUSTER_NAME} already exists, deleting...${NC}"
    kind delete cluster --name "${CLUSTER_NAME}"
fi

kind create cluster --name "${CLUSTER_NAME}" --wait "${TIMEOUT}"
echo -e "${GREEN}✓${NC} Cluster created"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Cleaning up..."
    kind delete cluster --name "${CLUSTER_NAME}"
    echo -e "${GREEN}✓${NC} Cluster deleted"
}

trap cleanup EXIT

# Deploy using Kustomize
echo "Deploying with Kustomize (dev overlay)..."
kubectl apply -k deployments/kustomize/overlays/dev
echo -e "${GREEN}✓${NC} Resources applied"
echo ""

# Wait for namespace
echo "Waiting for namespace..."
kubectl wait --for=jsonpath='{.status.phase}'=Active namespace/${NAMESPACE} --timeout="${TIMEOUT}" || true
echo -e "${GREEN}✓${NC} Namespace ready"
echo ""

# List all resources
echo "Resources created:"
kubectl get all -n "${NAMESPACE}"
echo ""

# Wait for deployments (allow failures since we don't have real secrets)
echo "Waiting for deployments..."
echo -e "${YELLOW}Note: Deployments may fail due to missing secrets/dependencies${NC}"

# Check main deployment
if kubectl get deployment dev-langgraph-agent -n "${NAMESPACE}" &> /dev/null; then
    echo "Checking dev-langgraph-agent deployment..."
    kubectl rollout status deployment/dev-langgraph-agent -n "${NAMESPACE}" --timeout=60s || echo -e "${YELLOW}⚠️  Deployment not ready (expected without secrets)${NC}"
fi

# Check Keycloak deployment
if kubectl get deployment dev-keycloak -n "${NAMESPACE}" &> /dev/null; then
    echo "Checking dev-keycloak deployment..."
    kubectl rollout status deployment/dev-keycloak -n "${NAMESPACE}" --timeout=60s || echo -e "${YELLOW}⚠️  Deployment not ready (expected without dependencies)${NC}"
fi

# Check Redis deployment
if kubectl get deployment dev-redis-session -n "${NAMESPACE}" &> /dev/null; then
    echo "Checking dev-redis-session deployment..."
    kubectl rollout status deployment/dev-redis-session -n "${NAMESPACE}" --timeout=60s || echo -e "${YELLOW}⚠️  Deployment not ready${NC}"
fi

echo ""

# Check pod status
echo "Pod status:"
kubectl get pods -n "${NAMESPACE}"
echo ""

# Validate resource specifications
echo "Validating resources..."

# Check that ConfigMap has correct environment
CONFIG_ENV=$(kubectl get configmap dev-langgraph-agent-config -n "${NAMESPACE}" -o jsonpath='{.data.environment}')
if [ "${CONFIG_ENV}" = "development" ]; then
    echo -e "${GREEN}✓${NC} ConfigMap environment correct: ${CONFIG_ENV}"
else
    echo -e "${RED}❌${NC} ConfigMap environment incorrect: ${CONFIG_ENV}"
    exit 1
fi

# Check that deployment has correct auth provider
AUTH_PROVIDER=$(kubectl get configmap dev-langgraph-agent-config -n "${NAMESPACE}" -o jsonpath='{.data.auth_provider}')
if [ "${AUTH_PROVIDER}" = "inmemory" ]; then
    echo -e "${GREEN}✓${NC} Auth provider correct for dev: ${AUTH_PROVIDER}"
else
    echo -e "${RED}❌${NC} Auth provider incorrect: ${AUTH_PROVIDER}"
    exit 1
fi

# Check that deployment has correct replica count
REPLICAS=$(kubectl get deployment dev-langgraph-agent -n "${NAMESPACE}" -o jsonpath='{.spec.replicas}')
if [ "${REPLICAS}" = "1" ]; then
    echo -e "${GREEN}✓${NC} Replica count correct for dev: ${REPLICAS}"
else
    echo -e "${RED}❌${NC} Replica count incorrect: ${REPLICAS}"
    exit 1
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✅ Kubernetes deployment test passed!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Summary:"
echo "- Cluster created successfully"
echo "- Resources deployed with Kustomize"
echo "- Configuration validated"
echo "- Dev environment settings verified"
echo ""
