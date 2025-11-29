#!/bin/bash
# Test runner for agentic loop components
# Ensures proper environment and runs all relevant tests

set -e

echo "========================================="
echo "Agentic Loop Test Suite"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
# RED reserved for future error messaging
# shellcheck disable=SC2034
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${YELLOW}Warning: Not in a virtual environment${NC}"
    echo "Running: uv sync"
    uv sync
    echo ""
fi

echo -e "${GREEN}Running Context Manager Tests...${NC}"
uv run --frozen pytest tests/test_context_manager.py -v --tb=short -m unit
echo ""

echo -e "${GREEN}Running Verifier Tests...${NC}"
uv run --frozen pytest tests/test_verifier.py -v --tb=short -m unit
echo ""

echo -e "${GREEN}Running Agentic Loop Integration Tests...${NC}"
uv run --frozen pytest tests/test_agentic_loop_integration.py -v --tb=short -m integration
echo ""

echo -e "${GREEN}Running All New Tests with Coverage...${NC}"
uv run --frozen pytest \
    tests/test_context_manager.py \
    tests/test_verifier.py \
    tests/test_agentic_loop_integration.py \
    --cov=src/mcp_server_langgraph/core/context_manager \
    --cov=src/mcp_server_langgraph/llm/verifier \
    --cov=src/mcp_server_langgraph/prompts \
    --cov-report=term-missing \
    --cov-report=html
echo ""

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}All Agentic Loop Tests Passed!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Coverage report generated: htmlcov/index.html"
echo ""
echo "To run tests individually:"
echo "  pytest tests/test_context_manager.py -v"
echo "  pytest tests/test_verifier.py -v"
echo "  pytest tests/test_agentic_loop_integration.py -v"
