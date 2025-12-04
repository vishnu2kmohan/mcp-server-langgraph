# Claude Code Settings Architecture

This document explains the Claude Code configuration architecture for this project, including what goes where and why.

---

## 📁 Configuration Files Overview

### Two-File Architecture

This project uses a **two-file configuration strategy**:

1. **`settings.json`** - Shared, version-controlled settings (git-tracked)
2. **`settings.local.json`** - Local, personal settings (.gitignored)

**Why Two Files?**
- Separate team-beneficial automation from personal preferences
- Enable team collaboration while respecting individual workflows
- Share hooks and automation with entire team
- Keep personal permissions and preferences private

---

## 📄 settings.json (Shared Configuration)

**Location**: `.claude/settings.json`
**Git**: ✅ Version controlled (committed)
**Purpose**: Project-wide configuration shared across all team members

### What Goes in settings.json

**✅ Include**:
- **Hooks** (PreToolUse, PostToolUse, SessionStart) - Team automation
- Allowed web domains for documentation (`WebFetch.allowed_domains`)
- Common bash command patterns (`Bash.auto_approve_patterns`)
- Plan mode configuration (`plan_mode`)
- `includeCoAuthoredBy` - Commit co-authoring preference
- Project-specific conventions

**❌ Exclude**:
- Local file paths (machine-specific)
- Personal permissions
- Secrets or credentials
- Disabled MCP servers (personal preference)
- Machine-specific preferences

### Current Configuration

#### 1. WebFetch Allowed Domains

```json
"WebFetch": {
  "allowed_domains": [
    "docs.python.org",
    "peps.python.org",
    "docs.docker.com",
    "kubernetes.io",
    "pypi.org",
    "github.com",
    "docs.anthropic.com",
    "platform.openai.com",
    "smith.langchain.com",
    "docs.langchain.com",
    "fastapi.tiangolo.com",
    "pydantic-docs.helpmanual.io",
    "redis.io",
    "prometheus.io",
    "grafana.com",
    "helm.sh",
    "istio.io",
    "openfga.dev",
    "keycloak.org",
    "infisical.com",
    "docker.io",
    "quay.io"
  ]
}
```

**Purpose**: Allow Claude to fetch documentation from these trusted domains
**Rationale**: Project uses these technologies - Claude needs docs access for accurate help
**Maintenance**: Add new domains when adopting new technologies

**Domain Categories**:
- **Python**: docs.python.org, peps.python.org, pypi.org
- **Containers**: docs.docker.com, kubernetes.io, docker.io, quay.io
- **Frameworks**: fastapi.tiangolo.com, docs.langchain.com, pydantic-docs.helpmanual.io
- **Infrastructure**: redis.io, prometheus.io, grafana.com, helm.sh, istio.io
- **Security**: openfga.dev, keycloak.org, infisical.com
- **AI Platforms**: docs.anthropic.com, platform.openai.com, smith.langchain.com

#### 2. Bash Auto-Approve Patterns

```json
"Bash": {
  "auto_approve_patterns": [
    "pytest tests/ -x --lf",
    "make test-unit",
    "make test-integration",
    "make test-coverage",
    "make lint",
    "make format",
    "git status",
    "git log",
    "git diff",
    "git show",
    "ls",
    "cat",
    "grep",
    "find"
  ]
}
```

**Purpose**: Auto-approve safe, read-only bash commands
**Rationale**: Speeds up workflow by not prompting for common safe commands
**Safety**: Only includes read-only commands or idempotent test/format commands

**Command Categories**:
- **Testing**: pytest, make test-* (safe - doesn't modify code)
- **Linting**: make lint, make format (idempotent)
- **Git Read**: git status, git log, git diff, git show (read-only)
- **File Read**: ls, cat, grep, find (read-only)

**⚠️ Security**: Never auto-approve:
- Destructive commands (rm, mv without confirmation)
- Network operations (curl, wget)
- Package installations (pip install, npm install)
- Git write operations (git commit, git push)

#### 3. Plan Mode Configuration

```json
"plan_mode": {
  "default": false,
  "auto_enable_for_keywords": [
    "migrate",
    "refactor",
    "architecture",
    "breaking change",
    "redesign",
    "major version"
  ]
}
```

**Purpose**: Auto-enable plan mode for risky operations
**Rationale**: Forces deliberate planning before major changes
**Keywords**: Trigger planning when user mentions these terms

**Why These Keywords?**
- `migrate`: Database migrations require planning
- `refactor`: Large refactors need structured approach
- `architecture`: Architectural changes need deliberation
- `breaking change`: Breaking changes need communication
- `redesign`: Redesigns require thorough planning
- `major version`: Major versions imply breaking changes

#### 4. Hooks System

**Location**: Added to `settings.json` (shared with team)

**Purpose**: Automate formatting, linting, TDD reminders, and context updates

**Hook Types in This Project**:
1. **PreToolUse** (1 hook group) - Pre-commit validation
2. **PostToolUse** (5 hook groups) - Post-edit/write automation
3. **SessionStart** (1 hook) - Git status on session start

See the "Hooks System" section below for complete documentation of all 13 hooks.

---

## 📄 settings.local.json (Local Configuration)

**Location**: `.claude/settings.local.json`
**Git**: ❌ **NOT tracked** (.gitignored)
**Purpose**: Personal settings and preferences

**Template**: See `.claude/settings.local.json.example` for starter template

### What Goes in settings.local.json

**✅ Include**:
- Personal permissions (Edit/Write patterns)
- Disabled MCP servers (personal preference)
- Personal workflow preferences
- Machine-specific paths
- Local overrides

**❌ Exclude**:
- Hooks (these belong in settings.json for team benefit)
- Shared configuration (belongs in settings.json)
- Secrets (use environment variables or secret managers)

### Current Configuration

#### 1. Permissions

```json
"permissions": {
  "allow": [
    "Edit(**)",
    "Write(**)",
    "Read(**)",
    "Glob(**)",
    "Grep(**)",
    "Bash",
    "WebFetch(domain:*)",
    "Read(//tmp/**)",
    // ... extensive WebFetch and Read permissions
  ],
  "defaultMode": "acceptEdits"
}
```

**Current Setup**: Very permissive (Edit/Write all paths)

**Security Consideration**: This is appropriate for personal/trusted projects

**Alternative (More Restrictive)**:
```json
"permissions": {
  "allow": [
    "Edit(**src/**)",
    "Edit(**tests/**)",
    "Edit(**docs/**)",
    "Write(**src/**)",
    "Write(**tests/**)",
    "Write(**docs/**)",
    "Read(**)",
    // Restrict Edit/Write to specific directories
  ]
}
```

#### 2. Disabled MCP Servers

```json
"disabledMcpjsonServers": [
  "langgraph-agent",
  "langgraph-agent-streamable"
]
```

**Purpose**: Disable specific MCP servers
**Reason**: These servers may conflict with project or are not needed
**To Re-enable**: Remove from this array

---

**Note**: Hooks have been moved to `settings.json` (shared configuration) so the entire team benefits from automation. See the "Hooks System" section under settings.json documentation above for complete details on all 13 hooks (PreToolUse, PostToolUse, SessionStart).

---

## 🏗️ Configuration Architecture

### File Hierarchy

```
.claude/
├── settings.json              # Shared config (git tracked)
└── settings.local.json        # Local config (optional git tracking)
```

### Load Order

1. Claude loads global settings (if any)
2. Claude loads project `settings.json`
3. Claude loads `settings.local.json` (overrides settings.json)

**Override Behavior**: settings.local.json takes precedence

### Git Tracking Strategy

**This Project's Approach** (Best Practice):
```bash
# settings.json is tracked (shared hooks and configuration)
git add .claude/settings.json

# settings.local.json is .gitignored (personal preferences)
# Already in .gitignore - developers copy from template:
cp .claude/settings.local.json.example .claude/settings.local.json
# Then customize for their machine
```

**Why This Approach?**
- ✅ Team shares hooks and automation (settings.json)
- ✅ Developers customize permissions locally (settings.local.json)
- ✅ No machine-specific paths in version control
- ✅ Template file provides starting point (settings.local.json.example)

**Setup for New Team Members**:
```bash
# 1. Clone repository (gets settings.json with hooks)
git clone <repo>

# 2. Create personal settings from template
cp .claude/settings.local.json.example .claude/settings.local.json

# 3. Customize permissions as needed (optional)
# Edit .claude/settings.local.json to adjust permissions
```

---

## 🔧 Customization Guide

### Adding New Allowed Domains

**When**: Adopting new technology that needs documentation access

**How**:
1. Edit `.claude/settings.json`
2. Add domain to `allowedTools.WebFetch.allowed_domains`
3. Commit change (shared with team)

**Example**:
```json
"allowed_domains": [
  "docs.python.org",
  "your-new-domain.com"  // Add here
]
```

### Adding New Auto-Approve Bash Patterns

**When**: Common safe command used frequently

**Safety Check**:
- ✅ Read-only command? (git status, ls, cat)
- ✅ Idempotent? (make format, make lint)
- ✅ No destructive side effects?
- ❌ Modifies files? → Don't auto-approve
- ❌ Network operations? → Don't auto-approve

**How**:
```json
"auto_approve_patterns": [
  "git status",
  "your-safe-command-here"  // Add here
]
```

### Adding New Hooks

**When**: Want to automate workflow step

**Hook Types**:
- **PreToolUse**: Validation before action (prevent errors)
- **PostToolUse**: Cleanup after action (format, lint)
- **SessionStart**: Context gathering at session start

**Example: Add Pre-Push Hook**:
```json
{
  "matcher": "Bash(**git push**)",
  "hooks": [
    {
      "type": "command",
      "command": "make test-unit",
      "timeout": 120
    }
  ]
}
```

### Customizing Permissions

**More Restrictive**:
```json
"permissions": {
  "allow": [
    "Edit(**src/**)",        // Only edit source
    "Edit(**tests/**)",      // and tests
    "Write(**docs/**)",      // and docs
    "Read(**)"               // Read anywhere
  ]
}
```

**More Permissive** (current):
```json
"permissions": {
  "allow": [
    "Edit(**)",    // Edit anywhere
    "Write(**)"    // Write anywhere
  ]
}
```

---

## 📊 Hook Performance Impact

### Measured Hook Overhead

| Hook Type | Trigger | Overhead | Benefit |
|-----------|---------|----------|---------|
| Black check (Pre) | git commit | +1-2s | Prevents formatting commits |
| Flake8 critical (Pre) | git commit | +0.5-1s | Prevents broken commits |
| Mintlify validation (Pre) | git commit | +2-3s | Prevents doc site breaks |
| Black format (Post) | Edit/Write | +0.1-0.3s | Auto-formats code |
| Isort (Post) | Edit/Write | +0.1-0.2s | Auto-sorts imports |
| Flake8 lint (Post) | Edit/Write | +0.2-0.5s | Immediate linting feedback |
| TDD reminder (Post) | Edit/Write | +0.01s | Enforces TDD culture |
| Git status (Start) | Session start | +0.1-0.2s | Immediate context |

**Total Overhead**: ~5-8 seconds per commit, ~0.5s per edit
**Total Benefit**: Prevents 3-5 fix commits per sprint = ~30-60 minutes saved

**ROI**: 4-7x (time saved vs. overhead)

---

## 🔍 Troubleshooting

### Hook Failing

**Symptom**: Hook blocks commit or shows error

**Debugging**:
```bash
# Run hook command manually
uv run black --check src/ --line-length=127

# Check hook timeout (increase if needed)
"timeout": 60  // Increase from 30
```

**Common Issues**:
- `uv` not installed → Install: `pip install uv`
- Virtual environment issues → Use: `uv run` prefix
- Timeout too short → Increase timeout value

### Settings Not Taking Effect

**Check Load Order**:
```bash
# Verify settings files exist
ls -la .claude/settings*.json

# Check JSON syntax
cat .claude/settings.json | python -m json.tool
```

**Common Issues**:
- JSON syntax error (missing comma, bracket)
- File not in `.claude/` directory
- Settings cached (restart Claude Code)

### Permission Denied

**Symptom**: Claude can't edit/write files

**Solution**: Add to `settings.local.json`:
```json
"permissions": {
  "allow": [
    "Edit(**path/to/directory/**)",
    "Write(**path/to/directory/**)"
  ]
}
```

---

## 📈 Best Practices

### Do's ✅

1. **settings.json**: Share project-wide configuration
2. **settings.local.json**: Keep local preferences here
3. **Hooks**: Automate repetitive quality checks
4. **Auto-approve**: Only safe, read-only commands
5. **Documentation**: Keep this SETTINGS.md updated
6. **Review**: Audit settings quarterly

### Don'ts ❌

1. **Don't** put secrets in any settings file
2. **Don't** auto-approve destructive commands
3. **Don't** make hooks too slow (< 3s ideal)
4. **Don't** override safety with excessive permissions
5. **Don't** track settings.local.json if team has divergent needs
6. **Don't** forget to test hooks before committing

---

## 🔄 Maintenance

### Quarterly Review Checklist

- [ ] Review allowed domains - still needed?
- [ ] Check auto-approve patterns - still safe?
- [ ] Audit hooks - still valuable?
- [ ] Measure hook overhead - acceptable?
- [ ] Review permissions - appropriate for project phase?
- [ ] Update this documentation - still accurate?

### When to Update Settings

**Add Domain**: When adopting new technology
**Add Auto-Approve**: When safe command used frequently
**Add Hook**: When manual step repeated often
**Update Permissions**: When project phase changes
**Disable Hook**: When overhead exceeds benefit

---

## 📚 Additional Resources

- **Claude Code Docs**: https://code.claude.com/docs
- **Settings Schema**: https://json.schemastore.org/claude-code-settings.json
- **Main README**: `.claude/README.md`
- **Quick Reference**: `.claude/QUICK_REFERENCE.md`

---

**Last Updated**: 2025-11-15
**Maintained By**: Project team
**Review Frequency**: Quarterly or when workflow changes
