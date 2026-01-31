# AI Agent Instructions

**For**: OpenAI Codex, GitHub Copilot, Cursor, Gemini Code Assist, Claude Code

---

## Quick Start

**Read first**: `.ai/CORE.md` - Contains all common instructions:
- Python environment (CRITICAL: always use `.venv`)
- Project overview and commands
- TDD workflow and code style
- Testing patterns and security

---

## Tool-Specific Configurations

| Tool | Config File |
|------|-------------|
| Cursor | `.cursorrules` |
| Copilot | `.github/copilot-instructions.md` |
| Claude Code | `.claude/CLAUDE.md` |
| All AI | `.ai/CORE.md` |

---

## OpenAI Codex Notes

**File size limit**: 32 KiB per instruction file

This project's AI instruction files are optimized to stay under this limit.

---

## Project Structure

```
mcp-server-langgraph/
├── src/mcp_server_langgraph/  # Main package
├── tests/                      # 20,000+ tests
├── deployments/                # K8s, Helm, Kustomize
├── docs/                       # Mintlify documentation
├── adr/                        # 104 Architecture Decision Records
├── .ai/                        # AI assistant configurations
│   ├── CORE.md                 # Shared core instructions
│   └── README.md               # AI tool configuration guide
├── .claude/                    # Claude Code automation
└── .github/                    # GitHub + Copilot configs
```

---

## Workflow

1. **EXPLORE**: Read related files, review ADRs, check tests
2. **PLAN**: Create task breakdown before coding
3. **CODE**: TDD cycle (Red → Green → Refactor)
4. **COMMIT**: Let git hooks validate

---

## Key Principles

- **Match existing patterns**: Follow codebase conventions
- **Minimal changes**: Don't refactor beyond the ask
- **Tests first**: TDD is mandatory
- **Never hardcode secrets**: Use env vars or Infisical

---

## Resources

| Resource | Description |
|----------|-------------|
| `.ai/CORE.md` | Shared AI instructions |
| `docs-internal/testing/TESTING.md` | Test patterns and markers |
| `CONTRIBUTING.md` | Contribution guidelines |
| `adr/` | Architecture decisions |

---

**Python 3.12 | LangGraph >=1.0.4 | uv package manager**
