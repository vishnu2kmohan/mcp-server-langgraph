# Act Quick Start

Run GitHub Actions locally with `act` using `gh` CLI authentication.

## Setup (One Time)

```bash
# 1. Install act
brew install act  # macOS
# or see: https://github.com/nektos/act/releases

# 2. Install and authenticate with gh CLI
brew install gh  # macOS
gh auth login

# 3. Verify setup
gh auth status
act --version
```

## Quick Commands

**All commands use this pattern:**
```bash
act -s GITHUB_TOKEN="$(gh auth token)" [options]
```

**Or create a shell alias** (recommended):
```bash
# Add to ~/.bashrc or ~/.zshrc
act-gh() {
  act -s GITHUB_TOKEN="$(gh auth token)" "$@"
}

# Then use: act-gh push --list
```

## Common Commands

```bash
# List all workflows
act -s GITHUB_TOKEN="$(gh auth token)" push --list

# Fast validation (30 seconds)
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/build-hygiene.yaml

# Unit tests (Python 3.12 only, ~3 minutes)
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --job test --matrix python-version:3.12

# Pre-commit checks (2 minutes)
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --job pre-commit

# Quality tests (15 minutes)
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/quality-tests.yaml

# Coverage tracking (5 minutes)
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/coverage-trend.yaml
```

## With Shell Alias

```bash
# After setting up act-gh alias:

act-gh push --list
act-gh push -W .github/workflows/build-hygiene.yaml
act-gh push -W .github/workflows/ci.yaml --job test --matrix python-version:3.12
```

## Troubleshooting

**"Invalid JWT" or "Bad credentials":**
```bash
gh auth status       # Check authentication
gh auth login        # Re-authenticate if needed
gh auth token        # Verify token is accessible
```

**"Docker permission denied":**
```bash
sudo usermod -aG docker $USER  # Add user to docker group
# Log out and back in
```

**"Error: failed to start container":**
```bash
systemctl status docker              # Check Docker is running
docker pull catthehacker/ubuntu:act-latest  # Pull runner image
```

## Documentation

- **Full Guide**: `.github/ACT_USAGE.md`
- **Act Docs**: https://nektosact.com/
- **GitHub CLI**: https://cli.github.com/

---

**Note**: Act is configured via `.actrc` to use optimized settings for this repository.
