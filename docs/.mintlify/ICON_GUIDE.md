# Mintlify Icon Style Guide

This guide defines the standard icon conventions for MCP Server LangGraph documentation. Consistent icon usage improves navigation and visual organization.

## Icon Selection Principles

1. **Semantic Relevance**: Icons should clearly represent the document's purpose
2. **Category Consistency**: Related documents should use related icons
3. **Visual Distinction**: Different categories should have distinct icon families
4. **Accessibility**: Icons should be recognizable and meaningful

## Icon Categories

### 1. Architecture Decision Records (ADRs)

**Icon**: `file-lines`

**Rationale**: Represents documented decisions and technical specifications.

**Usage**: All files in `docs/architecture/adr-*.mdx`

**Examples**:
```yaml
---
title: 1. Multi-Provider LLM Support via LiteLLM
description: 'Architecture decision for LLM provider abstraction'
icon: 'file-lines'
---
```

**Files**: 39 ADR documents (adr-0001 through adr-0039)

---

### 2. General Deployment Documentation

**Icon**: `rocket`

**Rationale**: Represents deployment, launch, and going to production.

**Usage**: General deployment guides, processes, configurations

**Examples**:
```yaml
---
title: Deployment Overview
description: 'Deploy MCP Server with LangGraph to production'
icon: 'rocket'
---
```

**Files**:
- `deployment/overview.mdx`
- `deployment/langgraph-platform.mdx`
- `deployment/release-process.mdx`
- `deployment/version-compatibility.mdx`
- `deployment/version-pinning.mdx`
- `deployment/vmware-resource-estimation.mdx`
- `deployment/model-configuration.mdx`
- `deployment/gdpr-storage-configuration.mdx`

---

### 3. Kubernetes-Specific Deployment

**Icon**: `dharmachakra`

**Rationale**: Official Kubernetes icon (ship's wheel/Dharmachakra).

**Usage**: Kubernetes deployment guides, manifests, K8s operations

**Examples**:
```yaml
---
title: Kubernetes Deployment
description: 'Deploy MCP Server with LangGraph on Kubernetes'
icon: 'dharmachakra'
---
```

**Files**:
- `deployment/kubernetes.mdx`
- `deployment/gke-staging-implementation-summary.mdx`
- `deployment/kubernetes/gke.mdx`
- `deployment/kubernetes/eks.mdx`
- `deployment/kubernetes/aks.mdx`

---

### 4. Container/Docker Deployment

**Icon**: `docker`

**Rationale**: Docker's official brand icon.

**Usage**: Docker-specific deployment guides

**Examples**:
```yaml
---
title: Docker Compose
description: 'Local development and testing with Docker Compose'
icon: 'docker'
---
```

**Files**:
- `deployment/docker.mdx`

---

### 5. Helm Deployment

**Icon**: `helm`

**Rationale**: Helm's official package manager icon.

**Usage**: Helm chart deployment guides

**Examples**:
```yaml
---
title: Helm Deployment
description: 'Deploy MCP Server using Helm charts for simplified management'
icon: 'helm'
---
```

**Files**:
- `deployment/helm.mdx`

---

### 6. Cloud Provider-Specific (GCP)

**Icon**: `google`

**Rationale**: Represents Google Cloud Platform services.

**Usage**: GCP-specific deployment guides (Cloud Run, Vertex AI, GKE-specific features)

**Examples**:
```yaml
---
title: Google Cloud Run
description: 'Deploy to Google Cloud Run for serverless GCP deployment'
icon: 'google'
---
```

```yaml
---
title: Vertex AI with Workload Identity
description: 'Configure Vertex AI using Workload Identity Federation on GKE for keyless authentication'
icon: 'google'
---
```

**Files**:
- `deployment/cloud-run.mdx`
- `deployment/vertex-ai-workload-identity.mdx`

**Note**: For AWS and Azure specific guides, use `aws` and `microsoft` icons respectively.

---

### 7. Security & Authentication

**Icon**: `shield-halved`

**Rationale**: Represents security, protection, and access control.

**Usage**: Security guides, authentication/authorization, API gateways, secrets management

**Examples**:
```yaml
---
title: Kong API Gateway
description: 'Deploy Kong Gateway for advanced API management, rate limiting, and security'
icon: 'shield-halved'
---
```

```yaml
---
title: Keycloak JWT Authentication Deployment Guide
description: 'Complete deployment guide for the Keycloak-centric authentication architecture'
icon: 'shield-halved'
---
```

**Files**:
- `deployment/kong-gateway.mdx`
- `deployment/keycloak-jwt-deployment.mdx`
- `deployment/infisical-installation.mdx`
- `security/*` (security-related documentation)

**Alternative security icons**:
- `shield`: General security
- `shield-check`: Security verification
- `lock`: Access control
- `key`: Authentication/credentials

---

### 8. Observability & Monitoring

**Icon**: `chart-line`

**Rationale**: Represents metrics, monitoring, and time-series data.

**Usage**: Monitoring, metrics, observability guides

**Examples**:
```yaml
---
title: Monitoring & Observability
description: 'Comprehensive monitoring, metrics, and observability setup'
icon: 'chart-line'
---
```

**Files**:
- `deployment/monitoring.mdx`

**Related observability icons**:
- `database`: Log aggregation/storage
- `chart-bar`: Dashboards
- `magnifying-glass-chart`: Analytics

---

### 9. Log Aggregation

**Icon**: `database`

**Rationale**: Represents log storage and data aggregation.

**Usage**: Logging infrastructure, log aggregation platforms

**Examples**:
```yaml
---
title: Log Aggregation
description: 'Multi-platform log aggregation with structured JSON logging'
icon: 'database'
---
```

**Files**:
- `deployment/log-aggregation.mdx`

---

### 10. Scaling & Performance

**Icon**: `arrow-up-right-dots`

**Rationale**: Represents upward scaling and growth.

**Usage**: Auto-scaling, performance optimization, resource scaling

**Examples**:
```yaml
---
title: Auto-Scaling
description: 'Configure horizontal and vertical scaling for production workloads'
icon: 'arrow-up-right-dots'
---
```

**Files**:
- `deployment/scaling.mdx`

---

### 11. Disaster Recovery & Resilience

**Icon**: `life-ring`

**Rationale**: Represents rescue, recovery, and safety nets.

**Usage**: Disaster recovery, backup/restore, failover strategies

**Examples**:
```yaml
---
title: Disaster Recovery
description: 'Backup, restore, and failover strategies for production resilience'
icon: 'life-ring'
---
```

**Files**:
- `deployment/disaster-recovery.mdx`

---

### 12. Production Readiness & Checklists

**Icon**: `clipboard-check`

**Rationale**: Represents verification, checklists, and task completion.

**Usage**: Production checklists, pre-deployment verification

**Examples**:
```yaml
---
title: Production Checklist
description: 'Pre-deployment verification for production environments'
icon: 'clipboard-check'
---
```

**Files**:
- `deployment/production-checklist.mdx`

---

### 13. Version History & Releases

**Icon**: `tag`

**Rationale**: Git tags represent releases and versions.

**Usage**: Release notes, version history, changelogs

**Examples**:
```yaml
---
title: Version History
description: 'Complete release history and version comparison'
icon: 'tag'
---
```

**Files**:
- `releases/overview.mdx`
- `releases/v2-1-0.mdx` through `releases/v2-8-0.mdx`

---

### 14. Development & Reference

**Icon**: `code`

**Rationale**: Represents code, development, and technical reference.

**Usage**: Development guides, API reference, code examples

**Examples**:
```yaml
---
title: Development Guide
description: 'Local development setup and workflow'
icon: 'code'
---
```

**Files**:
- `reference/development/*.mdx`
- API reference documentation

---

### 15. Getting Started & Guides

**Icon**: `rocket` or `book-open`

**Rationale**: `rocket` for quickstart/deployment, `book-open` for guides.

**Usage**: Quickstart guides, tutorials, how-to documentation

**Examples**:
```yaml
---
title: Quick Start
description: 'Get started with MCP Server LangGraph in 5 minutes'
icon: 'rocket'
---
```

**Files**:
- `getting-started/*`
- `guides/*`

---

## Frontmatter Standards

### Complete Frontmatter Template

```yaml
---
title: Document Title Here
description: 'Brief description of the document content'
icon: 'icon-name'
---
```

### Standards

1. **Title**:
   - No quotes
   - Title Case capitalization
   - Clear and descriptive

2. **Description**:
   - Single quotes `'...'`
   - No ending period
   - 1-2 sentences max
   - Descriptive but concise

3. **Icon**:
   - Single quotes `'icon-name'`
   - Font Awesome icon names (without `fa-` prefix)
   - Must be from approved icon set

---

## Icon Selection Flowchart

```
Is it an ADR?
├─ YES → Use 'file-lines'
└─ NO  → Continue

Is it deployment-related?
├─ YES → What type?
│        ├─ General/Multi-platform → 'rocket'
│        ├─ Kubernetes → 'dharmachakra'
│        ├─ Docker → 'docker'
│        ├─ Helm → 'helm'
│        ├─ GCP → 'google'
│        ├─ AWS → 'aws'
│        └─ Azure → 'microsoft'
└─ NO  → Continue

Is it security-related?
├─ YES → 'shield-halved' (or shield/lock/key variants)
└─ NO  → Continue

Is it observability?
├─ YES → What aspect?
│        ├─ Monitoring/Metrics → 'chart-line'
│        ├─ Logging → 'database'
│        └─ Scaling → 'arrow-up-right-dots'
└─ NO  → Continue

Is it operational?
├─ YES → What type?
│        ├─ Disaster Recovery → 'life-ring'
│        ├─ Checklist → 'clipboard-check'
│        └─ General → 'rocket'
└─ NO  → Continue

Is it a release/version?
├─ YES → 'tag'
└─ NO  → Continue

Is it development/code reference?
├─ YES → 'code'
└─ NO  → Use judgment or consult team
```

---

## Common Mistakes to Avoid

❌ **Don't**:
- Use inconsistent icons for the same category
- Mix icon families within related docs
- Use obscure or ambiguous icons
- Use quoted titles in frontmatter
- Use double quotes for descriptions

✅ **Do**:
- Follow category conventions
- Use semantic, meaningful icons
- Maintain consistency within directories
- Use unquoted titles
- Use single quotes for descriptions

---

## Validation

Use the validation script to check icon consistency:

```bash
python3 scripts/validate_mintlify_docs.py
```

The script will flag:
- Missing icons
- Inconsistent icon usage within categories
- Frontmatter format issues

---

## Updates and Exceptions

If you need to use an icon not listed in this guide:

1. **Check semantic fit**: Does the icon clearly represent the content?
2. **Check for conflicts**: Is this icon already used for a different category?
3. **Document the pattern**: Update this guide with the new usage
4. **Ensure consistency**: Use the same icon for similar documents

For questions or exceptions, consult the documentation team or create an issue.

---

## Font Awesome Icon Reference

Mintlify uses Font Awesome icons. Common useful icons:

**Infrastructure**:
- `server`, `network-wired`, `cloud`, `database`

**Tools**:
- `gear`, `wrench`, `screwdriver`, `toolbox`

**Actions**:
- `play`, `stop`, `refresh`, `download`, `upload`

**Status**:
- `check`, `xmark`, `exclamation`, `info`, `question`

**Navigation**:
- `arrow-right`, `arrow-left`, `arrow-up`, `arrow-down`

Full icon list: https://fontawesome.com/icons

---

**Last Updated**: 2025-10-31
**Version**: 1.0.0
