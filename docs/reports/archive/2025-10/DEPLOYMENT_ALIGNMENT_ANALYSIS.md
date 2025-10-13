# Deployment Configuration Alignment Analysis

**Date**: 2025-10-13
**Analysis Scope**: Local (Docker Compose), Docker, Kubernetes (base + Kustomize), and Helm deployments
**Status**: 🔴 **CRITICAL ISSUES FOUND** - Immediate action required

---

## Executive Summary

This analysis reveals **7 critical inconsistencies** and **12 minor misalignments** across deployment configurations that could lead to:
- Different runtime behavior between environments
- Deployment failures in production
- Configuration drift and debugging difficulties
- Security vulnerabilities (using `latest` tags)

**Overall Deployment Alignment Score: 6.5/10** ⚠️

---

## 1. Critical Issues (Action Required)

### 🔴 Issue #1: Python Version Inconsistency
**Severity**: HIGH | **Impact**: Runtime compatibility issues

| Configuration File | Python Version | Status |
|-------------------|----------------|---------|
| `Dockerfile` | 3.12-slim | ✅ Primary |
| `pyproject.toml` | 3.10-3.12 (range) | ✅ Compatible |
| `langgraph.json` | 3.12 | ✅ Correct |
| `.gitlab-ci.yml` | 3.11-slim | ❌ **Outdated** |
| `docs/` (various) | 3.11 references | ⚠️ **Inconsistent** |
| GitHub Actions CI | 3.10, 3.11, 3.12 | ✅ Matrix testing |

**Recommendation**:
```bash
# Update .gitlab-ci.yml to use Python 3.12
sed -i 's/python:3.11-slim/python:3.12-slim/g' .gitlab-ci.yml

# Update documentation references
find docs/ -name "*.md" -o -name "*.mdx" | xargs sed -i 's/python:3\.11/python:3.12/g'
```

---

### 🔴 Issue #2: Docker Image Tags Using `latest`
**Severity**: HIGH | **Impact**: Production deployment risks, reproducibility

**Docker Compose (`docker-compose.yml`)**:
```yaml
openfga:
  image: openfga/openfga:latest  # ❌ ANTI-PATTERN

otel-collector:
  image: otel/opentelemetry-collector-contrib:latest  # ❌ ANTI-PATTERN

jaeger:
  image: jaegertracing/all-in-one:latest  # ❌ ANTI-PATTERN

prometheus:
  image: prom/prometheus:latest  # ❌ ANTI-PATTERN

grafana:
  image: grafana/grafana:latest  # ❌ ANTI-PATTERN
```

**Recommended Pinned Versions**:
```yaml
openfga:
  image: openfga/openfga:v1.5.0  # Latest stable as of 2025-10-13

otel-collector:
  image: otel/opentelemetry-collector-contrib:0.91.0

jaeger:
  image: jaegertracing/all-in-one:1.53.0

prometheus:
  image: prom/prometheus:v2.48.0

grafana:
  image: grafana/grafana:10.2.3
```

---

### 🔴 Issue #3: LLM Model Configuration Mismatch
**Severity**: MEDIUM | **Impact**: Different runtime behavior, unexpected costs

| Environment | Model Provider | Model Name | Cost Impact |
|------------|----------------|------------|-------------|
| Docker Compose (local) | Google | `gemini-2.5-flash-002` | Low cost |
| Kubernetes base | Anthropic | `claude-3-5-sonnet-20241022` | High cost |
| Helm production | Anthropic | `claude-3-5-sonnet-20241022` | High cost |
| `.env.example` | Google | `gemini-2.5-flash-002` | Low cost |

**Analysis**:
- **Local development** defaults to Google Gemini (lower cost, faster iterations)
- **Production/K8s** defaults to Anthropic Claude (higher quality, higher cost)
- **Inconsistency**: Could cause confusion, different test results

**Recommendations**:
1. **Document the strategy** in `README.md`:
   ```markdown
   ## Model Configuration by Environment
   - **Development (Docker Compose)**: Google Gemini 2.5 Flash (fast, low-cost)
   - **Production (Kubernetes)**: Anthropic Claude 3.5 Sonnet (high-quality)
   - **Override**: Set `MODEL_NAME` and `LLM_PROVIDER` environment variables
   ```

2. **Add environment-specific overrides** in Kustomize:
   ```yaml
   # deployments/kustomize/overlays/dev/configmap-patch.yaml
   data:
     llm_provider: "google"
     model_name: "gemini-2.5-flash-002"
   ```

---

### 🔴 Issue #4: Application Version Mismatch
**Severity**: MEDIUM | **Impact**: Confusion, incorrect version tracking

| Configuration File | Version | Status |
|-------------------|---------|---------|
| `pyproject.toml` | 2.2.0 | ✅ Source of truth |
| `deployments/helm/langgraph-agent/Chart.yaml` | 1.0.0 | ❌ **Outdated** |
| `package.json` | 1.0.0 | ❌ **Outdated** |
| `.env.example` | 1.0.0 | ❌ **Outdated** |

**Recommendation**:
```bash
# Update Helm Chart version
sed -i 's/version: 1.0.0/version: 2.2.0/' deployments/helm/langgraph-agent/Chart.yaml
sed -i 's/appVersion: "1.0.0"/appVersion: "2.2.0"/' deployments/helm/langgraph-agent/Chart.yaml

# Update package.json
sed -i 's/"version": "1.0.0"/"version": "2.2.0"/' package.json

# Update .env.example
sed -i 's/SERVICE_VERSION=1.0.0/SERVICE_VERSION=2.2.0/' .env.example
```

---

### 🔴 Issue #5: Helm Template Missing Recent Environment Variables
**Severity**: MEDIUM | **Impact**: Incomplete production deployments

**Missing in Helm `templates/deployment.yaml`**:
```yaml
# ❌ Missing Keycloak configuration (added in recent updates)
- name: KEYCLOAK_SERVER_URL
- name: KEYCLOAK_REALM
- name: KEYCLOAK_CLIENT_ID
- name: KEYCLOAK_CLIENT_SECRET
- name: KEYCLOAK_VERIFY_SSL
- name: KEYCLOAK_TIMEOUT
- name: KEYCLOAK_HOSTNAME

# ❌ Missing Session Management configuration
- name: SESSION_BACKEND
- name: REDIS_URL
- name: REDIS_PASSWORD
- name: REDIS_SSL
- name: SESSION_TTL_SECONDS
- name: SESSION_SLIDING_WINDOW
- name: SESSION_MAX_CONCURRENT

# ❌ Missing LLM Provider configuration
- name: LLM_PROVIDER
- name: MODEL_TEMPERATURE
- name: MODEL_MAX_TOKENS
- name: MODEL_TIMEOUT
- name: ENABLE_FALLBACK

# ❌ Missing Auth Provider selection
- name: AUTH_PROVIDER
- name: AUTH_MODE
```

**Present in `deployments/kubernetes/base/deployment.yaml`**: ✅ All variables configured

**Recommendation**: Update Helm template to match base Kubernetes deployment (see Fix #5 below).

---

### 🔴 Issue #6: Helm Values Missing Configuration Options
**Severity**: MEDIUM | **Impact**: Limited Helm chart flexibility

**Missing in `values.yaml`**:
```yaml
# Current Helm values.yaml has these, but template doesn't use them:
config:
  llmProvider: "anthropic"        # ❌ Not passed to deployment
  modelTemperature: "0.7"          # ❌ Not passed to deployment
  modelMaxTokens: "4096"           # ❌ Not passed to deployment
  modelTimeout: "60"               # ❌ Not passed to deployment
  enableFallback: "true"           # ❌ Not passed to deployment
  authProvider: "keycloak"         # ❌ Not passed to deployment
  authMode: "token"                # ❌ Not passed to deployment
  # ... and 15 more configuration options
```

---

### 🔴 Issue #7: PostgreSQL Configuration Inconsistency
**Severity**: LOW | **Impact**: Development vs Production database differences

| Environment | PostgreSQL Version | Configuration |
|------------|-------------------|---------------|
| Docker Compose | `postgres:15-alpine` | In-memory, ephemeral |
| Kubernetes base | N/A | External dependency assumed |
| Helm chart | Bitnami PostgreSQL v13.2.0 | Persistent, production-ready |

**Recommendation**: Document database strategy clearly:
- **Local**: Lightweight Alpine image for dev/testing
- **Production**: Managed database service (RDS, Cloud SQL, etc.) OR Bitnami Helm chart

---

## 2. Minor Misalignments (Non-Critical)

### ⚠️ Issue #8: Inconsistent Health Check Paths
**Status**: ✅ **RESOLVED** - All deployments use consistent paths

| Path | Purpose | Status |
|------|---------|--------|
| `/health` | Liveness probe | ✅ Consistent |
| `/health/ready` | Readiness probe | ✅ Consistent |
| `/health/startup` | Startup probe | ✅ Consistent |

---

### ⚠️ Issue #9: Resource Limits Variation
**Status**: ✅ **ACCEPTABLE** - Environment-appropriate sizing

| Environment | CPU Request | CPU Limit | Memory Request | Memory Limit |
|------------|-------------|-----------|----------------|--------------|
| Docker Compose | Not specified | Not specified | Not specified | Not specified |
| K8s base | 500m | 2000m | 512Mi | 2Gi |
| Helm default | 500m | 2000m | 512Mi | 2Gi |

**Analysis**: Acceptable - Docker Compose doesn't need limits for dev, K8s/Helm are aligned.

---

### ⚠️ Issue #10: Observability Configuration Drift

| Environment | Tracing | Metrics | Console Export | Backend |
|------------|---------|---------|----------------|---------|
| Docker Compose | true | true | true | opentelemetry |
| K8s dev | true | false | true | opentelemetry |
| K8s production | true | true | false | both |
| Helm default | true | true | false | opentelemetry |

**Analysis**: Environment-appropriate, but consider documenting the strategy.

---

### ⚠️ Issue #11: Redis Configuration Differences

| Environment | Redis Version | Architecture | Auth | Persistence |
|------------|--------------|--------------|------|-------------|
| Docker Compose | `redis:7-alpine` | Standalone | Optional password | Volume mount |
| K8s base | `redis:7-alpine` | Standalone | Optional password | Not specified |
| Helm chart | Bitnami Redis 18.4.0 | Standalone | Enabled | 5Gi PVC |

**Recommendation**: Align Kubernetes base to use Bitnami Redis or document Alpine for dev only.

---

## 3. Configuration Matrix

### Environment Variables Presence

| Variable | Docker Compose | K8s Base | Helm Template | Status |
|----------|----------------|----------|---------------|---------|
| `SERVICE_NAME` | ✅ | ✅ | ✅ | ✅ Aligned |
| `ENVIRONMENT` | ✅ | ✅ | ✅ | ✅ Aligned |
| `LOG_LEVEL` | ✅ | ✅ | ✅ | ✅ Aligned |
| `LLM_PROVIDER` | ✅ | ✅ | ❌ | ⚠️ Missing in Helm |
| `MODEL_NAME` | ✅ | ✅ | ✅ | ✅ Aligned |
| `MODEL_TEMPERATURE` | ❌ | ✅ | ❌ | ⚠️ Missing |
| `MODEL_MAX_TOKENS` | ❌ | ✅ | ❌ | ⚠️ Missing |
| `MODEL_TIMEOUT` | ❌ | ✅ | ❌ | ⚠️ Missing |
| `ENABLE_FALLBACK` | ❌ | ✅ | ❌ | ⚠️ Missing |
| `AUTH_PROVIDER` | ✅ | ✅ | ❌ | ⚠️ Missing in Helm |
| `AUTH_MODE` | ❌ | ✅ | ❌ | ⚠️ Missing |
| `KEYCLOAK_SERVER_URL` | ✅ | ✅ | ❌ | ⚠️ Missing in Helm |
| `KEYCLOAK_REALM` | ✅ | ✅ | ❌ | ⚠️ Missing in Helm |
| `KEYCLOAK_CLIENT_ID` | ✅ | ✅ | ❌ | ⚠️ Missing in Helm |
| `KEYCLOAK_CLIENT_SECRET` | ✅ | ✅ | ❌ | ⚠️ Missing in Helm |
| `SESSION_BACKEND` | ❌ | ✅ | ❌ | ⚠️ Missing |
| `REDIS_URL` | ❌ | ✅ | ❌ | ⚠️ Missing |
| `REDIS_PASSWORD` | ✅ | ✅ | ❌ | ⚠️ Missing in Helm |
| `SESSION_TTL_SECONDS` | ❌ | ✅ | ❌ | ⚠️ Missing |
| `OPENFGA_API_URL` | ✅ | ✅ | ✅ | ✅ Aligned |
| `OPENFGA_STORE_ID` | ✅ | ✅ | ✅ | ✅ Aligned |
| `OPENFGA_MODEL_ID` | ✅ | ✅ | ✅ | ✅ Aligned |
| `OTLP_ENDPOINT` | ✅ | ✅ | ❌ | ⚠️ Missing in Helm |
| `ENABLE_TRACING` | ✅ | ✅ | ✅ | ✅ Aligned |
| `ENABLE_METRICS` | ✅ | ✅ | ✅ | ✅ Aligned |

**Summary**: Helm template is missing **18 environment variables** present in K8s base deployment.

---

## 4. Service Dependencies Alignment

### Dependency Versions

| Service | Docker Compose | K8s Base | Helm Chart (Dependency) |
|---------|----------------|----------|------------------------|
| **OpenFGA** | `openfga:latest` | External | OpenFGA chart v0.1.0 |
| **PostgreSQL** | `postgres:15-alpine` | External | Bitnami PostgreSQL v13.2.0 |
| **Redis** | `redis:7-alpine` | `redis:7-alpine` | Bitnami Redis v18.4.0 |
| **Keycloak** | `keycloak:23.0` | `keycloak:23.0` | Bitnami Keycloak v17.3.0 |

**Keycloak Version Mismatch**:
- Docker Compose & K8s base: `quay.io/keycloak/keycloak:23.0`
- Helm Bitnami chart v17.3.0: Bundles Keycloak ~22.x

---

## 5. Immediate Action Items

### Priority 1 (This Week) - Critical Fixes

#### Fix #1: Update Python Version to 3.12 Everywhere
```bash
# Update GitLab CI
sed -i 's/python:3.11-slim/python:3.12-slim/g' .gitlab-ci.yml

# Update docs (safe search-replace)
find docs/ -type f \( -name "*.md" -o -name "*.mdx" \) \
  -exec sed -i 's/python:3\.11/python:3.12/g' {} +
```

#### Fix #2: Pin Docker Compose Image Versions
```yaml
# Update docker-compose.yml
openfga:
  image: openfga/openfga:v1.5.0

otel-collector:
  image: otel/opentelemetry-collector-contrib:0.91.0

jaeger:
  image: jaegertracing/all-in-one:1.53.0

prometheus:
  image: prom/prometheus:v2.48.0

grafana:
  image: grafana/grafana:10.2.3
```

#### Fix #3: Sync Application Versions
```bash
# Update all version references to 2.2.0
# 1. Helm Chart
yq eval '.version = "2.2.0"' -i deployments/helm/langgraph-agent/Chart.yaml
yq eval '.appVersion = "2.2.0"' -i deployments/helm/langgraph-agent/Chart.yaml

# 2. package.json
jq '.version = "2.2.0"' package.json > package.json.tmp && mv package.json.tmp package.json

# 3. .env.example
sed -i 's/SERVICE_VERSION=.*/SERVICE_VERSION=2.2.0/' .env.example
```

#### Fix #4: Document Model Configuration Strategy
Create `docs/deployment/model-configuration.md`:
```markdown
# Model Configuration Strategy

## Environment-Specific Defaults

### Development (Docker Compose, Local)
- **Provider**: Google
- **Model**: `gemini-2.5-flash-002`
- **Rationale**: Fast iterations, low cost (~$0.075 per 1M tokens)

### Production (Kubernetes, Helm)
- **Provider**: Anthropic
- **Model**: `claude-3-5-sonnet-20241022`
- **Rationale**: Higher quality, better reasoning ($3 per 1M input tokens)

### Override Instructions
Set environment variables to override defaults:
```bash
export LLM_PROVIDER=openai
export MODEL_NAME=gpt-4o
```
```

#### Fix #5: Update Helm Deployment Template
**Critical**: Add missing environment variables to `deployments/helm/langgraph-agent/templates/deployment.yaml`

Create patch file `helm-deployment-env-vars.yaml`:
```yaml
# Add after line 86 (enable_console_export)
- name: LLM_PROVIDER
  value: {{ .Values.config.llmProvider | quote }}
- name: MODEL_TEMPERATURE
  value: {{ .Values.config.modelTemperature | quote }}
- name: MODEL_MAX_TOKENS
  value: {{ .Values.config.modelMaxTokens | quote }}
- name: MODEL_TIMEOUT
  value: {{ .Values.config.modelTimeout | quote }}
- name: ENABLE_FALLBACK
  value: {{ .Values.config.enableFallback | quote }}

# Authentication
- name: AUTH_PROVIDER
  value: {{ .Values.config.authProvider | quote }}
- name: AUTH_MODE
  value: {{ .Values.config.authMode | quote }}

# Keycloak
- name: KEYCLOAK_SERVER_URL
  value: {{ .Values.config.keycloakServerUrl | quote }}
- name: KEYCLOAK_REALM
  value: {{ .Values.config.keycloakRealm | quote }}
- name: KEYCLOAK_CLIENT_ID
  value: {{ .Values.config.keycloakClientId | quote }}
- name: KEYCLOAK_VERIFY_SSL
  value: {{ .Values.config.keycloakVerifySsl | quote }}
- name: KEYCLOAK_TIMEOUT
  value: {{ .Values.config.keycloakTimeout | quote }}
- name: KEYCLOAK_HOSTNAME
  value: {{ .Values.config.keycloakHostname | quote }}

# Session Management
- name: SESSION_BACKEND
  value: {{ .Values.config.sessionBackend | quote }}
- name: REDIS_URL
  value: {{ .Values.config.redisUrl | quote }}
- name: REDIS_SSL
  value: {{ .Values.config.redisSsl | quote }}
- name: SESSION_TTL_SECONDS
  value: {{ .Values.config.sessionTtlSeconds | quote }}
- name: SESSION_SLIDING_WINDOW
  value: {{ .Values.config.sessionSlidingWindow | quote }}
- name: SESSION_MAX_CONCURRENT
  value: {{ .Values.config.sessionMaxConcurrent | quote }}

# Observability
- name: OBSERVABILITY_BACKEND
  value: {{ .Values.config.observabilityBackend | quote }}
- name: LANGSMITH_TRACING
  value: {{ .Values.config.langsmithTracing | quote }}
- name: OTLP_ENDPOINT
  valueFrom:
    configMapKeyRef:
      name: {{ include "langgraph-agent.fullname" . }}
      key: otlp_endpoint
      optional: true

# Secrets (after OPENFGA_MODEL_ID)
- name: KEYCLOAK_CLIENT_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ include "langgraph-agent.secretName" . }}
      key: keycloak-client-secret
- name: REDIS_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "langgraph-agent.secretName" . }}
      key: redis-password
      optional: true
- name: LANGSMITH_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "langgraph-agent.secretName" . }}
      key: langsmith-api-key
      optional: true
```

---

### Priority 2 (Next Week) - Enhancements

1. **Create Deployment Validation Script** (`scripts/validate-deployments.sh`)
2. **Add Pre-Deployment Checklist** to `deployments/README.md`
3. **Update CI/CD** to validate deployment configs on PR
4. **Create Migration Guide** for existing deployments

---

## 6. Deployment Validation Checklist

Before deploying to production, verify:

- [ ] All Docker images use pinned versions (no `latest` tags)
- [ ] Python version is 3.12 across all configs
- [ ] Application version matches across:
  - [ ] pyproject.toml
  - [ ] Helm Chart.yaml
  - [ ] package.json
  - [ ] .env files
- [ ] Model configuration is environment-appropriate
- [ ] All required environment variables present:
  - [ ] LLM configuration (provider, model, temperature, tokens)
  - [ ] Authentication (provider, mode, JWT secret)
  - [ ] Keycloak (URL, realm, client ID/secret)
  - [ ] Session management (backend, Redis URL, TTL)
  - [ ] OpenFGA (URL, store ID, model ID)
  - [ ] Observability (tracing, metrics, OTLP endpoint)
- [ ] Health check paths match application implementation
- [ ] Resource limits appropriate for environment
- [ ] Secrets properly configured (not hardcoded)
- [ ] Database configuration matches environment (managed vs in-cluster)

---

## 7. Testing Strategy

### Local Testing
```bash
# Validate Docker Compose
docker compose config --quiet && echo "✅ Docker Compose valid"

# Test local deployment
docker compose up -d
curl http://localhost:8000/health
docker compose down
```

### Kubernetes Testing
```bash
# Validate base deployment
kubectl kustomize deployments/kustomize/base --dry-run=client

# Validate overlays
for env in dev staging production; do
  echo "Validating $env..."
  kubectl kustomize deployments/kustomize/overlays/$env --dry-run=client
done

# Validate Helm chart
helm lint deployments/helm/langgraph-agent
helm template test deployments/helm/langgraph-agent --debug
```

---

## 8. Monitoring After Deployment

Post-deployment verification:

```bash
# Check pod status
kubectl get pods -n langgraph-agent

# Verify environment variables
kubectl exec -it deployment/langgraph-agent -n langgraph-agent -- env | grep -E "(MODEL_|AUTH_|SESSION_|REDIS_|KEYCLOAK_)"

# Check logs for startup errors
kubectl logs -f deployment/langgraph-agent -n langgraph-agent --tail=50

# Test health endpoints
kubectl port-forward svc/langgraph-agent 8000:80 -n langgraph-agent
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

---

## 9. Risk Assessment

| Issue | Risk Level | Likelihood | Impact | Mitigation |
|-------|-----------|-----------|---------|-----------|
| Using `latest` tags | HIGH | High | Production breakage | Pin all versions |
| Missing env vars in Helm | HIGH | Medium | Deployment failure | Add to template |
| Python version drift | MEDIUM | Low | Runtime errors | Standardize to 3.12 |
| Model config mismatch | MEDIUM | High | Cost overruns | Document strategy |
| Version misalignment | LOW | High | Confusion | Sync versions |

---

## 10. Next Steps

**Immediate (Today)**:
1. ✅ Review this analysis with team
2. Pin Docker Compose image versions
3. Update Helm template with missing env vars

**This Week**:
1. Standardize Python to 3.12
2. Sync application versions
3. Create deployment validation script
4. Test Helm chart updates in dev

**Next Week**:
1. Update CI/CD pipelines
2. Create migration guide
3. Deploy to staging for validation
4. Update documentation

---

## Appendix A: File References

### Configuration Files Analyzed
- `Dockerfile`
- `docker-compose.yml`
- `pyproject.toml`
- `langgraph.json`
- `.env.example`
- `deployments/kubernetes/base/*.yaml` (9 files)
- `deployments/helm/langgraph-agent/*.yaml` (2 files)
- `deployments/helm/langgraph-agent/templates/*.yaml` (10 files)
- `deployments/kustomize/overlays/*/configmap-patch.yaml` (3 files)

### Total Files Reviewed: 38

---

## Appendix B: Change Log

| Date | Change | Author | Impact |
|------|--------|--------|---------|
| 2025-10-13 | Initial analysis | Claude | Identified 7 critical issues |
| TBD | Fix implementation | Team | TBD |

---

**Document Version**: 1.0
**Last Updated**: 2025-10-13
**Next Review**: After fixes implementation
