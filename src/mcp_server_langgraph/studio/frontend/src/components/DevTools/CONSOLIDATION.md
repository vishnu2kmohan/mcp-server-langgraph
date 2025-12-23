# DevTools Component Consolidation

This document tracks the consolidation of observability components into the unified DevTools panel.

## Component Mapping

| Original Component | DevTools Tab | Status | Notes |
|-------------------|--------------|--------|-------|
| `Layout/ActivityLog.tsx` | `ConsoleTab` | **Superseded** | ConsoleTab provides enhanced functionality with filtering, sources, and structured data |
| `Layout/ProblemsPanel.tsx` | `ProblemsTab` | **Superseded** | ProblemsTab aggregates more error sources with severity filtering |
| `Layout/InspectorPanel.tsx` | `StateTab` | **Superseded** | StateTab provides Redux state inspection with search and tree view |
| `Chat/AgentExecutionTracePanel.tsx` | `AgentTraceTab` | **Wrapped** | AgentTraceTab uses trace hook; consider using in chat context |
| `Observability/TraceViewer.tsx` | `AgentTraceTab` | **Superseded** | Functionality merged into AgentTraceTab |
| `Workflow/ExecutionTracePanel.tsx` | `ExecutionTraceTab` | **Wrapped** | ExecutionTraceTab wraps workflow execution trace |
| `devtools/TelemetryViewer.tsx` | `ConsoleTab` | **Superseded** | Telemetry data now flows through ConsoleTab |

## Migration Guide

### For ActivityLog Users

Before:
```tsx
import { ActivityLog } from '@/components/Layout/ActivityLog';

<ActivityLog maxItems={50} compact />
```

After (when using DevTools):
```tsx
// DevTools ConsoleTab is automatically available in StudioShellLayout
// No manual import needed - use keyboard shortcut Cmd+Shift+I
```

### For ProblemsPanel Users

Before:
```tsx
import { ProblemsPanel } from '@/components/Layout/ProblemsPanel';

<ProblemsPanel showCount compact />
```

After:
```tsx
// Problems are automatically aggregated in DevTools ProblemsTab
// Access via DevTools panel or status bar problem count
```

### For AgentExecutionTracePanel Users

The AgentExecutionTracePanel is still available for inline usage in chat messages.
For dedicated trace inspection, use the DevTools AgentTraceTab.

```tsx
// Inline usage (unchanged)
import { AgentExecutionTracePanel } from '@/components/Chat/AgentExecutionTracePanel';

// DevTools usage (new)
// AgentTraceTab automatically displays when viewing a session with trace data
```

## Deprecation Timeline

1. **Phase 1 (Current)**: Both old and new components coexist
2. **Phase 2**: Old components marked as deprecated with console warnings
3. **Phase 3**: Old components become thin wrappers around DevTools tabs
4. **Phase 4**: Old components removed, only DevTools tabs remain

## Feature Comparison

### ConsoleTab vs ActivityLog

| Feature | ActivityLog | ConsoleTab |
|---------|------------|------------|
| Notification display | ✓ | ✓ |
| Level filtering | ✗ | ✓ |
| Source filtering | ✗ | ✓ |
| Structured data view | ✗ | ✓ |
| Copy to clipboard | ✗ | ✓ |
| Clear console | ✗ | ✓ |
| Keyboard navigation | ✗ | ✓ |
| Auto-scroll | ✗ | ✓ |

### ProblemsTab vs ProblemsPanel

| Feature | ProblemsPanel | ProblemsTab |
|---------|--------------|-------------|
| Session errors | ✓ | ✓ |
| MCP errors | ✓ | ✓ |
| Validation errors | ✗ | ✓ |
| API errors | ✗ | ✓ |
| Severity filtering | ✗ | ✓ |
| Error details | ✗ | ✓ |
| Copy error | ✗ | ✓ |

### StateTab vs InspectorPanel

| Feature | InspectorPanel | StateTab |
|---------|---------------|----------|
| State display | ✓ | ✓ |
| Tree view | ✗ | ✓ |
| Search | ✗ | ✓ |
| Context-aware | ✗ | ✓ |
| Expand/collapse | ✗ | ✓ |
| Path display | ✗ | ✓ |
