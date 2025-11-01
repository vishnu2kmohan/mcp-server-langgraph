#!/bin/bash
set -e

# LangGraph Platform Deployment Script
# Deploys the agent to LangGraph Cloud using the LangChain CLI

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-mcp-server-langgraph}"
ENVIRONMENT="${ENVIRONMENT:-staging}"  # staging or production

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

check_prerequisites() {
    print_step "Checking prerequisites..."

    # Check if langgraph CLI is installed
    if ! command -v langgraph &> /dev/null; then
        print_error "langgraph CLI not found. Install with: uv tool install langgraph-cli"
        exit 1
    fi

    # Check if langsmith CLI is installed
    if ! command -v langsmith &> /dev/null; then
        print_warn "langsmith CLI not found. Install with: uv tool install langsmith"
        print_info "LangSmith CLI is optional but recommended for monitoring"
    fi

    # Check if logged in
    if ! langgraph whoami &> /dev/null; then
        print_error "Not logged in to LangChain. Run: langgraph login"
        exit 1
    fi

    print_info "Prerequisites check passed"
}

validate_config() {
    print_step "Validating configuration..."

    # Check if langgraph.json exists
    if [ ! -f "langgraph.json" ]; then
        print_error "langgraph.json not found in current directory"
        exit 1
    fi

    # Check if environment file exists
    ENV_FILE=".env.${ENVIRONMENT}"
    if [ ! -f "$ENV_FILE" ]; then
        print_warn "Environment file $ENV_FILE not found, using .env"
        ENV_FILE=".env"
    fi

    if [ -f "$ENV_FILE" ]; then
        print_info "Using environment file: $ENV_FILE"
        # Load environment variables
        export $(cat $ENV_FILE | grep -v '^#' | xargs)
    else
        print_warn "No environment file found, using system environment variables"
    fi

    print_info "Configuration validated"
}

test_locally() {
    print_step "Testing graph locally (optional)..."

    read -p "Test graph locally before deploying? (y/n): " test_local
    if [[ "$test_local" == "y" ]]; then
        print_info "Starting local server for testing..."
        print_info "Press Ctrl+C to stop and continue with deployment"

        # Start local server (will be interrupted by user)
        langgraph dev || true
    fi
}

deploy() {
    print_step "Deploying to LangGraph Platform..."

    # Build deployment command
    DEPLOY_CMD="langgraph deploy"

    # Add deployment name if specified
    if [ -n "$DEPLOYMENT_NAME" ]; then
        DEPLOY_CMD="$DEPLOY_CMD $DEPLOYMENT_NAME"
    fi

    # Add environment tag
    DEPLOY_CMD="$DEPLOY_CMD --tag $ENVIRONMENT"

    print_info "Running: $DEPLOY_CMD"

    # Execute deployment
    if $DEPLOY_CMD; then
        print_info "✓ Deployment successful!"
    else
        print_error "Deployment failed"
        exit 1
    fi
}

get_deployment_info() {
    print_step "Fetching deployment information..."

    # Get deployment URL
    DEPLOYMENT_URL=$(langgraph deployment get $DEPLOYMENT_NAME --json 2>/dev/null | grep -o '"url":"[^"]*"' | cut -d'"' -f4)

    if [ -n "$DEPLOYMENT_URL" ]; then
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo -e "${GREEN}✓ Deployment Complete!${NC}"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
        echo "Deployment Name: $DEPLOYMENT_NAME"
        echo "Environment: $ENVIRONMENT"
        echo "Deployment URL: $DEPLOYMENT_URL"
        echo ""
        echo "View deployment:"
        echo "  langgraph deployment get $DEPLOYMENT_NAME"
        echo ""
        echo "Stream logs:"
        echo "  langgraph deployment logs $DEPLOYMENT_NAME"
        echo ""
        echo "Test your deployment:"
        echo "  langgraph deployment invoke $DEPLOYMENT_NAME"
        echo ""
        echo "Update deployment:"
        echo "  langgraph deploy $DEPLOYMENT_NAME"
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
    else
        print_warn "Could not fetch deployment URL"
        print_info "Check deployment status with: langgraph deployment get $DEPLOYMENT_NAME"
    fi
}

# Main deployment flow
main() {
    echo "═══════════════════════════════════════════════════════════════"
    echo "  LangGraph Platform Deployment"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    check_prerequisites
    validate_config

    # Optional local testing
    if [[ "$1" != "--skip-test" ]]; then
        test_locally
    fi

    deploy
    get_deployment_info

    echo ""
    print_info "🎉 Deployment workflow complete!"
}

# Run main function
main "$@"
