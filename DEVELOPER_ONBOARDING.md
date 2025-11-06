# Developer Onboarding Guide

Welcome to the MCP Server LangGraph project! This guide will get you up and running in **under 10 minutes**.

## Prerequisites

Before you start, ensure you have:

- ✅ **Python 3.10-3.12** installed (`python --version`)
- ✅ **Docker Desktop** or **Docker Engine** running (`docker --version`)
- ✅ **Docker Compose v2** installed (`docker compose version`)
- ✅ **Git** installed (`git --version`)
- ✅ **uv** (Python package manager) installed ([installation](https://github.com/astral-sh/uv))

Optional but recommended:
- **Node.js** (for Mintlify docs): `node --version`
- **Make** (usually pre-installed on Linux/macOS)

## 🚀 Quick Start (5 Minutes)

### Option A: Automated Setup (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/vishnu2kmohan/mcp-server-langgraph.git
cd mcp-server-langgraph

# 2. Run complete developer setup
make dev-setup
```

This will:
- Install all dependencies
- Start Docker infrastructure (OpenFGA, Postgres, Keycloak, Prometheus, Grafana, etc.)
- Initialize OpenFGA authorization
- Set up Keycloak SSO
- Display next steps

**Expected duration**: 3-5 minutes ⏱️

### Option B: Manual Setup

```bash
# 1. Install dependencies (uv sync creates .venv automatically)
make install-dev  # Same as: uv sync

# 2. Start infrastructure
make setup-infra

# 3. Initialize services (wait for services to be ready first)
sleep 10
make setup-openfga
make setup-keycloak
```

<Note>
**No manual venv creation needed!** `uv sync` (run by `make install-dev`) automatically creates `.venv` and installs all dependencies.
</Note>

## ✅ Verify Installation

```bash
# Check system health
make health-check
```

You should see:
- ✓ All Docker services running
- ✓ All ports responding (8080, 5432, 8180, 16686, 9090, 3000, 6379)
- ✓ Virtual environment active

## 🏃 Running the Application

### Run Unit Tests
```bash
make test-unit
```

Expected: All 437 tests passing ✅

### Run the MCP Server (StreamableHTTP)
```bash
make run-streamable
```

The server will start on `http://localhost:8000`

### Alternative: Run stdio MCP Server
```bash
make run
```

## 📊 Access Monitoring Dashboards

```bash
make monitoring-dashboard
```

This opens Grafana at http://localhost:3000 with:
- **Username**: admin
- **Password**: admin

**Available Dashboards**:
- LangGraph Agent Performance
- Security & Authentication
- LLM Performance
- SLA Monitoring
- SOC2 Compliance
- And 4 more...

## 🔧 Essential Configuration

### 1. Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Update these required values in `.env`:
```bash
# OpenFGA (get these from setup-openfga output)
OPENFGA_STORE_ID=<your-store-id>
OPENFGA_MODEL_ID=<your-model-id>

# Keycloak (get this from setup-keycloak output)
KEYCLOAK_CLIENT_SECRET=<your-client-secret>

# LLM API Keys (optional for testing)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

### 2. Re-run Setup if Needed

If you need to reset everything:
```bash
make reset
```

This will clean up and re-initialize all services.

## 📚 Project Structure

```
mcp-server-langgraph/
├── src/mcp_server_langgraph/   # Main package
│   ├── core/                    # Agent, config, compliance
│   ├── auth/                    # Authentication & authorization
│   ├── llm/                     # LLM factory (LiteLLM)
│   ├── mcp/                     # MCP servers (stdio, HTTP)
│   ├── api/                     # REST API endpoints
│   └── observability/           # OpenTelemetry setup
├── tests/                       # Test suite (437 tests)
├── docs/                        # Mintlify documentation (77 pages)
├── deployments/                 # K8s, Helm, Kustomize configs
├── monitoring/                  # Grafana dashboards, Prometheus rules
├── examples/                    # Usage examples
└── Makefile                     # Developer commands
```

## 🧪 Running Tests

### All Tests
```bash
make test
```

### By Category
```bash
make test-unit          # Fast unit tests
make test-integration   # Integration tests
make test-compliance    # GDPR, HIPAA, SOC2, SLA tests
make test-property      # Property-based tests (Hypothesis)
make test-contract      # Contract tests (MCP protocol)
```

### With Coverage
```bash
make test-coverage
```

Opens HTML report at `htmlcov/index.html`

### Watch Mode
```bash
make test-watch
```

Re-runs tests on file changes (great for TDD)

## 🎯 Common Development Tasks

### Code Quality
```bash
make format         # Format with black + isort
make lint           # Run flake8 + mypy
make security-check # Run bandit security scan
```

### Pre-commit Hooks
```bash
make pre-commit-setup
```

This installs git hooks that automatically:
- Format code with black
- Sort imports with isort
- Run linting (flake8)
- Check types (mypy)
- Scan for security issues (bandit)

### View Logs
```bash
make logs-follow    # All services
make logs-agent     # Agent only
make logs-grafana   # Grafana only
```

### Database Operations
```bash
make db-shell      # Open PostgreSQL shell
make db-backup     # Create backup
make db-restore    # Restore from backup
```

## 📖 Documentation

### Serve Docs Locally
```bash
make docs-serve
```

Opens Mintlify docs at http://localhost:3000

### Key Documentation
- **Architecture**: `docs/architecture/` (21 ADRs)
- **Deployment**: `docs/deployment/`
- **Testing**: `docs/advanced/testing.mdx`
- **Monitoring**: `monitoring/MONITORING_QUICKSTART.md`
- **AI Agent Help**: `.github/CLAUDE.md`, `.github/AGENTS.md`

## 🐛 Troubleshooting

### Services Not Starting
```bash
# Check Docker is running
docker ps

# Check logs for errors
docker compose logs

# Restart services
make clean && make setup-infra
```

### Port Conflicts
If ports 3000, 8080, 9090, etc. are in use:
```bash
# Find process using port
lsof -ti:3000

# Kill process (replace 3000 with your port)
kill -9 $(lsof -ti:3000)
```

### Tests Failing
```bash
# Run tests with more verbose output
pytest -vv --tb=long

# Run specific test
pytest tests/test_agent.py::test_specific_function -v

# Debug a failing test
make test-debug
```

### Environment Issues
```bash
# Recreate virtual environment
rm -rf .venv
uv sync  # Creates .venv and installs dependencies

# Or use make
make install-dev
```

## 🎓 Learning Resources

### Getting Started
1. Read: `README.md` - Project overview
2. Review: `docs/getting-started/quickstart.mdx`
3. Explore: Architecture Decision Records in `docs/architecture/`

### Understanding the Code
1. Start with: `src/mcp_server_langgraph/core/agent.py` - LangGraph agent
2. Then: `src/mcp_server_langgraph/mcp/server_streamable.py` - MCP server
3. Review: `src/mcp_server_langgraph/auth/middleware.py` - Auth middleware

### AI Assistant Configuration
- **Claude Code**: `.github/CLAUDE.md`
- **GitHub Copilot**: `.github/copilot-instructions.md`
- **Cursor AI**: `.cursorrules`
- **OpenAI Codex**: `.openai/codex-instructions.md`

## 🤝 Contributing

### Before Making Changes
1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Install pre-commit hooks: `make pre-commit-setup`
3. Run tests: `make test-unit`

### Making Changes
1. Write code following existing patterns
2. Add tests for new functionality
3. Run `make format` before committing
4. Ensure `make test` passes

### Submitting Changes
1. Commit with conventional commits: `feat:`, `fix:`, `docs:`, etc.
2. Push to your branch
3. Open a Pull Request
4. Ensure CI passes

See `CONTRIBUTING.md` for detailed guidelines.

## 🚀 Releasing

### Automated Version Bumping

When a new GitHub release is created, deployment versions are automatically updated across all configuration files.

**Process**:
1. Create a new release on GitHub with a tag (e.g., `v2.5.0`)
2. GitHub Actions automatically:
   - Updates `pyproject.toml`
   - Updates `docker-compose.yml`
   - Updates Kubernetes deployment manifests
   - Updates Helm chart version and appVersion
   - Updates Kustomize image tags
   - Commits changes to main branch
   - Adds comment to release with deployment commands

**Manual Version Bump** (if needed):
```bash
# Test with dry run first
DRY_RUN=1 bash scripts/deployment/bump-versions.sh 2.5.0

# Apply version bump
bash scripts/deployment/bump-versions.sh 2.5.0

# Commit changes
git commit -am "chore: bump version to 2.5.0"
git push origin main
```

**Deployment After Release**:
- **Docker Compose**: `docker compose pull && docker compose up -d`
- **Kubernetes**: `kubectl set image deployment/langgraph-agent langgraph-agent=langgraph-agent:2.5.0`
- **Helm**: `helm upgrade langgraph-agent deployments/helm/langgraph-agent --set image.tag=2.5.0`
- **Kustomize**: `kubectl apply -k deployments/kustomize/overlays/production`

## 📞 Getting Help

### Resources
- **Documentation**: http://localhost:3000 (run `make docs-serve`)
- **Issues**: https://github.com/vishnu2kmohan/mcp-server-langgraph/issues
- **Discussions**: https://github.com/vishnu2kmohan/mcp-server-langgraph/discussions

### Quick Commands Reference
```bash
make help              # Show all available commands
make dev-setup         # Complete setup
make quick-start       # Quick start
make health-check      # System health
make test-unit         # Run tests
make monitoring-dashboard  # Open Grafana
make logs-follow       # View logs
make clean             # Clean up
```

## ✨ Next Steps

1. ✅ Complete setup: `make dev-setup`
2. ✅ Run tests: `make test-unit`
3. ✅ Explore dashboards: `make monitoring-dashboard`
4. ✅ Read architecture docs: `docs/architecture/overview.mdx`
5. ✅ Try examples: `python examples/openfga_usage.py`
6. ✅ Make your first contribution!

---

**Welcome to the team!** 🎉

For questions, reach out via GitHub Discussions or open an issue.

Happy coding! 🚀
