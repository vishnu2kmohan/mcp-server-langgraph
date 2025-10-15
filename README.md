# Documentation Index

Complete documentation for the MCP Server with LangGraph project.

## ✨ Latest Updates

**v2.5.0 (Unreleased)**:
- 🐳 **Containerized Integration Tests** - One-command Docker-based testing with 100% reliability
- 🔧 **Infisical Docker Builds** - Multi-track installation with 5 options (no Rust required for local dev)

**v2.4.0**:
- ⬆️ **LangGraph 0.6.10** - Major upgrade with full API compatibility
- ✅ **100% Test Pass Rate** - All 437/437 tests passing
- 📚 **21 Architecture Decision Records** - Comprehensive architectural documentation
- 🔄 **15 Dependabot PRs Merged** - All dependencies updated

**v2.3.0**:
- 🗄️ **Compliance Storage Backend** - Pluggable storage with 5 abstract interfaces
- 🔒 **Enhanced Type Safety** - Strict mypy coverage increased from 27% to 64%
- 📋 **Pydantic V2 Migration** - Future-proofed for Pydantic V3

**v2.2.0 - Compliance & Observability**:
- 🔐 **GDPR/SOC2/HIPAA Compliance** - Full data subject rights, evidence automation, technical safeguards
- 📊 **SLA Monitoring** - 99.9% uptime tracking with 20+ Prometheus alerts
- 📈 **2 New Grafana Dashboards** - SLA Monitoring + SOC 2 Compliance

**v2.1.0 - Production Ready**:
- 🔑 **Keycloak SSO Integration** - Enterprise authentication with OIDC
- 💾 **Redis Session Management** - Production-grade session storage
- 📖 **43 MDX Documentation Files** - Complete Mintlify docs (100% coverage)
- 🚀 **Kubernetes/Helm/Kustomize** - Multi-environment deployment infrastructure

## 📚 Quick Start

- **[Main README](../README.md)** - Project overview and quick start guide
- **[Development Guide](development/development.md)** - Local development setup
- **[Testing Guide](development/testing.md)** - Testing strategy and running tests

## 🚀 Deployment

Production-ready deployment guides for various platforms:

- **[Production Deployment](deployment/production.md)** - General production deployment guide
- **[Kubernetes Deployment](deployment/kubernetes.md)** - Deploy with Kubernetes + Helm/Kustomize
- **[Cloud Run Deployment](deployment/cloudrun.md)** - Deploy to Google Cloud Run
- **[LangGraph Platform](deployment/langgraph-platform.md)** - Deploy to managed LangGraph Cloud
- **[Infisical Installation](deployment/infisical-installation.md)** - 🆕 Docker-based builds with 5 installation options (v2.5.0)

## 🔌 Integrations

Integration guides for external services and tools:

- **[Keycloak SSO](integrations/keycloak.md)** - Enterprise authentication with OpenID Connect (v2.1.0)
- **[OpenFGA & Infisical](integrations/openfga-infisical.md)** - Authorization and secrets management
- **[Infisical Setup](deployment/infisical-installation.md)** - 🆕 Docker-based builds with 5 installation options (v2.5.0)
- **[LangSmith](integrations/langsmith.md)** - LLM observability and tracing
- **[Kong API Gateway](integrations/kong.md)** - API gateway integration
- **[LiteLLM](integrations/litellm.md)** - Multi-LLM provider support
- **[Google Gemini](integrations/gemini.md)** - Gemini API setup

## 🛠️ Development

Developer guides and workflows:

- **[Development Setup](development/development.md)** - Local environment configuration
- **[Testing Strategy](development/testing.md)** - Unit, integration, property, and contract tests
- **[Integration Testing](development/integration-testing.md)** - 🆕 Docker-based integration tests (v2.5.0)
- **[Build Verification](development/build-verification.md)** - Build and CI/CD verification
- **[CI/CD Pipeline](development/ci-cd.md)** - 🆕 Continuous integration and deployment (NEW v2.1.0)
- **[GitHub Actions Setup](development/github-actions.md)** - CI/CD pipeline configuration

## 📖 Reference

Technical reference documentation:

- **[AGENTS.md](../.github/AGENTS.md)** - ⚙️ AI assistant guidance (GitHub Copilot Workspace)
- **[Pydantic AI Integration](reference/pydantic-ai.md)** - Type-safe agent responses
- **[AI Tools Compatibility](reference/ai-tools-compatibility.md)** - Compatible AI tools and IDEs
- **[MCP Registry](reference/mcp-registry.md)** - Publishing to MCP registry
- **[Recommendations](reference/recommendations.md)** - Best practices and recommendations

> **Note**: `AGENTS.md` and `CLAUDE.md` are located in `.github/` as they are operational instruction files for AI coding assistants and development tools.

## 🎨 Template

Cookiecutter template documentation:

- **[Template Usage](template/usage.md)** - How to use this as a template
- **[Template Evaluation](template/evaluation.md)** - Template features and evaluation
- **[Cookiecutter Summary](template/cookiecutter-summary.md)** - Cookiecutter configuration

## 🏛️ Architecture Decision Records (ADR)

Technical decisions and their rationale (21 comprehensive ADRs):

- **[ADR Index](adr/README.md)** - All architecture decisions

**Core Architecture (0001-0005)**:
- **[0001: LLM Multi-Provider](adr/0001-llm-multi-provider.md)** - LiteLLM for provider abstraction
- **[0002: OpenFGA Authorization](adr/0002-openfga-authorization.md)** - Fine-grained access control
- **[0003: Dual Observability](adr/0003-dual-observability.md)** - OpenTelemetry + LangSmith
- **[0004: MCP StreamableHTTP](adr/0004-mcp-streamable-http.md)** - Production transport protocol
- **[0005: Pydantic AI Integration](adr/0005-pydantic-ai-integration.md)** - Type-safe responses

**Authentication & Sessions (0006-0007)**:
- **[0006: Session Store](adr/0006-session-store.md)** - Authentication sessions and storage backends
- **[0007: Provider Pattern](adr/0007-auth-provider-pattern.md)** - Pluggable authentication providers

**Infrastructure & Deployment (0008-0009, 0013, 0020-0021)**:
- **[0008: Secrets Management](adr/0008-secrets-management.md)** - Infisical integration strategy
- **[0009: Feature Flags](adr/0009-feature-flags.md)** - Runtime feature toggles
- **[0013: Deployment Strategy](adr/0013-deployment-strategy.md)** - Multi-cloud deployment patterns
- **[0020: MCP Transport](adr/0020-mcp-transport-selection.md)** - Transport layer selection rationale
- **[0021: CI/CD Pipeline](adr/0021-cicd-pipeline.md)** - GitHub Actions workflow design

**Development & Quality (0010, 0014-0019)**:
- **[0010: LangGraph API](adr/0010-langgraph-functional-api.md)** - Agent graph architecture
- **[0014: Type Safety](adr/0014-type-safety-strategy.md)** - Strict mypy typing rollout
- **[0015: Checkpointing](adr/0015-langgraph-checkpointing.md)** - Conversation state persistence
- **[0016: Testing Pyramid](adr/0016-testing-strategy.md)** - Multi-layered test approach
- **[0017: Error Handling](adr/0017-error-handling-strategy.md)** - Consistent error patterns (v2.3.0)
- **[0018: Versioning](adr/0018-versioning-strategy.md)** - Semantic versioning policy
- **[0019: Async Patterns](adr/0019-async-patterns.md)** - AsyncIO best practices

**Compliance (0011-0012)**:
- **[0011: Cookiecutter Template](adr/0011-cookiecutter-compliance-template.md)** - Project template design
- **[0012: Compliance Framework](adr/0012-compliance-framework.md)** - GDPR/SOC2/HIPAA compliance (v2.2.0)

## 📦 Archive

Historical documentation (may be outdated):

- **[Implementation Complete](archive/IMPLEMENTATION_COMPLETE.md)** - Original implementation summary
- **[Implementation Summary](archive/IMPLEMENTATION_SUMMARY.md)** - Detailed implementation notes
- **[Security Review](archive/security-review.md)** - Security audit report
- **[Mintlify Setup](archive/MINTLIFY_SETUP.md)** - Documentation site setup
- **[Security Audit](archive/SECURITY_AUDIT.md)** - Historical security audit

## 🔍 Finding Documentation

### By Topic

- **Getting Started**: [Main README](../README.md), [Development Setup](development/development.md)
- **Deployment**: See [Deployment](#-deployment) section above
- **Authentication**: [Keycloak SSO](integrations/keycloak.md) (NEW v2.1.0), [JWT Auth](integrations/openfga-infisical.md)
- **Security**: [OpenFGA Integration](integrations/openfga-infisical.md), [Security Review](archive/security-review.md)
- **Testing**: [Testing Guide](development/testing.md), [Integration Testing](development/integration-testing.md) (v2.5.0), [Build Verification](development/build-verification.md)
- **AI/LLM**: [AGENTS.md](../.github/AGENTS.md), [Pydantic AI](reference/pydantic-ai.md), [LiteLLM](integrations/litellm.md)
- **Observability**: [LangSmith Integration](integrations/langsmith.md), [Dual Observability ADR](adr/0003-dual-observability.md)

### Compliance & Enterprise Features (v2.2.0+)

**GDPR Data Subject Rights**:
- Complete implementation of Articles 15-21 (access, rectification, erasure, portability, consent)
- Multi-format data export (JSON, CSV)
- Automated data retention and cleanup

**SOC 2 Compliance Automation**:
- Evidence collection for all Trust Services Criteria (CC6.1, CC6.6, CC7.2, A1.2, etc.)
- Daily/weekly/monthly automated reporting
- Access review automation with remediation tracking

**HIPAA Technical Safeguards**:
- Emergency access procedures (164.312(a)(2)(i))
- PHI audit logging (164.312(b))
- Data integrity controls with HMAC-SHA256 (164.312(c)(1))
- Automatic session timeout - 15 minutes (164.312(a)(2)(iii))

**SLA Monitoring & Alerting**:
- 99.9% uptime tracking with monthly budget (43.2 min/month)
- Response time monitoring (p95 <500ms, p99 <1000ms)
- Error rate tracking (<1% target)
- 20+ Prometheus alert rules with forecasting
- 2 Grafana dashboards (SLA Monitoring, SOC 2 Compliance)

### By Role

**Developer**:
- Start: [Development Setup](development/development.md)
- Test: [Testing Guide](development/testing.md)
- Learn: [AGENTS.md](../.github/AGENTS.md), [ADRs](adr/README.md)

**DevOps/SRE**:
- Deploy: [Production Deployment](deployment/production.md), [Kubernetes](deployment/kubernetes.md)
- Auth/SSO: [Keycloak Integration](integrations/keycloak.md) (NEW v2.1.0)
- Monitor: [LangSmith Integration](integrations/langsmith.md)
- Secure: [OpenFGA & Infisical](integrations/openfga-infisical.md)
- CI/CD: [CI/CD Pipeline](development/ci-cd.md) (NEW v2.1.0)

**Template User**:
- Start: [Template Usage](template/usage.md)
- Customize: [Cookiecutter Summary](template/cookiecutter-summary.md)
- Evaluate: [Template Evaluation](template/evaluation.md)

## 📝 Contributing

See [CONTRIBUTING.md](../.github/CONTRIBUTING.md) for contribution guidelines.

## 📄 License

See [LICENSE](../LICENSE) for license information.
