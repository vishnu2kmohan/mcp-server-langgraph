#!/bin/bash
# ==============================================================================
# Keycloak Two-Phase OIDC-Ready Healthcheck
# ==============================================================================
#
# This script performs a two-phase healthcheck to ensure Keycloak is fully
# ready to serve OIDC requests, not just that the JVM has started.
#
# Phase 1: /health/ready on management port 9000
#   - Validates JVM is running and database is connected
#   - Fast check that catches early startup failures
#
# Phase 2: OIDC discovery endpoint on HTTP port 8080
#   - Validates the default realm is available
#   - Ensures OIDC-dependent services (OpenFGA, traefik-forward-auth)
#     can obtain valid configuration
#
# Reference:
# - https://www.keycloak.org/observability/health
# - https://www.keycloak.org/server/containers
#
# IMPORTANT: KC_HTTP_RELATIVE_PATH applies to ALL endpoints including health
# Default path prefix: /authn (can be overridden via KC_PATH_PREFIX env var)
#
# Usage:
#   ./healthcheck.sh                    # Default: uses /authn prefix
#   KC_PATH_PREFIX=/auth ./healthcheck.sh  # Custom prefix
#   SKIP_OIDC_CHECK=true ./healthcheck.sh  # Phase 1 only (faster)
#
# ==============================================================================

set -euo pipefail

# Configuration
PATH_PREFIX="${KC_PATH_PREFIX:-/authn}"
REALM="${KC_REALM:-default}"
MANAGEMENT_PORT="${KC_MANAGEMENT_PORT:-9000}"
HTTP_PORT="${KC_HTTP_PORT:-8080}"
SKIP_OIDC_CHECK="${SKIP_OIDC_CHECK:-false}"

# Logging helper
log() {
    if [ "${HEALTHCHECK_VERBOSE:-false}" = "true" ]; then
        echo "[healthcheck] $1" >&2
    fi
}

# HTTP request using bash TCP socket pattern
# Keycloak 26+ images don't have curl/wget
# Usage: http_check <host> <port> <method> <path> <expected_pattern>
http_check() {
    local host="$1"
    local port="$2"
    local method="$3"
    local path="$4"
    local pattern="$5"

    # Open bidirectional TCP socket, send request, grep for pattern
    # The 0<>/dev/tcp/host/port redirects both stdin and stdout to the socket
    {
        printf '%s %s HTTP/1.0\r\nHost: %s\r\nConnection: close\r\n\r\n' \
            "$method" "$path" "$host" >&0
        grep -q "$pattern"
    } 0<>/dev/tcp/"$host"/"$port"
}

# ==============================================================================
# Phase 1: Management Health Endpoint
# ==============================================================================
log "Phase 1: Checking ${PATH_PREFIX}/health/ready on port ${MANAGEMENT_PORT}..."

if ! http_check "localhost" "$MANAGEMENT_PORT" "HEAD" "${PATH_PREFIX}/health/ready" "HTTP/1.. 200"; then
    log "FAILED: Management health endpoint not ready"
    exit 1
fi

log "Phase 1: PASSED - Management health endpoint ready"

# ==============================================================================
# Phase 2: OIDC Discovery Endpoint (optional)
# ==============================================================================
if [ "$SKIP_OIDC_CHECK" = "true" ]; then
    log "Phase 2: SKIPPED (SKIP_OIDC_CHECK=true)"
    exit 0
fi

OIDC_PATH="${PATH_PREFIX}/realms/${REALM}/.well-known/openid-configuration"
log "Phase 2: Checking OIDC discovery at ${OIDC_PATH} on port ${HTTP_PORT}..."

if ! http_check "localhost" "$HTTP_PORT" "GET" "$OIDC_PATH" '"issuer"'; then
    log "FAILED: OIDC discovery endpoint not ready"
    exit 1
fi

log "Phase 2: PASSED - OIDC discovery endpoint ready"
log "Healthcheck complete: Keycloak is OIDC-ready"

exit 0
