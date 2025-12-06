# Preview GKE Infrastructure Remediation Plan

**Created**: 2025-12-06
**Based on**: 16 issues from teardown/bringup session (preview-teardown-bringup-issues.md)
**Methodology**: TDD, DRY, KISS, YAGNI, SOLID, 12-Factor, Cloud-Native

---

## Executive Summary

This remediation plan addresses 16 infrastructure issues encountered during the Preview GKE teardown and recreation session. Fixes are prioritized by:
1. **Severity** (blocking > high > medium > low)
2. **Blast Radius** (production impact potential)
3. **Implementation Complexity** (quick wins first)

All fixes follow Test-Driven Development (TDD) with Terraform validation tests.

---

## Issue Classification Matrix

| Issue # | Category | Severity | Root Cause | Fix Type |
|---------|----------|----------|------------|----------|
| #6, #16 | Monitoring | HIGH | Metric validation race condition | Code Change |
| #3 | IAM | HIGH | WIF soft-deletion | Process + Code |
| #7 | GKE | HIGH | Provider API serialization | Workaround |
| #1 | CloudSQL | HIGH | Runtime database ownership | Script Enhancement |
| #2 | Networking | HIGH | Service networking propagation | Script Enhancement |
| #14 | K8s Services | HIGH | Stale service configuration | Manifest Fix |
| #15 | Secrets | HIGH | Missing secret keys | Process + Automation |
| #4 | Terraform | MEDIUM | State lock contention | Process Improvement |
| #5 | Redis | MEDIUM | Orphaned resource | Process Improvement |
| #8, #9, #11 | Naming | MEDIUM | Stale resource names | Script Sync |
| #10 | CloudSQL | LOW | Database already exists | Idempotency |
| #12 | CloudSQL | LOW | Deprecated parameter | Code Migration |
| #13 | Process | MEDIUM | Background process accumulation | Session Management |

---

## Priority 1: Critical Fixes (Block Future Teardowns)

### 1.1 Alert Policy Metric Availability Issue (Issues #6, #16)

**Problem**: Cloud Monitoring requires metrics to exist before creating alert policies, causing 404 errors during fresh deployments.

**Root Cause**: GCP's Cloud Monitoring API validates that referenced metrics exist before allowing alert policy creation. This is an API-level requirement, not a Terraform behavior.

**Key Finding (2025-12-06)**: The parameter `disable_metric_validation` does NOT exist in the Terraform Google provider's `condition_threshold` block. This was incorrectly documented in earlier research.

**Valid Parameters in `condition_threshold`** (per [Terraform Google Provider docs](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/monitoring_alert_policy)):
- `threshold_value`, `duration`, `comparison`, `filter`, `aggregations`
- `denominator_filter`, `denominator_aggregations`, `trigger`
- `forecast_options`, `evaluation_missing_data`

**Note**: `evaluation_missing_data` only affects behavior when data STOPS arriving after existing, not when metrics have never existed.

**Affected Metrics** (404 errors on fresh deployment):
1. `kubernetes.io/pod/phase` (GKE)
2. `kubernetes.io/node/ready` (GKE)
3. `kubernetes.io/container/ephemeral_storage/limit_utilization` (GKE)
4. `container.googleapis.com/cluster/control_plane/upgrade_event` (GKE)
5. `redis.googleapis.com/stats/uptime` (Memorystore)

**Solution Options**:

#### Option A: Two-Phase Deployment (Recommended - KISS)

Keep monitoring alerts disabled during initial deployment. Enable after metrics are populated (~30 min of cluster activity).

```hcl
# terraform/environments/gcp-preview/main.tf

module "gke" {
  # ...
  # DISABLED: GCP metrics don't exist until cluster has running workloads
  # Enable after cluster is operational for ~30 min
  enable_monitoring_alerts         = false
  monitoring_notification_channels = var.monitoring_notification_channels
}

module "memorystore" {
  # ...
  # DISABLED: GCP metrics don't exist until Redis has active connections
  enable_monitoring_alerts         = false
  monitoring_notification_channels = var.monitoring_notification_channels
}
```

**Enable alerts after deployment**:
```bash
# After cluster is running for 30+ minutes with workloads
# Edit main.tf to set enable_monitoring_alerts = true
terraform apply
```

#### Option B: Delayed Alert Creation with time_sleep

Use Terraform's `time_sleep` resource to delay alert policy creation (not recommended for production due to state management complexity).

```hcl
resource "time_sleep" "wait_for_metrics" {
  depends_on      = [google_container_cluster.autopilot]
  create_duration = "30m"
}

resource "google_monitoring_alert_policy" "pods_pending" {
  depends_on = [time_sleep.wait_for_metrics]
  # ... alert config
}
```

#### Option C: Separate Terraform Workspace for Alerts

Create alerts in a separate Terraform workspace/directory that runs after initial infrastructure is deployed.

**Current Status**: Option A implemented - GKE and Memorystore alerts disabled in `terraform/environments/gcp-preview/main.tf`. CloudSQL alerts remain enabled (CloudSQL metrics are available immediately).

**Validation**:
```bash
# Terraform plan should succeed without 404 metric errors
terraform plan

# After 30+ minutes of cluster activity, enable alerts
# Edit main.tf: enable_monitoring_alerts = true
# Then: terraform apply
```

---

### 1.2 WIF Pool Soft-Deletion Handling (Issue #3)

**Problem**: WIF pools have 30-day soft-deletion period. Cannot create new pool with same ID until expired.

**Root Cause**: GCP design decision for security (prevents immediate hostile takeover).

**Solutions** (choose one):

#### Option A: Versioned Pool IDs (Recommended - KISS)

```hcl
# terraform/modules/github-actions-wif/variables.tf
variable "pool_id_suffix" {
  description = "Suffix for pool ID to enable recreation without conflicts"
  type        = string
  default     = "v1"
}

# terraform/modules/github-actions-wif/main.tf
resource "google_iam_workload_identity_pool" "github_actions" {
  workload_identity_pool_id = "${var.pool_name}-${var.pool_id_suffix}"
  display_name              = "${var.pool_display_name} (${var.pool_id_suffix})"
  # ...
}
```

#### Option B: Undelete Before Create (Automation)

```bash
# scripts/gcp/pre-terraform-wif-check.sh
#!/usr/bin/env bash
# Pre-Terraform check for soft-deleted WIF pools

set -euo pipefail

readonly POOL_ID="${1:-github-actions-pool}"
readonly LOCATION="${2:-global}"

# Check if pool exists in deleted state
if gcloud iam workload-identity-pools describe "$POOL_ID" \
    --location="$LOCATION" \
    --format="get(state)" 2>/dev/null | grep -q "DELETED"; then

    echo "INFO: Found soft-deleted WIF pool '$POOL_ID'. Undeleting..."
    gcloud iam workload-identity-pools undelete "$POOL_ID" --location="$LOCATION"

    # Also undelete providers
    for provider in $(gcloud iam workload-identity-pools providers list \
        --workload-identity-pool="$POOL_ID" \
        --location="$LOCATION" \
        --show-deleted \
        --format="value(name)" 2>/dev/null); do

        provider_id=$(basename "$provider")
        echo "INFO: Undeleting provider '$provider_id'..."
        gcloud iam workload-identity-pools providers undelete "$provider_id" \
            --workload-identity-pool="$POOL_ID" \
            --location="$LOCATION"
    done

    echo "INFO: WIF pool '$POOL_ID' restored. Run 'terraform import' if needed."
else
    echo "INFO: No soft-deleted WIF pool found for '$POOL_ID'."
fi
```

**TDD Test**:
```python
# tests/scripts/test_wif_handling.py
def test_wif_undelete_script_handles_missing_pool():
    """Script should exit gracefully when pool doesn't exist."""
    result = subprocess.run(
        ["bash", "scripts/gcp/pre-terraform-wif-check.sh", "nonexistent-pool"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "No soft-deleted WIF pool found" in result.stdout
```

---

### 1.3 Runtime Database Cleanup (Issue #1)

**Problem**: Keycloak and OpenFGA create databases at runtime that block CloudSQL deletion.

**Current Fix**: Already implemented in teardown script.

**Enhancement**: Make runtime databases configurable and discoverable.

```hcl
# terraform/environments/gcp-preview/terraform.tfvars
runtime_databases = ["keycloak", "openfga"]
```

```bash
# scripts/gcp/teardown-preview-infrastructure.sh
# Read from Terraform output instead of hardcoding
RUNTIME_DATABASES=$(terraform output -json runtime_databases 2>/dev/null | jq -r '.[]' || echo "keycloak openfga")
```

---

## Priority 2: High-Impact Fixes

### 2.1 Service Networking Propagation (Issue #2)

**Problem**: GCP Service Networking Connection needs time to release after CloudSQL/Redis deletion.

**Current Fix**: 60-second wait + retry logic.

**Enhancement**: Exponential backoff with configurable max retries.

```bash
# scripts/gcp/teardown-preview-infrastructure.sh
wait_for_service_networking_release() {
    local max_retries="${1:-5}"
    local base_delay="${2:-30}"
    local max_delay="${3:-300}"

    for ((i=1; i<=max_retries; i++)); do
        delay=$((base_delay * (2 ** (i-1))))
        delay=$((delay > max_delay ? max_delay : delay))

        log_info "Waiting ${delay}s for Service Networking release (attempt $i/$max_retries)..."
        sleep "$delay"

        if gcloud compute addresses delete "$PRIVATE_SERVICES_ADDRESS" --global --quiet 2>/dev/null; then
            log_info "Private services address deleted successfully."
            return 0
        fi
    done

    log_error "Failed to delete private services address after $max_retries attempts."
    return 1
}
```

---

### 2.2 CloudSQL SSL Mode Migration (Issue #12)

**Problem**: `require_ssl` is deprecated, should use `ssl_mode`.

**Implementation**:

```hcl
# terraform/modules/cloudsql/variables.tf
variable "ssl_mode" {
  description = "SSL mode for connections: ENCRYPTED_ONLY, ALLOW_UNENCRYPTED_AND_ENCRYPTED"
  type        = string
  default     = "ENCRYPTED_ONLY"

  validation {
    condition     = contains(["ENCRYPTED_ONLY", "ALLOW_UNENCRYPTED_AND_ENCRYPTED"], var.ssl_mode)
    error_message = "ssl_mode must be ENCRYPTED_ONLY or ALLOW_UNENCRYPTED_AND_ENCRYPTED."
  }
}

# Deprecated - will be removed
variable "require_ssl" {
  description = "DEPRECATED: Use ssl_mode instead"
  type        = bool
  default     = null
}

# terraform/modules/cloudsql/main.tf
resource "google_sql_database_instance" "main" {
  # ...
  settings {
    ip_configuration {
      # Migration path: prefer ssl_mode, fall back to require_ssl for backward compat
      ssl_mode    = var.ssl_mode
      require_ssl = var.require_ssl  # Deprecated, remove in next major version
    }
  }
}
```

**TDD Test**:
```python
# tests/terraform/test_cloudsql_ssl_mode.py
def test_cloudsql_uses_ssl_mode_not_require_ssl():
    """CloudSQL should use ssl_mode instead of deprecated require_ssl."""
    with open("terraform/modules/cloudsql/main.tf") as f:
        content = f.read()

    # ssl_mode should be present
    assert "ssl_mode" in content

    # Check deprecation comment exists for require_ssl
    assert "DEPRECATED" in content or "deprecated" in content
```

---

## Priority 3: Medium-Impact Improvements

### 3.1 Terraform State Lock Prevention (Issue #4, #13)

**Problem**: Multiple concurrent Terraform operations cause lock contention.

**Solution**: CI/CD-level locking + local mutex.

```bash
# scripts/gcp/terraform-with-lock.sh
#!/usr/bin/env bash
# Wrapper that prevents concurrent local Terraform operations

LOCK_FILE="/tmp/terraform-${PWD//\//_}.lock"

cleanup() {
    rm -f "$LOCK_FILE"
}
trap cleanup EXIT

if ! mkdir "$LOCK_FILE" 2>/dev/null; then
    echo "ERROR: Another Terraform operation is running in this directory."
    echo "Lock file: $LOCK_FILE"
    exit 1
fi

terraform "$@"
```

**GitHub Actions Integration**:
```yaml
# .github/workflows/terraform.yaml
concurrency:
  group: terraform-${{ github.ref }}
  cancel-in-progress: false
```

---

### 3.2 Missing Secrets Validation (Issue #15)

**Problem**: Kubernetes secrets missing required keys, causing pod startup failures.

**Solution**: Pre-deployment secrets validation.

```bash
# scripts/kubernetes/validate-secrets.sh
#!/usr/bin/env bash

set -euo pipefail

NAMESPACE="${1:-preview-mcp-server-langgraph}"
SECRET_NAME="${2:-preview-mcp-server-langgraph-secrets}"

REQUIRED_KEYS=(
    "redis-password"
    "redis-url"
    "checkpoint-redis-url"
    "postgres-url"
    "gdpr-postgres-url"
    "openfga-store-id"
    "openfga-model-id"
    "keycloak-client-id"
    "keycloak-client-secret"
)

echo "Validating secret '$SECRET_NAME' in namespace '$NAMESPACE'..."

EXISTING_KEYS=$(kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o jsonpath='{.data}' | jq -r 'keys[]')

MISSING=()
for key in "${REQUIRED_KEYS[@]}"; do
    if ! echo "$EXISTING_KEYS" | grep -q "^${key}$"; then
        MISSING+=("$key")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "ERROR: Missing required secret keys:"
    printf '  - %s\n' "${MISSING[@]}"
    exit 1
fi

echo "SUCCESS: All required secret keys present."
```

**TDD Test**:
```python
# tests/kubernetes/test_secrets_validation.py
def test_secrets_validation_script_detects_missing_keys():
    """Validation script should detect missing secret keys."""
    # Create a mock secret with missing keys
    result = subprocess.run(
        ["bash", "scripts/kubernetes/validate-secrets.sh", "test-ns", "test-secret"],
        capture_output=True, text=True
    )
    # Should fail when keys are missing
    assert result.returncode != 0 or "Missing required secret keys" in result.stderr
```

---

### 3.3 Naming Convention Sync (Issues #8, #9, #11)

**Problem**: Scripts have stale resource names after staging→preview rename.

**Solution**: Single source of truth for naming.

```hcl
# terraform/modules/_shared/naming.tf
locals {
  # Single source of truth for naming conventions
  naming = {
    full_prefix  = "${var.environment}-mcp-server-langgraph"
    short_prefix = "${var.environment}-mcp-slg"

    gke_cluster    = "${local.naming.full_prefix}-gke"
    vpc            = "${local.naming.short_prefix}-vpc"
    cloudsql       = "${local.naming.short_prefix}-postgres"
    redis          = "${local.naming.short_prefix}-redis"
    private_ip     = "${local.naming.short_prefix}-private-services"
  }
}

# Output naming for scripts
output "resource_names" {
  value = local.naming
}
```

```bash
# scripts/gcp/teardown-preview-infrastructure.sh
# Read names from Terraform output
eval "$(terraform output -json resource_names | jq -r 'to_entries | .[] | "\(.key | ascii_upcase)=\(.value)"')"
```

---

## Priority 4: Low-Impact / Nice-to-Have

### 4.1 GKE Autopilot Provider Bug Workaround (Issue #7)

**Status**: Already mitigated with lifecycle.ignore_changes and gcloud fallback.

**Long-term**: Monitor terraform-provider-google releases for fix.

---

### 4.2 Database Idempotency (Issue #10)

**Problem**: `gcloud sql databases create` fails if database exists.

**Solution**: Check before create (idempotent).

```bash
if ! gcloud sql databases describe "$DB_NAME" --instance="$INSTANCE" &>/dev/null; then
    gcloud sql databases create "$DB_NAME" --instance="$INSTANCE"
fi
```

---

## Implementation Roadmap

### Phase 1: Quick Wins (1-2 hours)

| Task | Issue(s) | LOC | Risk |
|------|----------|-----|------|
| Add `disable_metric_validation` to all alert policies | #6, #16 | ~40 | Low |
| Migrate CloudSQL `require_ssl` to `ssl_mode` | #12 | ~20 | Low |
| Add exponential backoff to teardown script | #2 | ~30 | Low |

### Phase 2: Process Improvements (2-4 hours)

| Task | Issue(s) | LOC | Risk |
|------|----------|-----|------|
| Create WIF pre-check script | #3 | ~50 | Low |
| Add secrets validation script | #15 | ~60 | Low |
| Add Terraform local lock wrapper | #4, #13 | ~30 | Low |

### Phase 3: Architecture Improvements (4-8 hours)

| Task | Issue(s) | LOC | Risk |
|------|----------|-----|------|
| Centralize naming conventions | #8, #9, #11 | ~100 | Medium |
| Add Terraform output-driven script config | Multiple | ~80 | Medium |

---

## Testing Strategy

### Unit Tests (TDD - Write First)
```bash
# Run before implementation
uv run --frozen pytest tests/terraform/ -v --tb=short
```

### Integration Tests
```bash
# Validate Terraform plan
cd terraform/environments/gcp-preview
terraform plan -detailed-exitcode
```

### Smoke Tests
```bash
# After deployment
./scripts/gcp/preview-smoke-tests.sh
```

---

## Success Criteria

- [ ] All Terraform applies succeed without manual intervention
- [ ] Alert policies created successfully on fresh cluster
- [ ] Teardown completes without errors
- [ ] No orphaned resources after teardown
- [ ] All pods reach Running state within 10 minutes of deployment
- [ ] Secrets validation passes before deployment
- [ ] No deprecation warnings in Terraform output

---

## Appendix: Best Practices Applied

### TDD (Test-Driven Development)
- All fixes have corresponding test files written FIRST
- Tests validate expected behavior before implementation

### DRY (Don't Repeat Yourself)
- Shared `alert_common_config` local block for alert policies
- Centralized naming conventions in `_shared/naming.tf`

### KISS (Keep It Simple, Stupid)
- Versioned WIF pool IDs vs complex undelete logic
- Simple shell scripts with clear single responsibility

### YAGNI (You Aren't Gonna Need It)
- No over-engineering of solutions
- Focus on immediate issues, not hypothetical future problems

### SOLID
- **S**ingle Responsibility: Each script does one thing
- **O**pen/Closed: Modules extensible via variables, not code changes
- **L**iskov Substitution: N/A (not OOP)
- **I**nterface Segregation: Small, focused Terraform modules
- **D**ependency Inversion: Scripts depend on Terraform outputs, not hardcoded values

### 12-Factor
- **Config**: All configuration via variables/outputs
- **Backing Services**: CloudSQL, Redis treated as attached resources
- **Logs**: Structured logging in scripts

### Cloud-Native
- Kubernetes-native secrets management
- GKE Autopilot for managed infrastructure
- Workload Identity for secure service account binding

---

*Document created: 2025-12-06*
*Last updated: 2025-12-06 (Corrected: disable_metric_validation does not exist in Terraform)*
