#!/bin/sh
# ==============================================================================
# OIDC Discovery Endpoint Wait Script
# ==============================================================================
#
# Waits for an OIDC discovery endpoint to become available before starting
# the main application. This addresses the race condition where a service
# health check passes but the OIDC endpoint is not yet ready.
#
# Usage:
#   ./wait-for-oidc.sh <oidc_issuer_url> <command> [args...]
#
# Example:
#   ./wait-for-oidc.sh http://keycloak:8080/realms/default /usr/bin/openfga run
#
# Environment Variables:
#   OIDC_WAIT_MAX_RETRIES - Maximum retry attempts (default: 30)
#   OIDC_WAIT_DELAY       - Initial delay in seconds (default: 2)
#   OIDC_WAIT_MAX_DELAY   - Maximum delay in seconds (default: 10)
#
# ==============================================================================

set -e

# Configuration with defaults
MAX_RETRIES="${OIDC_WAIT_MAX_RETRIES:-30}"
DELAY="${OIDC_WAIT_DELAY:-2}"
MAX_DELAY="${OIDC_WAIT_MAX_DELAY:-10}"

# Parse arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <oidc_issuer_url> <command> [args...]"
    echo "Example: $0 http://keycloak:8080/realms/default /usr/bin/openfga run"
    exit 1
fi

OIDC_ISSUER="$1"
shift

# Construct the OIDC discovery URL
# Remove trailing slash if present, then append /.well-known/openid-configuration
OIDC_DISCOVERY_URL="${OIDC_ISSUER%/}/.well-known/openid-configuration"

echo "============================================================"
echo "Waiting for OIDC Discovery Endpoint"
echo "============================================================"
echo "Issuer: ${OIDC_ISSUER}"
echo "Discovery URL: ${OIDC_DISCOVERY_URL}"
echo "Max retries: ${MAX_RETRIES}"
echo ""

attempt=0
current_delay="${DELAY}"

while [ ${attempt} -lt ${MAX_RETRIES} ]; do
    attempt=$((attempt + 1))

    # Try to fetch the OIDC discovery document
    # We use wget because it's available in Alpine-based images (like OpenFGA)
    # curl might not be available
    if command -v curl >/dev/null 2>&1; then
        response=$(curl -s -o /dev/null -w "%{http_code}" "${OIDC_DISCOVERY_URL}" 2>/dev/null || echo "000")
    elif command -v wget >/dev/null 2>&1; then
        # wget returns 0 on success, non-zero on failure
        if wget -q -O /dev/null "${OIDC_DISCOVERY_URL}" 2>/dev/null; then
            response="200"
        else
            response="000"
        fi
    else
        echo "ERROR: Neither curl nor wget available"
        exit 1
    fi

    if [ "${response}" = "200" ]; then
        echo "  [${attempt}/${MAX_RETRIES}] OIDC discovery endpoint is ready!"
        echo ""
        echo "Starting application: $*"
        echo "============================================================"
        exec "$@"
    fi

    echo "  [${attempt}/${MAX_RETRIES}] HTTP ${response}, retrying in ${current_delay}s..."
    sleep "${current_delay}"

    # Exponential backoff (capped at MAX_DELAY)
    # Shell arithmetic: multiply by 1.5 using integer math (multiply by 3, divide by 2)
    current_delay=$((current_delay * 3 / 2))
    if [ ${current_delay} -gt ${MAX_DELAY} ]; then
        current_delay=${MAX_DELAY}
    fi
done

echo ""
echo "ERROR: OIDC discovery endpoint did not become ready in time"
echo "URL: ${OIDC_DISCOVERY_URL}"
echo "Last response: HTTP ${response}"
exit 1
