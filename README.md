# MCP Server with LangGraph + OpenFGA & Infisical

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.8.0-blue.svg)](CHANGELOG.md)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Production Ready](https://img.shields.io/badge/production-ready-brightgreen.svg)](docs/deployment/production-checklist.mdx)
[![Documentation](https://img.shields.io/badge/docs-mintlify-green.svg)](https://vishnu2kmohan.github.io/mcp-server-langgraph/)
[![ADRs](https://img.shields.io/badge/ADRs-64-informational.svg)](adr/README.md)
[![Use This Template](https://img.shields.io/badge/use-this%20template-blue.svg?logo=cookiecutter)](https://github.com/vishnu2kmohan/mcp-server-langgraph#-use-this-template)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](Dockerfile)
[![Kubernetes](https://img.shields.io/badge/kubernetes-%23326ce5.svg?logo=kubernetes&logoColor=white)](docs/deployment/kubernetes.mdx)

[![Main Pipeline](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/ci.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/ci.yaml)
[![Security Scan](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/security-scan.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/security-scan.yaml)
[![Coverage](https://vishnu2kmohan.github.io/mcp-server-langgraph/badges/coverage.svg)](https://vishnu2kmohan.github.io/mcp-server-langgraph/coverage/)
[![Tests](https://vishnu2kmohan.github.io/mcp-server-langgraph/badges/tests.svg)](https://vishnu2kmohan.github.io/mcp-server-langgraph/)

> **Full CI/CD status & all badges**: [docs/ci-cd/badges.mdx](docs/ci-cd/badges.mdx) | **Telemetry Dashboard**: [vishnu2kmohan.github.io/mcp-server-langgraph](https://vishnu2kmohan.github.io/mcp-server-langgraph/)

A **production-ready cookie-cutter template** for building MCP servers with LangGraph's Functional API. Features comprehensive authentication (JWT), fine-grained authorization (OpenFGA), secrets management (Infisical), and OpenTelemetry-based observability.

**🎯 Opinionated, production-grade foundation for your MCP server projects.**

---

## 🚀 Choose Your Path

Pick the quickstart that matches your needs:

| Path | Time | What You Get | Best For |
|------|------|-------------|----------|
| **[Quickstart (Zero Infrastructure)](docs/getting-started/day-1-developer.mdx#quickstart-zero-infrastructure)** | < 2 min | In-memory agent, no Docker, free LLM tier | Learning, prototyping, exploring |
| **[Local Development](docs/getting-started/day-1-developer.mdx#local-development-minimal-infrastructure)** | ~5 min | Redis + PostgreSQL, persistence, dev mode | Feature development, integration testing |
| **[Full Production](docs/getting-started/day-1-developer.mdx#full-production-setup)** | ~20 min | Complete stack: auth, observability, compliance | Production deployment, enterprise features |

**New here?** → Start with **[Day-1 Developer Guide](docs/getting-started/day-1-developer.mdx)** for step-by-step instructions

---

## 🔧 For Contributors: CI/CD Configuration

This project uses **19 GitHub Actions workflows** with Google Cloud Platform (GCP) Workload Identity Federation for secure deployments.

**Quick setup**: [SECRETS.md](.github/SECRETS.md) | **Full CI/CD status**: [docs/ci-cd/badges.mdx](docs/ci-cd/badges.mdx) | **Workflow details**: [.github/archive/audits-2025-11/WORKFLOW_AUDIT_REMAINING.md](.github/archive/audits-2025-11/WORKFLOW_AUDIT_REMAINING.md)

---

## 📑 Table of Contents

**Quick Links**:
- 🚀 [Use as Template](#use-this-template) - Generate your own MCP server project
- ⚡ [Quick Start](#quick-start) - Get running in 2 minutes
- 📦 [Installation](#installation) - Setup instructions
- 🏗️ [Architecture](#architecture) - System design and agentic loop
- 🔐 [Authentication](#authentication-authorization) - Security setup
- 🚢 [Deployment](#deployment-options) - Production deployment guides

**Main Sections**:
- [Template vs Project Usage](#template-vs-project-usage) - Choose your approach
- [Features](#features) - Core capabilities and best practices
- [Documentation](#documentation) - Complete guides and references
- [Requirements](#requirements) - System and service requirements
- [Usage](#usage) - MCP server usage and client configuration
- [Testing Strategy](#testing-strategy) - Multi-layered testing approach
- [Feature Flags](#feature-flags) - Dynamic feature control
- [Observability](#observability) - LangSmith and OpenTelemetry
- [Configuration](#configuration) - Environment variables and settings
- [Security Considerations](#security-considerations) - Production checklist
- [API Gateway & Rate Limiting](#api-gateway-rate-limiting) - Kong integration
- [Quality Practices](#quality-practices) - Code quality standards
- [Contributing](#contributing) - Contribution guidelines
- [Support](#support) - Get help and report issues

---

## 🚀 Use This Template

```bash
# Generate your own MCP server project
uvx cookiecutter gh:vishnu2kmohan/mcp-server-langgraph

# Answer a few questions and get a fully configured project!
```

**See [Cookiecutter Template Strategy](adr/adr-0011-cookiecutter-template-strategy.md) for detailed information.**

---

## 📖 Template vs Project Usage

Choose the approach that matches your goals:

| **Use Case** | **As Template** | **Clone Directly** |
|--------------|-----------------|-------------------|
| **Best For** | Building your own custom MCP server | Learning, testing, or using reference implementation |
| **Command** | `uvx cookiecutter gh:vishnu2kmohan/mcp-server-langgraph` | `git clone https://github.com/vishnu2kmohan/mcp-server-langgraph.git && cd mcp-server-langgraph && uv sync` |
| **You Get** | Customizable project scaffold:<br/>• Your project name, author, license<br/>• Choose features (auth, observability, deployment)<br/>• Select LLM providers<br/>• Implement custom tools | Fully working reference implementation:<br/>• Example tools (`agent_chat`, `conversation_search`, `conversation_get`)<br/>• Complete observability stack<br/>• Production-ready deployment configs<br/>• Comprehensive test suite |
| **Next Steps** | 1. Customize tools in `agent.py`<br/>2. Update authorization in `scripts/setup/setup_openfga.py`<br/>3. Configure `.env` with your API keys<br/>4. Deploy your custom server | 1. Copy `.env.example` to `.env`<br/>2. Add API keys (GOOGLE_API_KEY, etc.)<br/>3. Run `make run-streamable`<br/>4. See [Quick Start](#quick-start) for details |
| **Learn More** | [Cookiecutter Template Strategy (ADR-0011)](adr/adr-0011-cookiecutter-template-strategy.md) | [Quick Start Guide](#quick-start) |

**💡 Recommendation**: Use **As Template** for production projects, **Clone Directly** for learning and testing.

---

## Features

### ⭐ Anthropic Best Practices (9.8/10 Adherence)

This project achieves **reference-quality implementation** of Anthropic's AI agent best practices with measurable improvements:

- **🎯 Just-in-Time Context Loading**: 60% token reduction via dynamic semantic search (Qdrant)
- **⚡ Parallel Tool Execution**: 1.5-2.5x faster through concurrent execution with dependency resolution
- **📝 Enhanced Structured Note-Taking**: LLM-based 6-category information extraction
- **✅ Complete Agentic Loop**: Gather-action-verify-repeat with 40-60% token reduction, 23% quality improvement

**See**: [Complete Assessment](reports/ANTHROPIC_BEST_PRACTICES_ASSESSMENT_20251017.md) | [ADR-0023](adr/adr-0023-anthropic-tool-design-best-practices.md), [ADR-0024](adr/adr-0024-agentic-loop-implementation.md), [ADR-0025](adr/adr-0025-anthropic-best-practices-enhancements.md)

### 🐍 Secure Code Execution (NEW)

Execute Python code securely with comprehensive validation and sandboxing:

- **Dual Backend Support**: Docker Engine (local/dev) + Kubernetes Jobs (production)
- **AST-Based Validation**: Import whitelist, blocks 30+ dangerous modules (os, subprocess, eval, etc.)
- **Resource Limits**: CPU, memory, timeout, disk quotas with enforcement
- **Network Isolation**: Configurable modes (none/allowlist/unrestricted)
- **OWASP Top 10 Defenses**: 34 security tests covering injection, deserialization, privilege escalation
- **Progressive Tool Discovery**: 98%+ token savings via `search_tools` endpoint (Anthropic best practice)
- **Feature Flagged**: Disabled by default (fail-closed security)

**Test Coverage**: 162 tests (100% passing) | **Security**: 96% code coverage | **Backends**: Docker + Kubernetes

**See**: [Implementation Summary](docs-internal/code-execution-implementation-summary.md) | [Anthropic MCP Guide](https://www.anthropic.com/engineering/code-execution-with-mcp)

### 🎯 Core Capabilities
- **Multi-LLM Support**: 100+ providers via LiteLLM (Anthropic, OpenAI, Google, Azure, Bedrock, Ollama) + open-source models (Llama, Qwen, Mistral)
- **MCP Protocol**: Standard stdio & StreamableHTTP transports for AI agent exposure
- **Enterprise Auth**: JWT authentication, Keycloak SSO (OIDC/OAuth2), automatic token refresh, JWKS verification
- **Session Management**: InMemory (dev) or Redis (prod) with TTL, sliding windows, lifecycle management
- **Fine-Grained Authorization**: OpenFGA (Zanzibar-style) with role mapping, Keycloak sync, hierarchies
- **Secrets Management**: Infisical integration + env var fallback
- **Observability**: Dual stack (OpenTelemetry + LangSmith), Jaeger/Prometheus/Grafana, 30+ metrics, structured JSON logging
- **LangGraph Platform**: One-command deploy to managed cloud

### 🔒 GDPR & Privacy Compliance

Complete GDPR compliance with **6 API endpoints** (Articles 15-21) and **PostgreSQL storage backend**. Features include atomic deletions, 7-year audit logs, and 14x cost savings vs Redis. Covers GDPR, HIPAA §164.312/§164.316, and SOC2 CC6.6/PI1.4.

**See**: [GDPR API Reference](docs/api-reference/gdpr-endpoints.mdx) | [ADR-0041: PostgreSQL Storage](adr/adr-0041-postgresql-gdpr-storage.md) | [Storage Configuration](docs/deployment/gdpr-storage-configuration.mdx) | [GDPR Compliance Guide](docs/compliance/gdpr/overview.mdx)

### 📦 Optional Dependencies

Install optional features on demand: **Code Execution** (`[code-execution]`), **Secrets Management** (`[secrets]`), **Self-Hosted Embeddings** (`[embeddings]`), **All Features** (`[all]`). Production requires persistent storage (PostgreSQL/Redis) for GDPR compliance—in-memory mode is blocked.

**Code Execution**: Requires Docker (local) or Kubernetes (production). Enable with `ENABLE_CODE_EXECUTION=true`.

**See**: [Installation Guide](docs/getting-started/installation.mdx#optional-dependencies) | [Code Execution Summary](docs-internal/code-execution-implementation-summary.md) | [GDPR Storage Configuration](docs/deployment/gdpr-storage-configuration.mdx)

### 🧪 Quality & Testing
27+ property tests, 20+ contract tests, performance regression tracking, mutation testing (80%+ target), strict typing (gradual rollout), OpenAPI validation. See [Testing Strategy](docs/advanced/testing.mdx).

### 🚀 Production Deployment
Kubernetes-ready for GKE/EKS/AKS with Helm charts, Kustomize overlays, automated CI/CD, HA (anti-affinity, HPA, PDB), 25+ Prometheus alerts, 4 Grafana dashboards. Service mesh compatible. See [Deployment Guide](docs/deployment/overview.mdx).

## 📚 Documentation

**Primary Resources**:
- **[Mintlify Documentation](https://mcp-server-langgraph.mintlify.app)** - Complete guides, tutorials, API references
- **[API Docs](http://localhost:8000/docs)** - Interactive OpenAPI/Swagger UI (local)
- **[39 Architecture Decision Records](adr/README.md)** - Key ADRs: [0001-LiteLLM](adr/adr-0001-llm-multi-provider.md), [0002-OpenFGA](adr/adr-0002-openfga-authorization.md), [0023-Anthropic Tools](adr/adr-0023-anthropic-tool-design-best-practices.md), [0024-Agentic Loop](adr/adr-0024-agentic-loop-implementation.md)

**Deployment & Operations**:
- [Deployment Quickstart](deployments/QUICKSTART.md) | [CI/CD Pipeline](docs/reference/development/ci-cd/overview.mdx) | [Keycloak SSO](integrations/keycloak.md)

**Examples**: [Examples Directory](examples/README.md) with demos for dynamic context loading, parallel execution, note-taking, and complete workflows

## Requirements

### System Requirements
- **Python**: 3.10, 3.11, or 3.12
- **Memory**: 2GB RAM minimum (4GB recommended for production)
- **Disk**: 500MB for dependencies + 1GB for optional vector databases
- **OS**: Linux, macOS, or Windows with WSL2

### Required Services (for full features)
- **Redis**: Session storage (or use in-memory mode)
- **PostgreSQL**: Compliance data storage (optional)
- **OpenFGA**: Fine-grained authorization (optional)

### Optional Components
- **Qdrant/Weaviate**: Vector database for semantic search
- **Jaeger**: Distributed tracing visualization
- **Prometheus + Grafana**: Metrics and monitoring

See [Production Checklist](docs/deployment/production-checklist.mdx) for detailed requirements.

## Installation

Using [uv](https://github.com/astral-sh/uv) (10-100x faster than pip, reproducible builds):

```bash
# From PyPI
uv pip install mcp-server-langgraph

# Or clone and develop
git clone https://github.com/vishnu2kmohan/mcp-server-langgraph.git
cd mcp-server-langgraph
uv sync  # Installs all dependencies from pyproject.toml + uv.lock
```

**Verify**: `python -c "import mcp_server_langgraph; print(mcp_server_langgraph.__version__)"`

**See**: [Complete Installation Guide](docs/getting-started/installation.mdx) for Docker, venv setup, optional dependencies, and configuration

## Architecture

**System Flow**: MCP Client → Auth Middleware (JWT + OpenFGA) → LangGraph Agent → Observability Stack (Jaeger/Prometheus/Grafana)

**Agentic Loop**: Implements Anthropic's **gather-action-verify-repeat** cycle with 6 enhancements:
- **Just-in-Time Context Loading**: Dynamic semantic search (60% token reduction)
- **Context Compaction**: Prevents overflow (40-60% token reduction)
- **Parallel Tool Execution**: Concurrent execution (1.5-2.5x speedup)
- **Enhanced Note-Taking**: LLM-based 6-category extraction
- **Output Verification**: LLM-as-judge pattern (23% quality improvement)
- **Iterative Refinement**: Up to 3 self-correction attempts

**See**: [Architecture Overview](docs/getting-started/architecture.mdx) | [ADR-0024: Agentic Loop](adr/adr-0024-agentic-loop-implementation.md) | [ADR-0025: Enhancements](adr/adr-0025-anthropic-best-practices-enhancements.md) | [All ADRs](docs/architecture/overview.mdx)

## Database Architecture

**Multi-Database Design**: Single PostgreSQL instance with **dedicated databases per service** for clear separation of concerns and optimized schema management.

### Database Overview

| Database | Purpose | Tables | Managed By | Retention |
|----------|---------|--------|------------|-----------|
| **gdpr** / **gdpr_test** | GDPR compliance data (user profiles, consents, audit logs) | 5 tables | Schema migrations | 7 years (audit logs) |
| **openfga** / **openfga_test** | OpenFGA authorization (relationship tuples, policies) | 3 tables | OpenFGA service | Indefinite |
| **keycloak** / **keycloak_test** | Keycloak authentication (users, realms, clients) | 3 tables | Keycloak service | Indefinite |

### Environment-Based Naming

Databases use environment-aware naming for clear separation:

```bash
# Development/Staging/Production
gdpr, openfga, keycloak

# Test Environment
gdpr_test, openfga_test, keycloak_test
```

**Detection**: Automatic environment detection from `POSTGRES_DB` variable (suffix `_test` triggers test mode)

### Automatic Initialization

Database initialization is **fully automated** via `migrations/000_init_databases.sh`:

1. Environment detection (dev vs test)
2. Create all 3 databases (idempotent)
3. Apply GDPR schema migrations
4. Validate table structure (5 GDPR tables)

**Validation**: Runtime validation via `src/mcp_server_langgraph/health/database_checks.py` ensures architecture compliance per ADR-0056.

### Quick Database Setup

```bash
# Docker Compose (automatic initialization)
docker-compose up -d postgres

# Manual validation
python -c "
from mcp_server_langgraph.health.database_checks import validate_database_architecture
import asyncio
result = asyncio.run(validate_database_architecture())
print(f'Valid: {result.is_valid}')
print(f'Databases: {list(result.databases.keys())}')
"
```

**See**: [ADR-0060: Database Architecture](adr/adr-0060-database-architecture-and-naming-convention.md) | [Migration Script](migrations/000_init_databases.sh) | [Database Validation Module](src/mcp_server_langgraph/health/database_checks.py)

## Quick Start

### 🐳 Docker Compose (Recommended)

Get the complete stack running in 2 minutes:

```bash
# Quick start script handles everything
./scripts/docker-compose-quickstart.sh
```

This starts:
- **Agent API**: http://localhost:8000 (MCP agent)
- **OpenFGA**: http://localhost:8080 (authorization)
- **OpenFGA Playground**: http://localhost:3001
- **Jaeger UI**: http://localhost:16686 (distributed tracing)
- **Prometheus**: http://localhost:9090 (metrics)
- **Grafana**: http://localhost:3000 (visualization, admin/admin)
- **PostgreSQL**: localhost:5432 (OpenFGA storage)

**Then setup OpenFGA**:
```bash
python scripts/setup/setup_openfga.py
# Add OPENFGA_STORE_ID and OPENFGA_MODEL_ID to .env
docker-compose restart agent
```

**Test the agent**:
```bash
curl http://localhost:8000/health
```

See [Docker Compose documentation](docs/deployment/docker.mdx) for details.

### 🐍 Local Python Development

```bash
uv sync                              # Install dependencies
make git-hooks                       # Setup git hooks (REQUIRED for contributors)
cp .env.example .env                 # Configure (add GOOGLE_API_KEY)
docker-compose up -d openfga postgres  # Start infrastructure
python scripts/setup/setup_openfga.py  # Setup auth (save IDs to .env)
python -m mcp_server_langgraph.mcp.server_streamable  # Run agent
curl http://localhost:8000/health    # Test
```

**Git Hooks** (2-stage validation):
- **Pre-commit** (< 30s): Fast validation on changed files - commit frequently!
- **Pre-push** (8-12 min): Comprehensive validation matching CI - prevents surprises!

**See**: [Complete Installation Guide](docs/getting-started/installation.mdx) | [Day-1 Developer Guide](docs/getting-started/day-1-developer.mdx) | [Git Hooks Guide](docs-internal/testing/TESTING.md#git-hooks-and-validation)

### 👤 Creating Test Users

**SECURITY NOTE**: As of version 2.8.0, InMemoryUserProvider no longer seeds default users (alice, bob, admin) to prevent hard-coded credential vulnerabilities (CWE-798).

For testing/development with InMemoryUserProvider, explicitly create users:

```python
from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider

# Create provider with password hashing
provider = InMemoryUserProvider(use_password_hashing=True)

# Add test users
provider.add_user(
    username="testuser",
    password="secure-password-123",
    email="testuser@example.com",
    roles=["user", "premium"]
)

provider.add_user(
    username="admin",
    password="admin-secure-password",
    email="admin@example.com",
    roles=["admin"]
)
```

**For Production**: Use `KeycloakUserProvider` instead of `InMemoryUserProvider`. See [Authentication](#authentication-authorization) for configuration details.

## Usage

### Running the MCP Server

```bash
python -m mcp_server_langgraph.mcp.server_stdio
```

### Testing with Example Client

```bash
python examples/client_stdio.py
```

### MCP Client Configuration

Add to your MCP client config (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "langgraph-agent": {
      "command": "python",
      "args": ["/path/to/mcp_server_langgraph/src/mcp_server_langgraph/mcp/server_stdio.py"]
    }
  }
}
```

## Authentication & Authorization

Enterprise-grade authentication and fine-grained authorization powered by Keycloak and OpenFGA:

| **Feature** | **Technology** | **Use Case** | **Guide** |
|-------------|----------------|--------------|-----------|
| **JWT Authentication** | Keycloak RS256 | All API calls require tokens (15min lifetime) | [Migration Guide](docs/guides/authentication-migration-v2-8.mdx) |
| **Service Principals** | Keycloak + 30-day refresh | Machine-to-machine authentication | [Service Principals](docs/guides/service-principals.mdx) |
| **API Keys** | Bcrypt-hashed keys → JWT | Long-lived keys for automation | [API Key Management](docs/guides/api-key-management.mdx) |
| **Identity Federation** | LDAP, SAML, OIDC | Integrate existing identity providers (Google, Azure AD, Okta) | [Identity Federation](docs/guides/identity-federation-quickstart.mdx) |
| **SCIM Provisioning** | SCIM 2.0 | Automated user/group sync from enterprise systems | [SCIM Provisioning](docs/guides/scim-provisioning.mdx) |
| **Fine-Grained Authz** | OpenFGA (Zanzibar) | Relationship-based access control per tool/resource | [OpenFGA Setup](docs/guides/openfga-setup.mdx) |

**Quick Example** (JWT Authentication):
```python
# 1. Login to get JWT
response = httpx.post("http://localhost:8000/auth/login",
    json={"username": "alice", "password": "alice123"})
token = response.json()["access_token"]

# 2. Use token in tool calls
response = httpx.post("http://localhost:8000/message",
    json={"method": "tools/call", "params": {"name": "agent_chat", "arguments": {"token": token, "message": "Hello!"}}})
```

**Development Users** (⚠️ Plaintext passwords - dev only):
- `alice` / `alice123` (premium user) | `bob` / `bob123` (standard user) | `admin` / `admin123` (admin)

**Production**: Use `AUTH_PROVIDER=keycloak` with proper SSO. See [Keycloak Integration Guide](integrations/keycloak.md) for setup.

## CI/CD Pipeline

Production-grade pipeline with **19 GitHub Actions workflows** organized into four categories:

- **🔄 CI/CD**: Main pipeline (Python 3.10-3.12, multi-arch Docker), E2E tests, quality tests (property/contract/mutation), coverage tracking
- **🔒 Security**: Trivy/CodeQL/secrets scanning, GCP compliance validation, drift detection (6-hour intervals)
- **🚀 Deployment**: Automated staging deploys, manual production approval, version management
- **🤖 Automation**: Dependabot auto-merge, link checking, stale issue management

**Key Metrics**: 12 min avg build (66% faster), 80%+ coverage enforced, ~$40/month cost, automated staging + manual prod approval

**See**: [Complete CI/CD Documentation](docs/reference/development/ci-cd/overview.mdx) | [Workflow Details](docs/reference/development/ci-cd/workflows.mdx) | [CI/CD Status](docs/ci-cd/badges.mdx)

## Testing Strategy

Multi-layered testing approach ensuring production quality:

| **Test Type** | **Count** | **Command** | **Purpose** |
|---------------|-----------|-------------|-------------|
| **Unit Tests** | ~400 tests | `make test-unit` | Fast tests with mocked dependencies (2-5s) |
| **Integration Tests** | ~200 tests | `make test-integration` | End-to-end with real infrastructure |
| **Property Tests** | 27+ tests | `make test-property` | Edge case discovery with Hypothesis |
| **Contract Tests** | 20+ tests | `make test-contract` | MCP protocol compliance validation |
| **Performance Tests** | Baseline tracking | `make test-regression` | Latency monitoring (p95 thresholds) |
| **Mutation Tests** | 80%+ target | `make test-mutation` | Test effectiveness measurement |

**Quick Start**: `make test` (runs unit + integration tests)
**Coverage Report**: `make test-coverage` (opens htmlcov/index.html)
**Complete Details**: See [Testing Documentation](docs/advanced/testing.mdx) for metrics, strategies, and CI/CD integration

### CI/CD Test Execution

Tests run in parallel across multiple GitHub Actions workflows for comprehensive quality assurance:

| **Workflow** | **Tests** | **Duration** | **Trigger** | **Status Check** |
|--------------|-----------|--------------|-------------|------------------|
| **[ci.yaml](.github/workflows/ci.yaml)** | Unit tests (`pytest -m "unit and not llm"`) | ~5-10 min | Every PR, push to main/develop | ✅ Required |
| **[integration-tests.yaml](.github/workflows/integration-tests.yaml)** | Integration tests (`pytest -m integration`) | ~8-12 min | Every PR, push to main/develop | ✅ Required |
| **[e2e-tests.yaml](.github/workflows/e2e-tests.yaml)** | E2E tests (`pytest -m e2e`) + API tests | ~15-20 min | Every PR, push to main/develop, weekly | ✅ Required |
| **[quality-tests.yaml](.github/workflows/quality-tests.yaml)** | Property, contract, performance tests | ~10-15 min | Every PR, push to main/develop | ✅ Required |

**Infrastructure**:
- **ci.yaml**: Fast unit tests with mocked dependencies
- **integration-tests.yaml**: Full Docker stack with **4x parallelization** via pytest-split (PostgreSQL:9432, Redis:9379, OpenFGA:9080, Keycloak:9082, Qdrant:9333)
- **e2e-tests.yaml**: Full Docker stack on offset ports for complete user journey validation
- **quality-tests.yaml**: Property-based testing (Hypothesis), contract validation (MCP protocol), performance regression tracking

**Parallelization**:
- **integration-tests.yaml** uses pytest-split with matrix strategy (4 groups) for **4x faster execution**
- Each group runs independently for maximum CI efficiency

**Pre-push Hooks**:
- **Fast mode** (default): Optimized unit tests (~2-3 min) via pytest-xdist parallel execution
- **Comprehensive mode**: `make validate-pre-push` runs all test suites including integration tests (~8-12 min)

**Best Practice**: All workflows run in parallel for fast feedback. Integration tests now have **full CI visibility** with parallelization, catching infrastructure issues before merge.

## Feature Flags

Control features dynamically without code changes:

```bash
# Enable/disable features via environment variables
FF_ENABLE_PYDANTIC_AI_ROUTING=true      # Type-safe routing (default: true)
FF_ENABLE_LLM_FALLBACK=true             # Multi-model fallback (default: true)
FF_ENABLE_OPENFGA=true                  # Authorization (default: true)
FF_OPENFGA_STRICT_MODE=false            # Fail-closed vs fail-open (default: false)
FF_PYDANTIC_AI_CONFIDENCE_THRESHOLD=0.7 # Routing confidence (default: 0.7)

# All flags with FF_ prefix (20+ available)
```

**Key Flags**:
- `enable_pydantic_ai_routing`: Type-safe routing with confidence scores
- `enable_llm_fallback`: Automatic fallback to alternative models
- `enable_openfga`: Fine-grained authorization (disable for development)
- `openfga_strict_mode`: Fail-closed (deny on error) vs fail-open (allow on error)
- `enable_experimental_*`: Master switches for experimental features

**See**: `src/mcp_server_langgraph/core/feature_flags.py` for all flags and validation

## Observability

**Dual observability stack**: OpenTelemetry for infrastructure + LangSmith for LLM-specific tracing.

### LangSmith (LLM Observability)
Set `LANGSMITH_API_KEY` for automatic tracing of all LLM calls. Features: prompt engineering, evaluations, user feedback, cost tracking, debugging. View at [smith.langchain.com](https://smith.langchain.com/).

### OpenTelemetry (Infrastructure)
End-to-end distributed tracing with Jaeger (http://localhost:16686), metrics with Prometheus (http://localhost:9090), structured JSON logging with trace correlation. Automatic collection of 30+ metrics (tool calls, auth failures, response duration).

**Quick Start**: Run `docker compose up` to launch full observability stack (Jaeger, Prometheus, Grafana).

**See**: [Complete Observability Guide](docs/guides/observability.mdx) | [LangSmith Integration](integrations/langsmith.md) | [Monitoring Setup](docs/deployment/monitoring/overview.mdx)

## LangGraph Agent

The agent uses the functional API with:

- **State Management**: TypedDict-based state with message history
- **Conditional Routing**: Dynamic routing based on message content
- **Tool Integration**: Extensible tool system (extend in `src/mcp_server_langgraph/core/agent.py`)
- **Checkpointing**: Conversation persistence with MemorySaver

### Extending the Agent

Add tools in `src/mcp_server_langgraph/core/agent.py`:

```python
def custom_tool(state: AgentState) -> AgentState:
    # Your tool logic
    return state

workflow.add_node("custom_tool", custom_tool)
workflow.add_edge("router", "custom_tool")
```

## Configuration

All settings via environment variables, Infisical, or `.env` file. Key variable categories:

- **LLM**: `ANTHROPIC_API_KEY`, `MODEL_NAME` (Claude Sonnet 4.5 default), `GOOGLE_API_KEY`
- **Auth/Session**: `JWT_SECRET_KEY`, `OPENFGA_STORE_ID`, `OPENFGA_MODEL_ID`, `AUTH_PROVIDER` (inmemory/keycloak)
- **Observability**: `OTLP_ENDPOINT`, `LANGSMITH_API_KEY`, `LOG_LEVEL`
- **Anthropic Features**: Dynamic context loading, parallel execution, verification (all disabled by default)
- **Secrets Loading**: Infisical (preferred) → Environment variables → Defaults

**See**: [Complete Configuration Reference](docs/reference/environment-variables.mdx) | [Config Source Code](src/mcp_server_langgraph/core/config.py) | [Example .env](.env.example)

## Monitoring Dashboard

Access Grafana at http://localhost:3000 (admin/admin) and create dashboards using:

- **Prometheus datasource**: Metrics visualization
- **Jaeger datasource**: Trace exploration

Example queries:
- Request rate: `rate(agent_tool_calls_total[5m])`
- Error rate: `rate(agent_calls_failed_total[5m])`
- P95 latency: `histogram_quantile(0.95, agent_response_duration_bucket)`

## Security Considerations

🔒 **Production Checklist**:

- [ ] Store JWT secret in Infisical
- [ ] Use production Infisical project with proper access controls
- [ ] Configure OpenFGA with PostgreSQL backend (not in-memory)
- [ ] Enable OpenFGA audit logging
- [ ] Enable TLS for all services (OTLP, OpenFGA, PostgreSQL)
- [ ] Implement rate limiting on MCP endpoints
- [ ] Use production-grade user database
- [ ] Review and minimize OpenFGA permissions
- [ ] Set up secret rotation in Infisical
- [ ] Enable monitoring alerts for auth failures
- [ ] Implement token rotation and revocation
- [ ] Use separate OpenFGA stores per environment
- [ ] Enable MFA for Infisical access

## Deployment Options

Choose your deployment platform based on operational needs:

| Platform | Deploy Time | Best For | Key Features | Guide |
|----------|------------|----------|--------------|-------|
| **LangGraph Platform** | `uvx langgraph-cli deploy` | Zero-ops, full observability | Managed hosting, auto-scaling, integrated LangSmith | [Guide](docs/deployment/langgraph-platform.mdx) |
| **Google Cloud Run** | ~5 min | Serverless, pay-per-use | 0-100+ instances, auto HTTPS, Secret Manager | [Guide](docs/deployment/cloud-run.mdx) |
| **Kubernetes (GKE)** | ~30 min | Production, multi-cloud | Full Terraform, 32 overlays, Workload Identity, 🟢 Prod Ready | [Guide](docs/deployment/kubernetes.mdx) |
| **Kubernetes (EKS)** | ~30 min | AWS production | Full Terraform, Karpenter, IRSA, RDS/ElastiCache, 🟢 Prod Ready | [Guide](docs/deployment/kubernetes/eks-production.mdx) |
| **Kubernetes (AKS)** | ~45 min | Azure production | Manual deployment, 🔴 Alpha (Terraform in dev) | [Guide](docs/deployment/kubernetes/aks.mdx) |
| **Docker Compose** | 2 min | Local development | Full stack with observability, quick iteration | [Guide](docs/deployment/docker.mdx) |
| **Helm Charts** | 10 min | K8s with customization | Flexible values, multi-environment support | [Guide](docs/deployment/helm.mdx) |

**Kubernetes Platform Maturity**:
- **GKE**: Full automation (dev/staging/prod), 32 Kustomize overlays, Cloud SQL, Workload Identity
- **EKS**: Full automation (dev/staging/prod), Karpenter autoscaling, IRSA, RDS/ElastiCache
- **AKS**: Manual deployment only, Terraform automation under development
- **Rancher/Tanzu**: Generic manifests, community-supported

**Quick Kubernetes Deploy**:
```bash
# Helm deployment
helm install langgraph-agent ./deployments/helm/langgraph-agent --set image.tag=v1.0.0

# Or Kustomize
kubectl apply -k deployments/kustomize/overlays/production
```

**See**: [Complete Deployment Guide](docs/deployment/overview.mdx) | [Production Checklist](docs/deployment/production-checklist.mdx) | [GKE Staging Setup](docs/deployment/kubernetes/gke-staging.mdx)

## API Gateway & Rate Limiting

Kong API Gateway integration provides:
- **Rate Limiting**: Tiered limits (60-1000 req/min) per consumer/tier
- **Authentication**: JWT, API Key, OAuth2
- **Traffic Control**: Request transformation, routing, load balancing
- **Security**: IP restriction, bot detection, CORS
- **Monitoring**: Prometheus metrics, request logging

```bash
# Deploy with Kong rate limiting
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --set kong.enabled=true \
  --set kong.rateLimitTier=premium

# Or apply Kong manifests directly
kubectl apply -k deployments/kubernetes/kong/
```

See **[Kong Gateway Integration](integrations/kong.md)** for complete Kong setup and rate limiting configuration.

## MCP Transports & Registry

The agent supports multiple MCP transports:
- **StreamableHTTP** (Recommended): Modern HTTP streaming for production
- **stdio**: For Claude Desktop and local applications

```bash
# StreamableHTTP (recommended for web/production)
python -m mcp_server_langgraph.mcp.server_streamable

# stdio (local/desktop)
python -m mcp_server_langgraph.mcp.server_stdio

# Access StreamableHTTP endpoints
POST /message         # Main MCP endpoint (streaming or regular)
GET /tools            # List tools
GET /resources        # List resources
```

**Why StreamableHTTP?**
- ✅ Modern HTTP/2+ streaming
- ✅ Better load balancer/proxy compatibility
- ✅ Proper request/response pairs
- ✅ Full MCP spec compliance
- ✅ Works with Kong rate limiting

**Registry compliant** - Includes manifest files for MCP Registry publication.

See **[MCP Registry Guide](reference/mcp-registry.md)** for registry deployment and transport configuration.

## Quality Practices

**Quality Score: 9.6/10** across 7 dimensions (Code Organization, Testing, Type Safety, Documentation, Error Handling, Observability, Security).

**Quality Gates**: Pre-commit hooks (Ruff linting + formatting, mypy type checking, bandit security scanning) + CI/CD (unit/integration/property/contract/regression/mutation tests, OpenAPI validation). All tests run on Python 3.10-3.12.

**Linting & Formatting** (consolidated to Ruff for 10-100x faster performance):
- `make lint-check` - Run Ruff linter (replaces flake8 + isort checks)
- `make lint-fix` - Auto-fix linting issues + format code (replaces black + isort)
- `make lint-format` - Format code only (replaces black)
- `make lint-type-check` - Run mypy type checking (unchanged)
- `make lint-security` - Run bandit security scan (unchanged)

**Testing**:
- `make test-unit` - Fast unit tests with mocked dependencies
- `make test-integration` - End-to-end with real infrastructure
- `make test-coverage` - Generate coverage report
- `make validate-pre-push` - Quick validation (skip integration tests)
- `CI_PARITY=1 make validate-pre-push` - Full CI-equivalent validation (includes integration tests)

**Development**: Branch protection, conventional commits, code review required, 59 ADRs documenting architectural decisions.

**See**: [Complete Development Guide](.github/CLAUDE.md) | [Testing Strategy](docs/advanced/testing.mdx) | [Contributing Guidelines](CONTRIBUTING.md)

## Contributors

Thanks to all the amazing people who have contributed to this project! 🙌

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification.

Want to be listed here? See [CONTRIBUTING.md](.github/CONTRIBUTING.md)!

## Support

Need help? Check out our [Support Guide](.github/SUPPORT.md) for:

- 📚 Documentation links
- 💬 Where to ask questions
- 🐛 How to report bugs
- 🔒 Security reporting

## License

MIT - see [LICENSE](LICENSE) file for details

## Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent framework
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [OpenFGA](https://openfga.dev/) - Authorization
- [LiteLLM](https://github.com/BerriAI/litellm) - Multi-LLM support
- [OpenTelemetry](https://opentelemetry.io/) - Observability

Special thanks to the open source community!

## Contributing

We welcome contributions from the community! 🎉

### Quick Start for Contributors

1. **Read the guides**:
   - [CONTRIBUTING.md](.github/CONTRIBUTING.md) - Contribution guidelines
   - [Development Guide](docs/reference/development/development.mdx) - Developer setup

2. **Find something to work on**:
   - [Good First Issues](https://github.com/vishnu2kmohan/mcp-server-langgraph/labels/good%20first%20issue)
   - [Help Wanted](https://github.com/vishnu2kmohan/mcp-server-langgraph/labels/help%20wanted)

3. **Get help**:
   - [GitHub Discussions](https://github.com/vishnu2kmohan/mcp-server-langgraph/discussions)
   - [Support Guide](.github/SUPPORT.md)

### Git Hook Performance

This project uses tiered validation hooks optimized for developer productivity:

| Stage | Duration | What Runs | When |
|-------|----------|-----------|------|
| **Pre-commit** | < 30s | Formatting, linting, quick checks | Every commit |
| **Pre-push** | 8-12min | Unit, smoke, API, integration tests | Every push |
| **CI/Full** | 12-15min | Complete validation with CI profile | Pull requests, CI |

**Key Points**:
- Pre-push uses **dev profile** (25 property test examples) for faster iteration
- CI uses **ci profile** (100 property test examples) for thorough validation
- Integration tests included in pre-push for CI parity
- Bypass for emergencies: `git push --no-verify` (use sparingly!)

**Validation Tiers**:
```bash
make validate-commit      # Tier-1: < 30s (quick checks)
make validate-push        # Tier-2: 3-5min (focused validation)
make validate-pre-push    # Tier-3: 8-12min (CI-equivalent, includes integration)
```

See [CONTRIBUTING.md](.github/CONTRIBUTING.md#validation-workflow) for detailed validation workflow.

### Contribution Areas

- 💻 **Code**: Features, bug fixes, performance improvements
- 📖 **Documentation**: Guides, tutorials, API docs
- 🧪 **Testing**: Unit tests, integration tests, test coverage
- 🔒 **Security**: Security improvements, audits
- 🌐 **Translations**: i18n support (future)
- 💡 **Ideas**: Feature requests, architecture discussions

All contributors will be recognized in our [Contributors](#contributors) section!
