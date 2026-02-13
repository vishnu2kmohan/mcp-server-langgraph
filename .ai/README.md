# AI Assistant Configurations

**Purpose**: Directory for AI coding assistant configurations

---

## Supported Tools

| Tool | Primary Config | Status |
|------|---------------|--------|
| Claude Code | `.claude/CLAUDE.md` | Primary |
| Cursor | `.cursorrules` | Supported |
| GitHub Copilot | `.github/copilot-instructions.md` | Supported |
| Gemini Code Assist | `.gemini/GEMINI.md` | Supported |
| OpenAI Codex | `.codex/instructions.md` + `AGENTS.md` | Supported |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `CORE.md` | **Shared core** - Python env, commands, TDD, style |
| `.claude/CLAUDE.md` | Claude Code quick start |
| `.github/CLAUDE.md` | Claude Code full guide |
| `.cursorrules` | Cursor-specific rules + MCP config |
| `.github/copilot-instructions.md` | Copilot-specific patterns |
| `.gemini/GEMINI.md` | Gemini Code Assist instructions |
| `.codex/instructions.md` | OpenAI Codex instructions |
| `AGENTS.md` | Cross-tool overview (auto-generated) |

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
├── CORE.md          # Shared instructions (all tools)
├── build-agents.sh  # Auto-generate AGENTS.md
├── check-sync.sh    # Drift detection across configs
├── prompts.md       # Common AI prompt templates
└── README.md        # This file

.claude/
├── CLAUDE.md    # Claude Code quick start
├── commands/    # 24 project-specific commands (generic promoted to ~/.claude/)
├── context/     # Living context files
└── memory/      # Persistent guidance

.gemini/
├── GEMINI.md    # Gemini Code Assist instructions
└── sandbox.venv/# Gemini sandbox environment

.codex/
└── instructions.md # Codex instructions

.github/
├── CLAUDE.md              # Claude Code full guide
└── copilot-instructions.md # Copilot patterns

Root/
├── AGENTS.md    # Cross-tool overview (auto-generated)
└── .cursorrules # Cursor AI rules
```

---

## Key Principle

All AI instruction files reference `CORE.md` for common content.
Tool-specific files contain only unique patterns for that tool.

---

**See**: `CORE.md` for shared instructions
