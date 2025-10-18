# Developer Setup Guide

Complete guide for setting up your local development environment.

## Table of Contents

- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Debugging](#debugging)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

Get up and running in 5 minutes:

```bash
# 1. Clone the repository
git clone https://github.com/vishnu2kmohan/mcp-server-langgraph.git
cd mcp_server_langgraph

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# 4. Copy environment file
cp .env.example .env

# 5. Get an API key (choose one)
# - Google Gemini: https://aistudio.google.com/apikey (FREE)
# - Anthropic: https://console.anthropic.com/
# - OpenAI: https://platform.openai.com/

# 6. Edit .env and add your API key
echo "GOOGLE_API_KEY=your-api-key-here" >> .env

# 7. Start infrastructure
docker compose up -d

# 8. Setup OpenFGA
python scripts/setup_openfga.py

# 9. Run tests
pytest -m unit -v

# 10. Test the agent
python examples/client_stdio.py
```

**You're ready to develop!** 🚀

---

## Detailed Setup

### Prerequisites

#### Required

- **Python 3.10+** (3.11+ recommended)
  - Check: `python --version`
  - Install: [python.org](https://www.python.org/downloads/)

- **Git**
  - Check: `git --version`
  - Install: [git-scm.com](https://git-scm.com/)

- **Docker & Docker Compose**
  - Check: `docker --version && docker-compose --version`
  - Install: [docker.com](https://www.docker.com/get-started)

#### Optional (for advanced features)

- **kubectl** - For Kubernetes development
  - Install: [kubernetes.io](https://kubernetes.io/docs/tasks/tools/)

- **Helm 3+** - For Helm chart development
  - Install: [helm.sh](https://helm.sh/docs/intro/install/)

- **Make** - For convenience commands
  - Linux/Mac: Usually pre-installed
  - Windows: Install via [Chocolatey](https://chocolatey.org/) or use Git Bash

### Installation Steps

#### 1. Fork and Clone

```bash
# Fork the repository on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/mcp_server_langgraph.git
cd mcp_server_langgraph

# Add upstream remote
git remote add upstream https://github.com/vishnu2kmohan/mcp-server-langgraph.git

# Verify remotes
git remote -v
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Linux/Mac:
source venv/bin/activate

# Windows (PowerShell):
venv\Scripts\Activate.ps1

# Windows (CMD):
venv\Scripts\activate.bat

# Verify activation (should show venv path)
which python  # Linux/Mac
where python  # Windows
```

#### 3. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install runtime dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-test.txt

# Verify installation
pip list | grep langgraph
pip list | grep mcp
```

**Using Make (recommended):**

```bash
# Install all dependencies
make install-dev

# This runs:
# - pip install -r requirements-pinned.txt
# - pip install -r requirements-test.txt
```

#### 4. Get LLM API Key

You need at least one LLM provider API key. Choose the one that works best for you:

**Option 1: Google Gemini (Recommended for Development)**

- FREE tier with generous limits
- Go to: https://aistudio.google.com/apikey
- Click "Get API key" → "Create API key"
- Copy your key

**Option 2: Anthropic Claude**

- Requires payment
- Go to: https://console.anthropic.com/
- Settings → API Keys → Create Key
- Copy your key

**Option 3: OpenAI GPT**

- Requires payment
- Go to: https://platform.openai.com/api-keys
- Create new secret key
- Copy your key

**Option 4: Local Models (Ollama)**

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.1

# No API key needed, runs locally!
```

#### 5. Configure Environment

```bash
# Copy example environment
cp .env.example .env

# Edit with your preferred editor
vim .env
# or
nano .env
# or
code .env  # VS Code
```

**Minimal .env configuration:**

```bash
# Choose your LLM provider
LLM_PROVIDER=google  # or anthropic, openai, ollama

# Add corresponding API key
GOOGLE_API_KEY=your-key-here
# or
ANTHROPIC_API_KEY=your-key-here
# or
OPENAI_API_KEY=your-key-here

# For Ollama (local), no key needed
LLM_PROVIDER=ollama
MODEL_NAME=llama3.1

# JWT secret (for development)
JWT_SECRET_KEY=dev-secret-change-in-production
```

#### 6. Start Infrastructure Services

```bash
# Start all services (OpenFGA, Jaeger, Prometheus, Grafana)
docker compose up -d

# Verify services are running
docker compose ps

# Should see:
# - openfga (port 8080)
# - postgres (port 5432)
# - jaeger (port 16686)
# - prometheus (port 9090)
# - grafana (port 3000)
```

**Check service health:**

```bash
# OpenFGA
curl http://localhost:8080/healthz

# Jaeger UI
open http://localhost:16686

# Prometheus
open http://localhost:9090

# Grafana (admin/admin)
open http://localhost:3000
```

#### 7. Setup OpenFGA Authorization

```bash
# Run setup script
python scripts/setup_openfga.py

# This will output:
# ✓ Created OpenFGA store: 01HXXXXXXXXX
# ✓ Created authorization model: 01HYYYYYYYY
# ✓ Wrote test tuples

# Copy the Store ID and Model ID to your .env
echo "OPENFGA_STORE_ID=01HXXXXXXXXX" >> .env
echo "OPENFGA_MODEL_ID=01HYYYYYYYY" >> .env
```

#### 8. Verify Installation

```bash
# Run unit tests
pytest -m unit -v

# Should see all tests passing
# ===== X passed in Y.YYs =====

# Test the MCP server
python examples/client_stdio.py

# Should see agent responses
```

---

## Development Workflow

### Daily Development Cycle

```bash
# 1. Start your day - update from upstream
git fetch upstream
git checkout main
git merge upstream/main

# 2. Create feature branch
git checkout -b feat/your-feature

# 3. Start infrastructure
docker compose up -d

# 4. Make your changes
# ... edit code ...

# 5. Run tests frequently
pytest -m unit -v

# 6. Format and lint before committing
make format
make lint

# 7. Commit your changes
git add .
git commit -m "feat: add new feature"

# 8. Push to your fork
git push origin feat/your-feature

# 9. Create Pull Request on GitHub
```

### Using Make Commands

```bash
# See all available commands
make help

# Common commands:
make install-dev       # Install dependencies
make test              # Run all tests
make test-unit         # Run unit tests only
make test-coverage     # Run with coverage report
make format            # Format code with black/isort
make lint              # Run linters
make security-check    # Run security scans
make setup-infra       # Start Docker services
make clean             # Clean up generated files
```

### IDE Setup

#### VS Code

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "127"],
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

#### PyCharm

1. File → Settings → Project → Python Interpreter
2. Add Interpreter → Virtualenv Environment → Existing
3. Select `.venv/bin/python`
4. Enable pytest: Settings → Tools → Python Integrated Tools → Default test runner → pytest

---

## Testing

### Running Tests

```bash
# All tests
pytest

# Unit tests only (fast)
pytest -m unit -v

# Integration tests (requires services)
pytest -m integration -v

# Specific test file
pytest tests/test_auth.py -v

# Specific test function
pytest tests/test_auth.py::test_create_token -v

# With coverage
pytest --cov=. --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Writing Tests

Create test files in `tests/` directory:

```python
# tests/test_my_feature.py
import pytest
from my_module import my_function

@pytest.mark.unit
def test_my_function():
    """Test my function does what it should"""
    result = my_function("input")
    assert result == "expected"

@pytest.mark.integration
async def test_my_integration():
    """Test integration with real service"""
    # Test with actual dependencies
    pass
```

### Test Markers

- `@pytest.mark.unit` - Unit tests (no external deps)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Slow tests (>1 second)

---

## Debugging

### Debug MCP Server

```bash
# Run with debug logging
LOG_LEVEL=DEBUG python -m mcp_server_langgraph.mcp.server_stdio

# Or set in .env
echo "LOG_LEVEL=DEBUG" >> .env
```

### Debug with Python Debugger

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in (Python 3.7+)
breakpoint()
```

### Debug Tests

```bash
# Run pytest with debugger
pytest --pdb

# Stop at first failure
pytest -x --pdb
```

### View Traces

```bash
# Open Jaeger UI
open http://localhost:16686

# Select service: mcp-server-langgraph
# View traces with full context
```

### Check Logs

```bash
# Docker service logs
docker compose logs -f

# Specific service
docker compose logs -f openfga

# Application logs (if LOG_FILE set)
tail -f mcp-server-langgraph.log
```

---

## Troubleshooting

### Common Issues

#### "ModuleNotFoundError"

```bash
# Ensure virtual environment is activated
which python  # Should show venv path

# Reinstall dependencies
pip install -r requirements.txt
```

#### "Port already in use"

```bash
# Check what's using the port
lsof -i :8080  # Mac/Linux
netstat -ano | findstr :8080  # Windows

# Stop Docker services
docker compose down

# Restart
docker compose up -d
```

#### "OpenFGA connection refused"

```bash
# Check if OpenFGA is running
docker compose ps

# Check logs
docker compose logs openfga

# Restart service
docker compose restart openfga
```

#### "API key invalid"

```bash
# Verify key is set
echo $GOOGLE_API_KEY  # Linux/Mac
echo %GOOGLE_API_KEY%  # Windows

# Check .env file
cat .env | grep API_KEY

# Regenerate key from provider dashboard
```

#### Tests failing

```bash
# Update dependencies
pip install -r requirements-pinned.txt

# Clear pytest cache
pytest --cache-clear

# Run specific failing test
pytest tests/test_name.py::test_function -v
```

### Getting Help

1. **Check Documentation**
   - [../README.md](../README.md)
   - [../../../TESTING.md](../../../TESTING.md)

2. **Search Issues**
   - [Existing Issues](https://github.com/vishnu2kmohan/mcp-server-langgraph/issues)
   - [Closed Issues](https://github.com/vishnu2kmohan/mcp-server-langgraph/issues?q=is%3Aissue+is%3Aclosed)

3. **Ask Community**
   - [GitHub Discussions](https://github.com/vishnu2kmohan/mcp-server-langgraph/discussions)
   - Create new discussion with "Q&A" category

4. **Create Issue**
   - Use issue templates
   - Provide full context and logs

---

## Next Steps

- Read [CONTRIBUTING.md](../../../.github/CONTRIBUTING.md) for contribution guidelines
- Check [Good First Issues](https://github.com/vishnu2kmohan/mcp-server-langgraph/labels/good%20first%20issue)
- Join [GitHub Discussions](https://github.com/vishnu2kmohan/mcp-server-langgraph/discussions)
- Review [Code Style Guide](../../../.github/CONTRIBUTING.md#code-style)

**Happy Coding!** 🎉
