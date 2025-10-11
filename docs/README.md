# Documentation Index

Complete documentation for the MCP Server with LangGraph project.

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

## 🔌 Integrations

Integration guides for external services and tools:

- **[OpenFGA & Infisical](integrations/openfga-infisical.md)** - Authorization and secrets management
- **[LangSmith](integrations/langsmith.md)** - LLM observability and tracing
- **[Kong API Gateway](integrations/kong.md)** - API gateway integration
- **[LiteLLM](integrations/litellm.md)** - Multi-LLM provider support
- **[Google Gemini](integrations/gemini.md)** - Gemini API setup

## 🛠️ Development

Developer guides and workflows:

- **[Development Setup](development/development.md)** - Local environment configuration
- **[Testing Strategy](development/testing.md)** - Unit, integration, property, and contract tests
- **[Build Verification](development/build-verification.md)** - Build and CI/CD verification
- **[GitHub Actions Setup](development/github-actions.md)** - CI/CD pipeline configuration

## 📖 Reference

Technical reference documentation:

- **[Agents Architecture](reference/agents.md)** - LangGraph agent design and patterns
- **[Pydantic AI Integration](reference/pydantic-ai.md)** - Type-safe agent responses
- **[AI Tools Compatibility](reference/ai-tools-compatibility.md)** - Compatible AI tools and IDEs
- **[MCP Registry](reference/mcp-registry.md)** - Publishing to MCP registry
- **[Recommendations](reference/recommendations.md)** - Best practices and recommendations

## 🎨 Template

Cookiecutter template documentation:

- **[Template Usage](template/usage.md)** - How to use this as a template
- **[Template Evaluation](template/evaluation.md)** - Template features and evaluation
- **[Cookiecutter Summary](template/cookiecutter-summary.md)** - Cookiecutter configuration

## 🏛️ Architecture Decision Records (ADR)

Technical decisions and their rationale:

- **[ADR Index](adr/README.md)** - All architecture decisions
- **[0001: LLM Multi-Provider](adr/0001-llm-multi-provider.md)** - LiteLLM for provider abstraction
- **[0002: OpenFGA Authorization](adr/0002-openfga-authorization.md)** - Fine-grained access control
- **[0003: Dual Observability](adr/0003-dual-observability.md)** - OpenTelemetry + LangSmith
- **[0004: MCP StreamableHTTP](adr/0004-mcp-streamable-http.md)** - Production transport protocol
- **[0005: Pydantic AI Integration](adr/0005-pydantic-ai-integration.md)** - Type-safe responses

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
- **Security**: [OpenFGA Integration](integrations/openfga-infisical.md), [Security Review](archive/security-review.md)
- **Testing**: [Testing Guide](development/testing.md), [Build Verification](development/build-verification.md)
- **AI/LLM**: [Agents Architecture](reference/agents.md), [Pydantic AI](reference/pydantic-ai.md), [LiteLLM](integrations/litellm.md)
- **Observability**: [LangSmith Integration](integrations/langsmith.md), [Dual Observability ADR](adr/0003-dual-observability.md)

### By Role

**Developer**:
- Start: [Development Setup](development/development.md)
- Test: [Testing Guide](development/testing.md)
- Learn: [Agents Architecture](reference/agents.md), [ADRs](adr/README.md)

**DevOps/SRE**:
- Deploy: [Production Deployment](deployment/production.md), [Kubernetes](deployment/kubernetes.md)
- Monitor: [LangSmith Integration](integrations/langsmith.md)
- Secure: [OpenFGA & Infisical](integrations/openfga-infisical.md)

**Template User**:
- Start: [Template Usage](template/usage.md)
- Customize: [Cookiecutter Summary](template/cookiecutter-summary.md)
- Evaluate: [Template Evaluation](template/evaluation.md)

## 📝 Contributing

See [CONTRIBUTING.md](../.github/CONTRIBUTING.md) for contribution guidelines.

## 📄 License

See [LICENSE](../LICENSE) for license information.
