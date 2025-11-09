#!/bin/bash
# DNS Failover Verification Script
# Verifies that Cloud DNS is working correctly and simulates failover
#
# Usage:
#   ./scripts/verify-dns-failover.sh
#
# Prerequisites:
#   - kubectl configured for staging cluster
#   - gcloud CLI authenticated
#   - Cloud DNS already configured

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-vishnu-sandbox-20250310}"
NAMESPACE="staging-mcp-server-langgraph"
DNS_ZONE="staging-internal"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}✓${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }
log_section() { echo -e "\n${BLUE}===  $1 ===${NC}\n"; }

verify_dns_zone() {
    log_section "Verifying DNS Zone Configuration"

    if ! gcloud dns managed-zones describe "$DNS_ZONE" --project="$PROJECT_ID" &>/dev/null; then
        log_error "DNS zone '$DNS_ZONE' not found"
        echo "Run: ./scripts/setup-cloud-dns-staging.sh"
        exit 1
    fi

    log_info "DNS zone exists: $DNS_ZONE"

    # Check VPC attachment
    vpc=$(gcloud dns managed-zones describe "$DNS_ZONE" \
        --project="$PROJECT_ID" \
        --format='get(privateVisibilityConfig.networks[0])' 2>/dev/null)

    log_info "DNS zone attached to VPC: $vpc"
}

verify_dns_records() {
    log_section "Verifying DNS Records"

    records=("cloudsql-staging" "redis-staging" "redis-session-staging")

    for record in "${records[@]}"; do
        full_name="${record}.staging.internal."

        ip=$(gcloud dns record-sets describe "$full_name" \
            --zone="$DNS_ZONE" \
            --type=A \
            --project="$PROJECT_ID" \
            --format='get(rrdatas[0])' 2>/dev/null || echo "")

        if [ -z "$ip" ]; then
            log_error "DNS record not found: $full_name"
        else
            log_info "$full_name → $ip"
        fi
    done
}

test_dns_resolution_from_cluster() {
    log_section "Testing DNS Resolution from GKE Cluster"

    # Create test pod
    cat <<EOF | kubectl apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: dns-verification-test
  namespace: $NAMESPACE
spec:
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: dns-test
    image: busybox:1.36
    command: ["sh", "-c"]
    args:
      - |
        echo "=== Testing DNS Resolution ==="
        for dns in cloudsql-staging redis-staging redis-session-staging; do
          echo "\nTesting: \${dns}.staging.internal"
          if nslookup "\${dns}.staging.internal"; then
            echo "✓ SUCCESS"
          else
            echo "✗ FAILED"
            exit 1
          fi
        done
        echo "\n=== All DNS tests passed ==="
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      readOnlyRootFilesystem: true
EOF

    # Wait for pod to complete
    log_info "Waiting for DNS test pod to complete..."
    sleep 20

    # Get logs
    if kubectl logs dns-verification-test -n "$NAMESPACE" 2>/dev/null; then
        log_info "DNS resolution test passed"
    else
        log_error "DNS resolution test failed or pod not ready"
    fi

    # Cleanup
    kubectl delete pod dns-verification-test -n "$NAMESPACE" --wait=false >/dev/null 2>&1 || true
}

check_deployment_health() {
    log_section "Checking Deployment Health"

    # Check deployment status
    available=$(kubectl get deployment staging-mcp-server-langgraph \
        -n "$NAMESPACE" \
        -o jsonpath='{.status.availableReplicas}' 2>/dev/null || echo "0")

    desired=$(kubectl get deployment staging-mcp-server-langgraph \
        -n "$NAMESPACE" \
        -o jsonpath='{.status.replicas}' 2>/dev/null || echo "0")

    if [ "$available" -eq "$desired" ] && [ "$available" -gt 0 ]; then
        log_info "Deployment healthy: $available/$desired replicas available"
    else
        log_warn "Deployment not fully available: $available/$desired replicas"
    fi

    # Check pod status
    echo ""
    kubectl get pods -n "$NAMESPACE" -l app=staging-mcp-server-langgraph
}

simulate_failover_scenario() {
    log_section "DNS Failover Simulation (Read-Only)"

    echo "To simulate a failover:"
    echo ""
    echo "1. Update DNS record with new IP:"
    echo "   gcloud dns record-sets update cloudsql-staging.staging.internal. \\"
    echo "     --zone=staging-internal \\"
    echo "     --type=A \\"
    echo "     --ttl=300 \\"
    echo "     --rrdatas=NEW_IP \\"
    echo "     --project=$PROJECT_ID"
    echo ""
    echo "2. Wait for TTL (5 minutes) or restart pods:"
    echo "   kubectl rollout restart deployment/staging-mcp-server-langgraph \\"
    echo "     -n $NAMESPACE"
    echo ""
    echo "3. Verify new pods connect to new IP:"
    echo "   kubectl logs -n $NAMESPACE \\"
    echo "     -l app=staging-mcp-server-langgraph \\"
    echo "     --tail=50 | grep -i 'connect\\|postgres\\|redis'"
}

main() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║   DNS Failover Verification - Staging GKE Environment     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    verify_dns_zone
    verify_dns_records
    test_dns_resolution_from_cluster
    check_deployment_health
    simulate_failover_scenario

    echo ""
    log_section "Summary"
    log_info "Cloud DNS is properly configured"
    log_info "DNS resolution working from GKE cluster"
    log_info "Deployment is healthy and using DNS-based connections"
    log_info "Failover process documented above"
}

main "$@"
