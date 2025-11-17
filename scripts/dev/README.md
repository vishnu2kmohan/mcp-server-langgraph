# Development Analysis Tools

This directory contains development-time analysis and profiling utilities.

## Tools

### Performance Analysis

- **`measure_hook_performance.py`** - Profile pre-commit hook execution time
  - Usage: `python scripts/dev/measure_hook_performance.py --stage all`
  - Measures hook timing to identify slow validators

### Test Analysis

- **`identify_critical_tests.py`** - Identify high-impact tests for prioritization
  - Helps determine which tests to run first for fast feedback
  - Analyzes test dependencies and coverage impact

### Code Quality

- **`audit_resource_ratios.py`** - Analyze resource request/limit ratios in Kubernetes configs
  - Validates that resource limits are reasonable multiples of requests
  - Prevents OOMKilled pods from misconfigured ratios

- **`detect_missing_lang_tags.py`** - Find code blocks in MDX docs missing language tags
  - Ensures proper syntax highlighting in documentation
  - Validates documentation quality

## Usage

These tools are NOT integrated into CI/CD or git hooks. They are for local development and analysis only.

**Run during development:**
```bash
# Measure pre-commit hook performance
python scripts/dev/measure_hook_performance.py --stage pre-commit

# Identify critical tests for fast feedback
python scripts/dev/identify_critical_tests.py

# Audit K8s resource ratios
python scripts/dev/audit_resource_ratios.py deployments/

# Find missing MDX language tags
python scripts/dev/detect_missing_lang_tags.py docs/
```

## Integration

To integrate any of these tools into automated systems:
1. Add to `.pre-commit-config.yaml` (for hooks)
2. Add to `Makefile` (for make targets)
3. Add to `.github/workflows/` (for CI/CD)

See `scripts/SCRIPT_INVENTORY.md` for examples of integrated scripts.
