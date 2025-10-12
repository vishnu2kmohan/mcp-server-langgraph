# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2025-10-11

### Changed - BREAKING

**Package Reorganization**: Complete restructure into pythonic src/ layout

- **Import Paths** (BREAKING): All imports changed from flat to hierarchical structure
  - `from config import settings` → `from mcp_server_langgraph.core.config import settings`
  - `from auth import AuthMiddleware` → `from mcp_server_langgraph.auth.middleware import AuthMiddleware`
  - `from llm_factory import create_llm_from_config` → `from mcp_server_langgraph.llm.factory import create_llm_from_config`
  - `from observability import logger` → `from mcp_server_langgraph.observability.telemetry import logger`
  - All other modules follow same pattern

- **File Organization**:
  - Created `src/mcp_server_langgraph/` package with submodules
  - `core/` - agent.py, config.py, feature_flags.py
  - `auth/` - middleware.py (auth.py), openfga.py (openfga_client.py)
  - `llm/` - factory.py, validators.py, pydantic_agent.py
  - `mcp/` - server_stdio.py, server_streamable.py, streaming.py
  - `observability/` - telemetry.py (observability.py), langsmith.py
  - `secrets/` - manager.py (secrets_manager.py)
  - `health/` - checks.py (health_check.py)
  - Moved examples to `examples/` directory
  - Moved setup scripts to `scripts/` directory

- **Console Scripts**: Entry points remain unchanged
  - `mcp-server` - stdio transport
  - `mcp-server-streamable` - StreamableHTTP transport

- **Configuration**: Updated pyproject.toml, setup.py, Dockerfile, Makefile for new structure

### Removed
- **HTTP/SSE Transport**: Removed deprecated `mcp_server_http.py` and SSE transport implementation
- **sse-starlette Dependency**: Removed from all dependency files
- **Flat File Structure**: Removed 20 Python files from root directory

### Migration Guide

**For users importing the package**:
```python
# Before (v1.x)
from config import settings
from auth import AuthMiddleware
from agent import agent_graph

# After (v2.x)
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.core.agent import agent_graph
```

**For CLI users**: No changes required - console scripts work the same

## [1.0.0] - 2025-10-10

### Added
- **Multi-LLM Support**: LiteLLM integration supporting 100+ providers (Anthropic, OpenAI, Google, Azure, AWS Bedrock, Ollama)
- **Open-Source Models**: Support for Llama 3.1, Qwen 2.5, Mistral, DeepSeek via Ollama
- **LangGraph Agent**: Functional API with stateful conversation, conditional routing, and checkpointing
- **MCP Server**: Model Context Protocol implementation with two transport modes:
  - StreamableHTTP (recommended for production)
  - stdio (for Claude Desktop and local apps)
- **Authentication**: JWT-based authentication with token validation and expiration
- **Fine-Grained Authorization**: OpenFGA (Zanzibar-style) relationship-based access control
- **Secrets Management**: Infisical integration for secure secret storage and retrieval
- **Distributed Tracing**: OpenTelemetry tracing with Jaeger backend
- **Metrics**: Prometheus-compatible metrics for monitoring
- **Structured Logging**: JSON logging with trace context correlation
- **Observability Stack**: Docker Compose setup with OpenFGA, Jaeger, Prometheus, and Grafana
- **Automatic Fallback**: Multi-model fallback for high availability
- **Kubernetes Deployment**: Production-ready manifests for GKE, EKS, AKS, Rancher, VMware Tanzu
- **Helm Charts**: Flexible deployment with customizable values
- **Kustomize**: Overlay-based configuration for dev/staging/production environments
- **Kong API Gateway**: Rate limiting, authentication, and traffic control
- **Health Checks**: Kubernetes-compatible liveness, readiness, and startup probes
- **CI/CD Pipeline**: GitHub Actions workflow with automated testing, linting, security scanning, and multi-environment deployment
- **Comprehensive Testing**: Unit, integration, and E2E tests with 70%+ coverage
- **Security Scanning**: Bandit integration for vulnerability detection
- **Code Quality**: Black, flake8, isort, mypy integration
- **Documentation**: 9 comprehensive guides covering all aspects of deployment and usage

### Security
- JWT secret management with Infisical fallback
- Non-root Docker containers with multi-stage builds
- Network policies for Kubernetes deployments
- Pod security policies and RBAC configuration
- Rate limiting via Kong API Gateway
- Security scanning in CI/CD pipeline
- OpenFGA audit logging support

### Documentation
- README.md with quick start and feature overview
- KUBERNETES_DEPLOYMENT.md for production deployment
- KONG_INTEGRATION.md for API gateway setup
- MCP_REGISTRY.md for MCP registry publication
- TESTING.md for comprehensive testing guide
- LITELLM_GUIDE.md for multi-LLM configuration
- GEMINI_SETUP.md for Google Gemini integration
- GITHUB_ACTIONS_SETUP.md for CI/CD configuration
- README_OPENFGA_INFISICAL.md for auth and secrets setup

### Infrastructure
- Docker Compose for local development
- Multi-arch Docker builds (amd64/arm64)
- Horizontal Pod Autoscaling (HPA) configuration
- Pod Disruption Budgets (PDB) for high availability
- Service mesh compatibility
- Ingress configuration with TLS support

## [Unreleased]

### Planned
- Chaos engineering tests
- Performance/load testing with Locust
- Mutation testing with mutmut
- Property-based testing with hypothesis
- Visual regression tests for dashboards
- Contract tests for MCP protocol
- Additional LLM provider integrations
- Enhanced monitoring dashboards
- Automatic secret rotation
- Multi-region deployment support

---

## Release Notes

### Version 1.0.0 - Production Release

This is the first production-ready release of MCP Server with LangGraph. The codebase includes:

- **Production-grade infrastructure**: Kubernetes, Helm, Docker, CI/CD
- **Enterprise security**: OpenFGA, JWT, secrets management, RBAC
- **Full observability**: Tracing, metrics, logging with OpenTelemetry
- **Multi-LLM flexibility**: Support for 100+ LLM providers via LiteLLM
- **Comprehensive testing**: 70%+ code coverage with unit and integration tests
- **Complete documentation**: 9 detailed guides for all use cases

### Migration Guide

This is the initial release. For deployment:

1. Review [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for pre-deployment checklist
2. Configure secrets using Infisical or environment variables
3. Run pre-deployment validation: `python scripts/validate_production.py`
4. Deploy using Helm or Kustomize based on your platform
5. Verify health checks: `/health`, `/health/ready`, `/health/startup`

### Breaking Changes

None (initial release)

### Deprecations

None (HTTP/SSE transport previously deprecated in 1.0.0 was removed in Unreleased)

---

[1.0.0]: https://github.com/vishnu2kmohan/mcp_server_langgraph/releases/tag/v1.0.0
