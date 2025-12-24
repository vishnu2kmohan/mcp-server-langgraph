#!/usr/bin/env bash
#
# Seed Test Data
#
# Creates test users in Keycloak and authorization tuples in OpenFGA.
# Idempotent - safe to run multiple times.
#
# Usage:
#   ./scripts/seed-test-data.sh
#   DRY_RUN=true ./scripts/seed-test-data.sh  # Show what would be done
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/../../../.."

# Configuration
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:9082}"
KEYCLOAK_ADMIN="${KEYCLOAK_ADMIN:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
KEYCLOAK_REALM="${KEYCLOAK_REALM:-studio}"

OPENFGA_URL="${OPENFGA_URL:-http://localhost:9080}"
OPENFGA_STORE_ID="${OPENFGA_STORE_ID:-}"

DRY_RUN="${DRY_RUN:-false}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Test user definitions
# Format: username:password:email:persona
declare -a TEST_USERS=(
    "admin-user:admin123:admin@test.local:admin"
    "security-admin:security123:security@test.local:admin"
    "auditor-user:auditor123:auditor@test.local:admin"
    "alice-builder:alice123:alice-builder@test.local:developer"
    "alice-analyst:alice123:alice-analyst@test.local:developer"
    "alice-devops:alice123:alice-devops@test.local:developer"
    "compliance-officer:compliance123:compliance@test.local:user"
    "bob-user:bob123:bob@test.local:user"
)

echo ""
echo "=========================================="
echo "  Seeding Test Data"
echo "=========================================="
echo ""

if [[ "$DRY_RUN" == "true" ]]; then
    log_warning "DRY RUN mode - no changes will be made"
fi

# Get Keycloak admin token
log_info "Obtaining Keycloak admin token..."

if [[ "$DRY_RUN" != "true" ]]; then
    ADMIN_TOKEN=$(curl -sf -X POST \
        "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$KEYCLOAK_ADMIN" \
        -d "password=$KEYCLOAK_ADMIN_PASSWORD" \
        -d "grant_type=password" \
        -d "client_id=admin-cli" \
        | jq -r '.access_token' 2>/dev/null) || {
        log_error "Failed to get Keycloak admin token"
        exit 1
    }

    if [[ -z "$ADMIN_TOKEN" || "$ADMIN_TOKEN" == "null" ]]; then
        log_error "Invalid Keycloak admin token"
        exit 1
    fi
    log_success "Got admin token"
else
    log_info "[DRY RUN] Would get admin token"
    ADMIN_TOKEN="dry-run-token"
fi

# Ensure realm exists
log_info "Checking realm '$KEYCLOAK_REALM'..."

if [[ "$DRY_RUN" != "true" ]]; then
    REALM_EXISTS=$(curl -sf -o /dev/null -w "%{http_code}" \
        "$KEYCLOAK_URL/admin/realms/$KEYCLOAK_REALM" \
        -H "Authorization: Bearer $ADMIN_TOKEN")

    if [[ "$REALM_EXISTS" != "200" ]]; then
        log_info "Creating realm '$KEYCLOAK_REALM'..."
        curl -sf -X POST \
            "$KEYCLOAK_URL/admin/realms" \
            -H "Authorization: Bearer $ADMIN_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"realm\": \"$KEYCLOAK_REALM\", \"enabled\": true}" || {
            log_error "Failed to create realm"
            exit 1
        }
        log_success "Created realm '$KEYCLOAK_REALM'"
    else
        log_success "Realm '$KEYCLOAK_REALM' exists"
    fi
fi

# Create test users
log_info "Creating test users..."

for user_spec in "${TEST_USERS[@]}"; do
    IFS=':' read -r username password email persona <<< "$user_spec"

    log_info "  Creating user: $username (persona: $persona)"

    if [[ "$DRY_RUN" != "true" ]]; then
        # Check if user exists
        EXISTING_USERS=$(curl -sf \
            "$KEYCLOAK_URL/admin/realms/$KEYCLOAK_REALM/users?username=$username&exact=true" \
            -H "Authorization: Bearer $ADMIN_TOKEN" \
            | jq -r 'length')

        if [[ "$EXISTING_USERS" -gt 0 ]]; then
            log_success "  User '$username' already exists"
            continue
        fi

        # Create user
        USER_PAYLOAD=$(jq -n \
            --arg username "$username" \
            --arg email "$email" \
            --arg persona "$persona" \
            '{
                username: $username,
                email: $email,
                emailVerified: true,
                enabled: true,
                attributes: {
                    persona: [$persona]
                },
                credentials: [{
                    type: "password",
                    value: "'"$password"'",
                    temporary: false
                }]
            }')

        curl -sf -X POST \
            "$KEYCLOAK_URL/admin/realms/$KEYCLOAK_REALM/users" \
            -H "Authorization: Bearer $ADMIN_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$USER_PAYLOAD" || {
            log_error "  Failed to create user '$username'"
            continue
        }

        log_success "  Created user '$username'"
    else
        log_info "  [DRY RUN] Would create user: $username"
    fi
done

# Seed OpenFGA tuples
log_info "Seeding OpenFGA authorization tuples..."

TUPLES_FILE="$PROJECT_ROOT/config/openfga/sample-tuples.json"
if [[ -f "$TUPLES_FILE" ]]; then
    if [[ "$DRY_RUN" != "true" ]]; then
        # Get store ID if not provided
        if [[ -z "$OPENFGA_STORE_ID" ]]; then
            log_info "  Getting OpenFGA store ID..."
            OPENFGA_STORE_ID=$(curl -sf "$OPENFGA_URL/stores" \
                | jq -r '.stores[0].id // empty') || true

            if [[ -z "$OPENFGA_STORE_ID" ]]; then
                log_warning "  No OpenFGA store found. Skipping tuple seeding."
            else
                log_success "  Found store: $OPENFGA_STORE_ID"
            fi
        fi

        if [[ -n "$OPENFGA_STORE_ID" ]]; then
            # Write tuples from file
            TUPLES=$(jq '.tuples' "$TUPLES_FILE")
            curl -sf -X POST \
                "$OPENFGA_URL/stores/$OPENFGA_STORE_ID/write" \
                -H "Content-Type: application/json" \
                -d "{\"writes\": {\"tuple_keys\": $TUPLES}}" > /dev/null 2>&1 || {
                log_warning "  Some tuples may already exist (expected)"
            }
            log_success "  Seeded authorization tuples"
        fi
    else
        log_info "  [DRY RUN] Would seed tuples from: $TUPLES_FILE"
    fi
else
    log_warning "  Tuples file not found: $TUPLES_FILE"
fi

echo ""
log_success "Test data seeding complete!"
echo ""
