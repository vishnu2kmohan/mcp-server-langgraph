---
description: Comprehensive Pull Request validation summary
argument-hint: <number>
---
# PR Checks Summary

**Usage**: `/pr-checks` or `/pr-checks <pr-number>`

**Purpose**: Comprehensive Pull Request validation summary

---

## 🔍 What This Command Does

Shows complete PR validation status including:

1. Required checks status (passing/failing/pending)
2. Review approval status
3. Merge conflicts status
4. PR size and complexity metrics
5. CI/CD workflow results
6. Code coverage impact

---

## 📊 PR Validation Workflow

### Step 1: Identify Pull Request

Determine which PR to check:

```bash
# If PR number provided
if [ -n "$ARGUMENTS" ]; then
    PR_NUMBER="$ARGUMENTS"
else
    # Get PR for current branch
    PR_NUMBER=$(gh pr view --json number --jq '.number' 2>/dev/null)

    if [ -z "$PR_NUMBER" ]; then
        echo "No PR found for current branch"
        echo "Create PR with: gh pr create"
        exit 1
    fi
fi

echo "Checking PR #$PR_NUMBER"
```

### Step 2: Fetch PR Information

Get comprehensive PR details:

```bash
# Get PR metadata
gh pr view $PR_NUMBER --json \
  number,title,state,isDraft,mergeable,reviewDecision,\
  statusCheckRollup,additions,deletions,changedFiles,\
  url,baseRefName,headRefName,author,createdAt,updatedAt

# Example output structure:
# {
#   "number": 123,
#   "title": "feat: add session management",
#   "state": "OPEN",
#   "isDraft": false,
#   "mergeable": "MERGEABLE",
#   "reviewDecision": "APPROVED",
#   "statusCheckRollup": [...]
#   "additions": 450,
#   "deletions": 120,
#   "changedFiles": 8
# }
```

### Step 3: Check Required Status Checks

Analyze CI/CD check status:

```bash
# Parse status checks
gh pr view $PR_NUMBER --json statusCheckRollup \
  --jq '.statusCheckRollup[] | {name: .name, status: .status, conclusion: .conclusion}'

# Group by status
PASSING=$(gh pr view $PR_NUMBER --json statusCheckRollup \
  --jq '[.statusCheckRollup[] | select(.conclusion=="SUCCESS")] | length')

FAILING=$(gh pr view $PR_NUMBER --json statusCheckRollup \
  --jq '[.statusCheckRollup[] | select(.conclusion=="FAILURE")] | length')

PENDING=$(gh pr view $PR_NUMBER --json statusCheckRollup \
  --jq '[.statusCheckRollup[] | select(.status=="PENDING")] | length')

TOTAL=$(gh pr view $PR_NUMBER --json statusCheckRollup --jq '.statusCheckRollup | length')
```

### Step 4: Check Review Status

Analyze code review state:

```bash
# Get review decision
REVIEW_STATUS=$(gh pr view $PR_NUMBER --json reviewDecision --jq -r '.reviewDecision')

# Get review details
gh pr view $PR_NUMBER --json reviews \
  --jq '.reviews[] | {author: .author.login, state: .state, submittedAt: .submittedAt}'

# Count approvals
APPROVALS=$(gh pr view $PR_NUMBER --json reviews \
  --jq '[.reviews[] | select(.state=="APPROVED")] | unique_by(.author.login) | length')

# Check if changes requested
CHANGES_REQUESTED=$(gh pr view $PR_NUMBER --json reviews \
  --jq '[.reviews[] | select(.state=="CHANGES_REQUESTED")] | length')
```

### Step 5: Analyze PR Size and Complexity

Calculate PR metrics:

```bash
# Get file changes
ADDITIONS=$(gh pr view $PR_NUMBER --json additions --jq '.additions')
DELETIONS=$(gh pr view $PR_NUMBER --json deletions --jq '.deletions')
FILES_CHANGED=$(gh pr view $PR_NUMBER --json changedFiles --jq '.changedFiles')

# Calculate total changes
TOTAL_CHANGES=$((ADDITIONS + DELETIONS))

# Determine PR size
if [ $TOTAL_CHANGES -lt 50 ]; then
    SIZE="XS (Tiny)"
elif [ $TOTAL_CHANGES -lt 200 ]; then
    SIZE="S (Small)"
elif [ $TOTAL_CHANGES -lt 500 ]; then
    SIZE="M (Medium)"
elif [ $TOTAL_CHANGES -lt 1000 ]; then
    SIZE="L (Large)"
else
    SIZE="XL (Very Large)"
fi

# Check if too large
if [ $TOTAL_CHANGES -gt 500 ]; then
    echo "⚠️  Warning: PR is large ($SIZE). Consider splitting."
fi
```

### Step 6: Check Merge Status

Determine if PR is ready to merge:

```bash
# Get mergeable status
MERGEABLE=$(gh pr view $PR_NUMBER --json mergeable --jq -r '.mergeable')

# Translate to user-friendly status
case "$MERGEABLE" in
    MERGEABLE)
        MERGE_STATUS="✅ Ready to merge"
        ;;
    CONFLICTING)
        MERGE_STATUS="❌ Has merge conflicts"
        ;;
    UNKNOWN)
        MERGE_STATUS="🔄 Checking..."
        ;;
esac

# Check if draft
IS_DRAFT=$(gh pr view $PR_NUMBER --json isDraft --jq '.isDraft')
if [ "$IS_DRAFT" = "true" ]; then
    MERGE_STATUS="📝 Draft - not ready for merge"
fi
```

### Step 7: Generate PR Summary Report

Create comprehensive report:

```markdown
# PR Checks Summary: #{pr_number}

**Title**: {pr_title}
**Status**: {state} {(draft_indicator)}
**Author**: {author}
**Created**: {created_date}
**Updated**: {updated_date}

---

## ✅ Validation Status

### Required Checks: {passing}/{total}

| Check | Status | Result | Duration |
|-------|--------|--------|----------|
| CI/CD Pipeline | Complete | ✅ Success | 2m 45s |
| Unit Tests | Complete | ✅ Success | 45s |
| Integration Tests | Complete | ✅ Success | 1m 30s |
| Quality Tests | Running | 🔄 Pending | - |
| Security Scan | Complete | ✅ Success | 1m 15s |

**Overall**: {passing_emoji} {passing}/{total} checks passing

---

## 👥 Review Status

**Decision**: {review_decision_emoji} {review_decision}

**Reviews**:
- ✅ @reviewer1 approved (2 hours ago)
- ✅ @reviewer2 approved (1 hour ago)
- 💬 @reviewer3 commented (30 minutes ago)

**Approvals**: {approvals}/{required}

---

## 📏 PR Size & Complexity

| Metric | Value | Assessment |
|--------|-------|------------|
| Files Changed | {files} | {assessment} |
| Lines Added | {additions} | |
| Lines Deleted | {deletions} | |
| Total Changes | {total} | **{size}** |

**Size Classification**: {size}
**Recommendation**: {recommendation}

---

## 🔀 Merge Status

**Mergeable**: {merge_status}

**Blockers**:
{list_of_blockers_if_any}

**Ready to Merge**: {yes/no}

---

## 📊 Impact Analysis

**Code Coverage**: {coverage_change}
**Files Modified**: {file_list}
**Breaking Changes**: {yes/no}

---

## 🎯 Next Steps

{action_items_based_on_status}
```

---

## 📋 Status Examples

### Example 1: Ready to Merge

```
User: /pr-checks

Claude:
Checking PR for current branch...

═══════════════════════════════════════
PR #145: feat: add session management
═══════════════════════════════════════

Status: OPEN (Ready for Merge) ✅
Author: @developer
Updated: 5 minutes ago

Required Checks: 5/5 ✅
┌─────────────────────┬──────────┬──────────┐
│ Check               │ Status   │ Result   │
├─────────────────────┼──────────┼──────────┤
│ CI/CD Pipeline      │ Complete │ ✅ Pass  │
│ PR Checks           │ Complete │ ✅ Pass  │
│ Quality Tests       │ Complete │ ✅ Pass  │
│ Security Scan       │ Complete │ ✅ Pass  │
│ Code Coverage       │ Complete │ ✅ Pass  │
└─────────────────────┴──────────┴──────────┘

Review Status: APPROVED ✅
- @reviewer1 approved (1 hour ago)
- @reviewer2 approved (30 min ago)

PR Size: M (Medium)
- Files: 8
- Additions: +450
- Deletions: -120
- Total: 570 changes

Merge Status: ✅ READY TO MERGE
- No conflicts
- All checks passing
- Approved by 2 reviewers
- Not a draft

Next Steps:
1. ✅ All requirements met
2. Ready to merge with: gh pr merge 145
3. Squash merge recommended (8 commits)

Merge command:
gh pr merge 145 --squash --delete-branch
```

### Example 2: Pending Checks

```
User: /pr-checks 142

Claude:
═══════════════════════════════════════
PR #142: fix: resolve async test issues
═══════════════════════════════════════

Status: OPEN (Checks In Progress) 🔄
Author: @developer
Updated: 2 minutes ago

Required Checks: 3/5 🔄
┌─────────────────────┬──────────┬──────────┐
│ Check               │ Status   │ Result   │
├─────────────────────┼──────────┼──────────┤
│ CI/CD Pipeline      │ Running  │ 🔄 2m 15s│
│ PR Checks           │ Complete │ ✅ Pass  │
│ Quality Tests       │ Queued   │ ⏸️  Pend  │
│ Security Scan       │ Complete │ ✅ Pass  │
│ Code Coverage       │ Queued   │ ⏸️  Pend  │
└─────────────────────┴──────────┴──────────┘

Currently Running:
🔄 CI/CD Pipeline (2m 15s elapsed)
   Jobs: 3/5 complete
   - ✅ Lint (15s)
   - ✅ Unit Tests (45s)
   - ✅ Integration Tests (1m 15s)
   - 🔄 Quality Tests (running)
   - ⏸️  Build & Deploy (pending)

   Estimated remaining: ~2 minutes

Review Status: PENDING 📝
- No reviews yet
- Waiting for reviewers

PR Size: S (Small)
- Files: 3
- Changes: +45/-12 (57 total)

Merge Status: ⏸️  WAITING
- Checks in progress
- Needs review approval

Next Steps:
1. Wait for CI/CD to complete (~2 min)
2. Request reviews from team
3. Address any feedback

Monitor progress:
gh run watch $(gh run list --branch $(git branch --show-current) --limit 1 --json databaseId --jq '.[0].databaseId')
```

### Example 3: Checks Failed

```
User: /pr-checks

Claude:
═══════════════════════════════════════
PR #139: refactor: update auth flow
═══════════════════════════════════════

Status: OPEN (Checks Failed) ❌
Author: @developer
Updated: 10 minutes ago

Required Checks: 3/5 ❌
┌─────────────────────┬──────────┬──────────┐
│ Check               │ Status   │ Result   │
├─────────────────────┼──────────┼──────────┤
│ CI/CD Pipeline      │ Complete │ ❌ FAIL  │
│ PR Checks           │ Complete │ ✅ Pass  │
│ Quality Tests       │ Complete │ ❌ FAIL  │
│ Security Scan       │ Complete │ ✅ Pass  │
│ Code Coverage       │ Complete │ ✅ Pass  │
└─────────────────────┴──────────┴──────────┘

Failed Checks:

❌ CI/CD Pipeline
   Job: Unit Tests
   Error: FAILED tests/test_auth.py::test_login
   Duration: 1m 23s
   Logs: gh run view 456 --log-failed

❌ Quality Tests
   Job: Property Tests
   Error: 2 property tests failed
   Duration: 5m 12s
   Logs: gh run view 457 --log-failed

Review Status: CHANGES_REQUESTED 🔄
- @reviewer1 requested changes (1 hour ago)
  "Please fix the failing tests before merging"

PR Size: L (Large)
- Files: 15
- Changes: +650/-200 (850 total)
- ⚠️  Large PR - consider splitting

Merge Status: ❌ BLOCKED
- 2 checks failing
- Changes requested
- Cannot merge until fixed

Next Steps:
1. ❌ Fix failing unit test in test_auth.py
2. ❌ Fix failing property tests
3. 🔄 Address reviewer feedback
4. 🔄 Push fixes to trigger re-run

Quick debug:
/quick-debug "FAILED tests/test_auth.py::test_login"

View failures:
gh run view 456 --log-failed
```

---

## 🎯 PR Quality Guidelines

### Size Recommendations

**XS (< 50 changes)**: ✅ Perfect
- Fast review
- Low risk
- Easy to understand

**S (50-200 changes)**: ✅ Good
- Reasonable review time
- Manageable complexity

**M (200-500 changes)**: 🟡 OK
- Longer review time
- Consider if can split

**L (500-1000 changes)**: ⚠️  Large
- Difficult to review thoroughly
- Recommend splitting if possible

**XL (> 1000 changes)**: ❌ Too Large
- Very difficult to review
- High risk of issues
- Should split into multiple PRs

### Check Requirements

**Must Pass**:
- CI/CD Pipeline
- Unit Tests
- Integration Tests
- Security Scan

**Should Pass**:
- Quality Tests (property, contract, regression)
- Code Coverage (maintain or improve)

**Nice to Have**:
- Performance Benchmarks
- Documentation Updates

---

## 💡 Quick Actions

### Request Reviews

```bash
# Request review from team members
gh pr edit $PR_NUMBER --add-reviewer @user1,@user2

# Request review from team
gh pr edit $PR_NUMBER --add-reviewer team-name
```

### Update PR

```bash
# Update title
gh pr edit $PR_NUMBER --title "new title"

# Update description
gh pr edit $PR_NUMBER --body "new description"

# Mark as ready (if draft)
gh pr ready $PR_NUMBER
```

### Merge PR

```bash
# Squash merge (recommended for feature branches)
gh pr merge $PR_NUMBER --squash --delete-branch

# Merge commit (for release branches)
gh pr merge $PR_NUMBER --merge

# Rebase merge (for linear history)
gh pr merge $PR_NUMBER --rebase --delete-branch
```

---

## 🔗 Related Commands

- `/ci-status` - General CI/CD status
- `/test-summary` - Local test results
- `/quick-debug` - Debug failing checks

---

## 🛠️ Troubleshooting

### Issue: No PR found for branch

```bash
# Create PR
gh pr create --title "..." --body "..."

# Or create from web
gh pr create --web
```

### Issue: Checks not running

```bash
# Check workflow files
ls .github/workflows/

# Trigger manually
gh workflow run ci.yaml --ref $(git branch --show-current)
```

### Issue: Review not appearing

```bash
# Check PR reviews
gh pr view $PR_NUMBER --json reviews

# Request review again
gh pr edit $PR_NUMBER --add-reviewer @username
```

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
**Requires**: GitHub CLI (`gh`)
**Permissions**: Read access to repository
