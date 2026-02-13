---
name: data-synthesis
description: Synthesize information from multiple sources into coherent reports. Use when combining data from various inputs into structured summaries.
allowed-tools:
- Read
- Glob
- Grep
compatibility: Requires pandas>=2.0.0. No network access needed.
metadata:
  version: 1.0.0
  category: research
  author: Emergence AI
  dependencies:
  - pandas>=2.0.0
  sandbox_config:
    network: none
    filesystem: readonly
---
# Data Synthesis Skill

Combine and synthesize information from multiple sources into coherent, well-structured reports.

## Capabilities

- **Multi-Source Integration**: Combine data from various sources
- **Conflict Resolution**: Identify and resolve conflicting information
- **Pattern Detection**: Find patterns across sources
- **Report Generation**: Produce structured synthesis reports

## Usage Examples

- "Synthesize findings from these 5 research papers"
- "Create a comparative analysis of these datasets"
- "Identify common themes across these documents"

## Guidelines

1. Cross-reference facts across sources
2. Note disagreements between sources
3. Weight sources by authority/recency
4. Produce actionable conclusions

## Output Format

```markdown
# Synthesis Report: [Topic]

## Overview
[High-level synthesis]

## Source Analysis
| Source | Key Points | Reliability |
|--------|------------|-------------|

## Common Themes
- [Theme 1]
- [Theme 2]

## Conflicts/Disagreements
[Where sources disagree]

## Synthesized Conclusions
[Unified conclusions]
```
