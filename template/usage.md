# Using This as a Template

This repository serves as a **cookie-cutter template** for building production-ready MCP servers with LangGraph's Functional API.

## 🚀 Quick Start (Automated)

### Option 1: Using Cookiecutter (Recommended)

```bash
# Generate your project (uvx runs cookiecutter without installing it)
uvx cookiecutter gh:vishnu2kmohan/mcp-server-langgraph

# Follow the interactive prompts
```

### Option 2: GitHub Template

1. Click **"Use this template"** button on GitHub
2. Create your repository
3. Clone and customize (see Manual Customization below)

### Option 3: Direct Clone

```bash
git clone https://github.com/vishnu2kmohan/mcp-server-langgraph.git my-mcp-server
cd my-mcp-server
# Follow manual customization steps below
```

---

## 📝 Interactive Configuration

When using `cookiecutter`, you'll be prompted for:

### Project Basics
- **project_name**: Human-readable name (e.g., "Slack Bot")
- **project_slug**: Python module name (e.g., "slack_bot")
- **author_name**: Your name
- **author_email**: Your email
- **github_username**: Your GitHub username
- **version**: Initial version (default: 0.1.0)

### MCP Configuration
- **mcp_transports**: Which transports to include
  - `stdio` - Standard I/O (for Claude Desktop)
  - `http_sse` - HTTP with Server-Sent Events
  - `streamable_http` - StreamableHTTP (recommended)
  - `all` - Include all three

### Security & Auth
- **use_authentication**: Enable authentication?
  - `yes` - Include JWT authentication
  - `no` - No authentication
- **authentication_method** (if yes):
  - `jwt` - JSON Web Tokens
  - `api_key` - API key authentication
  - `none` - Skip authentication
- **use_authorization**: Enable fine-grained authorization?
  - `yes` - Include OpenFGA
  - `no` - No authorization
- **authorization_backend** (if yes):
  - `openfga` - OpenFGA (Zanzibar-style)
  - `simple_rbac` - Simple role-based access
  - `none` - Skip authorization
- **use_secrets_manager**: Secrets management?
  - `yes` - Include Infisical
  - `no` - Environment variables only

### LLM Configuration
- **llm_providers**:
  - `all` - Support all 100+ LiteLLM providers
  - `openai_only` - OpenAI models only
  - `anthropic_only` - Anthropic Claude only
  - `local_only` - Local models (Ollama)
  - `custom` - Custom selection

### Observability
- **observability_level**:
  - `full` - OpenTelemetry + Prometheus + Grafana + Jaeger
  - `basic` - Basic logging and metrics
  - `minimal` - Logging only

### Deployment
- **deployment_target**:
  - `production` - Full production setup (K8s, monitoring, security)
  - `cloudrun` - Google Cloud Run serverless deployment
  - `staging` - Staging environment setup
  - `development` - Local development only
  - `all` - All environments
- **include_kubernetes**: Include K8s manifests?
  - `yes` - Full Kubernetes support
  - `no` - Docker only
- **kubernetes_flavor** (if yes):
  - `helm` - Helm charts
  - `kustomize` - Kustomize overlays
  - `both` - Both options
- **include_cloudrun**: Include Google Cloud Run deployment?
  - `yes` - Cloud Run configs and scripts
  - `no` - No Cloud Run support
- **include_docker**: Include Docker setup?
  - `yes` - Dockerfile + docker-compose
  - `no` - No Docker files

### Testing & Quality
- **testing_level**:
  - `comprehensive` - Unit + Integration + E2E + Benchmarks
  - `standard` - Unit + Integration
  - `basic` - Unit tests only
  - `minimal` - Basic smoke tests
- **code_style**:
  - `strict` - Black + isort + flake8 + mypy + bandit
  - `standard` - Black + isort + flake8
  - `minimal` - Black only
- **include_pre_commit**: Include pre-commit hooks?
  - `yes` - Automated quality checks
  - `no` - Manual formatting

### CI/CD
- **include_ci_cd**: Include CI/CD?
  - `yes` - Automated testing and deployment
  - `no` - Manual workflow
- **ci_platform** (if yes):
  - `github_actions` - GitHub Actions workflows
  - `gitlab_ci` - GitLab CI
  - `none` - Skip CI

### Documentation
- **include_documentation**: Include docs?
  - `yes` - Full documentation
  - `no` - README only
- **documentation_format** (if yes):
  - `mintlify` - Mintlify docs (recommended)
  - `mkdocs` - MkDocs
  - `sphinx` - Sphinx
  - `basic_markdown` - Markdown only

### Other
- **deployment_target**:
  - `production` - Full production setup
  - `staging` - Staging environment
  - `development` - Local dev only
  - `all` - All environments
- **include_examples**: Include example files?
  - `yes` - Example usage code
  - `no` - Clean project
- **license**: License type
  - `MIT`, `Apache-2.0`, `BSD-3-Clause`, `GPL-3.0`, `Proprietary`

---

## 🛠️ Manual Customization

If you cloned directly without cookiecutter, follow these steps:

### Step 1: Search and Replace

Replace these values across the entire project:

```bash
# Project name (44+ files)
find . -type f -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/__pycache__/*" \
  -exec sed -i 's/mcp-server-langgraph/YOUR-PROJECT-NAME/g' {} +
find . -type f -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/__pycache__/*" \
  -exec sed -i 's/mcp_server_langgraph/your_project_slug/g' {} +
find . -type f -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/__pycache__/*" \
  -exec sed -i 's/MCP Server with LangGraph/Your Project Name/g' {} +

# Author and GitHub
find . -type f -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/__pycache__/*" \
  -exec sed -i 's/vishnu2kmohan/YOUR-GITHUB-USERNAME/g' {} +
find . -type f -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/__pycache__/*" \
  -exec sed -i 's/maintainers@example.com/YOUR-EMAIL/g' {} +
```

### Step 2: Update Key Files

Manually update these critical files:

1. **`pyproject.toml`**:
   ```toml
   [project]
   name = "your-project-name"
   description = "Your project description"
   authors = [{name = "Your Name", email = "your@email.com"}]
   ```

2. **`package.json`**:
   ```json
   {
     "name": "your-project-name",
     "author": "Your Name"
   }
   ```

3. **`README.md`**:
   - Update title
   - Update description
   - Update badges with your username/repo

4. **`.env.example`**:
   - Review and customize environment variables

5. **`src/mcp_server_langgraph/core/config.py`**:
   - Update SERVICE_NAME constant

6. **`observability.py`**:
   - Update SERVICE_NAME

### Step 3: Remove Unwanted Features

Choose which features to keep:

**If you don't need OpenFGA (authorization)**:
```bash
rm openfga_client.py scripts/setup_openfga.py examples/openfga_usage.py
# Remove OpenFGA references from docker-compose.yaml
# Remove from requirements.txt
```

**If you don't need Infisical (secrets)**:
```bash
rm secrets_manager.py scripts/setup_infisical.py
# Remove from requirements.txt
```

**If you only need one MCP transport**:
```bash
# Keep only the one you need:
rm src/mcp_server_langgraph/mcp/server_stdio.py  # stdio
# or
rm mcp_server_http.py  # HTTP/SSE
# or
rm src/mcp_server_langgraph/mcp/server_streamable.py  # StreamableHTTP
```

**If you don't need Kubernetes**:
```bash
rm -rf kubernetes/ helm/ kustomize/
rm KUBERNETES_DEPLOYMENT.md
```

**If you don't need full observability**:
```bash
rm -rf grafana/ monitoring/
rm otel-collector-config.yaml
# Simplify observability.py
```

### Step 4: Update Dependencies

```bash
# Review and remove unused dependencies
vim requirements.txt

# Regenerate pinned versions
pip install -r requirements.txt
pip freeze > requirements-pinned.txt
```

### Step 5: Initialize Git

```bash
rm -rf .git  # Remove template git history
git init
git add .
git commit -m "Initial commit from mcp-server-langgraph template"
```

---

## 🎯 Common Configurations

### Minimal MCP Server

For a basic MCP server with no auth/authz:

**Cookiecutter config**:
```
mcp_transports: stdio
use_authentication: no
use_authorization: no
use_secrets_manager: no
observability_level: minimal
include_kubernetes: no
testing_level: basic
```

**Manual removal**:
- Delete: `src/mcp_server_langgraph/auth/middleware.py`, `openfga_client.py`, `secrets_manager.py`
- Delete: `kubernetes/`, `helm/`, `grafana/`, `monitoring/`
- Keep: `src/mcp_server_langgraph/mcp/server_stdio.py`, `src/mcp_server_langgraph/core/agent.py`, `src/mcp_server_langgraph/core/config.py`

### Standard Production Server

Full-featured production setup:

**Cookiecutter config**:
```
mcp_transports: all
use_authentication: yes
use_authorization: yes
use_secrets_manager: yes
observability_level: full
include_kubernetes: yes
testing_level: comprehensive
```

**Manual**: Use template as-is, just update names

### Local Development Only

For local experimentation:

**Cookiecutter config**:
```
mcp_transports: stdio
use_authentication: no
use_authorization: no
observability_level: basic
include_kubernetes: no
include_cloudrun: no
include_docker: yes
deployment_target: development
```

### Cloud Run Serverless

For Google Cloud Run deployment:

**Cookiecutter config**:
```
mcp_transports: streamable_http
use_authentication: yes
use_authorization: yes
observability_level: basic
include_kubernetes: no
include_cloudrun: yes
include_docker: yes
deployment_target: cloudrun
```

---

## 📋 Customization Checklist

After generation, customize these aspects:

### Core Functionality
- [ ] Update agent behavior in `src/mcp_server_langgraph/core/agent.py`
- [ ] Add your custom tools
- [ ] Modify prompts in `prompt.py`
- [ ] Configure LLM models in `llm_factory.py`

### Configuration
- [ ] Update `.env.example` with your env vars
- [ ] Customize `src/mcp_server_langgraph/core/config.py` with your settings
- [ ] Review `pyproject.toml` dependencies

### Security
- [ ] Change default JWT secret
- [ ] Review OpenFGA model if using authorization
- [ ] Set up Infisical project if using secrets
- [ ] Update security audit checklist

### Testing
- [ ] Update test fixtures in `conftest.py`
- [ ] Add your custom tool tests
- [ ] Configure CI/CD for your repo

### Deployment
- [ ] Update Docker image name
- [ ] Configure Kubernetes namespace
- [ ] Set resource limits in Helm values
- [ ] Update monitoring dashboards

### Documentation
- [ ] Customize README with your project details
- [ ] Update ../.github/CONTRIBUTING.md
- [ ] Add your specific deployment docs
- [ ] Update Mintlify docs if using

---

## 🔍 File-by-File Guide

### Must Customize
| File | What to Change |
|------|----------------|
| `README.md` | Title, description, badges, quick start |
| `pyproject.toml` | name, author, description, version |
| `src/mcp_server_langgraph/core/config.py` | SERVICE_NAME constant |
| `.env.example` | Project-specific env vars |
| `src/mcp_server_langgraph/core/agent.py` | Agent tools and behavior |

### Should Customize
| File | What to Change |
|------|----------------|
| `observability.py` | SERVICE_NAME, metrics |
| `docker-compose.yaml` | Service names, ports |
| `helm/*/Chart.yaml` | name, description |
| `helm/*/values.yaml` | image, resources |
| `kubernetes/**/*.yaml` | namespace, labels |

### Optional Customize
| File | What to Change |
|------|----------------|
| `mcp_server*.py` | MCP transport specifics |
| `src/mcp_server_langgraph/auth/middleware.py` | Authentication logic |
| `openfga_client.py` | Authorization model |
| `llm_factory.py` | LLM provider config |
| `../.github/CONTRIBUTING.md` | Contribution guidelines |

### Can Keep As-Is
- `observability.py` (if using standard OpenTelemetry)
- Test infrastructure (`conftest.py`, test markers)
- CI/CD workflows (update repo names only)
- Pre-commit hooks
- EditorConfig

---

## 💡 Pro Tips

### 1. Start Minimal, Add Features Later

Begin with minimal configuration and add features as needed:

```bash
# Start with this
uvx cookiecutter gh:vishnu2kmohan/mcp-server-langgraph \
  --replay-file minimal-config.json

# Add features later by cherry-picking files
```

### 2. Use Version Control from Day 1

```bash
git init
git add .
git commit -m "Initial commit from template"
git remote add origin https://github.com/yourusername/your-repo.git
git push -u origin main
```

### 3. Keep Template Updates

Stay updated with template improvements:

```bash
# Add template as remote
git remote add template https://github.com/vishnu2kmohan/mcp-server-langgraph.git
git fetch template

# Cherry-pick updates
git cherry-pick <commit-hash>
```

### 4. Document Your Customizations

Create a `CUSTOMIZATIONS.md` file:

```markdown
# Customizations from Template

## Removed Features
- OpenFGA (using simple RBAC instead)
- Kubernetes deployment (Docker only)

## Added Features
- Custom Slack integration
- Redis caching layer

## Modified Files
- src/mcp_server_langgraph/core/agent.py - Added Slack tools
- src/mcp_server_langgraph/core/config.py - Added Redis config
```

---

## 🐛 Troubleshooting

### Cookiecutter Generation Failed

```bash
# Enable debug mode
uvx cookiecutter --debug gh:vishnu2kmohan/mcp-server-langgraph

# Or use local template
git clone https://github.com/vishnu2kmohan/mcp-server-langgraph.git
uvx cookiecutter ./mcp_server_langgraph
```

### Find-Replace Missed Files

```bash
# Search for template placeholders
grep -r "mcp-server-langgraph" .
grep -r "vishnu2kmohan" .
grep -r "MCP Server with LangGraph" .
```

### Import Errors After Customization

```bash
# Rebuild dependencies
pip install -r requirements.txt --force-reinstall

# Check for hardcoded imports
grep -r "from mcp_server_langgraph" .
grep -r "import mcp_server_langgraph" .
```

---

## 📚 Examples

See `examples/` directory for:

- `minimal/` - Bare-bones MCP server
- `standard/` - Typical production setup
- `enterprise/` - Full-featured deployment
- `custom-tools/` - Adding custom agent tools

---

## 🤝 Contributing Template Improvements

Found a way to improve this template? Please contribute!

1. Fork the template repository
2. Make your improvements
3. Test with `cookiecutter`
4. Submit a pull request

See [../.github/CONTRIBUTING.md](../.github/CONTRIBUTING.md) for guidelines.

---

## 📖 Further Reading

- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Cookiecutter Documentation](https://cookiecutter.readthedocs.io/)
- [Production Deployment Guide](../docs/deployment/production-checklist.mdx)
- [Security Best Practices](../archive/SECURITY_AUDIT.md)

---

**Questions?** Open an issue: https://github.com/vishnu2kmohan/mcp-server-langgraph/issues

**Last Updated**: 2025-10-10
