# AI Tools Compatibility Guide

This codebase is optimized for compatibility with multiple AI coding assistants and IDEs.

## ✅ Fully Supported AI Tools

### 1. **Claude Code** (Anthropic)
- **Status**: ✅ Fully Supported
- **Configuration**: Uses `.cursorrules` and `.ai/` directory
- **Features**:
  - Project-aware code generation
  - Context-aware refactoring
  - Documentation generation
  - Test generation
- **Best Practices**:
  - Reads entire codebase context
  - Follows established patterns
  - Maintains consistency

### 2. **GitHub Copilot** (Microsoft/OpenAI)
- **Status**: ✅ Fully Supported
- **Configuration**:
  - `.github/copilot-instructions.md`
  - `.vscode/settings.json`
- **Features**:
  - Inline code completions
  - Function generation
  - Test suggestions
  - Documentation
- **Best Practices**:
  - Use inline comments to guide suggestions
  - Leverage `#file:` syntax for context
  - Tab through multiple suggestions

### 3. **Cursor** (Anysphere)
- **Status**: ✅ Fully Supported
- **Configuration**:
  - `.cursorrules`
  - `.cursor/mcp.json`
  - `.vscode/*` (inherited)
- **Features**:
  - Chat with codebase
  - Multi-file edits
  - MCP server integration
  - @-mentions for docs
- **Best Practices**:
  - Use `@codebase` for project-wide questions
  - Use `@docs` for documentation queries
  - Use `@git` for history context

### 4. **Gemini Code Assist** (Google)
- **Status**: ✅ Supported
- **Configuration**: Uses workspace settings
- **Features**:
  - Code completions
  - Refactoring suggestions
  - Documentation generation
- **Best Practices**:
  - Integrates with Google Cloud
  - Follows EditorConfig
  - Respects .gitignore

### 5. **OpenAI Codex** (OpenAI)
- **Status**: ✅ Fully Supported
- **Configuration**:
  - `.openai/codex-instructions.md`
  - `.openai/code-completion-config.json`
  - `.vscode/settings.json` (OpenAI section)
- **Features**:
  - Advanced code completions
  - Multi-line suggestions
  - Context-aware generation
  - Code explanation and documentation
- **Best Practices**:
  - Use clear function signatures as prompts
  - Provide context via comments
  - Review generated code for security
  - Test completions thoroughly

### 6. **OpenAI GPT-4** (via extensions)
- **Status**: ✅ Supported
- **Configuration**: Extension-specific, uses `.openai/` configs
- **Features**:
  - Code generation
  - Explanation
  - Debugging assistance
  - Refactoring suggestions
- **Best Practices**:
  - Use prompt templates from `.ai/prompts.md`
  - Provide context from documentation
  - Leverage `.openai/codex-instructions.md`

## 🔧 IDE Compatibility

### Visual Studio Code
- **Status**: ✅ Fully Configured
- **Configuration Files**:
  - `.vscode/settings.json` - Editor, Python, formatting
  - `.vscode/extensions.json` - Recommended extensions
  - `.vscode/launch.json` - Debugging configurations
  - `.vscode/tasks.json` - Build and test tasks
- **AI Extensions Supported**:
  - GitHub Copilot
  - GitHub Copilot Chat
  - OpenAI Codex
  - Cursor (VSCode fork)
  - Tabnine
  - AWS CodeWhisperer
- **Recommended Extensions**:
  ```
  ms-python.python
  ms-python.black-formatter
  ms-python.isort
  github.copilot
  github.copilot-chat
  ms-azuretools.vscode-docker
  ms-kubernetes-tools.vscode-kubernetes-tools
  ```

### Cursor
- **Status**: ✅ Fully Configured
- **Configuration Files**:
  - `.cursorrules` - AI behavior rules
  - `.cursor/mcp.json` - MCP server integration
  - Inherits all `.vscode/*` configs
- **Unique Features**:
  - Native MCP protocol support
  - Multi-file editing
  - Codebase-aware chat
- **Setup**:
  1. Open project in Cursor
  2. MCP server auto-detected via `.cursor/mcp.json`
  3. Use `Cmd+K` for inline edits
  4. Use `Cmd+L` for chat

### JetBrains IDEs (PyCharm, IntelliJ)
- **Status**: ⚠️ Partial Support
- **Configuration**: `.editorconfig` provides base settings
- **AI Support**:
  - GitHub Copilot plugin
  - AI Assistant (JetBrains)
- **Note**: May need manual Python interpreter setup

### Neovim / Vim
- **Status**: ⚠️ Manual Configuration Needed
- **Recommendations**:
  - Use `coc.nvim` with Python LSP
  - Install GitHub Copilot plugin
  - Respect `.editorconfig`
- **Configuration**: User-managed

## 📋 Configuration Files Overview

### Universal (All Tools)
| File | Purpose | Supported By |
|------|---------|--------------|
| `.editorconfig` | Editor settings | All IDEs |
| `.gitignore` | VCS exclusions | All tools |
| `pyproject.toml` | Python tooling | All Python tools |
| `.pre-commit-config.yaml` | Git hooks | All VCS workflows |

### AI-Specific
| File | Purpose | Used By |
|------|---------|---------|
| `.cursorrules` | AI behavior rules | Cursor, Claude Code |
| `.github/copilot-instructions.md` | Copilot guidelines | GitHub Copilot |
| `.openai/codex-instructions.md` | OpenAI Codex guide | OpenAI Codex, GPT-4 |
| `.openai/code-completion-config.json` | Codex configuration | OpenAI Codex |
| `.ai/README.md` | AI assistant guide | All AI tools |
| `.ai/prompts.md` | Prompt templates | All AI tools |

### IDE-Specific
| File | Purpose | Used By |
|------|---------|---------|
| `.vscode/settings.json` | Editor config | VSCode, Cursor |
| `.vscode/extensions.json` | Extension recommendations | VSCode, Cursor |
| `.vscode/launch.json` | Debug configs | VSCode, Cursor |
| `.vscode/tasks.json` | Build tasks | VSCode, Cursor |
| `.cursor/mcp.json` | MCP server | Cursor |

## 🚀 Quick Start by Tool

### VSCode with GitHub Copilot

1. **Install VSCode**: https://code.visualstudio.com/
2. **Install Extensions**:
   ```bash
   code --install-extension ms-python.python
   code --install-extension github.copilot
   code --install-extension github.copilot-chat
   ```
3. **Open Project**:
   ```bash
   code /path/to/mcp_server_langgraph
   ```
4. **Install Recommended Extensions**: Click "Install" when prompted
5. **Setup Python**:
   - `Cmd+Shift+P` → "Python: Select Interpreter"
   - Choose `./venv/bin/python`

### Cursor

1. **Install Cursor**: https://cursor.sh/
2. **Open Project**:
   ```bash
   cursor /path/to/mcp_server_langgraph
   ```
3. **MCP Auto-detected**: Cursor reads `.cursor/mcp.json` automatically
4. **Start Coding**:
   - `Cmd+K` for inline edits
   - `Cmd+L` for chat
   - `@codebase` for project context

### Claude Code (CLI)

1. **Install Claude Code**: https://docs.anthropic.com/claude-code
2. **Navigate to Project**:
   ```bash
   cd /path/to/mcp_server_langgraph
   ```
3. **Start Session**:
   ```bash
   claude-code
   ```
4. **Reads Automatically**:
   - `.cursorrules`
   - `.ai/README.md`
   - Project structure

### OpenAI Codex

1. **Install OpenAI Extension**:
   - VSCode: Install OpenAI extension
   - Or use OpenAI API directly
2. **Configure API Key**:
   ```bash
   # Add to environment
   export OPENAI_API_KEY="sk-..."
   ```
3. **Open Project**:
   ```bash
   code /path/to/mcp_server_langgraph
   ```
4. **Configuration Auto-loaded**:
   - `.openai/codex-instructions.md`
   - `.openai/code-completion-config.json`
   - `.vscode/settings.json` (OpenAI section)

### Gemini Code Assist

1. **Install Cloud Code**: https://cloud.google.com/code
2. **Open Project in Supported IDE**:
   - VSCode
   - JetBrains
3. **Enable Gemini**:
   - Settings → Cloud Code → AI Assistance
4. **Start Coding**: Inline suggestions appear automatically

## 🎯 Feature Comparison

| Feature | VSCode+Copilot | Cursor | Claude Code | OpenAI Codex | Gemini |
|---------|----------------|--------|-------------|--------------|--------|
| Inline Completions | ✅ | ✅ | ✅ | ✅ | ✅ |
| Chat Interface | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multi-file Edits | ⚠️ | ✅ | ✅ | ✅ | ⚠️ |
| Codebase Context | ⚠️ | ✅ | ✅ | ✅ | ⚠️ |
| MCP Integration | ❌ | ✅ | ✅ | ⚠️ | ❌ |
| Test Generation | ✅ | ✅ | ✅ | ✅ | ✅ |
| Refactoring | ✅ | ✅ | ✅ | ✅ | ✅ |
| Documentation | ✅ | ✅ | ✅ | ✅ | ✅ |
| Function-level Gen | ✅ | ✅ | ✅ | ✅ | ✅ |
| Security Analysis | ⚠️ | ✅ | ✅ | ✅ | ⚠️ |

Legend: ✅ Excellent | ⚠️ Partial | ❌ Not Available

## 🎨 Code Style Consistency

All AI tools respect these configurations:

### Formatting
- **Black**: 127 character line length
- **isort**: Black-compatible import sorting
- **flake8**: Linting with E203, W503 ignored
- **mypy**: Strict type checking

### Editor Settings
- **Indent**: 4 spaces for Python
- **Indent**: 2 spaces for YAML, JSON
- **Trailing whitespace**: Auto-removed
- **Final newline**: Auto-inserted
- **Line endings**: LF (Unix)

### File Exclusions
All tools ignore:
- `venv/`, `.venv/`
- `__pycache__/`, `*.pyc`
- `.pytest_cache/`, `.mypy_cache/`
- `logs/`
- `htmlcov/`, `.coverage`

## 📚 Documentation for AI Tools

### Where AI Tools Should Look First

1. **Project Overview**: `README.md`
2. **Architecture**: `README.md` → Architecture section
3. **Development Setup**: `DEVELOPMENT.md`
4. **Contributing**: `CONTRIBUTING.md`
5. **Code Patterns**:
   - `.cursorrules` (Cursor, Claude)
   - `.openai/codex-instructions.md` (OpenAI Codex)
   - `.github/copilot-instructions.md` (GitHub Copilot)
6. **API Reference**: `http://localhost:8000/docs` (when running)

### Prompt Templates

See `.ai/prompts.md` for pre-written prompts for common tasks:
- Adding new tools
- Creating API endpoints
- Writing tests
- Debugging issues
- Performance optimization
- Security reviews

## 🔒 Security Considerations

All AI tools are configured to:

### Never Commit
- Secrets or API keys
- `.env` files (only `.env.example`)
- Credentials
- Private keys

### Always Validate
- User inputs with Pydantic
- JWT tokens
- Authorization with OpenFGA
- Environment variables

### Logging Rules
- ✅ Log events, errors, metrics
- ✅ Log user IDs, resource IDs
- ❌ Never log passwords, tokens, secrets
- ❌ Never log PII without encryption

## 🧪 Testing with AI Tools

### Test Generation Prompts

For any AI tool:
```
Generate comprehensive tests for [function/class] including:
- Happy path
- Error cases
- Edge cases
- Performance benchmarks (if applicable)

Use pytest markers:
- @pytest.mark.unit
- @pytest.mark.integration
- @pytest.mark.benchmark

Mock external dependencies.
```

### Running Tests

All AI tools can suggest:
```bash
# All tests
pytest -v

# Specific marker
pytest -m unit -v

# With coverage
pytest --cov=. --cov-report=html

# Benchmarks
pytest -m benchmark --benchmark-only
```

## 🐛 Debugging with AI Tools

### Debug Prompts
```
I'm seeing this error:
[paste error]

Help me debug by:
1. Explaining the error
2. Identifying root cause
3. Suggesting fixes
4. Adding tests to prevent regression
```

### Debug Configurations

VSCode/Cursor users can use preconfigured launch configs:
- **Python: MCP Server (StreamableHTTP)**
- **Python: Debug Tests**
- **Python: Current File**

See `.vscode/launch.json` for all options.

## 📊 Telemetry and Observability

AI tools understand our observability patterns:

### Tracing
```python
with tracer.start_as_current_span("operation") as span:
    span.set_attribute("key", "value")
    # operation
```

### Logging
```python
logger.info("Event", extra={"context": "data"})
```

### Metrics
```python
metrics.counter.add(1, {"label": "value"})
```

AI tools will suggest adding telemetry to new code.

## 🚢 Deployment Awareness

AI tools understand deployment contexts:

- **Local Development**: Docker Compose
- **Staging**: Kubernetes with Kustomize
- **Production**: Kubernetes with Helm

See `KUBERNETES_DEPLOYMENT.md` and `PRODUCTION_DEPLOYMENT.md`.

## 🤝 Contributing AI Configurations

If you improve AI tool configurations:

1. Test with multiple tools (VSCode, Cursor, Claude)
2. Document in this file
3. Update `.ai/README.md`
4. Submit PR with examples

## 📞 Support

### Issues with AI Tools

- **VSCode/Copilot**: https://github.com/github/copilot-docs/issues
- **Cursor**: https://forum.cursor.sh/
- **Claude Code**: https://support.anthropic.com/
- **Gemini**: https://cloud.google.com/support

### Project-Specific Issues

- **GitHub Issues**: https://github.com/vishnu2kmohan/mcp-server-langgraph/issues
- **Discussions**: https://github.com/vishnu2kmohan/mcp-server-langgraph/discussions

## 🔄 Keeping Configurations Updated

When updating AI configurations:

1. **Test Changes**: Verify with at least 2 AI tools
2. **Update Docs**: This file and `.ai/README.md`
3. **Version Control**: Commit with clear message
4. **Notify Team**: PR description should explain changes

## 📈 Future Compatibility

We're monitoring and will add support for:

- ⏳ **Amazon CodeWhisperer** - AWS-powered completions
- ⏳ **Tabnine** - Privacy-focused AI assistant
- ⏳ **Codeium** - Free AI code acceleration
- ⏳ **Sourcegraph Cody** - Code intelligence platform
- ⏳ **Replit Ghostwriter** - Collaborative AI coding

PRs welcome for additional tool support!

### Recently Added

- ✅ **OpenAI Codex** (2025-10-10) - Full configuration added

## ✅ Verification Checklist

To verify AI tool compatibility:

- [ ] `.editorconfig` respected
- [ ] `.vscode/settings.json` loaded
- [ ] Python formatter (Black) working
- [ ] Import sorter (isort) working
- [ ] Linter (flake8) showing errors
- [ ] Type checker (mypy) working
- [ ] Tests runnable
- [ ] Debug configs working
- [ ] AI completions appearing
- [ ] Project context understood

Run this verification in your IDE of choice!

---

**Last Updated**: 2025-10-10
**Maintained By**: @vishnu2kmohan
**License**: MIT
