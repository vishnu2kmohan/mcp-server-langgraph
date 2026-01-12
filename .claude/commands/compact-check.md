---
description: Monitor context usage and suggest /compact when approaching limits
allowed-tools: Bash
---

# Context Health Monitor

Analyze current session state and recommend context management actions.

## Context Estimation Heuristics

Since exact token count isn't directly accessible, estimate based on:

1. **Conversation length** - Messages exchanged
2. **Files read** - Each file consumes ~400-2000 tokens
3. **Tool outputs** - Command results, search results
4. **Complexity** - Multi-file operations use more context

## Thresholds

| Usage Level | Indicator | Action |
|-------------|-----------|--------|
| < 50% | Fresh session, few files read | Continue normally |
| 50-70% | Multiple files, some back-and-forth | Consider completing current task |
| 70-85% | Many files, long conversation | **Run /compact now** |
| > 85% | Approaching limit | Complete task → /clear → resume |

## Signs You're at 70%+

- Claude's responses becoming less coherent about earlier context
- Repeated questions about things discussed earlier
- Difficulty tracking multiple files simultaneously
- Session feels "heavy" with accumulated context

## Recommended Workflow

```
# At 70% - Compact to preserve context
/compact

# At 85% - Checkpoint and clear
/checkpoint
/clear
/catchup
```

## When to Run /compact

1. After completing a logical unit of work
2. Before starting a new sub-task within same feature
3. When you notice context degradation
4. Proactively every 30-40 minutes of active work

## /compact vs /clear

| Command | Effect | When to Use |
|---------|--------|-------------|
| `/compact` | Summarizes history, preserves key context | Mid-task, want to continue |
| `/clear` | Fresh start, no memory | Task complete, switching focus |

## Quick Check

Ask yourself:
- Have I read 10+ files this session? → Consider /compact
- Has this session been running 30+ minutes? → Consider /compact
- Am I about to do a complex multi-file operation? → /compact first
- Finished a major feature/bug? → /clear and start fresh
