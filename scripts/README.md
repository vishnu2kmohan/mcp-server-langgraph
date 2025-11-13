# Deployment Scripts

Automated deployment scripts for all cloud providers implementing 11 Kubernetes best practices.

## Available Scripts

- `deploy-gcp-gke.sh` - Deploy to Google Cloud Platform (GKE)
- `deploy-aws-eks.sh` - Deploy to Amazon Web Services (EKS)
- `deploy-azure-aks.sh` - Deploy to Microsoft Azure (AKS)

## Prerequisites

### Common Requirements

- `kubectl` - Kubernetes command-line tool
- `helm` - Kubernetes package manager
- `terraform` - Infrastructure as Code tool
- `jq` - JSON processor (for verification steps)
- `git` - For VPA installation

### Cloud-Specific Requirements

**GCP (GKE)**:
- `gcloud` CLI
- Authenticated with GCP: `gcloud auth login`
- Project set: `gcloud config set project PROJECT_ID`

**AWS (EKS)**:
- `aws` CLI
- Configured credentials: `aws configure`
- Or use IAM roles/instance profiles

**Azure (AKS)**:
- `az` CLI
- Logged in: `az login`

## Usage

### GCP GKE Deployment

```bash
# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export GKE_CLUSTER_NAME="mcp-production"  # Optional, defaults to mcp-production
export GCP_REGION="us-central1"           # Optional, defaults to us-central1

# Run deployment
./scripts/deploy-gcp-gke.sh
```

### AWS EKS Deployment

```bash
# Set environment variables
export AWS_REGION="us-east-1"             # Optional, defaults to us-east-1
export EKS_CLUSTER_NAME="mcp-production"  # Optional, defaults to mcp-production
export AWS_ACCOUNT_ID="123456789012"      # Optional, auto-detected if not set

# Run deployment
./scripts/deploy-aws-eks.sh
```

### Azure AKS Deployment

```bash
# Set environment variables
export AZURE_RESOURCE_GROUP="mcp-production-rg"  # Optional
export AKS_CLUSTER_NAME="mcp-production"         # Optional
export AZURE_LOCATION="eastus"                   # Optional, defaults to eastus

# Run deployment
./scripts/deploy-azure-aks.sh
```

## Platform Automation Status

| Script | Status | Notes |
|--------|--------|-------|
| `deploy-gcp-gke.sh` | ✅ **Production Ready** | Full automation with dev/staging/prod environments |
| `deploy-aws-eks.sh` | ✅ **Production Ready** | Full automation with dev/staging/prod environments |
| `deploy-azure-aks.sh` | ❌ **Manual Only** | Terraform automation not yet available, see [aks.mdx](../docs/deployment/kubernetes/aks.mdx) |

**Note**: AKS deployment currently requires manual setup using Azure CLI. The script will display instructions pointing to the manual runbook.

## What Each Script Does

All deployment scripts follow the same pattern and implement all 11 best practices:

1. **Prerequisite Checks** - Validates all required tools are installed
2. **Infrastructure Deployment** - Deploys cloud resources via Terraform
3. **Kubectl Configuration** - Configures kubectl access to the cluster
4. **Velero Backup/DR** - Installs Velero with cloud-specific storage
5. **Karpenter (EKS only)** - Deploys intelligent autoscaling
6. **Namespace & Security** - Creates namespace with PSS and network policies
7. **Istio Service Mesh** - Installs/configures Istio with mTLS STRICT
8. **Monitoring Stack** - Deploys Loki, Kubecost with cloud billing integration
9. **Application Deployment** - Deploys app with Helm using cloud-managed databases
10. **VPA Deployment** - Installs Vertical Pod Autoscalers
11. **Verification** - Validates all components are working correctly

## Environment Selection

The GKE and EKS scripts now support environment selection:

**GKE Environments**:
```bash
export GCP_ENVIRONMENT=gcp-dev      # Development environment
export GCP_ENVIRONMENT=gcp-staging  # Staging environment
export GCP_ENVIRONMENT=gcp-prod     # Production environment (default)
```

**EKS Environments**:
```bash
export AWS_ENVIRONMENT=aws-dev      # Development (minimal cost)
export AWS_ENVIRONMENT=aws-staging  # Staging (cost-optimized)
export AWS_ENVIRONMENT=prod         # Production (default)
```

## Deployment Time

Approximate deployment times (automated deployments):

- **GKE**: 25-35 minutes
- **EKS**: 30-40 minutes (includes Karpenter)
- **AKS**: Manual deployment only (see documentation)

## Post-Deployment

After successful deployment, each script outputs next steps including:

- How to access Kubecost dashboard
- How to access Grafana
- How to view Velero backups
- How to verify Istio mTLS
- How to monitor costs in cloud console

## Troubleshooting

### Common Issues

**Issue**: Script exits with "command not found"
**Solution**: Install the missing tool (kubectl, helm, terraform, cloud CLI)

**Issue**: Terraform fails with authentication error
**Solution**: Ensure you're logged into the correct cloud provider

**Issue**: Pods stuck in Pending state
**Solution**: Check cluster has sufficient capacity and multiple availability zones

**Issue**: Istio sidecar not injected
**Solution**: Ensure namespace has `istio-injection: enabled` label

### Getting Help

1. Check logs: `kubectl logs -n <namespace> <pod-name>`
2. Check events: `kubectl get events -n <namespace> --sort-by='.lastTimestamp'`
3. Verify resources: `kubectl get all -n <namespace>`
4. Check Istio: `istioctl analyze -n <namespace>`

## Cleanup

To remove all deployed resources:

```bash
# GCP
terraform destroy -chdir=terraform/environments/gcp
gcloud container clusters delete $CLUSTER_NAME --region=$REGION

# AWS
terraform destroy -chdir=terraform/environments/aws
aws eks delete-cluster --name $CLUSTER_NAME --region $REGION

# Azure
terraform destroy -chdir=terraform/environments/azure
az aks delete --name $CLUSTER_NAME --resource-group $RESOURCE_GROUP
```

## Manual Deployment

If you prefer manual deployment or need to customize steps:

1. See `docs/IMPLEMENTATION_SUMMARY.md` for detailed deployment checklist
2. See `docs/kubernetes-best-practices-implementation.md` for comprehensive guide
3. See individual component READMEs in respective directories

---

## Documentation Validation Scripts (TDD)

### Overview

Comprehensive validation infrastructure built with Test-Driven Development to ensure documentation quality and prevent regressions.

**Key Scripts**:
- `fix_mdx_syntax.py` - Auto-fix MDX syntax errors
- `check_internal_links.py` - Validate internal links
- `check_version_consistency.py` - Ensure version consistency

### `fix_mdx_syntax.py`

**Purpose**: Automatically detect and fix common MDX syntax errors that break Mintlify builds.

**Usage**:
```bash
# Fix all MDX files
python3 scripts/fix_mdx_syntax.py --all

# Fix specific file
python3 scripts/fix_mdx_syntax.py --file docs/guides/installation.mdx

# Preview changes without modifying (dry-run)
python3 scripts/fix_mdx_syntax.py --all --dry-run

# Via Makefile
make docs-fix-mdx
```

**Patterns Fixed**:
1. ``` followed by ```bash (duplicate language tag)
2. ```bash before </CodeGroup> (should be just ```)
3. ```python before <Note> or other MDX tags
4. ```yaml before markdown text (**bold**, ##heading)

**Test Suite**: `tests/test_mdx_validation.py` (18 tests)

**Example**:
```markdown
Before:
```bash
echo "test"
```bash
<Note>Important!</Note>

After:
```bash
echo "test"
```

<Note>Important!</Note>
```

---

### `check_internal_links.py`

**Purpose**: Validate that internal documentation links point to existing files.

**Usage**:
```bash
# Check all documentation
python3 scripts/check_internal_links.py --all

# Check specific file
python3 scripts/check_internal_links.py --file docs/guide.mdx

# Via Makefile
make docs-validate-links
```

**Validates**:
- Markdown links: `[text](../path.mdx)`
- Absolute links: `[text](/api-reference/auth)`
- MDX Link components: `<Link href="/path">text</Link>`
- Card/Button hrefs: `<Card href="/path">`

**Handles**:
- Relative paths with `../` and `./`
- Absolute paths from docs root
- Files with/without `.mdx` extension
- Anchor links (`#section`)

**Test Suite**: `tests/test_link_checker.py` (10 tests)

**Example Output**:
```
Checking 235 files for broken internal links...

❌ docs/guides/authentication.mdx
   Broken: ../setup/nonexistent.mdx
   Broken: /api-reference/missing-endpoint

📊 Summary: 2 broken links in 1 file
```

---

### `check_version_consistency.py`

**Purpose**: Ensure version numbers in documentation match the current project version.

**Usage**:
```bash
# Check all documentation
python3 scripts/check_version_consistency.py

# Via Makefile
make docs-validate-version
```

**Detects**:
- Version numbers in code examples
- API version references
- Outdated installation instructions
- Dependency version mismatches

**Intelligent Skipping**:
- Release notes (intentionally historical)
- ADR-0018 (version strategy examples)
- CHANGELOG.md (historical records)
- Dependency versions (different versioning)

**Current Version**: Reads from `pyproject.toml` [project.version]

**Example Output**:
```
Current version: 2.8.0

📄 docs/guides/installation.mdx
   Line 45: v2.6.0 → should be v2.8.0
   Context: Install mcp-server-langgraph version 2.6.0 or later

📊 Summary: 12 outdated version references in 8 files
```

---

## Makefile Integration

Quick access to all validation tools:

```bash
make docs-validate            # Run all validations
make docs-validate-mdx        # MDX syntax only
make docs-validate-links      # Internal links only
make docs-validate-version    # Version consistency
make docs-validate-mintlify   # Mintlify build check
make docs-fix-mdx             # Auto-fix MDX errors
make docs-test                # Run validation tests
make docs-audit               # Comprehensive audit
```

---

## Pre-commit Integration

Scripts run automatically on every commit:

```bash
# Install pre-commit hooks
pre-commit install

# Run all hooks manually
pre-commit run --all-files

# Run specific documentation hooks
pre-commit run fix-mdx-syntax --all-files
pre-commit run check-doc-links --all-files
```

**Configured Hooks**:
- `fix-mdx-syntax` - Auto-fixes MDX syntax
- `check-doc-links` - Validates internal links
- `check-version-consistency` - Checks versions
- `validate-mintlify-docs` - Validates docs.json
- `validate-documentation-quality` - Comprehensive checks

See `.pre-commit-config.yaml` for complete configuration.

---

## CI/CD Integration

Automated validation on every pull request:

**Workflow**: `.github/workflows/docs-validation.yml`

**Jobs**:
1. **mdx-syntax-validation** - Tests MDX syntax, runs validation scripts
2. **mintlify-validation** - Builds docs, creates issues on failure
3. **link-validation** - Checks all internal links
4. **version-consistency** - Validates version references
5. **summary** - Aggregates results, posts PR comment

**PR Comments**: Automatically posted with validation status table

**Artifacts**: Mintlify logs uploaded on failure (7-day retention)

---

## Test-Driven Development

All validation scripts have comprehensive test suites:

```bash
# Run all documentation validation tests
pytest tests/test_mdx_validation.py tests/test_link_checker.py -v

# With coverage report
pytest tests/test_mdx_validation.py tests/test_link_checker.py \
  --cov=scripts \
  --cov-report=html \
  --cov-report=term-missing

# Via Makefile
make docs-test
```

**Test Coverage**:
- MDX Validation: 18 tests
- Link Checking: 10 tests
- Pattern Detection: 100% coverage
- Real-world Examples: 7 tests
- Edge Cases: 6 tests

---

## Documentation

**Comprehensive Guide**: `docs-internal/VALIDATION_INFRASTRUCTURE.md`

**Topics Covered**:
- Quick start guide
- Architecture overview
- Usage patterns
- TDD principles
- Error prevention matrix
- Troubleshooting guide
- Best practices
- Future enhancements

**Also See**:
- `docs-internal/DOCUMENTATION_AUDIT_2025-11-12_FIXES.md` - Audit results
- `TESTING.md` - Overall testing strategy
- `.pre-commit-config.yaml` - Hook configuration
- `.github/workflows/docs-validation.yml` - CI/CD workflow

---

**Last Updated**: 2025-11-12
