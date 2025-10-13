#!/bin/bash
# Monthly dependency audit script for MCP Server with LangGraph
#
# Purpose: Comprehensive dependency health check
# Usage: ./scripts/dependency-audit.sh
# Schedule: First Monday of every month

set -euo pipefail

# Activate virtual environment if available
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Report file
REPORT_FILE="dependency-audit-$(date +%Y%m%d).txt"

# Print header
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Dependency Audit Report${NC}"
    echo -e "${BLUE}  Date: $(date)${NC}"
    echo -e "${BLUE}  Project: MCP Server with LangGraph${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Check if required tools are installed
check_requirements() {
    echo -e "${BLUE}=== Checking Required Tools ===${NC}"

    local missing_tools=()

    if ! command -v pip &> /dev/null; then
        missing_tools+=("pip")
    fi

    if ! command -v jq &> /dev/null; then
        missing_tools+=("jq")
    fi

    if [ ${#missing_tools[@]} -gt 0 ]; then
        echo -e "${RED}ERROR: Missing required tools: ${missing_tools[*]}${NC}"
        echo "Install missing tools and try again."
        exit 1
    fi

    echo -e "${GREEN}✓ All required tools installed${NC}"
    echo ""
}

# Install audit tools if needed
install_audit_tools() {
    echo -e "${BLUE}=== Installing Audit Tools ===${NC}"

    # Check if pip-audit is installed
    if ! pip show pip-audit &> /dev/null; then
        echo "Installing pip-audit..."
        uv pip install pip-audit
    else
        echo -e "${GREEN}✓ pip-audit already installed${NC}"
    fi

    # Check if pip-licenses is installed
    if ! pip show pip-licenses &> /dev/null; then
        echo "Installing pip-licenses..."
        uv pip install pip-licenses
    else
        echo -e "${GREEN}✓ pip-licenses already installed${NC}"
    fi

    echo ""
}

# Check for outdated packages
check_outdated() {
    echo -e "${BLUE}=== Outdated Packages ===${NC}"

    local outdated_count=$(pip list --outdated --format=json | jq 'length')

    if [ "$outdated_count" -eq 0 ]; then
        echo -e "${GREEN}✓ All packages are up to date${NC}"
    else
        echo -e "${YELLOW}⚠ Found $outdated_count outdated packages:${NC}"
        echo ""
        pip list --outdated --format=columns

        # Show critical outdated packages
        echo ""
        echo -e "${YELLOW}Critical packages requiring updates:${NC}"
        pip list --outdated --format=json | jq -r '.[] | select(.name | test("langgraph|fastapi|pydantic|cryptography|pyjwt|openfga")) | "\(.name): \(.version) → \(.latest_version)"'
    fi

    echo ""
}

# Security vulnerability scan
security_scan() {
    echo -e "${BLUE}=== Security Vulnerabilities ===${NC}"

    local pip_audit_cmd="pip-audit"
    if [ -f ".venv/bin/pip-audit" ]; then
        pip_audit_cmd=".venv/bin/pip-audit"
    fi

    if $pip_audit_cmd --desc --format=columns 2>&1 | grep -q "No known vulnerabilities found"; then
        echo -e "${GREEN}✓ No known vulnerabilities found${NC}"
    else
        echo -e "${RED}⚠ Security vulnerabilities detected:${NC}"
        echo ""
        $pip_audit_cmd --desc --format=columns || true

        echo ""
        echo -e "${RED}ACTION REQUIRED: Review and patch vulnerabilities immediately${NC}"
    fi

    echo ""
}

# License compliance check
license_check() {
    echo -e "${BLUE}=== License Compliance ===${NC}"

    local pip_licenses_cmd="pip-licenses"
    if [ -f ".venv/bin/pip-licenses" ]; then
        pip_licenses_cmd=".venv/bin/pip-licenses"
    fi

    echo "Package licenses:"
    $pip_licenses_cmd --format=markdown --order=license | head -50

    echo ""
    echo -e "${YELLOW}⚠ Review licenses for compliance:${NC}"
    $pip_licenses_cmd --format=json | jq -r '.[] | select(.License | test("GPL|AGPL")) | "\(.Name): \(.License)"' || echo -e "${GREEN}✓ No copyleft licenses found${NC}"

    echo ""
}

# Dependency conflicts
check_conflicts() {
    echo -e "${BLUE}=== Dependency Conflicts ===${NC}"

    if pip check; then
        echo -e "${GREEN}✓ No dependency conflicts${NC}"
    else
        echo -e "${RED}⚠ Dependency conflicts detected${NC}"
        echo -e "${YELLOW}ACTION REQUIRED: Resolve conflicts${NC}"
    fi

    echo ""
}

# Version consistency check
check_version_consistency() {
    echo -e "${BLUE}=== Version Consistency (pyproject.toml vs requirements.txt) ===${NC}"

    # Check if requirements.txt exists
    if [ ! -f "requirements.txt" ]; then
        echo -e "${GREEN}✓ Using pyproject.toml as single source of truth${NC}"
        echo ""
        return
    fi

    echo -e "${YELLOW}⚠ Multiple dependency files detected${NC}"
    echo "Recommend consolidating to pyproject.toml only"
    echo ""

    # Check common packages
    echo "Checking version consistency for critical packages:"
    for pkg in "langgraph" "fastapi" "pydantic" "cryptography" "openfga-sdk"; do
        echo "  - $pkg:"

        # Get version from pyproject.toml
        pyproject_version=$(grep -A 1 "\"$pkg" pyproject.toml | grep -oP '>=\K[0-9.]+' || echo "not found")

        # Get version from requirements.txt
        req_version=$(grep "^$pkg" requirements.txt | grep -oP '>=\K[0-9.]+' || echo "not found")

        if [ "$pyproject_version" != "$req_version" ]; then
            echo -e "    ${YELLOW}⚠ Mismatch: pyproject.toml ($pyproject_version) vs requirements.txt ($req_version)${NC}"
        else
            echo -e "    ${GREEN}✓ Consistent: $pyproject_version${NC}"
        fi
    done

    echo ""
}

# Dependency tree
show_dependency_tree() {
    echo -e "${BLUE}=== Dependency Statistics ===${NC}"

    local total_packages=$(pip list --format=json | jq 'length')
    local outdated_packages=$(pip list --outdated --format=json | jq 'length')
    local dev_packages=$(pip list --format=json | jq '[.[] | select(.name | test("pytest|black|mypy|flake8|bandit|isort"))] | length')

    echo "Total packages installed: $total_packages"
    echo "Outdated packages: $outdated_packages"
    echo "Development packages: $dev_packages"
    echo "Production packages: $((total_packages - dev_packages))"

    echo ""
    echo "Top-level dependencies from pyproject.toml:"
    grep -A 100 "^dependencies = \[" pyproject.toml | grep "\"" | head -20 || echo "  (unable to parse)"

    echo ""
}

# Dependabot PR summary
dependabot_summary() {
    echo -e "${BLUE}=== Open Dependabot PRs ===${NC}"

    if command -v gh &> /dev/null; then
        local pr_count=$(gh pr list --author "app/dependabot" --state open --json number | jq 'length')

        if [ "$pr_count" -eq 0 ]; then
            echo -e "${GREEN}✓ No open Dependabot PRs${NC}"
        else
            echo -e "${YELLOW}⚠ $pr_count open Dependabot PRs:${NC}"
            echo ""
            gh pr list --author "app/dependabot" --state open --json number,title,labels | \
                jq -r '.[] | "#\(.number): \(.title)"'

            echo ""
            echo -e "${YELLOW}ACTION REQUIRED: Review and merge pending updates${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ GitHub CLI not installed, skipping Dependabot check${NC}"
    fi

    echo ""
}

# Generate recommendations
generate_recommendations() {
    echo -e "${BLUE}=== Recommendations ===${NC}"

    local has_recommendations=false

    # Check for outdated critical packages
    local outdated_critical=$(pip list --outdated --format=json | jq -r '.[] | select(.name | test("langgraph|fastapi|pydantic|cryptography|pyjwt")) | .name')
    if [ -n "$outdated_critical" ]; then
        echo -e "${YELLOW}1. Update critical packages:${NC}"
        echo "$outdated_critical" | while read -r pkg; do
            echo "   - $pkg"
        done
        echo ""
        has_recommendations=true
    fi

    # Check for security vulnerabilities
    local pip_audit_cmd="pip-audit"
    if [ -f ".venv/bin/pip-audit" ]; then
        pip_audit_cmd=".venv/bin/pip-audit"
    fi

    if ! $pip_audit_cmd --quiet 2>&1 | grep -q "No known vulnerabilities found"; then
        echo -e "${RED}2. Address security vulnerabilities immediately${NC}"
        echo "   Run: $pip_audit_cmd --desc"
        echo ""
        has_recommendations=true
    fi

    # Check for dependency conflicts
    if ! pip check &> /dev/null; then
        echo -e "${YELLOW}3. Resolve dependency conflicts${NC}"
        echo "   Run: pip check"
        echo ""
        has_recommendations=true
    fi

    # Check for duplicate dependency files
    if [ -f "requirements.txt" ]; then
        echo -e "${YELLOW}4. Consolidate dependency files${NC}"
        echo "   Recommend using pyproject.toml as single source of truth"
        echo "   See: docs/DEPENDENCY_MANAGEMENT.md"
        echo ""
        has_recommendations=true
    fi

    if [ "$has_recommendations" = false ]; then
        echo -e "${GREEN}✓ No immediate actions required${NC}"
        echo "Continue monitoring dependencies monthly."
    fi

    echo ""
}

# Summary
print_summary() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Audit Complete${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "Report saved to: $REPORT_FILE"
    echo ""
    echo "Next steps:"
    echo "  1. Review recommendations above"
    echo "  2. Create GitHub issues for required updates"
    echo "  3. Schedule dependency updates"
    echo "  4. Update docs/DEPENDENCY_MANAGEMENT.md"
    echo ""
    echo "Next audit due: $(date -d '+1 month' +%Y-%m-%d)"
    echo ""
}

# Main execution
main() {
    # Run audit and save to file
    {
        print_header
        check_requirements
        install_audit_tools
        check_outdated
        security_scan
        license_check
        check_conflicts
        check_version_consistency
        show_dependency_tree
        dependabot_summary
        generate_recommendations
        print_summary
    } | tee "$REPORT_FILE"
}

# Run main function
main
