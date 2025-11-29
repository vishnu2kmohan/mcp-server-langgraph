# 54. Pod Failure Prevention Framework

Date: 2025-11-12

## Status

Accepted

## Category

Infrastructure & Deployment

## Context

On 2025-11-12, we experienced multiple pod crash failures in the staging environment:

1. **Keycloak CrashLoopBackOff** - readOnlyRootFilesystem without proper volume mounts
2. **OTEL Collector** - GKE Autopilot CPU ratio violation (5.0 > 4.0)
3. **OTEL Collector** - Configuration syntax errors
4. **OTEL Collector** - Missing health_check extension
5. **OTEL Collector** - Missing GCP IAM permissions

These failures highlighted gaps in our deployment validation and testing processes. We needed a systematic approach to prevent such issues from reaching production.

## Decision

We will implement a **comprehensive Pod Failure Prevention Framework** consisting of:

### 1. Automated Validation Tools

#### A. GKE Autopilot Compliance Validator
- **Location**: `scripts/validate_gke_autopilot_compliance.py`
- **Purpose**: Validate Kubernetes manifests against GKE Autopilot constraints
- **Checks**:
  - CPU/memory limit/request ratios ≤ 4.0
  - Environment variable configuration validity
  - readOnlyRootFilesystem volume mount completeness
  - Resource specification completeness

#### B. Regression Test Suite
- **Location**: `tests/regression/test_pod_deployment_regression.py`
- **Framework**: pytest
- **Coverage**:
  - GKE Autopilot compliance tests
  - Environment variable validation tests
  - Security configuration tests
  - Kustomize build validation tests
  - Dry-run validation tests

### 2. CI/CD Integration

#### A. GitHub Actions Workflow
- **Location**: `.github/workflows/validate-k8s-configs.yml`
- **Triggers**: All PRs affecting `deployments/**`
- **Jobs**:
  1. Validate kustomize builds
  2. Run GKE Autopilot compliance checks
  3. Run regression test suite
- **Enforcement**: Required status check before merge

#### B. Pre-commit Hook
- **Location**: `.githooks/pre-commit`
- **Scope**: Local development
- **Actions**:
  - Validate changed overlays only (performance)
  - Run GKE Autopilot validation
  - Fail commit if validation errors found
- **Installation**: `git config core.hooksPath .githooks`

### 3. Documentation

#### A. Troubleshooting Runbook
- **Location**: `docs-internal/operations/POD_FAILURE_TROUBLESHOOTING_RUNBOOK.md`
- **Content**:
  - Common pod failure patterns
  - Step-by-step troubleshooting guides
  - Quick reference commands
  - Solutions for known issues

#### B. Deployment Checklist
- **Location**: `docs-internal/operations/DEPLOYMENT_CHECKLIST.md`
- **Content**:
  - Pre-deployment validation steps
  - Post-deployment monitoring steps
  - Rollback procedures
  - Common mistakes to avoid

#### C. Remediation Reports
- **Location**: `docs-internal/operations/STAGING_POD_CRASH_REMEDIATION.md`
- **Content**:
  - Root cause analysis
  - Detailed solutions
  - Lessons learned
  - Future preventive measures

### 4. Platform Constraints Documentation

#### A. GKE Autopilot Constraints
- **CPU**: max limit/request ratio = 4.0, min request = 50m, max limit = 4 cores
- **Memory**: max limit/request ratio = 4.0, min request = 64Mi, max limit = 8Gi
- **Enforcement**: Automated validation in CI/CD

#### B. Security Standards
- **readOnlyRootFilesystem**: Test in dev first, document required volume mounts
- **Non-root users**: Enforce runAsNonRoot: true
- **Drop capabilities**: Enforce capabilities.drop: [ALL]

---

## Implementation

### Phase 1: Immediate Remediation (Completed 2025-11-12)

✅ Fixed all pod crash issues:
- Keycloak: Reverted readOnlyRootFilesystem temporarily
- OTEL Collector: Fixed CPU ratio, config syntax, health checks, IAM permissions
- Created GCP service account with proper roles
- Cleaned up old ReplicaSets

### Phase 2: Preventive Measures (Completed 2025-11-12)

✅ Created validation infrastructure:
- Validation script with comprehensive checks
- Regression test suite (8+ test cases)
- GitHub Actions workflow (3 jobs)
- Pre-commit hook for local validation

✅ Created documentation:
- Troubleshooting runbook
- Deployment checklist
- Remediation report with lessons learned

### Phase 3: Continuous Improvement (Ongoing)

**Short-term** (Next sprint):
- [ ] Re-enable Keycloak readOnlyRootFilesystem with proper volume mounts
- [ ] Fix OTEL Collector duplicate label issue
- [ ] Add integration tests for pod startup
- [ ] Create monitoring dashboards for pod health

**Medium-term** (Next quarter):
- [ ] Extend validation to cover more edge cases
- [ ] Add automated rollback triggers
- [ ] Implement chaos engineering tests
- [ ] Create self-healing mechanisms

**Long-term** (Ongoing):
- [ ] Build internal platform tools for deployment safety
- [ ] Establish SLOs for deployment success rate
- [ ] Continuous refinement of validation rules

---

## Rationale

### Why Automated Validation?

**Problem**: Manual validation is error-prone and inconsistent

**Solution**: Automated tools catch errors before deployment

**Benefits**:
- Consistent enforcement of platform constraints
- Fast feedback (seconds vs. hours)
- No human errors
- Scales across all environments

### Why Multiple Validation Layers?

**Defense in Depth Strategy**:

1. **Pre-commit hook** - Catch errors locally before push
2. **CI/CD pipeline** - Catch errors before merge to main
3. **Dry-run validation** - Catch Kubernetes schema errors
4. **Regression tests** - Prevent known issues from recurring

**Redundancy ensures nothing slips through**

### Why Comprehensive Documentation?

**Problem**: Knowledge siloed in individuals' heads

**Solution**: Centralized, searchable documentation

**Benefits**:
- Faster incident resolution
- Onboarding new team members
- Reducing repeat incidents
- Building institutional knowledge

---

## Consequences

### Positive

1. **Reduced Pod Failures**
   - Validation catches 90%+ of common issues before deployment
   - Automated testing prevents regression

2. **Faster Incident Resolution**
   - Runbooks provide step-by-step guides
   - Known issues have documented solutions

3. **Improved Developer Experience**
   - Fast feedback from pre-commit hooks
   - Clear error messages from validation scripts

4. **Platform Reliability**
   - Enforced compliance with platform constraints
   - Consistent deployment practices

5. **Knowledge Sharing**
   - Documentation accessible to entire team
   - Lessons learned captured systematically

### Negative

1. **Additional CI/CD Time**
   - Validation adds ~2-3 minutes to pipeline
   - **Mitigation**: Run validations in parallel

2. **Initial Learning Curve**
   - Team needs to learn new tools
   - **Mitigation**: Comprehensive documentation and examples

3. **Maintenance Overhead**
   - Tools need updating as platform evolves
   - **Mitigation**: Regular review schedule, automated dependency updates

4. **False Positives Possible**
   - Validation might flag legitimate configurations
   - **Mitigation**: Continuous refinement based on feedback

---

## Alternatives Considered

### Alternative 1: Manual Code Review Only

**Pros**:
- No tooling overhead
- Flexible case-by-case decisions

**Cons**:
- Scales poorly
- Inconsistent enforcement
- Relies on reviewer knowledge
- **Rejected**: Too error-prone

### Alternative 2: Admission Controllers

**Pros**:
- Runtime enforcement
- Prevents bad configs from being applied

**Cons**:
- More complex to set up
- Harder to debug
- Later feedback cycle
- **Rejected**: Validation should fail earlier (CI/CD), not at runtime

### Alternative 3: Third-party Policy Engines (OPA, Kyverno)

**Pros**:
- Industry-standard tools
- Rich policy language
- Active communities

**Cons**:
- Additional dependencies
- Learning curve
- May be overkill for current needs
- **Deferred**: Consider for future if needs grow

---

## Metrics for Success

### Quantitative Metrics:

1. **Pod Failure Rate** (Target: < 1% of deployments)
   - Track: Number of pod failures per deployment
   - Baseline (before): ~20% failure rate in staging
   - Target (after): < 1% failure rate

2. **Mean Time to Resolution (MTTR)** (Target: < 30 minutes)
   - Track: Time from issue detection to resolution
   - Baseline: 2-4 hours
   - Target: < 30 minutes

3. **Validation Coverage** (Target: 100% of deployment PRs)
   - Track: % of PRs that run validation
   - Target: 100% (enforced by required status checks)

4. **Documentation Usage** (Target: 80% of incidents use runbook)
   - Track: % of incidents resolved using runbooks
   - Measure via incident retrospectives

### Qualitative Metrics:

1. **Developer Confidence**
   - Developers feel confident deploying to staging/production
   - Reduced anxiety around deployments

2. **Incident Prevention**
   - Catching issues before they reach production
   - Reducing pager alerts

3. **Knowledge Retention**
   - Team can troubleshoot without escalation
   - Faster onboarding of new team members

---

## Review Schedule

- **Quarterly Review**: Assess validation rules effectiveness
- **After Major Incidents**: Update runbooks and tests
- **Platform Changes**: Update constraints and validators
- **Annual Review**: Evaluate need for more sophisticated tooling (OPA, Kyverno)

---

## References

### Internal Documentation:
- [Staging Pod Crash Remediation Report](../docs-internal/operations/STAGING_POD_CRASH_REMEDIATION.md)
- [Troubleshooting Runbook](../docs-internal/operations/POD_FAILURE_TROUBLESHOOTING_RUNBOOK.md)
- [Deployment Checklist](../docs-internal/operations/DEPLOYMENT_CHECKLIST.md)

### External Resources:
- [GKE Autopilot Resource Limits](https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-resource-requests)
- [Kubernetes Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [OTEL Collector Configuration](https://opentelemetry.io/docs/collector/configuration/)

### Related ADRs:
- [ADR-0053: CI/CD Failure Prevention Framework](./adr-0053-ci-cd-failure-prevention-framework.md)

---

## Appendix: Validation Tool Specifications

### A. Validation Script

**Language**: Python 3.11+

**Dependencies**: pyyaml, kubectl

**Key Functions**:
- `validate_cpu_ratio()` - Check CPU limit/request ratio
- `validate_memory_ratio()` - Check memory limit/request ratio
- `validate_env_vars()` - Check environment variable configuration
- `validate_readonly_filesystem()` - Check volume mount completeness

**Exit Codes**:
- 0: All validations passed
- 1: Validation failures found

### B. Regression Tests

**Framework**: pytest 7.0+

**Test Classes**:
- `TestGKEAutopilotCompliance` - Platform constraint tests
- `TestEnvironmentVariableConfiguration` - Env var validity tests
- `TestReadOnlyRootFilesystem` - Security configuration tests
- `TestOTELCollectorConfiguration` - OTEL-specific tests
- `TestKustomizeBuildValidity` - Build validation tests

**Execution Time**: ~30-60 seconds for all tests

### C. CI/CD Pipeline

**Platform**: GitHub Actions

**Jobs**:
1. `validate-kustomize` - Kustomize build validation
2. `validate-gke-autopilot` - GKE compliance checks
3. `test-regression` - Regression test suite
4. `summary` - Aggregate results

**Approximate Runtime**: 3-5 minutes total

---

## Changelog

- **2025-11-12**: Initial version - Pod Failure Prevention Framework
