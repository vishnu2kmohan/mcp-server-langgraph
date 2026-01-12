# Session Workflow Patterns

**Purpose**: Document proven patterns for managing Claude Code sessions effectively
**Last Updated**: 2025-01-10

---

## The Session Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                      SESSION START                          │
│  • Git status shown (hook)                                  │
│  • TDD reminder shown (hook)                                │
│  • Read recent-work.md if resuming                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    ACTIVE WORK PHASE                        │
│  • Use TodoWrite to track progress                          │
│  • Batch file reads at task start                           │
│  • Monitor context level mentally                           │
│  • Run /compact at ~70% capacity                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   TASK COMPLETION                           │
│  • Mark todos complete                                      │
│  • Commit if requested                                      │
│  • Run /checkpoint if more work remains                     │
│  • Run /clear before unrelated work                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Pattern 1: Research-Then-Implement

**When**: Major features, unfamiliar code, architectural changes

```
Session 1 (Research):
├── /research <topic>
├── Explore codebase (read-only)
├── Document findings in .claude/research/
├── /checkpoint
└── /clear

Session 2 (Implement):
├── Read research document
├── /catchup
├── Implement with clear understanding
└── Commit
```

**Benefits**:
- Clean context for implementation
- Documented decisions
- Reduced back-and-forth

---

## Pattern 2: Compact at Threshold

**When**: Long sessions, many files read, context feeling "heavy"

### Indicators to Compact

| Indicator | Action |
|-----------|--------|
| 10+ files read | Consider /compact |
| 30+ minutes active | Consider /compact |
| Complex multi-file task ahead | /compact first |
| Claude seems to forget earlier context | /compact immediately |

### Compact Flow

```
<notice context degradation>
├── Finish current atomic task
├── /compact
└── Continue with cleaner context
```

---

## Pattern 3: Checkpoint Before Clear

**When**: Incomplete work, end of day, switching tasks

```
<work in progress>
├── /checkpoint
│   └── Creates .claude/checkpoints/YYYY-MM-DD-HHMMSS.md
├── /clear
└── <switch to other work>

<returning later>
├── Read checkpoint file
├── /catchup
└── Continue from "Next Steps"
```

**Checkpoint Contains**:
- What was accomplished
- Current state
- Key decisions made
- Next steps (prioritized)
- Open questions

---

## Pattern 4: Task-Scoped Sessions

**When**: Multiple unrelated tasks

```
Task A:
├── Work on Task A
├── Commit Task A
├── /clear
└── (Task A context discarded)

Task B:
├── Fresh context
├── Work on Task B
├── Commit Task B
└── /clear
```

**Anti-pattern**: Mixing unrelated tasks in one session
- Context pollution
- Reduced coherence
- Risk of cross-contamination

---

## Pattern 5: Parallel Worktree Sessions

**When**: Need to context-switch frequently

```
Worktree 1 (feature/auth):
└── Claude session focused on auth

Worktree 2 (feature/frontend):
└── Claude session focused on frontend
```

**Benefits**:
- Complete isolation
- No context mixing
- Can pause/resume independently

---

## Context Budget Guidelines

### Estimated Token Usage

| Content | Approximate Tokens |
|---------|-------------------|
| Average Python file | 800-1,500 |
| Large module | 2,000-4,000 |
| Test file | 600-1,200 |
| Config file | 200-500 |
| Tool output (typical) | 100-500 |

### Budget Allocation

With ~175k token context window:

| Phase | Budget | Guidance |
|-------|--------|----------|
| System prompts | ~15k | Fixed, unavoidable |
| CLAUDE.md + memory | ~10k | Loaded automatically |
| Active work | ~100k | Main workspace |
| Buffer | ~50k | Safety margin |

**Rule of thumb**: Start fresh at ~80% to avoid degradation

---

## Command Quick Reference

| Command | When | Effect |
|---------|------|--------|
| `/compact` | 70% context | Summarize, preserve key info |
| `/clear` | Task complete | Fresh start |
| `/checkpoint` | Before /clear | Save resumption state |
| `/catchup` | After /clear | Restore git context |
| `/research <topic>` | Before implementing | Explore without coding |
| `/compact-check` | Unsure | Get context health assessment |

---

## Anti-Patterns to Avoid

### 1. Context Exhaustion
```
# BAD: Push to the limit
<work until Claude struggles>

# GOOD: Proactive management
<compact at 70%>
```

### 2. Mixing Concerns
```
# BAD: Auth bug → then frontend styling → then database query
# Scattered context, poor coherence

# GOOD: Complete auth bug → /clear → frontend styling
# Focused sessions
```

### 3. No Checkpoint Before Clear
```
# BAD: /clear with work in progress
# Lost context, lost decisions

# GOOD: /checkpoint → /clear
# Resumable state
```

### 4. Re-Reading Everything
```
# BAD: After /clear, read all 20 files again
# Wasteful, slow

# GOOD: After /clear, read checkpoint + key 3-5 files
# Efficient restoration
```

---

## Session Hygiene Checklist

**Starting a session**:
- [ ] Check git status (shown automatically)
- [ ] Review recent-work.md if resuming multi-day work
- [ ] Plan scope: what will this session accomplish?

**During session**:
- [ ] Use TodoWrite for task tracking
- [ ] Batch file reads
- [ ] Monitor context level
- [ ] Run /compact if needed

**Ending session**:
- [ ] Mark todos complete
- [ ] Commit if requested
- [ ] Run /checkpoint if work remains
- [ ] Run /clear before switching context

---

**Remember**: Sessions are cheap. Context is expensive. When in doubt, /checkpoint → /clear → resume fresh.
