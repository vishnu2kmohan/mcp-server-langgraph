# Developer Setup Guide

Complete guide for setting up the MCP Server LangGraph development environment with all required and optional tools.

**Last Updated:** 2025-11-24
**Target Audience:** New developers, CI/CD engineers, contributors

---

## Table of Contents

- [Quick Start](#quick-start)
- [Required Tools](#required-tools)
- [Optional Tools](#optional-tools)
- [Platform-Specific Installation](#platform-specific-installation)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/your-org/mcp-server-langgraph.git
cd mcp-server-langgraph

# 2. Install required tools (see platform-specific sections below)

# 3. Install Python dependencies
make install-dev

# 4. Verify setup
make validate-setup

# 5. Run tests
make test-dev
```

**Estimated setup time:** 15-30 minutes

---

## Required Tools

These tools are **mandatory** for core development workflows. Pre-commit hooks will **block commits** if these are missing.

### Python 3.12+

**Purpose:** Main programming language
**Used by:** All development, testing, CI/CD
**Install:**
- **macOS:** `brew install python@3.12`
- **Linux (Ubuntu/Debian):** `sudo apt install python3.12 python3.12-venv`
- **Linux (Fedora/RHEL):** `sudo dnf install python3.12`
- **Windows:** Download from [python.org](https://www.python.org/downloads/)

**Verification:**
```bash
python3 --version  # Should show 3.12.x or higher
```

---

### uv (Package Manager)

**Purpose:** Fast Python package management (10-100x faster than pip)
**Used by:** All dependency installation, virtual environment management
**Install:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Verification:**
```bash
uv --version
```

**Documentation:** [https://github.com/astral-sh/uv](https://github.com/astral-sh/uv)

---

### Git

**Purpose:** Version control
**Used by:** All development workflows
**Install:**
- **macOS:** `brew install git` or use Xcode Command Line Tools
- **Linux:** `sudo apt install git` or `sudo dnf install git`
- **Windows:** Download from [git-scm.com](https://git-scm.com/)

**Verification:**
```bash
git --version
```

---

### ShellCheck

**Purpose:** Shell script linting and validation
**Used by:** Pre-commit hooks (REQUIRED - blocks commits if missing)
**Install:**
- **macOS:** `brew install shellcheck`
- **Linux (Ubuntu/Debian):** `sudo apt install shellcheck`
- **Linux (Fedora/RHEL):** `sudo dnf install ShellCheck`
- **Windows (WSL):** `sudo apt install shellcheck`

**Verification:**
```bash
shellcheck --version
```

**Why Required:** Validates all bash scripts in `scripts/` directory. Without shellcheck, pre-commit hooks will fail.

**Documentation:** [https://www.shellcheck.net/](https://www.shellcheck.net/)

---

## Optional Tools

These tools enhance development workflows but are **not required**. Pre-commit hooks will **gracefully skip** validation if these are missing.

### Docker & Docker Compose

**Purpose:** Local infrastructure (PostgreSQL, Redis, Keycloak, etc.)
**Used by:** Integration tests, local development
**Install:**
- **macOS:** [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- **Linux:** [Docker Engine](https://docs.docker.com/engine/install/)
- **Windows:** [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)

**Verification:**
```bash
docker --version
docker-compose --version  # or docker compose version
```

**Note:** Integration tests require Docker. Without it, run `make test-dev` (unit tests only) instead of `make test` (all tests).

---

### Trivy (Security Scanner)

**Purpose:** Container and Kubernetes manifest security scanning
**Used by:** Pre-commit hooks (optional), CI security scans
**Install:**
- **macOS:** `brew install trivy`
- **Linux:**
  ```bash
  wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
  echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
  sudo apt update && sudo apt install trivy
  ```
- **Windows (WSL):** Same as Linux

**Verification:**
```bash
trivy --version
```

**Documentation:** [https://trivy.dev/](https://trivy.dev/)

---

### Helm

**Purpose:** Kubernetes package management
**Used by:** Deployment validation, Helm chart linting
**Install:**
- **macOS:** `brew install helm`
- **Linux:**
  ```bash
  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
  ```
- **Windows:** `choco install kubernetes-helm`

**Verification:**
```bash
helm version
```

**Documentation:** [https://helm.sh/docs/intro/install/](https://helm.sh/docs/intro/install/)

---

### kubectl

**Purpose:** Kubernetes command-line tool
**Used by:** Kustomize validation, deployment testing
**Install:**
- **macOS:** `brew install kubectl`
- **Linux:**
  ```bash
  curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
  chmod +x kubectl
  sudo mv kubectl /usr/local/bin/
  ```
- **Windows:** `choco install kubernetes-cli`

**Verification:**
```bash
kubectl version --client
```

**Documentation:** [https://kubernetes.io/docs/tasks/tools/](https://kubernetes.io/docs/tasks/tools/)

---

### Terraform

**Purpose:** Infrastructure as Code
**Used by:** Infrastructure deployment, pre-commit Terraform formatting
**Install:**
- **macOS:** `brew install terraform`
- **Linux:**
  ```bash
  wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
  echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
  sudo apt update && sudo apt install terraform
  ```
- **Windows:** `choco install terraform`

**Verification:**
```bash
terraform --version
```

**Documentation:** [https://developer.hashicorp.com/terraform/downloads](https://developer.hashicorp.com/terraform/downloads)

---

### Node.js & npm

**Purpose:** Mintlify documentation validation
**Used by:** Documentation link checking, Mintlify local preview
**Install:**
- **macOS:** `brew install node`
- **Linux (Ubuntu/Debian):**
  ```bash
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt install -y nodejs
  ```
- **Windows:** Download from [nodejs.org](https://nodejs.org/)

**Verification:**
```bash
node --version
npm --version
```

**Documentation:** [https://nodejs.org/](https://nodejs.org/)

---

### actionlint

**Purpose:** GitHub Actions workflow validation
**Used by:** Pre-commit hooks (optional), CI workflow syntax checking
**Install:**
- **macOS:** `brew install actionlint`
- **Linux:**
  ```bash
  bash <(curl https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash)
  sudo mv ./actionlint /usr/local/bin/
  ```
- **Windows (WSL):** Same as Linux

**Verification:**
```bash
actionlint --version
```

**Documentation:** [https://github.com/rhysd/actionlint](https://github.com/rhysd/actionlint)

---

## Platform-Specific Installation

### macOS (Homebrew)

**One-liner to install all tools:**
```bash
brew install python@3.12 git shellcheck docker helm kubectl terraform node actionlint trivy
```

**Install uv separately:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

### Linux (Ubuntu/Debian)

**Required tools:**
```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv git shellcheck
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Optional tools:**
```bash
# Docker
curl -fsSL https://get.docker.com | sh

# Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin/

# Terraform
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Trivy
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt update && sudo apt install trivy

# actionlint
bash <(curl https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash)
sudo mv ./actionlint /usr/local/bin/
```

---

### Windows (WSL2 Recommended)

We recommend using **WSL2 (Windows Subsystem for Linux)** for development on Windows.

**Install WSL2:**
```powershell
wsl --install
```

Then follow the [Linux (Ubuntu/Debian)](#linux-ubuntudebian) instructions inside WSL.

**Alternative (Native Windows with Chocolatey):**
```powershell
choco install python git docker-desktop kubernetes-helm kubernetes-cli terraform nodejs
```

---

## Verification

### Automated Setup Verification

Run the automated setup verification script:

```bash
make validate-setup
```

This checks for all required and optional tools and reports their status.

---

### Manual Verification

**Check required tools:**
```bash
python3 --version        # Should be 3.12+
uv --version            # Should be installed
git --version           # Any recent version
shellcheck --version    # Should be installed
```

**Check optional tools:**
```bash
docker --version        # Optional
trivy --version         # Optional
helm version           # Optional
kubectl version --client  # Optional
terraform --version    # Optional
node --version         # Optional
npm --version          # Optional
actionlint --version   # Optional
```

---

## Troubleshooting

### "shellcheck: command not found" during pre-commit

**Problem:** ShellCheck is required but not installed.

**Solution:**
```bash
# macOS
brew install shellcheck

# Linux
sudo apt install shellcheck
```

**Why:** ShellCheck validates bash scripts and is a required dependency for pre-commit hooks.

---

### "Docker daemon is not running" during integration tests

**Problem:** Integration tests require Docker, but Docker daemon is not running.

**Solution:**
```bash
# macOS/Windows: Start Docker Desktop application

# Linux: Start Docker service
sudo systemctl start docker
```

**Alternative:** Skip integration tests:
```bash
make test-dev  # Runs unit tests only (no Docker required)
```

---

### "uv: command not found"

**Problem:** uv package manager is not installed or not in PATH.

**Solution:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.cargo/bin:$PATH"

# Reload shell
source ~/.bashrc  # or source ~/.zshrc
```

---

### Pre-commit hook fails with "Skipping: tool not installed"

**Problem:** Optional tool is missing, but hook is trying to run.

**Solution:** This is expected behavior. Optional tools gracefully skip with a warning message. The commit will still succeed.

If you want to install the tool for full validation:
- See the [Optional Tools](#optional-tools) section above
- Or run the tool-specific install command shown in the warning message

---

### Python version mismatch (3.11 vs 3.12)

**Problem:** System has Python 3.11 but project requires 3.12+.

**Solution:**
```bash
# macOS
brew install python@3.12

# Linux (Ubuntu)
sudo apt install python3.12 python3.12-venv

# Use specific version
python3.12 -m venv .venv
```

---

## Next Steps

After completing setup:

1. **Install Python dependencies:**
   ```bash
   make install-dev
   ```

2. **Run tests:**
   ```bash
   make test-dev  # Fast unit tests (~2-3 min)
   ```

3. **Start local infrastructure (optional):**
   ```bash
   make quick-start  # Starts Docker infrastructure
   ```

4. **Read development guides:**
   - [TESTING.md](TESTING.md) - Test-driven development guide
   - [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
   - [README.md](../README.md) - Project overview

---

## CLI Tool Summary

| Tool | Required? | Purpose | Install Command (macOS) |
|------|-----------|---------|-------------------------|
| Python 3.12+ | ✅ Required | Main language | `brew install python@3.12` |
| uv | ✅ Required | Package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Git | ✅ Required | Version control | `brew install git` |
| ShellCheck | ✅ Required | Shell linting | `brew install shellcheck` |
| Docker | ⚠️ Optional | Infrastructure | `brew install --cask docker` |
| Trivy | ⚠️ Optional | Security scanning | `brew install trivy` |
| Helm | ⚠️ Optional | K8s packages | `brew install helm` |
| kubectl | ⚠️ Optional | K8s CLI | `brew install kubectl` |
| Terraform | ⚠️ Optional | Infrastructure | `brew install terraform` |
| Node.js/npm | ⚠️ Optional | Documentation | `brew install node` |
| actionlint | ⚠️ Optional | Workflow validation | `brew install actionlint` |

---

## References

- **Codex Audit Finding:** Make/Test Flow Issue 1.3 (CLI dependency documentation)
- **Hooks & Tooling Issue 2.2:** Ambient CLI dependencies
- **Pre-commit Configuration:** `.pre-commit-config.yaml` - Complete hook catalog
- **Makefile Targets:** `Makefile` - All available development commands

---

**Questions or Issues?**

- Check [Troubleshooting](#troubleshooting) section above
- Review `.claude/memory/python-environment-usage.md` for Python-specific guidance
- Open an issue: [GitHub Issues](https://github.com/your-org/mcp-server-langgraph/issues)
