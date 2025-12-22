#!/bin/bash
# Switch LLM provider when primary is throttled/unavailable
#
# Usage: ./switch-llm-provider.sh <target-provider> [namespace]
#
# Reference: ADR-0026 - Comprehensive Client Resilience Patterns

set -euo pipefail

TARGET_PROVIDER="${1:-}"
NAMESPACE="${2:-default}"
DRY_RUN="${DRY_RUN:-false}"
MCP_DEPLOYMENT="${MCP_DEPLOYMENT:-mcp-server-langgraph}"
CONFIGMAP_NAME="${CONFIGMAP_NAME:-mcp-server-langgraph-config}"
COOLDOWN_FILE="/tmp/llm-switch-cooldown"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-600}"  # 10 minute cooldown for provider switches

# Valid providers
VALID_PROVIDERS="openai anthropic google azure ollama"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
    fi
}

# Validate input
if [[ -z "$TARGET_PROVIDER" ]]; then
    log_error "Usage: $0 <target-provider> [namespace]"
    log_error "  target-provider: $VALID_PROVIDERS"
    log_error "  namespace: Kubernetes namespace (default: default)"
    exit 1
fi

# Validate provider
if ! echo "$VALID_PROVIDERS" | grep -qw "$TARGET_PROVIDER"; then
    log_error "Invalid provider: $TARGET_PROVIDER"
    log_error "Valid providers: $VALID_PROVIDERS"
    exit 1
fi

# Check cooldown
if [[ -f "$COOLDOWN_FILE" ]]; then
    LAST_RUN=$(cat "$COOLDOWN_FILE")
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - LAST_RUN))

    if [[ $ELAPSED -lt $COOLDOWN_SECONDS ]]; then
        REMAINING=$((COOLDOWN_SECONDS - ELAPSED))
        log_warn "Cooldown active for LLM provider switch. ${REMAINING}s remaining. Skipping."
        exit 0
    fi
fi

log_info "Starting LLM provider switch to: $TARGET_PROVIDER"

# Check if deployment exists
if ! kubectl get deployment "$MCP_DEPLOYMENT" -n "$NAMESPACE" &>/dev/null; then
    log_error "Deployment $MCP_DEPLOYMENT not found in namespace $NAMESPACE"
    exit 1
fi

# Check for skip annotation
SKIP_ANNOTATION=$(kubectl get deployment "$MCP_DEPLOYMENT" -n "$NAMESPACE" \
    -o jsonpath='{.metadata.annotations.remediation\.llm-switch\.skip}' 2>/dev/null || echo "")

if [[ "$SKIP_ANNOTATION" == "true" ]]; then
    log_warn "LLM switch skip annotation found. Skipping."
    exit 0
fi

# Get current provider from environment
CURRENT_PROVIDER=$(kubectl get deployment "$MCP_DEPLOYMENT" -n "$NAMESPACE" \
    -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="LLM_PROVIDER")].value}' 2>/dev/null || echo "unknown")

log_info "Current LLM provider: $CURRENT_PROVIDER"

if [[ "$CURRENT_PROVIDER" == "$TARGET_PROVIDER" ]]; then
    log_info "Already using $TARGET_PROVIDER. No action needed."
    exit 0
fi

# Provider-specific validation
case "$TARGET_PROVIDER" in
    openai)
        SECRET_KEY="OPENAI_API_KEY"
        ;;
    anthropic)
        SECRET_KEY="ANTHROPIC_API_KEY"
        ;;
    google)
        SECRET_KEY="GOOGLE_API_KEY"
        ;;
    azure)
        SECRET_KEY="AZURE_OPENAI_API_KEY"
        ;;
    ollama)
        SECRET_KEY=""  # Ollama doesn't require API key
        ;;
esac

# Check if target provider has credentials (for non-ollama)
if [[ -n "$SECRET_KEY" ]]; then
    HAS_SECRET=$(kubectl get deployment "$MCP_DEPLOYMENT" -n "$NAMESPACE" \
        -o jsonpath="{.spec.template.spec.containers[0].env[?(@.name==\"$SECRET_KEY\")].value}" 2>/dev/null || echo "")

    # Also check secretKeyRef
    HAS_SECRET_REF=$(kubectl get deployment "$MCP_DEPLOYMENT" -n "$NAMESPACE" \
        -o jsonpath="{.spec.template.spec.containers[0].env[?(@.name==\"$SECRET_KEY\")].valueFrom.secretKeyRef.name}" 2>/dev/null || echo "")

    if [[ -z "$HAS_SECRET" ]] && [[ -z "$HAS_SECRET_REF" ]]; then
        log_warn "No $SECRET_KEY found for $TARGET_PROVIDER"
        log_warn "Ensure credentials are configured before switching"
    fi
fi

# Perform the switch
log_info "Switching LLM provider from $CURRENT_PROVIDER to $TARGET_PROVIDER"

if [[ "$DRY_RUN" == "true" ]]; then
    log_warn "[DRY RUN] Would execute: kubectl set env deployment/$MCP_DEPLOYMENT LLM_PROVIDER=$TARGET_PROVIDER -n $NAMESPACE"
else
    # Update environment variable
    kubectl set env deployment/"$MCP_DEPLOYMENT" "LLM_PROVIDER=$TARGET_PROVIDER" -n "$NAMESPACE"

    # Wait for rollout
    log_info "Waiting for rollout to complete..."
    kubectl rollout status deployment "$MCP_DEPLOYMENT" -n "$NAMESPACE" --timeout=300s

    # Update cooldown file
    date +%s > "$COOLDOWN_FILE"

    # Create Kubernetes event
    kubectl create event \
        --type=Normal \
        --reason=ResilienceRemediation \
        --message="Switched LLM provider from $CURRENT_PROVIDER to $TARGET_PROVIDER due to provider throttling" \
        --for="deployment/$MCP_DEPLOYMENT" \
        -n "$NAMESPACE" 2>/dev/null || true

    # Verify new provider
    NEW_PROVIDER=$(kubectl get deployment "$MCP_DEPLOYMENT" -n "$NAMESPACE" \
        -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="LLM_PROVIDER")].value}' 2>/dev/null || echo "unknown")
    log_info "New LLM provider: $NEW_PROVIDER"

    # Alert on-call (if webhook configured)
    ONCALL_WEBHOOK="${ONCALL_WEBHOOK:-}"
    if [[ -n "$ONCALL_WEBHOOK" ]]; then
        log_info "Notifying on-call via webhook..."
        curl -s -X POST "$ONCALL_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"LLM provider switched from $CURRENT_PROVIDER to $TARGET_PROVIDER in $NAMESPACE namespace due to provider throttling\"}" || true
    fi
fi

log_info "LLM provider switch complete: $CURRENT_PROVIDER -> $TARGET_PROVIDER"
