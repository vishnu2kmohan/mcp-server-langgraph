#!/usr/bin/env bash
#
# Smart Wait Utility for Docker Compose Services
# ===============================================
#
# Replaces hardcoded sleep commands with intelligent health check polling.
# Waits for Docker Compose services to become healthy before proceeding.
#
# USAGE:
#   scripts/utils/wait_for_services.sh [compose-file] [service1] [service2] ...
#
# EXAMPLES:
#   # Wait for all services in docker-compose.test.yml
#   scripts/utils/wait_for_services.sh docker-compose.test.yml
#
#   # Wait for specific services only
#   scripts/utils/wait_for_services.sh docker-compose.test.yml postgres-test redis-checkpoints-test
#
#   # Use with Makefile
#   $(MAKE) test-infra-up && scripts/utils/wait_for_services.sh docker-compose.test.yml
#
# BENEFITS:
#   - Eliminates race conditions from hardcoded sleep durations
#   - Fails fast if services don't become healthy
#   - Adapts to different CI/local environments automatically
#   - Provides clear progress feedback
#
# EXIT CODES:
#   0  - All services healthy
#   1  - Invalid arguments
#   2  - Service failed to become healthy
#   3  - docker compose command not available

set -euo pipefail

# Configuration
readonly MAX_WAIT_SECONDS=120
readonly POLL_INTERVAL=2
SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME

# Colors for output
readonly COLOR_RESET="\033[0m"
readonly COLOR_GREEN="\033[0;32m"
readonly COLOR_YELLOW="\033[0;33m"
readonly COLOR_RED="\033[0;31m"
readonly COLOR_BLUE="\033[0;34m"

# Usage information
usage() {
    cat <<EOF
${COLOR_BLUE}Smart Wait Utility for Docker Compose Services${COLOR_RESET}

USAGE:
    $SCRIPT_NAME [compose-file] [service1] [service2] ...

ARGUMENTS:
    compose-file    Path to docker-compose file (e.g., docker-compose.test.yml)
    service(s)      Optional: Specific services to wait for (default: all services with healthchecks)

EXAMPLES:
    # Wait for all services
    $SCRIPT_NAME docker-compose.test.yml

    # Wait for specific services
    $SCRIPT_NAME docker-compose.test.yml postgres-test redis-checkpoints-test

    # Use with Makefile
    make test-infra-up && $SCRIPT_NAME docker-compose.test.yml

EXIT CODES:
    0  - All services healthy
    1  - Invalid arguments
    2  - Service failed to become healthy within timeout
    3  - docker compose command not available

EOF
}

# Logging functions
log_info() {
    echo -e "${COLOR_BLUE}ℹ${COLOR_RESET} $*"
}

log_success() {
    echo -e "${COLOR_GREEN}✓${COLOR_RESET} $*"
}

log_warning() {
    echo -e "${COLOR_YELLOW}⚠${COLOR_RESET} $*"
}

log_error() {
    echo -e "${COLOR_RED}✗${COLOR_RESET} $*" >&2
}

# Check if docker compose is available
check_docker_compose() {
    if ! command -v docker >/dev/null 2>&1; then
        log_error "docker command not found"
        return 3
    fi

    # Try docker compose (v2 syntax)
    if docker compose version >/dev/null 2>&1; then
        echo "docker compose"
        return 0
    fi

    # Try docker-compose (v1 syntax)
    if command -v docker-compose >/dev/null 2>&1; then
        echo "docker-compose"
        return 0
    fi

    log_error "Neither 'docker compose' nor 'docker-compose' is available"
    return 3
}

# Get list of services with healthchecks from compose file
get_services_with_healthchecks() {
    local compose_file="$1"
    local docker_compose_cmd="$2"

    # Use docker compose config to get parsed YAML, then extract services with healthchecks
    # This works even if services don't have explicit healthcheck sections
    $docker_compose_cmd -f "$compose_file" config --services 2>/dev/null || {
        log_error "Failed to read services from $compose_file"
        return 1
    }
}

# Check if a service is healthy
check_service_health() {
    local compose_file="$1"
    local service="$2"
    local docker_compose_cmd="$3"

    # Get container status using docker compose ps
    # Returns: "running (healthy)", "running (unhealthy)", "running (starting)", etc.
    local status
    status=$($docker_compose_cmd -f "$compose_file" ps --format json "$service" 2>/dev/null | \
             jq -r '.[0].Health // .[0].State' 2>/dev/null || echo "unknown")

    case "$status" in
        "healthy"|"running")
            return 0  # Healthy
            ;;
        "starting"|"unhealthy")
            return 1  # Not yet healthy
            ;;
        *)
            return 2  # Unknown/error state
            ;;
    esac
}

# Wait for a single service to become healthy
wait_for_service() {
    local compose_file="$1"
    local service="$2"
    local docker_compose_cmd="$3"

    local elapsed=0
    local status

    log_info "Waiting for ${COLOR_YELLOW}${service}${COLOR_RESET} to become healthy..."

    while [ $elapsed -lt $MAX_WAIT_SECONDS ]; do
        if check_service_health "$compose_file" "$service" "$docker_compose_cmd"; then
            log_success "${service} is healthy (${elapsed}s)"
            return 0
        fi

        sleep $POLL_INTERVAL
        elapsed=$((elapsed + POLL_INTERVAL))

        # Show progress every 10 seconds
        if [ $((elapsed % 10)) -eq 0 ]; then
            log_info "${service} not yet healthy (${elapsed}s / ${MAX_WAIT_SECONDS}s)..."
        fi
    done

    log_error "${service} failed to become healthy within ${MAX_WAIT_SECONDS}s"

    # Show service logs for debugging
    log_info "Last 20 lines of ${service} logs:"
    $docker_compose_cmd -f "$compose_file" logs --tail=20 "$service" 2>&1 || true

    return 2
}

# Main function
main() {
    # Check arguments
    if [ $# -lt 1 ]; then
        usage
        exit 1
    fi

    local compose_file="$1"
    shift

    # Check if compose file exists
    if [ ! -f "$compose_file" ]; then
        log_error "Compose file not found: $compose_file"
        exit 1
    fi

    # Check docker compose availability
    local docker_compose_cmd
    docker_compose_cmd=$(check_docker_compose) || exit $?

    log_info "Using: $docker_compose_cmd"
    log_info "Compose file: $compose_file"

    # Determine which services to wait for
    local services=()
    if [ $# -eq 0 ]; then
        # No specific services provided - get all services
        log_info "No specific services specified - waiting for all services with healthchecks"
        mapfile -t services < <(get_services_with_healthchecks "$compose_file" "$docker_compose_cmd")
    else
        # Use provided services
        services=("$@")
    fi

    if [ ${#services[@]} -eq 0 ]; then
        log_warning "No services found to wait for"
        exit 0
    fi

    log_info "Waiting for ${#services[@]} service(s): ${services[*]}"
    echo ""

    # Wait for each service
    local failed_services=()
    for service in "${services[@]}"; do
        if ! wait_for_service "$compose_file" "$service" "$docker_compose_cmd"; then
            failed_services+=("$service")
        fi
    done

    echo ""

    # Report results
    if [ ${#failed_services[@]} -eq 0 ]; then
        log_success "All ${#services[@]} service(s) are healthy!"
        return 0
    else
        log_error "${#failed_services[@]} service(s) failed to become healthy:"
        for service in "${failed_services[@]}"; do
            log_error "  - $service"
        done
        return 2
    fi
}

# Run main function
main "$@"
