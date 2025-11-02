# MCP Server with LangGraph + OpenFGA & Infisical

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Production Ready](https://img.shields.io/badge/production-ready-brightgreen.svg)](docs/deployment/production-checklist.mdx)
[![Use This Template](https://img.shields.io/badge/use-this%20template-blue.svg?logo=cookiecutter)](https://github.com/vishnu2kmohan/mcp-server-langgraph#-use-this-template)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](Dockerfile)
[![Kubernetes](https://img.shields.io/badge/kubernetes-%23326ce5.svg?logo=kubernetes&logoColor=white)](docs/deployment/kubernetes.mdx)

<!-- CI/CD Status Badges -->
**CI/CD Pipeline:**
[![Main Pipeline](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/ci.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/ci.yaml)
[![E2E Tests](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/e2e-tests.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/e2e-tests.yaml)
[![Quality Tests](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/quality-tests.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/quality-tests.yaml)
[![Build Hygiene](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/build-hygiene.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/build-hygiene.yaml)
[![Coverage Trend](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/coverage-trend.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/coverage-trend.yaml)
[![Optional Deps](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/optional-deps-test.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/optional-deps-test.yaml)

**Security:**
[![Security Scan](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/security-scan.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/security-scan.yaml)
[![GCP Compliance](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/gcp-compliance-scan.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/gcp-compliance-scan.yaml)
[![GCP Drift Detection](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/gcp-drift-detection.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/gcp-drift-detection.yaml)

**Deployment:**
[![Release](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/release.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/release.yaml)
[![Deploy Staging](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/deploy-staging-gke.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/deploy-staging-gke.yaml)
[![Deploy Production](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/deploy-production-gke.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/deploy-production-gke.yaml)

**Automation:**
[![Dependabot Auto-merge](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/dependabot-automerge.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/dependabot-automerge.yaml)
[![Link Checker](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/link-checker.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/link-checker.yaml)
[![Stale Issues](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/stale.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/stale.yaml)
[![Version Bump](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/bump-deployment-versions.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/bump-deployment-versions.yaml)

[![Security Audit](https://img.shields.io/badge/security-audited-success.svg)](archive/SECURITY_AUDIT.md)
[![Code Quality](https://img.shields.io/badge/code%20quality-9.6%2F10-brightgreen.svg)](#quality-practices)
[![Code Coverage](https://img.shields.io/badge/coverage-see_testing_docs-blue.svg)](#testing-strategy)
[![Property Tests](https://img.shields.io/badge/property%20tests-27%2B-blue.svg)](#testing-strategy)
[![Contract Tests](https://img.shields.io/badge/contract%20tests-20%2B-blue.svg)](#testing-strategy)
[![Mutation Testing](https://img.shields.io/badge/mutation%20testing-enabled-yellow.svg)](docs-internal/MUTATION_TESTING.md)

A **production-ready cookie-cutter template** for building MCP servers with LangGraph's Functional API. Features comprehensive authentication (JWT), fine-grained authorization (OpenFGA), secrets management (Infisical), and OpenTelemetry-based observability.

**🎯 Opinionated, production-grade foundation for your MCP server projects.**

## 📑 Table of Contents

**Quick Links**:
- 🚀 [Use as Template](#-use-this-template) - Generate your own MCP server project
- ⚡ [Quick Start](#quick-start) - Get running in 2 minutes
- 📦 [Installation](#installation) - Setup instructions
- 🏗️ [Architecture](#architecture) - System design and agentic loop
- 🔐 [Authentication](#authentication--authorization) - Security setup
- 🚢 [Deployment](#deployment-options) - Production deployment guides

**Main Sections**:
- [Template vs Project Usage](#-template-vs-project-usage) - Choose your approach
- [Features](#features) - Core capabilities and best practices
- [Documentation](#-documentation) - Complete guides and references
- [Requirements](#requirements) - System and service requirements
- [Usage](#usage) - MCP server usage and client configuration
- [Testing Strategy](#testing-strategy) - Multi-layered testing approach
- [Feature Flags](#feature-flags) - Dynamic feature control
- [Observability](#observability) - LangSmith and OpenTelemetry
- [Configuration](#configuration) - Environment variables and settings
- [Security Considerations](#security-considerations) - Production checklist
- [API Gateway & Rate Limiting](#api-gateway--rate-limiting) - Kong integration
- [Quality Practices](#quality-practices) - Code quality standards
- [Contributing](#contributing) - Contribution guidelines
- [Support](#support) - Get help and report issues

---

## 🚀 Use This Template

```bash
# Generate your own MCP server project
uvx cookiecutter gh:vishnu2kmohan/mcp_server_langgraph

# Answer a few questions and get a fully configured project!
```

**See [Cookiecutter Template Strategy](adr/adr-0011-cookiecutter-template-strategy.md) for detailed information.**

---

## 📖 Template vs Project Usage

Choose the approach that matches your goals:

| **Use Case** | **As Template** | **Clone Directly** |
|--------------|-----------------|-------------------|
| **Best For** | Building your own custom MCP server | Learning, testing, or using reference implementation |
| **Command** | `uvx cookiecutter gh:vishnu2kmohan/mcp_server_langgraph` | `git clone https://github.com/vishnu2kmohan/mcp-server-langgraph.git && cd mcp-server-langgraph && uv sync` |
| **You Get** | Customizable project scaffold:<br/>• Your project name, author, license<br/>• Choose features (auth, observability, deployment)<br/>• Select LLM providers<br/>• Implement custom tools | Fully working reference implementation:<br/>• Example tools (`agent_chat`, `conversation_search`, `conversation_get`)<br/>• Complete observability stack<br/>• Production-ready deployment configs<br/>• Comprehensive test suite |
| **Next Steps** | 1. Customize tools in `agent.py`<br/>2. Update authorization in `scripts/setup/setup_openfga.py`<br/>3. Configure `.env` with your API keys<br/>4. Deploy your custom server | 1. Copy `.env.example` to `.env`<br/>2. Add API keys (GOOGLE_API_KEY, etc.)<br/>3. Run `make run-streamable`<br/>4. See [Quick Start](#quick-start) for details |
| **Learn More** | [Cookiecutter Template Strategy (ADR-0011)](adr/adr-0011-cookiecutter-template-strategy.md) | [Quick Start Guide](#quick-start) |

**💡 Recommendation**: Use **As Template** for production projects, **Clone Directly** for learning and testing.

---

## Features

### ⭐ Anthropic Best Practices (9.8/10 Adherence)

This project achieves **reference-quality implementation** of Anthropic's AI agent best practices:

- **🎯 Just-in-Time Context Loading**: Dynamic semantic search with Qdrant vector database
  - Load only relevant context when needed (60% token reduction)
  - Progressive discovery through iterative search
  - Token-aware batch loading with configurable budgets
- **⚡ Parallel Tool Execution**: Concurrent execution with automatic dependency resolution
  - 1.5-2.5x latency reduction for independent operations
  - Topological sorting for correct execution order
  - Graceful error handling and recovery
- **📝 Enhanced Structured Note-Taking**: LLM-based 6-category information extraction
  - Automatic categorization: decisions, requirements, facts, action_items, issues, preferences
  - Context preservation across multi-turn conversations
  - Fallback to rule-based extraction for reliability
- **✅ Complete Agentic Loop**: Full gather-action-verify-repeat cycle
  - Context compaction (40-60% token reduction)
  - LLM-as-judge verification (23% quality improvement)
  - Iterative refinement (up to 3 attempts)
  - Observable with full tracing

**See**: [Anthropic Best Practices Assessment](reports/ANTHROPIC_BEST_PRACTICES_ASSESSMENT_20251017.md) | [ADR-0023](adr/adr-0023-anthropic-tool-design-best-practices.md) | [ADR-0024](adr/adr-0024-agentic-loop-implementation.md) | [ADR-0025](adr/adr-0025-anthropic-best-practices-enhancements.md) | [Examples](examples/README.md)

### 🎯 Core Capabilities
- **Multi-LLM Support (LiteLLM)**: 100+ LLM providers - Anthropic, OpenAI, Google, Azure, AWS Bedrock, Ollama
- **Open-Source Models**: Llama 3.1, Qwen 2.5, Mistral, DeepSeek, and more via Ollama
- **LangGraph Functional API**: Stateful agent with conditional routing and checkpointing
- **MCP Server**: Standard protocol for exposing AI agents as tools (stdio, StreamableHTTP)
- **Enterprise Authentication**: Pluggable auth providers (InMemory, Keycloak SSO)
  - **JWT Authentication**: Token-based authentication with validation and expiration
  - **Keycloak Integration**: Production-ready SSO with OIDC/OAuth2 ([integrations/keycloak.md](integrations/keycloak.md))
  - **Token Refresh**: Automatic refresh token rotation
  - **JWKS Verification**: Public key verification without shared secrets
- **Session Management**: Flexible session storage backends
  - **InMemory**: Fast in-memory sessions for development
  - **Redis**: Persistent sessions with TTL, sliding windows, concurrent limits
  - **Advanced Features**: Session lifecycle management, bulk revocation, user tracking
- **Fine-Grained Authorization**: OpenFGA (Zanzibar-style) relationship-based access control
  - **Role Mapping**: Declarative role mappings with YAML configuration
  - **Keycloak Sync**: Automatic role/group synchronization to OpenFGA
  - **Hierarchies**: Role inheritance and conditional mappings
- **Secrets Management**: Infisical integration for secure secret storage and retrieval
- **Feature Flags**: Gradual rollouts with environment-based configuration
- **Dual Observability**: OpenTelemetry + LangSmith for comprehensive monitoring
  - **OpenTelemetry**: Distributed tracing with Jaeger, metrics with Prometheus (30+ auth metrics)
  - **LangSmith**: LLM-specific tracing, prompt engineering, evaluations
- **Structured Logging**: JSON logging with trace context correlation
- **Full Observability Stack**: Docker Compose setup with OpenFGA, Keycloak, Redis, Jaeger, Prometheus, Grafana, and Qdrant
- **LangGraph Platform**: Deploy to managed LangGraph Cloud with one command
- **Automatic Fallback**: Resilient multi-model fallback for high availability

### 🔒 GDPR & Privacy Compliance

Complete GDPR compliance implementation with production-ready PostgreSQL storage ([ADR-0041](adr/ADR-0041-postgresql-gdpr-storage.md)):

- **Data Subject Rights API**: 6 endpoints implementing GDPR Articles 15-21
  - **Right to Access** (Article 15): `GET /api/v1/users/me/data` - Complete data export
  - **Right to Data Portability** (Article 20): `GET /api/v1/users/me/export` - JSON/CSV export
  - **Right to Rectification** (Article 16): `PATCH /api/v1/users/me` - Update profile
  - **Right to Erasure** (Article 17): `DELETE /api/v1/users/me` - Delete all data
  - **Right to Object** (Article 21): `POST/GET /api/v1/users/me/consent` - Consent management
  - See: [GDPR API Reference](docs/api-reference/gdpr-endpoints.mdx)

- **PostgreSQL Storage Backend**: ACID-compliant, cost-effective compliance storage
  - **5 Tables**: user_profiles, user_preferences, consent_records, conversations, audit_logs
  - **Atomic Deletions**: Single transaction for GDPR Article 17 compliance
  - **Retention Policies**: 7-year audit logs (HIPAA §164.316), 90-day conversations (GDPR Article 5)
  - **14x Cost Savings**: $50/month vs $720/month for Redis (7-year storage)
  - **5-10ms Latency**: Acceptable for user-initiated GDPR operations
  - See: [GDPR Storage Configuration](docs/deployment/gdpr-storage-configuration.mdx)

- **Audit Trail**: Complete compliance logging
  - All GDPR operations logged with user_id, timestamp, IP address, GDPR article
  - Anonymized audit logs after deletion (user_id → cryptographic hash)
  - 7-year retention for HIPAA/SOC2 compliance

- **Production Guard**: Runtime protection against data loss
  - Blocks GDPR endpoints if using in-memory storage in production
  - Prevents compliance violations from misconfiguration

**Compliance Coverage**: GDPR (Articles 5, 7, 15-17, 20-21), HIPAA (§164.312, §164.316), SOC2 (CC6.6, PI1.4)

**Documentation**:
- [GDPR API Endpoints](docs/api-reference/gdpr-endpoints.mdx) - Complete API reference with examples
- [ADR-0041: PostgreSQL GDPR Storage](adr/ADR-0041-postgresql-gdpr-storage.md) - Architecture decision
- [GDPR Storage Configuration](docs/deployment/gdpr-storage-configuration.mdx) - Setup guide
- [Database Migrations](docs/deployment/database-migrations.mdx) - Schema management

### 📦 Optional Dependencies

The project supports optional feature sets that can be installed on demand:

- **Secrets Management** (`[secrets]`): Infisical integration for centralized secrets
  - Install: `uv sync --extra secrets`
  - Fallback: Environment variables (`.env` file)
  - Production: Recommended for secure secret rotation
  - See: [Infisical Installation Guide](docs/deployment/infisical-installation.mdx)

- **Self-Hosted Embeddings** (`[embeddings]`): sentence-transformers for local embedding generation
  - Install: `uv sync --extra embeddings`
  - Fallback: Google Gemini API (langchain-google-genai, installed by default)
  - Production: Use API-based embeddings (lower latency, no GPU required)
  - Note: Self-hosted embeddings require significant resources

- **GDPR Storage Backend**: PostgreSQL or Redis for compliance data persistence
  - **CRITICAL**: In-memory storage is NOT production-ready
  - Required for: GDPR compliance endpoints (`/api/v1/users/me/*`)
  - Config: Set `GDPR_STORAGE_BACKEND=postgres` or `redis` in production
  - See: [GDPR Storage Configuration](docs/deployment/gdpr-storage-configuration.mdx)

- **All Features** (`[all]`): Install all optional dependencies
  - Install: `uv sync --all-extras`
  - Use for: Development, testing, full feature evaluation

**Development vs Production**:
- Development: All features work with fallbacks (in-memory, env vars, API-based)
- Production: Use persistent backends (Redis, PostgreSQL) and proper secret management

### 🧪 Quality & Testing
- **Property-Based Testing**: 27+ Hypothesis tests discovering edge cases automatically
- **Contract Testing**: 20+ JSON Schema tests ensuring MCP protocol compliance
- **Performance Regression Testing**: Automated latency tracking against baselines
- **Mutation Testing**: Test effectiveness verification with mutmut (80%+ target)
- **Strict Typing**: Gradual mypy strict mode rollout (3 modules complete)
- **OpenAPI Validation**: Automated schema generation and breaking change detection
- **Comprehensive Test Coverage**: Unit, integration, property-based, and contract tests. See [testing docs](docs/advanced/testing.mdx) for metrics.

### 🚀 Production Deployment
- **Kubernetes Ready**: Production manifests for GKE, EKS, AKS, Rancher, VMware Tanzu
- **Helm Charts**: Flexible deployment with customizable values and dependencies
- **Kustomize**: Environment-specific overlays (dev/staging/production)
- **Multi-Platform**: Docker Compose, kubectl, Kustomize, Helm deployment options
- **CI/CD Pipeline**: Automated testing, validation, build, and deployment with GitHub Actions
- **Deployment Validation**: Comprehensive validation scripts for all deployment configurations
- **E2E Testing**: Automated deployment tests with kind clusters
- **High Availability**: Pod anti-affinity, HPA, PDB, rolling updates
- **Monitoring**: 25+ Prometheus alerts, 4 Grafana dashboards, 9 operational runbooks
- **Observability**: Full monitoring for Keycloak, Redis, sessions, and application
- **Secrets**: External secrets operator support, sealed secrets compatible
- **Service Mesh**: Compatible with Istio, Linkerd, and other service meshes

## 📚 Documentation

- **[📖 Mintlify Documentation](https://mcp-server-langgraph.mintlify.app)** - Complete online documentation with guides, tutorials, and references
- **[API Documentation](http://localhost:8000/docs)** - Interactive OpenAPI/Swagger UI (when running locally)
- **[Mintlify Deployment Guide](docs-internal/DEPLOYMENT.md)** - How to deploy documentation updates

### 📖 Quality & Testing Guides
- **[Mutation Testing Guide](docs-internal/testing/mutation-testing.md)** - Test effectiveness measurement and improvement
- **[Strict Typing Guide](docs-internal/architecture/strict-typing-guide.md)** - Gradual mypy strict mode rollout
- **[Architecture Decision Records](adr/)** - Documented architectural choices

### 🚀 Deployment & Operations
- **[Deployment Quickstart](deployments/QUICKSTART.md)** - Quick deployment guide for all platforms
- **[Deployment README](deployments/README.md)** - Comprehensive deployment documentation
- **[CI/CD Guide](docs/reference/development/ci-cd.mdx)** - Continuous integration and deployment pipeline
- **[Keycloak Integration](integrations/keycloak.md)** - Enterprise SSO setup and configuration

### 📝 Architecture Decision Records (ADRs)
- [0001: Multi-Provider LLM Support (LiteLLM)](adr/adr-0001-llm-multi-provider.md)
- [0002: Fine-Grained Authorization (OpenFGA)](adr/adr-0002-openfga-authorization.md)
- [0003: Dual Observability Strategy](adr/adr-0003-dual-observability.md)
- [0004: MCP Transport Selection (StreamableHTTP)](adr/adr-0004-mcp-streamable-http.md)
- [0005: Type-Safe Responses (Pydantic AI)](adr/adr-0005-pydantic-ai-integration.md)
- [0023: Anthropic Tool Design Best Practices](adr/adr-0023-anthropic-tool-design-best-practices.md)
- [0024: Agentic Loop Implementation](adr/adr-0024-agentic-loop-implementation.md)
- [0025: Anthropic Best Practices - Advanced Enhancements](adr/adr-0025-anthropic-best-practices-enhancements.md)
- [See all 39 ADRs](adr/README.md)

### 💡 Examples & Tutorials
- **[Examples Directory](examples/README.md)** - Comprehensive examples demonstrating all features
  - [Dynamic Context Loading](examples/dynamic_context_usage.py) - Just-in-Time semantic search
  - [Parallel Tool Execution](examples/parallel_execution_demo.py) - Concurrent execution patterns
  - [Enhanced Note-Taking](examples/llm_extraction_demo.py) - LLM-based information extraction
  - [Complete Workflow](examples/full_workflow_demo.py) - Full agentic loop demonstration

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

### Quick Install

**Using uv (recommended)**:

This project uses [uv](https://github.com/astral-sh/uv) for fast, reliable dependency management:

```bash
# Install from PyPI
uv pip install mcp-server-langgraph

# Or clone and develop locally (creates virtual environment automatically)
git clone https://github.com/vishnu2kmohan/mcp-server-langgraph.git
cd mcp-server-langgraph
uv sync  # Installs all dependencies from pyproject.toml and uv.lock
```

**Why uv?**
- ⚡ **10-100x faster** than pip
- 🔒 **Reproducible builds** via uv.lock lockfile
- 📦 **Single source of truth** in pyproject.toml
- 🛡️ **Better dependency resolution**

> **Note**: requirements*.txt files are deprecated. Use `uv sync` instead.

### Verify Installation
```bash
python -c "import mcp_server_langgraph; print(mcp_server_langgraph.__version__)"
```

See [Installation Guide](docs/getting-started/installation.mdx) for complete instructions, including:
- Docker installation
- Virtual environment setup
- Dependency management
- Configuration options

## Architecture

### System Architecture

```mermaid
flowchart TB
    subgraph client["MCP Client"]
        mcpclient["Claude Desktop<br/>or other MCP client"]
    end

    subgraph server["MCP Server<br/>(server_stdio.py / streamable.py)"]
        auth["Auth Middleware<br/>• JWT Verification<br/>• OpenFGA Authorization"]
        agent["LangGraph Agent<br/>• Context Compaction<br/>• Pydantic AI Routing<br/>• Tool Execution<br/>• Response Generation<br/>• Output Verification<br/>• Iterative Refinement"]
    end

    subgraph observability["Observability Stack"]
        jaeger["Jaeger<br/>(Traces)"]
        prometheus["Prometheus<br/>(Metrics)"]
        grafana["Grafana<br/>(Dashboards)"]
    end

    mcpclient --> auth
    auth --> agent
    agent --> jaeger
    agent --> prometheus
    jaeger --> grafana
    prometheus --> grafana

    %% ColorBrewer2 Set3 palette - each component type uniquely colored
    classDef clientStyle fill:#8dd3c7,stroke:#2a9d8f,stroke-width:2px,color:#333
    classDef authStyle fill:#fdb462,stroke:#e67e22,stroke-width:2px,color:#333
    classDef agentStyle fill:#b3de69,stroke:#7cb342,stroke-width:2px,color:#333
    classDef observabilityStyle fill:#fccde5,stroke:#ec7ab8,stroke-width:2px,color:#333

    class mcpclient clientStyle
    class auth authStyle
    class agent agentStyle
    class jaeger,prometheus,grafana observabilityStyle
```

### Agentic Loop (ADR-0024, ADR-0025)

Our agent implements Anthropic's full **gather-action-verify-repeat** cycle with advanced enhancements:

```mermaid
flowchart TD
    START([START]) --> load["0. Load Context<br/>(Dynamic)<br/><br/>Just-in-Time<br/>Semantic Search"]
    load --> gather["1. Gather Context<br/>(Compact)<br/><br/>Compaction when<br/>approaching limits"]
    gather --> action["2. Take Action<br/>(Route/Tools)<br/><br/>Route & Execute<br/>(Parallel if enabled)"]
    action --> respond["Generate Response"]
    respond --> verify{"3. Verify Work<br/>(Verify)<br/><br/>LLM-as-Judge<br/>Quality Check"}
    verify -->|Passed| END([END])
    verify -->|Failed| refine["4. Repeat<br/>(Refine)<br/><br/>Max 3×"]
    refine --> respond

    %% ColorBrewer2 Set3 palette - each component type uniquely colored
    classDef startEndStyle fill:#8dd3c7,stroke:#2a9d8f,stroke-width:2px,color:#333
    classDef processStyle fill:#fdb462,stroke:#e67e22,stroke-width:2px,color:#333
    classDef responseStyle fill:#b3de69,stroke:#7cb342,stroke-width:2px,color:#333
    classDef decisionStyle fill:#ffffb3,stroke:#f1c40f,stroke-width:2px,color:#333
    classDef refineStyle fill:#bc80bd,stroke:#8e44ad,stroke-width:2px,color:#333

    class START,END startEndStyle
    class load,gather,action processStyle
    class respond responseStyle
    class verify decisionStyle
    class refine refineStyle
```

**Key Features**:
- **Just-in-Time Context Loading**: Dynamic semantic search (60% token reduction)
- **Context Compaction**: Prevents overflow on long conversations (40-60% token reduction)
- **Parallel Tool Execution**: Concurrent execution with dependency resolution (1.5-2.5x speedup)
- **Enhanced Note-Taking**: LLM-based 6-category extraction for long-term context
- **Output Verification**: LLM-as-judge pattern catches errors before users see them (23% quality improvement)
- **Iterative Refinement**: Up to 3 self-correction attempts for quality
- **Observable**: Full tracing of each loop component

See [ADR-0024: Agentic Loop Implementation](adr/adr-0024-agentic-loop-implementation.md) and [ADR-0025: Advanced Enhancements](adr/adr-0025-anthropic-best-practices-enhancements.md) for details.

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

1. **Install dependencies**:
```bash
uv sync  # Install all dependencies and create virtual environment
# Note: Creates .venv automatically with all dependencies from pyproject.toml
```

2. **Start infrastructure** (without agent):
```bash
# Start only supporting services
docker-compose up -d openfga postgres otel-collector jaeger prometheus grafana
```

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your API keys:
# - GOOGLE_API_KEY (get from https://aistudio.google.com/apikey)
# - ANTHROPIC_API_KEY or OPENAI_API_KEY (optional)
```

4. **Setup OpenFGA**:
```bash
python scripts/setup/setup_openfga.py
# Save OPENFGA_STORE_ID and OPENFGA_MODEL_ID to .env
```

5. **Run the agent locally**:
```bash
python -m mcp_server_langgraph.mcp.server_streamable
```

6. **Test**:
```bash
# Test with example client
python examples/client_stdio.py

# Or curl
curl http://localhost:8000/health
```

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

## CI/CD Pipeline Architecture

Our CI/CD pipeline implements a comprehensive, production-grade workflow with 16 specialized workflows organized into four categories:

```mermaid
graph TB
    %% Event Triggers
    PR[Pull Request]
    PUSH[Push to main/develop]
    RELEASE[Release Published]
    SCHEDULE[Scheduled Runs]
    MANUAL[Manual Trigger]

    %% CI/CD Pipeline Category
    subgraph "🔄 CI/CD Pipeline"
        CI[Main CI/CD Pipeline<br/>- Unit tests Python 3.10-3.12<br/>- Docker builds base/full/test<br/>- Multi-platform amd64/arm64]
        E2E[E2E Tests<br/>- Full user journeys<br/>- Isolated test infra<br/>- Integration scenarios]
        QUALITY[Quality Tests<br/>- Property tests Hypothesis<br/>- Contract tests MCP<br/>- Performance regression<br/>- Mutation testing]
        COVERAGE[Coverage Tracking<br/>- Historical trends<br/>- Fail if drop >5%<br/>- PR comments]
        BUILD_HYG[Build Hygiene<br/>- Artifact validation<br/>- Build reproducibility]
        OPT_DEPS[Optional Deps Test<br/>- Test all combinations<br/>- Graceful degradation]
    end

    %% Security Category
    subgraph "🔒 Security"
        SECURITY[Security Scan<br/>- Trivy fs/image/config<br/>- Dependency check<br/>- CodeQL analysis<br/>- Secrets scan<br/>- SBOM generation]
        GCP_COMPLIANCE[GCP Compliance<br/>- Terraform security<br/>- K8s manifest validation<br/>- CIS benchmarks<br/>- OPA policies]
        GCP_DRIFT[GCP Drift Detection<br/>- Terraform drift check<br/>- Auto-remediation option<br/>- Issue creation]
    end

    %% Deployment Category
    subgraph "🚀 Deployment"
        RELEASE_WF[Release Workflow<br/>- Automated releases<br/>- Changelog generation<br/>- Multi-arch images]
        DEPLOY_STAGING[Deploy Staging GKE<br/>- Auto-deploy main<br/>- Smoke tests<br/>- Rollback on failure]
        DEPLOY_PROD[Deploy Production GKE<br/>- Manual approval<br/>- Pre-deploy validation<br/>- Security checks<br/>- Performance baseline]
        VERSION_BUMP[Version Bump<br/>- Auto-update deployments<br/>- Kustomize overlays]
    end

    %% Automation Category
    subgraph "🤖 Automation"
        DEPENDABOT[Dependabot Auto-merge<br/>- Auto-approve patches<br/>- Run tests before merge]
        LINK_CHECK[Link Checker<br/>- Validate docs links<br/>- Create issues if broken]
        STALE[Stale Management<br/>- Auto-close inactive<br/>- Reminder comments]
    end

    %% Event flow
    PR --> CI
    PR --> E2E
    PR --> QUALITY
    PR --> COVERAGE
    PR --> BUILD_HYG
    PR --> SECURITY
    PR --> LINK_CHECK

    PUSH --> CI
    PUSH --> E2E
    PUSH --> QUALITY
    PUSH --> COVERAGE
    PUSH --> SECURITY
    PUSH --> GCP_COMPLIANCE
    PUSH --> DEPLOY_STAGING

    RELEASE --> RELEASE_WF
    RELEASE --> DEPLOY_PROD
    RELEASE --> VERSION_BUMP

    SCHEDULE --> QUALITY
    SCHEDULE --> SECURITY
    SCHEDULE --> GCP_COMPLIANCE
    SCHEDULE --> GCP_DRIFT
    SCHEDULE --> LINK_CHECK
    SCHEDULE --> STALE
    SCHEDULE --> OPT_DEPS

    MANUAL --> CI
    MANUAL --> SECURITY
    MANUAL --> DEPLOY_PROD

    %% Dependencies
    CI -.-> DEPLOY_STAGING
    RELEASE_WF -.-> DEPLOY_PROD
    SECURITY -.-> DEPLOY_PROD

    %% Styling
    classDef cicd fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef security fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef deployment fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef automation fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef event fill:#fce4ec,stroke:#c2185b,stroke-width:2px

    class CI,E2E,QUALITY,COVERAGE,BUILD_HYG,OPT_DEPS cicd
    class SECURITY,GCP_COMPLIANCE,GCP_DRIFT security
    class RELEASE_WF,DEPLOY_STAGING,DEPLOY_PROD,VERSION_BUMP deployment
    class DEPENDABOT,LINK_CHECK,STALE automation
    class PR,PUSH,RELEASE,SCHEDULE,MANUAL event
```

**Key Metrics:**
- **Build Time:** 12 min avg (66% faster than baseline)
- **Cost:** ~$40/month GitHub Actions
- **Coverage:** 80%+ code coverage enforced
- **Security:** Daily scans + PR checks
- **Deployment:** Automated staging, manual prod approval

**Workflow Details:** See individual workflow files in `.github/workflows/` for complete configuration.

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

This project supports **dual observability**: OpenTelemetry for infrastructure metrics and LangSmith for LLM-specific tracing.

### LangSmith Tracing (LLM Observability)

LangSmith provides comprehensive LLM and agent observability:

**Setup**:
```bash
# Add to .env
LANGSMITH_API_KEY=your-key-from-smith.langchain.com
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=mcp-server-langgraph
```

**Features**:
- 🔍 **Automatic Tracing**: All LLM calls and agent steps traced
- 🎯 **Prompt Engineering**: Iterate on prompts with production data
- 📊 **Evaluations**: Compare model performance on datasets
- 💬 **User Feedback**: Collect and analyze user ratings
- 💰 **Cost Tracking**: Monitor LLM API costs per user/session
- 🐛 **Debugging**: Root cause analysis with full context

**View traces**: https://smith.langchain.com/

See **[LangSmith Integration Guide](integrations/langsmith.md)** for complete setup guide.

### OpenTelemetry Tracing (Infrastructure)

Every request is traced end-to-end with OpenTelemetry:

```python
from mcp_server_langgraph.observability.telemetry import tracer

with tracer.start_as_current_span("my_operation") as span:
    span.set_attribute("custom.attribute", "value")
    # Your code here
```

View traces in Jaeger: http://localhost:16686

### Metrics

Standard metrics are automatically collected:

- `agent.tool.calls`: Tool invocation counter
- `agent.calls.successful`: Successful operation counter
- `agent.calls.failed`: Failed operation counter
- `auth.failures`: Authentication failure counter
- `authz.failures`: Authorization failure counter
- `agent.response.duration`: Response time histogram

View metrics in Prometheus: http://localhost:9090

### Logging

Structured logging with trace context:

```python
from mcp_server_langgraph.observability.telemetry import logger

logger.info("Event occurred", extra={
    "user_id": "user_123",
    "custom_field": "value"
})
```

Logs include trace_id and span_id for correlation with traces.

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

All settings via environment variables, Infisical, or `.env` file:

### Core Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_NAME` | Service identifier | `mcp-server-langgraph` |
| `OTLP_ENDPOINT` | OpenTelemetry collector | `http://localhost:4317` |
| `JWT_SECRET_KEY` | Secret for JWT signing | (loaded from Infisical) |
| `ANTHROPIC_API_KEY` | Anthropic API key | (loaded from Infisical) |
| `MODEL_NAME` | Claude model to use | `claude-sonnet-4-5` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `OPENFGA_API_URL` | OpenFGA server URL | `http://localhost:8080` |
| `OPENFGA_STORE_ID` | OpenFGA store ID | (from setup) |
| `OPENFGA_MODEL_ID` | OpenFGA model ID | (from setup) |
| `INFISICAL_CLIENT_ID` | Infisical auth client ID | (optional) |
| `INFISICAL_CLIENT_SECRET` | Infisical auth secret | (optional) |
| `INFISICAL_PROJECT_ID` | Infisical project ID | (optional) |

### Anthropic Best Practices Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| **Dynamic Context Loading** | | |
| `ENABLE_DYNAMIC_CONTEXT_LOADING` | Enable just-in-time context loading | `false` |
| `QDRANT_URL` | Qdrant server URL | `localhost` |
| `QDRANT_PORT` | Qdrant server port | `6333` |
| `QDRANT_COLLECTION_NAME` | Collection name for contexts | `mcp_context` |
| `DYNAMIC_CONTEXT_MAX_TOKENS` | Max tokens per context load | `2000` |
| `DYNAMIC_CONTEXT_TOP_K` | Number of contexts to retrieve | `3` |
| `EMBEDDING_MODEL` | SentenceTransformer model | `all-MiniLM-L6-v2` |
| `CONTEXT_CACHE_SIZE` | LRU cache size | `100` |
| **Parallel Execution** | | |
| `ENABLE_PARALLEL_EXECUTION` | Enable parallel tool execution | `false` |
| `MAX_PARALLEL_TOOLS` | Max concurrent tool executions | `5` |
| **Enhanced Note-Taking** | | |
| `ENABLE_LLM_EXTRACTION` | Enable LLM-based extraction | `false` |
| **Context Management** | | |
| `ENABLE_CONTEXT_COMPACTION` | Enable context compaction | `true` |
| `COMPACTION_THRESHOLD` | Token count triggering compaction | `8000` |
| `TARGET_AFTER_COMPACTION` | Target tokens after compaction | `4000` |
| `RECENT_MESSAGE_COUNT` | Messages to keep uncompacted | `5` |
| **Verification** | | |
| `ENABLE_VERIFICATION` | Enable response verification | `true` |
| `VERIFICATION_QUALITY_THRESHOLD` | Quality score threshold | `0.7` |
| `MAX_REFINEMENT_ATTEMPTS` | Max refinement iterations | `3` |

See `src/mcp_server_langgraph/core/config.py` for all options and `.env.example` for complete examples.

### Secrets Loading Priority

1. **Infisical** (if configured)
2. **Environment variables** (fallback)
3. **Default values** (last resort)

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

### LangGraph Platform (Managed Cloud)

Deploy to LangGraph Platform for fully managed, serverless hosting:

```bash
# Login (uvx runs langgraph-cli without installing it)
uvx langgraph-cli login

# Deploy
uvx langgraph-cli deploy
```

**Benefits**:
- ✅ Zero infrastructure management
- ✅ Integrated LangSmith observability
- ✅ Automatic versioning and rollbacks
- ✅ Built-in scaling and load balancing
- ✅ One-command deployment

See **[LangGraph Platform Guide](docs/deployment/langgraph-platform.mdx)** for complete platform deployment guide.

### Google Cloud Run (Serverless)

Deploy to Google Cloud Run for fully managed, serverless deployment:

```bash
# Quick deploy
cd cloudrun
./deploy.sh --setup

# Or use gcloud directly
gcloud run deploy mcp-server-langgraph \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

**Benefits**:
- ✅ Serverless autoscaling (0 to 100+ instances)
- ✅ Pay only for actual usage
- ✅ Automatic HTTPS and SSL certificates
- ✅ Integrated with Google Secret Manager
- ✅ Built-in monitoring and logging

See **[Cloud Run Deployment Guide](docs/deployment/cloud-run.mdx)** for complete Cloud Run deployment guide.

### Kubernetes Deployment

The agent is fully containerized and ready for Kubernetes deployment. Supported platforms:
- Google Kubernetes Engine (GKE)
- Amazon Elastic Kubernetes Service (EKS)
- Azure Kubernetes Service (AKS)
- Rancher
- VMware Tanzu

**Quick Deploy**:

```bash
# Build and push image
docker build -t your-registry/langgraph-agent:v1.0.0 .
docker push your-registry/langgraph-agent:v1.0.0

# Deploy with Helm
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --set image.repository=your-registry/langgraph-agent \
  --set image.tag=v1.0.0

# Or deploy with Kustomize
kubectl apply -k deployments/kustomize/overlays/production
```

See **[Kubernetes Deployment Guide](docs/deployment/kubernetes.mdx)** for complete deployment guide.

### GKE Staging Environment (Production-Grade)

Deploy to a secure, production-ready staging environment on Google Kubernetes Engine:

```bash
# One-time infrastructure setup
./scripts/gcp/setup-staging-infrastructure.sh

# Deploy application
kubectl apply -k deployments/overlays/staging-gke

# Run smoke tests
./scripts/gcp/staging-smoke-tests.sh
```

**Security Features**:
- ✅ **Network Isolation**: Separate VPC from production
- ✅ **Workload Identity**: Keyless authentication (no service account keys)
- ✅ **Private GKE**: Private nodes with shielded boot
- ✅ **Binary Authorization**: Only approved images deployed
- ✅ **Network Policies**: Restrict pod-to-pod traffic
- ✅ **Secret Manager**: Centralized secret management

**Automated Deployments**:
- GitHub Actions with Workload Identity Federation
- Automated smoke tests and validation
- Auto-rollback on failure
- Approval gates before deployment

See **[GKE Staging Guide](docs/deployment/kubernetes/gke-staging.mdx)** for complete setup guide.

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

This project maintains high code quality through:

### 📈 Current Quality Score: **9.6/10**

Assessed across 7 dimensions:
- ✅ **Code Organization**: 9/10 - Clear module structure, separation of concerns
- ✅ **Testing**: 10/10 - Multi-layered testing (unit, integration, property, contract, regression, mutation)
- ✅ **Type Safety**: 9/10 - Gradual strict mypy rollout (Phases 1-3 complete: 18+ modules strict, ~22 modules remaining)
- ✅ **Documentation**: 10/10 - ADRs, guides, API docs, inline documentation
- ✅ **Error Handling**: 9/10 - Comprehensive error handling, fallback modes
- ✅ **Observability**: 10/10 - Dual observability (OpenTelemetry + LangSmith)
- ✅ **Security**: 9/10 - JWT auth, fine-grained authz, secrets management, security scanning

### 🎯 Quality Gates

**Pre-Commit**:
- Code formatting (black, isort)
- Linting (flake8, mypy)
- Security scan (bandit)

**CI/CD (GitHub Actions)**:
- Unit tests (Python 3.10, 3.11, 3.12)
- Integration tests
- Property-based tests
- Contract tests
- Performance regression tests
- OpenAPI validation
- Mutation tests (weekly)

**Commands**:
```bash
# Code quality checks
make format           # Format code (black + isort)
make lint             # Run linters (flake8 + mypy)
make security-check   # Security scan (bandit)

# Test suite
make test-unit        # Fast unit tests
make test-all-quality # Property + contract + regression
make test-coverage    # Coverage report
```

### 📝 Development Workflow

1. **Branch Protection**: All changes via Pull Requests
2. **Conventional Commits**: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`
3. **Code Review**: Required before merge
4. **Quality Gates**: All tests must pass
5. **Documentation**: ADRs for architectural decisions

**See**: [.github/CLAUDE.md](.github/CLAUDE.md) for complete development guide

### 🔄 Continuous Improvement

**In Progress**:
- Expanding strict mypy to all modules (3/11 complete)
- Increasing mutation score to 80%+ on all critical modules
- Adding more property-based tests for edge case discovery

**Recent Improvements** (2025):
- Implemented Anthropic's agentic loop (ADR-0024) with context compaction and verification
- Adopted Anthropic's tool design best practices (ADR-0023)
- Added 27+ property-based tests (Hypothesis)
- Added 20+ contract tests (JSON Schema)
- Implemented performance regression tracking
- Set up mutation testing with mutmut
- Created 25 Architecture Decision Records
- Implemented feature flag system

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
   - [Good First Issues](https://github.com/vishnu2kmohan/mcp_server_langgraph/labels/good%20first%20issue)
   - [Help Wanted](https://github.com/vishnu2kmohan/mcp_server_langgraph/labels/help%20wanted)

3. **Get help**:
   - [GitHub Discussions](https://github.com/vishnu2kmohan/mcp_server_langgraph/discussions)
   - [Support Guide](.github/SUPPORT.md)

### Contribution Areas

- 💻 **Code**: Features, bug fixes, performance improvements
- 📖 **Documentation**: Guides, tutorials, API docs
- 🧪 **Testing**: Unit tests, integration tests, test coverage
- 🔒 **Security**: Security improvements, audits
- 🌐 **Translations**: i18n support (future)
- 💡 **Ideas**: Feature requests, architecture discussions

All contributors will be recognized in our [Contributors](#contributors) section!
