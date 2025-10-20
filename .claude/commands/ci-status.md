# CI/CD Status

**Usage**: `/ci-status` or `/ci-status --workflow <name>`

**Purpose**: Real-time GitHub Actions workflow status and recent runs

---

## 🔄 What This Command Does

Displays current CI/CD pipeline status using GitHub CLI:

1. Shows workflow run status for current branch
2. Lists recent workflow runs with results
3. Displays failing jobs and steps
4. Shows run duration and timing
5. Provides links to detailed logs

---

## 📊 Workflow Status Display

### Step 1: Check GitHub CLI

Verify `gh` CLI is installed and authenticated:

```bash
# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI not installed"
    echo "Install: https://cli.github.com/"
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub"
    echo "Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI ready"
```

### Step 2: Get Current Branch

Determine which branch to check:

```bash
# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $CURRENT_BRANCH"

# Get latest commit
LATEST_COMMIT=$(git rev-parse --short HEAD)
echo "Latest commit: $LATEST_COMMIT"
```

### Step 3: Fetch Workflow Runs

Get recent workflow runs for current branch:

```bash
# List recent workflow runs
gh run list \
  --branch "$CURRENT_BRANCH" \
  --limit 5 \
  --json databaseId,displayTitle,name,status,conclusion,createdAt,updatedAt,url

# Alternative: Get runs for specific commit
gh run list \
  --commit "$LATEST_COMMIT" \
  --json databaseId,displayTitle,name,status,conclusion,url
```

### Step 4: Parse Workflow Status

Extract and format workflow information:

```bash
# Parse JSON output
gh run list --branch "$CURRENT_BRANCH" --limit 5 --json name,status,conclusion,createdAt,url | \
jq -r '.[] | "\(.name)\t\(.status)\t\(.conclusion // "N/A")\t\(.createdAt)\t\(.url)"' | \
while IFS=$'\t' read -r name status conclusion created url; do
    # Format status with emoji
    case "$conclusion" in
        success)   icon="✅" ;;
        failure)   icon="❌" ;;
        cancelled) icon="🚫" ;;
        skipped)   icon="⏭️ " ;;
        *)         icon="🔄" ;;
    esac

    # Format timestamp
    time_ago=$(date -d "$created" +'%Y-%m-%d %H:%M')

    echo "$icon $name | $status | $time_ago"
    echo "   $url"
done
```

### Step 5: Show Failing Jobs (if any)

If workflows failed, show which jobs/steps failed:

```bash
# Get failing workflow run ID
FAILED_RUN=$(gh run list --branch "$CURRENT_BRANCH" --limit 1 \
  --json databaseId,conclusion --jq '.[] | select(.conclusion=="failure") | .databaseId')

if [ -n "$FAILED_RUN" ]; then
    echo ""
    echo "❌ Failed Workflow Details:"
    echo ""

    # Get failing jobs
    gh run view "$FAILED_RUN" --json jobs --jq '.jobs[] | select(.conclusion=="failure") | {name, steps}'

    # Show failed steps
    echo "Failed Steps:"
    gh run view "$FAILED_RUN" --log-failed
fi
```

### Step 6: Generate Status Report

Create formatted status report:

```markdown
# CI/CD Status Report

**Generated**: {timestamp}
**Branch**: {current_branch}
**Commit**: {latest_commit}

---

## Workflow Status

| Workflow | Status | Conclusion | Started | Duration |
|----------|--------|------------|---------|----------|
| CI/CD Pipeline | in_progress | - | 2m ago | 1m 23s |
| PR Checks | completed | success | 5m ago | 2m 45s |
| Quality Tests | completed | success | 5m ago | 3m 12s |
| Security Scan | queued | - | pending | - |

---

## Recent Runs (Last 5)

1. ✅ **CI/CD Pipeline** - success (5 minutes ago)
   - Duration: 2m 45s
   - Commit: {hash} - {message}
   - URL: {workflow_url}

2. ❌ **CI/CD Pipeline** - failure (1 hour ago)
   - Duration: 1m 23s
   - Failed: Unit Tests job
   - URL: {workflow_url}

3. ✅ **PR Checks** - success (2 hours ago)
   - Duration: 3m 10s
   - URL: {workflow_url}

---

## Failing Workflows ❌

### CI/CD Pipeline (Run #123)

**Job**: Unit Tests
**Step**: Run pytest
**Error**:
```
FAILED tests/test_auth.py::test_login - ImportError
```

**Logs**: {log_url}

**Quick Actions**:
- View full logs: `gh run view 123`
- Re-run failed jobs: `gh run rerun 123 --failed`
- View in browser: {url}

---

## Overall Status

Current branch: ✅ All checks passing
Latest commit: ❌ 1 workflow failing

**Action Required**: Fix failing unit test
```

---

## 📋 Status Examples

### Example 1: All Passing

```
User: /ci-status

Claude:
Checking CI/CD status for branch: main
Latest commit: abc1234

CI/CD Status: ✅ ALL PASSING

Recent Workflow Runs:
┌─────────────────────┬──────────┬────────────┬──────────┐
│ Workflow            │ Status   │ Result     │ Time     │
├─────────────────────┼──────────┼────────────┼──────────┤
│ CI/CD Pipeline      │ Complete │ ✅ Success │ 2m ago   │
│ PR Checks           │ Complete │ ✅ Success │ 5m ago   │
│ Quality Tests       │ Complete │ ✅ Success │ 5m ago   │
│ Security Scan       │ Complete │ ✅ Success │ 10m ago  │
└─────────────────────┴──────────┴────────────┴──────────┘

Latest Run: CI/CD Pipeline
- Started: 2 minutes ago
- Duration: 2m 45s
- Jobs: 5/5 passed
- Coverage: 69%

Status: ✅ Safe to merge/deploy

Workflow URLs:
- CI/CD: https://github.com/user/repo/actions/runs/123
- PR Checks: https://github.com/user/repo/actions/runs/122
```

### Example 2: Workflow In Progress

```
User: /ci-status

Claude:
Checking CI/CD status for branch: feature/new-auth
Latest commit: def5678

CI/CD Status: 🔄 IN PROGRESS

Current Workflow: CI/CD Pipeline
- Status: Running (1m 23s elapsed)
- Progress: 3/5 jobs completed

Completed Jobs:
✅ Lint and Format (15s)
✅ Unit Tests (45s)
✅ Integration Tests (23s)

Running Jobs:
🔄 Quality Tests (running, 18s so far)
⏸️  Security Scan (pending)

Estimated Time Remaining: ~2 minutes

Live URL: https://github.com/user/repo/actions/runs/124

You can monitor progress with:
gh run watch 124
```

### Example 3: Workflow Failed

```
User: /ci-status

Claude:
Checking CI/CD status for branch: fix/session-bug
Latest commit: ghi9012

CI/CD Status: ❌ FAILURE DETECTED

Failed Workflow: CI/CD Pipeline (Run #125)
- Started: 3 minutes ago
- Duration: 1m 45s
- Failed at: Unit Tests job

Failure Details:
┌────────────────┬──────────────────────────────────┐
│ Job            │ Unit Tests                       │
│ Step           │ Run pytest                       │
│ Exit Code      │ 1                                │
│ Duration       │ 42s                              │
└────────────────┴──────────────────────────────────┘

Error Summary:
FAILED tests/test_session.py::test_create_session
ImportError: cannot import name 'get_session_store'

12 tests collected, 11 passed, 1 failed

Root Cause Analysis:
❌ Import error detected
   File exists but may have uncommitted changes

Quick Fix:
```bash
git status src/  # Check for uncommitted files
git add src/mcp_server_langgraph/auth/session.py
git commit -m "fix: add missing session store"
git push
```

After fix, workflow will auto-trigger on push.

Full logs: gh run view 125 --log-failed
Re-run: gh run rerun 125
Browser: https://github.com/user/repo/actions/runs/125
```

---

## 🎯 Workflow Information

### Default Workflows (This Repo)

**CI/CD Pipeline** (`.github/workflows/ci.yaml`):
- Runs on: push, pull_request
- Jobs: Lint, Unit Tests, Integration Tests, Quality Tests
- Duration: ~3-5 minutes
- Critical path for merging

**PR Checks** (`.github/workflows/pr-checks.yaml`):
- Runs on: pull_request
- Jobs: Title check, Label check, Size check
- Duration: ~30 seconds
- Required for PR approval

**Quality Tests** (`.github/workflows/quality-tests.yaml`):
- Runs on: pull_request, schedule
- Jobs: Property tests, Contract tests, Regression tests
- Duration: ~10-15 minutes
- Can run in parallel with CI/CD

**Security Scan** (`.github/workflows/security-scan.yaml`):
- Runs on: push to main, pull_request, schedule
- Jobs: Bandit, Safety, Trivy
- Duration: ~2-3 minutes
- Blocks merge if critical issues found

**Dependabot Auto-Merge** (`.github/workflows/dependabot-auto-merge.yaml`):
- Runs on: pull_request (Dependabot only)
- Jobs: Auto-approve and merge
- Duration: ~30 seconds
- Automated dependency updates

---

## 🔧 Advanced Features

### Feature 1: Watch Workflow

Monitor workflow in real-time:

```bash
# Get latest run ID
RUN_ID=$(gh run list --branch "$CURRENT_BRANCH" --limit 1 --json databaseId --jq '.[0].databaseId')

# Watch in terminal
gh run watch $RUN_ID

# Or tail logs
gh run view $RUN_ID --log
```

### Feature 2: Workflow Filtering

Filter by specific workflow:

```bash
# Show only CI/CD workflow
gh run list --workflow=ci.yaml --branch "$CURRENT_BRANCH" --limit 5

# Show only failed runs
gh run list --branch "$CURRENT_BRANCH" --json conclusion,name,url \
  --jq '.[] | select(.conclusion=="failure")'
```

### Feature 3: Performance Tracking

Track workflow duration trends:

```bash
# Get duration for last 10 runs
gh run list --workflow=ci.yaml --limit 10 \
  --json createdAt,updatedAt,conclusion \
  --jq '.[] | select(.conclusion=="success") |
       ((.updatedAt | fromdateiso8601) - (.createdAt | fromdateiso8601)) / 60'

# Average duration
gh run list --workflow=ci.yaml --limit 30 --json createdAt,updatedAt,conclusion \
  --jq '[.[] | select(.conclusion=="success") |
        ((.updatedAt | fromdateiso8601) - (.createdAt | fromdateiso8601))] |
        add / length / 60'
```

---

## 💡 Quick Actions

### Re-run Failed Workflow

```bash
# Get failed run ID
FAILED_ID=$(gh run list --limit 1 --json databaseId,conclusion \
  --jq '.[] | select(.conclusion=="failure") | .databaseId')

# Re-run only failed jobs
gh run rerun $FAILED_ID --failed

# Or re-run entire workflow
gh run rerun $FAILED_ID
```

### Cancel Running Workflow

```bash
# Get running workflow
RUNNING_ID=$(gh run list --limit 1 --json databaseId,status \
  --jq '.[] | select(.status=="in_progress") | .databaseId')

# Cancel it
gh run cancel $RUNNING_ID
```

### View Workflow Logs

```bash
# View all logs
gh run view $RUN_ID --log

# View only failed job logs
gh run view $RUN_ID --log-failed

# Download logs
gh run download $RUN_ID
```

---

## 🔗 Related Commands

- `/pr-checks` - PR-specific check status
- `/test-summary` - Local test results
- `/benchmark` - Performance benchmarks

---

## 🛠️ Troubleshooting

### Issue: GitHub CLI not authenticated

```bash
# Authenticate
gh auth login

# Check status
gh auth status
```

### Issue: No workflows found

```bash
# Check if in git repository
git status

# Check if workflows exist
ls .github/workflows/

# Check if on correct branch
git branch
```

### Issue: Workflow taking too long

```bash
# Check which job is slow
gh run view $RUN_ID --json jobs \
  --jq '.jobs[] | {name, startedAt, completedAt}'

# Cancel and re-run if stuck
gh run cancel $RUN_ID
gh run rerun $RUN_ID
```

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
**Requires**: GitHub CLI (`gh`)
**Authentication**: GitHub account with repo access
