---
purpose: Standardized YAML frontmatter conventions for .claude documentation
priority: high
category: conventions
last-updated: 2026-02-05
---

# Frontmatter Conventions

This document defines the YAML frontmatter standards for all `.claude` documentation.

---

## Why Frontmatter?

Per [Vercel's AGENTS.md research](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals):

1. **Progressive disclosure** - Metadata loaded first, content on demand
2. **Context efficiency** - Only ~100 tokens for metadata vs full file
3. **Retrieval-led reasoning** - Structured data enables smart loading
4. **Cross-platform compatibility** - AgentSkills.io standard

---

## File Types & Required Fields

### Skills (SKILL.md)

```yaml
---
name: skill-name                    # Required: 1-64 chars, lowercase+hyphens
description: >-                     # Required: 1-1024 chars, third person
  Does X and Y. Use when user asks about Z.
metadata:                           # Optional: key-value pairs
  author: mcp-server-langgraph
  version: "1.0"
compatibility: Claude Code 1.0+    # Optional: environment requirements
# Claude Code extensions (valid but not agentskills.io standard):
context: fork                      # fork | inline
agent: Explore                     # Agent type for subagent
allowed-tools: Read, Grep, Glob    # Pre-approved tools
disable-model-invocation: true     # User-only invocation
argument-hint: [--flag <value>]    # CLI argument hints
---
```

### Commands (*.md in commands/)

```yaml
---
description: Brief description of what command does
argument-hint: <required-arg> [optional-arg]  # Optional
---
```

### Memory Files (memory/*.md)

```yaml
---
purpose: One-line description of what this file contains
priority: critical | high | medium | low
category: efficiency | patterns | tools | environment | conventions
last-updated: YYYY-MM-DD
---
```

### Context Files (context/*.md)

```yaml
---
purpose: One-line description of the context this file provides
priority: high | medium | low
category: testing | patterns | frontend | api
last-updated: YYYY-MM-DD
# Optional domain-specific fields:
test-count: 437+
stack: React 18, Redux Toolkit
---
```

### Templates (templates/*.md)

```yaml
---
purpose: What this template is used for
category: templates
when-to-use: Scenario description
---
```

---

## Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `purpose` | string | Yes | One-line description (60-100 chars) |
| `priority` | enum | Memory/Context | `critical`, `high`, `medium`, `low` |
| `category` | string | Yes | Grouping category for organization |
| `last-updated` | date | Recommended | ISO date format YYYY-MM-DD |
| `name` | string | Skills only | 1-64 chars, lowercase + hyphens |
| `description` | string | Skills/Commands | 1-1024 chars, third person |

---

## Priority Levels

| Level | Meaning | Auto-load |
|-------|---------|-----------|
| `critical` | Must always be followed | Yes |
| `high` | Important for most tasks | Yes |
| `medium` | Useful reference material | On demand |
| `low` | Supplementary information | On demand |

---

## Naming Conventions

### Skills (agentskills.io compliant)

```yaml
# Good - gerund form (verb + -ing)
name: processing-pdfs
name: analyzing-code
name: testing-coverage

# Acceptable - noun phrases
name: pdf-processing
name: code-analysis

# Bad - avoid these patterns
name: PDF-Processing    # No uppercase
name: -pdf-processing   # No leading hyphen
name: pdf--processing   # No consecutive hyphens
name: helper            # Too vague
name: utils             # Too generic
```

### Descriptions (third person, action-oriented)

```yaml
# Good - third person, includes when to use
description: >-
  Analyzes test coverage gaps and generates reports.
  Use when user asks about coverage, untested code, or test gaps.

# Bad - first/second person
description: I can help you analyze coverage...
description: Use this to analyze your coverage...

# Bad - too vague
description: Helps with tests.
```

---

## File Length Guidelines

Per agentskills.io and Claude Code best practices:

| File Type | Recommended | Maximum | Action if exceeded |
|-----------|-------------|---------|-------------------|
| SKILL.md body | < 500 lines | 500 lines | Split into references/ |
| Memory files | < 200 lines | 300 lines | Split by topic |
| Context files | < 400 lines | 500 lines | Split by domain |
| README files | < 350 lines | 400 lines | Extract to sub-docs |

**Current violations:**
- `context/code-patterns.md`: 960 lines (split recommended)

---

## Validation

Check frontmatter syntax:

```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('file.md').read().split('---')[1])"

# Check all memory files
for f in .claude/memory/*.md; do
  python3 -c "import yaml; yaml.safe_load(open('$f').read().split('---')[1])" 2>/dev/null || echo "Invalid: $f"
done
```

---

## Sources

- [AgentSkills.io Specification](https://agentskills.io/specification)
- [Claude Code Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Vercel AGENTS.md Research](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)
- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
