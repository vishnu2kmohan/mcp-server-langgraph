#!/bin/bash
set -e

# Docker Compose Quick Start Script for MCP Server with LangGraph
# This script helps you get started with local development using Docker Compose

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "================================================"
echo "MCP Server with LangGraph - Docker Compose Quick Start"
echo "================================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose installed${NC}"

# Check if .env file exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${YELLOW}⚠ .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo -e "${GREEN}✓ .env file created${NC}"
    echo ""
    echo -e "${YELLOW}IMPORTANT: Edit .env and add your API keys:${NC}"
    echo "  - GOOGLE_API_KEY (for Google Gemini)"
    echo "  - ANTHROPIC_API_KEY (for Claude)"
    echo "  - OPENAI_API_KEY (for GPT)"
    echo ""
    read -p "Press Enter after you've added your API keys to .env..."
fi

# Validate required environment variables
echo ""
echo "Validating environment variables..."

source "$PROJECT_ROOT/.env"

# Check for at least one LLM API key
if [ -z "$GOOGLE_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}❌ No LLM API key found in .env${NC}"
    echo "Please add at least one of:"
    echo "  - GOOGLE_API_KEY"
    echo "  - ANTHROPIC_API_KEY"
    echo "  - OPENAI_API_KEY"
    exit 1
fi

echo -e "${GREEN}✓ Environment variables validated${NC}"

# Ask user which mode to run
echo ""
echo "Select deployment mode:"
echo "  1) Development (hot reload, debug logging)"
echo "  2) Production-like (optimized build)"
echo ""
read -p "Enter choice [1-2]: " mode_choice

cd "$PROJECT_ROOT"

if [ "$mode_choice" = "1" ]; then
    echo ""
    echo "Starting in DEVELOPMENT mode..."
    echo "  - Hot reload enabled"
    echo "  - Debug logging"
    echo "  - Code mounted as volumes"
    echo ""

    COMPOSE_FILES="-f docker-compose.yml -f docker/docker-compose.dev.yml"
else
    echo ""
    echo "Starting in PRODUCTION-LIKE mode..."
    echo "  - Optimized build"
    echo "  - Production logging"
    echo ""

    COMPOSE_FILES="-f docker-compose.yml"
fi

# Build and start services
echo ""
echo "Building and starting services..."
echo "This may take a few minutes on first run..."
echo ""

docker compose $COMPOSE_FILES up -d --build

# Wait for services to be healthy
echo ""
echo "Waiting for services to be healthy..."
echo ""

# Wait for agent to be healthy (max 60 seconds)
for i in {1..60}; do
    if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Agent service is healthy${NC}"
        break
    fi

    if [ $i -eq 60 ]; then
        echo -e "${RED}❌ Agent service failed to start${NC}"
        echo "Check logs with: docker compose $COMPOSE_FILES logs agent"
        exit 1
    fi

    echo -n "."
    sleep 1
done

echo ""
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✓ MCP Server with LangGraph is running!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Service URLs:"
echo "  🤖 Agent API:          http://localhost:8000"
echo "  🛡️  OpenFGA API:        http://localhost:8080"
echo "  🔍 Jaeger UI:          http://localhost:16686"
echo "  📈 Prometheus:         http://localhost:9090"
echo "  📊 Grafana:            http://localhost:3001 (admin/admin)"
echo ""
echo "Health check:"
echo "  curl http://localhost:8000/health"
echo ""
echo "Test the agent:"
echo "  curl -X POST http://localhost:8000/message \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}]}'"
echo ""
echo "View logs:"
echo "  docker compose $COMPOSE_FILES logs -f agent"
echo ""
echo "Stop services:"
echo "  docker compose $COMPOSE_FILES down"
echo ""
echo "Next steps:"
echo "  1. Setup OpenFGA: python scripts/setup/setup_openfga.py"
echo "  2. Test the agent with your favorite MCP client"
echo "  3. View traces in Jaeger (http://localhost:16686)"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
