# Markdown Reference Syntax Guide

This guide documents the `[[type:qualifier:id]]` reference syntax for linking to tools, skills, and artifacts in chat messages.

## Overview

References allow you to create clickable links to MCP tools, skills, and artifacts within chat messages. When the message is rendered, references appear as styled chips that can be hovered or clicked for more information.

## Syntax

The basic syntax follows this pattern:

```
[[type:qualifier:id]]
[[type:qualifier:id|Custom Label]]
```

### Components

| Component | Description | Required |
|-----------|-------------|----------|
| `type` | The reference type: `tool`, `skill`, `artifact`, `memory`, or `plan` | Yes |
| `qualifier` | Server name (for tools) or name (for skills/artifacts/memory/plans) | Yes |
| `id` | Tool name, skill name, artifact ID, note ID, or plan ID | Yes |
| `label` | Custom display label (after the `\|` pipe) | No |

## Reference Types

### Tool References

Reference MCP tools by server and tool name:

```markdown
Use [[tool:filesystem:read_file]] to read files.
Use [[tool:database:query]] for SQL queries.
```

**Format**: `[[tool:server_name:tool_name]]`

### Skill References

Reference skills by name:

```markdown
Run [[skill:code-review]] for code analysis.
Use [[skill:test-generator]] to create tests.
```

**Format**: `[[skill:skill_name]]`

### Artifact References

Reference artifacts by ID:

```markdown
See [[artifact:chart-123]] for the visualization.
Review [[artifact:doc-456|Annual Report]] for details.
```

**Format**: `[[artifact:artifact_id]]`

### Memory References

Reference session notes by ID:

```markdown
See [[memory:note-abc]] for the meeting notes.
Review [[memory:insight-123|Key Insights]] from earlier.
```

**Format**: `[[memory:note_id]]`

**Authorization**: Requires `session:viewer` access. Memory notes are scoped to sessions.

### Plan References

Reference execution plans by ID:

```markdown
Check [[plan:plan-456]] for the implementation strategy.
Review [[plan:task-789|Sprint Tasks]] for assignments.
```

**Format**: `[[plan:plan_id]]`

**Authorization**: Requires `session:viewer` access. Plans are scoped to sessions.

## Custom Labels

Add a custom label using the pipe (`|`) character:

```markdown
[[tool:filesystem:read_file|Read File Tool]]
[[skill:code-review|Code Review Skill]]
[[artifact:chart-123|Q4 Sales Chart]]
```

The custom label replaces the default display name shown in the chip.

## Visual Rendering

References render as styled chips with:

- **Type-specific icon**: Wrench (tool), Sparkles (skill), File (artifact), Brain (memory), ListTodo (plan)
- **Type-specific colors**: Primary (tool), Success (skill), Neutral (artifact), Insight (memory), Warning (plan)
- **Hover popover**: Shows description and metadata
- **Click action**: Opens details or navigates to source

## Autocomplete

When typing `[[` in the chat input, an autocomplete menu appears:

1. **Type selection**: Choose tool, skill, or artifact
2. **Search**: Filter available options
3. **Selection**: Arrow keys to navigate, Enter to select

The autocomplete automatically formats the reference syntax.

## Bulk Insertion

Use the reference picker (accessible from the chat toolbar) to:

1. Search across all available references
2. Filter by type (Tools, Skills, Artifacts, Memory, Plans)
3. Select multiple references
4. Insert all at once

## Error States

| Status | Display | Meaning |
|--------|---------|---------|
| Valid | Normal chip | Reference resolved successfully |
| Not Found | Strikethrough, dimmed | Referenced item doesn't exist |
| Unauthorized | Dimmed with lock | User lacks permission |
| Loading | Pulsing animation | Resolution in progress |

## Accessibility

Reference chips follow WCAG 2.2 AA guidelines:

- Proper ARIA roles and labels
- Keyboard navigation support
- Screen reader announcements
- Sufficient color contrast

## Examples

### Basic Usage

```markdown
I'll use [[tool:filesystem:read_file]] to read the config, then run
[[skill:code-review]] to analyze the changes. The results will be
saved as [[artifact:analysis-001]].
```

### With Labels

```markdown
Check the [[artifact:chart-q4-2025|Q4 Sales Dashboard]] for the latest
numbers. Use [[tool:database:query|Run Query]] to fetch more data.
```

### Memory and Plan References

```markdown
Based on [[memory:meeting-notes-123|Today's Meeting]], we'll follow
[[plan:sprint-456|Sprint Plan]]. Reference [[memory:decision-789]]
for the architecture decisions.
```

### In Code Blocks (Escaped)

References inside code blocks are NOT parsed:

```markdown
To reference a tool, use: `[[tool:server:name]]`
```

The backticks prevent the reference from being rendered as a chip.

## API Integration

References are resolved via the `/api/v1/references/resolve` endpoint:

```typescript
// Request
POST /api/v1/references/resolve
{
  "references": [
    { "type": "tool", "qualifier": "filesystem", "id": "read_file" },
    { "type": "skill", "qualifier": "code-review", "id": "code-review" },
    { "type": "memory", "qualifier": "meeting-notes", "id": "note-123" },
    { "type": "plan", "qualifier": "sprint", "id": "plan-456" }
  ]
}

// Response
{
  "resolved": [
    {
      "type": "tool",
      "qualifier": "filesystem",
      "id": "read_file",
      "displayName": "read_file",
      "description": "Read contents of a file",
      "status": "valid",
      "metadata": { "connectionId": "conn-123" }
    },
    ...
  ]
}
```

## Feature Flag

The reference system is controlled by the `enable_markdown_references` feature flag. When disabled, `[[...]]` syntax is rendered as plain text.

## Authorization

Each reference type has specific OpenFGA authorization requirements:

| Type | OpenFGA Check | Scope |
|------|---------------|-------|
| `tool` | `connection:{connection_id}:viewer` | Per-connection |
| `skill` | `skill:default:viewer` | Global |
| `artifact` | `artifact:{id}:viewer` | Per-artifact |
| `memory` | `session:{session_id}:viewer` | Per-session |
| `plan` | `session:{session_id}:viewer` | Per-session |

Users must have `reference:default:viewer` permission to use the reference resolution API.

## Components

| Component | Purpose |
|-----------|---------|
| `ReferenceChip` | Inline reference display |
| `ReferencePopover` | Hover/click details |
| `ReferenceAutocompleteMenu` | Autocomplete dropdown |
| `ToolDisambiguationDialog` | Resolve tool conflicts |
| `SkillVersionWarning` | Version mismatch alerts |
| `BulkReferenceInserter` | Multi-select picker |

## Related

- [MCP Connections](./MCP_CONNECTIONS_FEATURE.md) - Connection management
- [Feature Flags](./feature-flags-mapping.md) - Feature flag reference
- [Design System](./DESIGN_SYSTEM.md) - UI component guidelines
