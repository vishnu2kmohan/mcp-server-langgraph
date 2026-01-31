# AI Assistant Configurations

**Purpose**: Directory for AI coding assistant configurations

---

## Supported Tools

| Tool | Primary Config | Status |
|------|---------------|--------|
| OpenAI Codex | `CORE.md` | Supported |
| GitHub Copilot | `.github/copilot-instructions.md` | Supported |
| Cursor | `.cursorrules` | Supported |
| Claude Code | `.claude/CLAUDE.md` | Supported |
| Gemini Code Assist | `CORE.md` | Supported |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `CORE.md` | **Shared core** - Python env, commands, TDD, style |
| `.github/copilot-instructions.md` | Copilot-specific patterns |
| `.cursorrules` | Cursor-specific rules + MCP config |
| `.claude/CLAUDE.md` | Claude Code quick start |
| `.github/CLAUDE.md` | Claude Code full guide |
| `AGENTS.md` | Cross-tool overview |

---

## Quick Start for AI Assistants

1. **Read first**: `CORE.md` (this directory)
2. **Tool-specific**: Check your tool's config file above
3. **Follow**: TDD workflow (tests first)
4. **Use**: `.venv` for all Python commands

---

## Directory Structure

```
.ai/
├── CORE.md      # Shared instructions (all tools)
└── README.md    # This file

.claude/
├── CLAUDE.md    # Claude Code quick start
├── commands/    # 46 slash commands
├── context/     # Living context files
├── memory/      # Persistent guidance
└── templates/   # 8 professional templates

.github/
├── CLAUDE.md              # Claude Code full guide
└── copilot-instructions.md # Copilot patterns

Root/
├── AGENTS.md    # Cross-tool overview
└── .cursorrules # Cursor AI rules
```

---

## Key Principle

All AI instruction files reference `CORE.md` for common content.
Tool-specific files contain only unique patterns for that tool.

---

**See**: `CORE.md` for shared instructions
