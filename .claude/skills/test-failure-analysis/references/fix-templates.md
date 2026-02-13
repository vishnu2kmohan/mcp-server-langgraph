# Fix Templates

Reference for automated fix scripts, advanced analysis features, and troubleshooting. Used after Step 6 of the test failure analysis workflow to apply fixes.

---

## Fix Templates

### Template 1: ImportError Cascade Fix

```bash
#!/bin/bash
# Fix cascade import failures

# 1. Identify missing file
MISSING_FILE=$(grep -o "from .* import" ${TMPDIR:-/tmp}/test_output.txt | \
               awk '{print $2}' | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')

# 2. Check git status
git status src/ | grep -i "$MISSING_FILE"

# 3. Stage and commit
git add src/**/*${MISSING_FILE}*.py
git commit -m "fix: add missing ${MISSING_FILE} module"

# 4. Re-run tests
uv run --frozen pytest --lf -v
```

### Template 2: Docker Service Fix

```bash
#!/bin/bash
# Fix infrastructure failures

# 1. Identify which service
SERVICE=$(grep -o "localhost:[0-9]*" ${TMPDIR:-/tmp}/test_output.txt | \
          sed 's/localhost://' | sort | uniq)

# Map port to service
case $SERVICE in
    6379) SERVICE_NAME="redis" ;;
    5432) SERVICE_NAME="postgres" ;;
    8080) SERVICE_NAME="openfga" ;;
esac

# 2. Start service
docker compose up -d $SERVICE_NAME

# 3. Wait for healthy
timeout 60s bash -c "until docker compose ps $SERVICE_NAME | grep healthy; do sleep 2; done"

# 4. Re-run tests
uv run --frozen pytest --lf -v
```

### Template 3: AsyncMock Batch Fix

```python
#!/usr/bin/env python3
"""Fix AsyncMock issues in test files."""

import re
import sys
from pathlib import Path

def fix_async_mock(file_path):
    content = Path(file_path).read_text()

    # Find @patch decorators above async functions
    pattern = r'@patch\("([^"]+)"\)\s*\nasync def'

    # Replace with AsyncMock version
    replacement = r'@patch("\1", new_callable=AsyncMock)\nasync def'

    fixed_content = re.sub(pattern, replacement, content)

    if fixed_content != content:
        Path(file_path).write_text(fixed_content)
        print(f"Fixed: {file_path}")
        return True
    return False

# Run on all test files
for test_file in Path("tests").rglob("test_*.py"):
    fix_async_mock(test_file)
```

---

## Advanced Features

### Feature 1: Failure Trend Analysis

Track failure patterns over time:

```bash
# Store failure data
mkdir -p .test-history
echo "$(date +%Y-%m-%d),$FAILURES,$ERRORS,$PASSED" >> .test-history/trend.csv

# Analyze trend
tail -30 .test-history/trend.csv | awk -F',' '
{
    total = $2 + $3 + $4
    fail_rate = ($2 + $3) / total * 100
    print $1, fail_rate "%"
}'
```

### Feature 2: Failure Clustering

Group similar failures:

```python
def cluster_failures(failures):
    clusters = {}

    for failure in failures:
        # Extract error message
        error = extract_error(failure)

        # Find similar errors (edit distance < 5)
        cluster_key = find_similar(error, clusters.keys())

        if not cluster_key:
            cluster_key = error

        clusters[cluster_key] = clusters.get(cluster_key, []) + [failure]

    return clusters
```

### Feature 3: AI-Powered Suggestions

Use Claude to suggest fixes:

```
For each unique failure:
1. Extract stack trace
2. Extract surrounding code
3. Ask Claude: "What's the likely cause of this error?"
4. Get suggested fix
5. Apply if high confidence
```

---

## Troubleshooting

### Issue: Too many failures to analyze

```bash
# Focus on most common error
grep "FAILED" ${TMPDIR:-/tmp}/test_output.txt | \
  awk -F':' '{print $NF}' | \
  sort | uniq -c | sort -rn | head -5
```

### Issue: Can't determine root cause

```bash
# Run with full traceback
uv run --frozen pytest --lf -vv --tb=long

# Enable debugging
uv run --frozen pytest --lf --pdb
```

### Issue: Failures are intermittent

```bash
# Run multiple times
for i in {1..10}; do
    uv run --frozen pytest tests/ > ${TMPDIR:-/tmp}/run_$i.txt 2>&1
    grep -c "FAILED" ${TMPDIR:-/tmp}/run_$i.txt
done
```
