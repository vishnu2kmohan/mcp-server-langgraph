#!/bin/bash
# Monitor Dependabot PR rebase and CI status
# Usage: ./scripts/check-pr-status.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# PRs to monitor (in priority order)
SECURITY_PRS=(32 30)
GROUPED_PRS=(35)
TEST_PRS=(31 28 33)
CICD_PRS=(27 26 25 21 20)

echo -e "${BLUE}=== Dependabot PR Status Monitor ===${NC}"
echo -e "Updated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')\n"

# Get main branch SHA
MAIN_SHA=$(git rev-parse --short HEAD)
echo -e "${BLUE}Main branch SHA:${NC} $MAIN_SHA"
echo

# Function to check PR status
check_pr() {
    local pr_number=$1
    # category parameter intentionally unused - reserved for future filtering logic
    # shellcheck disable=SC2034
    local category=$2

    # Get PR details
    local pr_data
    pr_data=$(gh pr view "$pr_number" --json headRefOid,title,updatedAt,statusCheckRollup 2>/dev/null || echo "")

    if [ -z "$pr_data" ]; then
        echo -e "  ${RED}✗${NC} PR #${pr_number} - Not found"
        return
    fi

    local pr_sha
    pr_sha=$(echo "$pr_data" | jq -r '.headRefOid[0:7]')
    local pr_title
    pr_title=$(echo "$pr_data" | jq -r '.title' | cut -c1-60)
    local pr_updated
    pr_updated=$(echo "$pr_data" | jq -r '.updatedAt')
    local total_checks
    total_checks=$(echo "$pr_data" | jq '[.statusCheckRollup[]] | length')

    # Count check statuses
    local passing
    passing=$(echo "$pr_data" | jq '[.statusCheckRollup[] | select(.conclusion == "success")] | length')
    local failing
    failing=$(echo "$pr_data" | jq '[.statusCheckRollup[] | select(.conclusion == "failure")] | length')
    local pending
    pending=$(echo "$pr_data" | jq '[.statusCheckRollup[] | select(.status == "in_progress" or .status == "queued")] | length')

    # Determine status
    if [ "$total_checks" -eq 0 ]; then
        status="${YELLOW}⏳ No checks yet${NC}"
    elif [ "$failing" -gt 0 ]; then
        status="${RED}✗ ${failing} failing${NC}"
    elif [ "$pending" -gt 0 ]; then
        status="${YELLOW}⏳ ${pending} pending${NC}"
    elif [ "$passing" -eq "$total_checks" ]; then
        status="${GREEN}✓ All passing${NC}"
    else
        status="${YELLOW}? Unknown${NC}"
    fi

    # Check if rebased with main
    if [ "$pr_sha" != "b637073" ]; then
        rebase_status="${GREEN}✓ Rebased${NC}"
    else
        rebase_status="${YELLOW}⏳ Pre-rebase${NC}"
    fi

    echo -e "  ${BLUE}PR #${pr_number}${NC}: $pr_title"
    echo -e "    SHA: $pr_sha | $rebase_status | Checks: $status (${passing}/${total_checks})"
    echo -e "    Updated: ${pr_updated:0:16}"
}

# Check security patches
echo -e "${BLUE}=== Priority 1: Security Patches 🔒 ===${NC}"
for pr in "${SECURITY_PRS[@]}"; do
    check_pr $pr "security"
done
echo

# Check grouped updates
echo -e "${BLUE}=== Priority 2: Grouped Updates 📦 ===${NC}"
for pr in "${GROUPED_PRS[@]}"; do
    check_pr $pr "grouped"
done
echo

# Check test framework
echo -e "${BLUE}=== Priority 3: Test Framework 🧪 ===${NC}"
for pr in "${TEST_PRS[@]}"; do
    check_pr $pr "test"
done
echo

# Check CI/CD actions
echo -e "${BLUE}=== Priority 4: CI/CD Actions 🔧 ===${NC}"
for pr in "${CICD_PRS[@]}"; do
    check_pr $pr "cicd"
done
echo

# Summary
echo -e "${BLUE}=== Summary ===${NC}"

all_prs=("${SECURITY_PRS[@]}" "${GROUPED_PRS[@]}" "${TEST_PRS[@]}" "${CICD_PRS[@]}")
total_prs=${#all_prs[@]}
ready_count=0
pending_count=0
failing_count=0

for pr in "${all_prs[@]}"; do
    pr_data=$(gh pr view "$pr" --json statusCheckRollup 2>/dev/null || echo "")
    if [ -z "$pr_data" ]; then
        continue
    fi

    total_checks=$(echo "$pr_data" | jq '[.statusCheckRollup[]] | length')
    passing=$(echo "$pr_data" | jq '[.statusCheckRollup[] | select(.conclusion == "success")] | length')
    failing=$(echo "$pr_data" | jq '[.statusCheckRollup[] | select(.conclusion == "failure")] | length')

    if [ "$total_checks" -eq 0 ]; then
        ((pending_count++))
    elif [ "$failing" -gt 0 ]; then
        ((failing_count++))
    elif [ "$passing" -eq "$total_checks" ] && [ "$total_checks" -gt 0 ]; then
        ((ready_count++))
    else
        ((pending_count++))
    fi
done

echo -e "Total PRs monitored: ${BLUE}$total_prs${NC}"
echo -e "Ready to merge: ${GREEN}$ready_count${NC}"
echo -e "Pending CI: ${YELLOW}$pending_count${NC}"
echo -e "Failing CI: ${RED}$failing_count${NC}"

if [ "$ready_count" -gt 0 ]; then
    echo -e "\n${GREEN}✓ ${ready_count} PR(s) ready to merge!${NC}"
    echo "Run: ./scripts/merge-ready-prs.sh"
elif [ "$pending_count" -eq "$total_prs" ]; then
    echo -e "\n${YELLOW}⏳ All PRs still pending (Dependabot rebase or CI in progress)${NC}"
    echo "Check again in 5-10 minutes"
elif [ "$failing_count" -gt 0 ]; then
    echo -e "\n${RED}⚠️  ${failing_count} PR(s) have failing checks${NC}"
    echo "Investigate failures with: gh pr checks <PR-NUMBER>"
fi

echo -e "\n${BLUE}Next check:${NC} $(date -u -d '+5 minutes' '+%Y-%m-%d %H:%M UTC' 2>/dev/null || date -u '+%Y-%m-%d %H:%M UTC')"
