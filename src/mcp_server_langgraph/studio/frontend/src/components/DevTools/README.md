# DevTools Panel

A Chrome DevTools-inspired debugging panel for Agent Studio that provides context-aware debugging, AI-powered insights, and unified observability.

## Features

- **Context-Aware Tabs**: Adapts displayed tabs based on whether you're debugging a chat session or workflow
- **AI-Powered Insights**: Uses Multi-Agent Orchestrator for intelligent layout suggestions and anomaly detection
- **Unified Observability**: Consolidates 8+ scattered observability components into a single panel
- **Keyboard Navigation**: Full keyboard support with familiar shortcuts

## Quick Start

### Opening DevTools

- **Keyboard**: `Cmd+Shift+I` (Mac) or `Ctrl+Shift+I` (Windows/Linux)
- **Status Bar**: Click the terminal icon in the status bar
- **Default**: Open by default for developer/admin personas, collapsed for users

### Tabs Overview

| Tab | Description | Contexts |
|-----|-------------|----------|
| Console | Logs, notifications, API calls, errors | All |
| Problems | Aggregated errors and warnings | All |
| Network | API and WebSocket monitoring | All |
| State | Redux/session/workflow state inspection | All |
| Agent Trace | LangGraph node visualization | Session |
| Execution Trace | Workflow node execution | Workflow |
| AI Insights | Anomalies, bottlenecks, suggestions | All (behind flag) |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd+Shift+I` | Toggle DevTools panel |
| `Cmd+Shift+C` | Focus Console tab |
| `Cmd+K` | Clear Console (when Console focused) |
| `Cmd+]` | Next tab |
| `Cmd+[` | Previous tab |

## Architecture

```
DevToolsPanel
├── DevToolsHeader
│   ├── ContextIndicator ("Session: chat-123" | "Workflow: flow-456")
│   ├── TabBar (context-aware tabs)
│   └── Actions [Clear, AI Toggle, Maximize, Collapse]
└── TabContent (lazy-loaded)
    ├── ConsoleTab
    ├── ProblemsTab
    ├── NetworkTab
    ├── StateTab
    ├── AgentTraceTab (session context)
    ├── ExecutionTraceTab (workflow context)
    └── AIInsightsTab (behind feature flag)
```

## Component Structure

```
src/components/DevTools/
├── index.ts                    # Public exports
├── types.ts                    # TypeScript types
├── lazy.ts                     # Lazy loading configuration
├── DevToolsPanel.tsx           # Main panel component
├── DevToolsPanel.test.tsx      # Tests
├── DevToolsHeader.tsx          # Header with tabs and actions
├── DevToolsTabs.tsx            # Tab bar component
├── CONSOLIDATION.md            # Migration guide from old components
├── hooks/
│   ├── useDevToolsContext.ts   # Context detection (session/workflow/global)
│   ├── useDevToolsKeyboard.ts  # Keyboard shortcuts
│   ├── useDevToolsAI.ts        # AI layout suggestions
│   ├── useDevToolsResize.ts    # Panel resize handling
│   ├── useConsoleEntries.ts    # Console log aggregation
│   ├── useNetworkEntries.ts    # Network request tracking
│   ├── useProblems.ts          # Error aggregation
│   ├── useAgentTrace.ts        # LangGraph trace data
│   └── useWorkflowExecution.ts # Workflow execution data
└── tabs/
    ├── ConsoleTab.tsx          # Console logs with filtering
    ├── ProblemsTab.tsx         # Error/warning aggregation
    ├── NetworkTab.tsx          # API/WebSocket monitoring
    ├── StateTab.tsx            # Redux state inspection
    ├── AgentTraceTab.tsx       # LangGraph visualization
    ├── ExecutionTraceTab.tsx   # Workflow execution
    └── AIInsightsTab.tsx       # AI-powered insights
```

## Redux State

The DevTools panel uses the `devToolsSlice` for state management:

```typescript
interface DevToolsState {
  collapsed: boolean;       // Panel visibility
  height: number;           // Panel height (150-400px)
  maximized: boolean;       // Fullscreen mode
  activeTab: DevToolsTabId; // Currently active tab
  detectedContext: 'session' | 'workflow' | 'global';
  contextEntityId: string | null;
  consoleFilter: 'all' | 'info' | 'warning' | 'error';
  aiInsightsEnabled: boolean;
  aiSuggestedLayout: DevToolsTabId[] | null;
}
```

### Selectors

```typescript
import {
  selectDevToolsCollapsed,
  selectActiveTab,
  selectAvailableTabs,
  selectConsoleFilter,
  selectDetectedContext,
} from '@/store/slices/devToolsSlice';
```

### Actions

```typescript
import {
  toggleDevTools,
  setActiveTab,
  setHeight,
  setConsoleFilter,
  setDetectedContext,
  applyAILayout,
} from '@/store/slices/devToolsSlice';
```

## Feature Flags

DevTools functionality is controlled by backend feature flags:

| Flag | Default | Description |
|------|---------|-------------|
| `devtools_panel` | `true` | Master toggle for DevTools panel |
| `devtools_ai_insights` | `false` | Enable AI Insights tab |
| `devtools_ai_layout` | `false` | Enable AI layout suggestions |
| `devtools_network_tab` | `true` | Enable Network tab |

### Checking Feature Flags

```typescript
import { useFeatureFlags } from '@/hooks/useFeatureFlags';

function MyComponent() {
  const { devtools_panel, devtools_ai_insights } = useFeatureFlags();

  if (!devtools_panel) return null;
  // ...
}
```

## Console Tab

The Console tab aggregates logs from multiple sources:

### Sources

- **System**: Application lifecycle events
- **API**: HTTP request/response logs
- **MCP**: MCP protocol messages
- **Notification**: User notifications
- **Execution**: Agent execution logs
- **WebSocket**: WebSocket messages

### Filtering

```typescript
// Filter by level
<ConsoleTab filter="error" />

// Filter by source
<ConsoleTab sources={['api', 'mcp']} />
```

### Custom Entries

```typescript
import { useConsoleEntries } from './hooks/useConsoleEntries';

const { addEntry } = useConsoleEntries();

addEntry({
  level: 'info',
  source: 'custom',
  message: 'Custom log message',
  data: { key: 'value' },
});
```

## State Tab

The State tab provides Redux state inspection:

### Context-Aware State

- **Session Context**: Shows `session` and `canvas` slices
- **Workflow Context**: Shows workflow-related state
- **Global Context**: Shows all Redux state

### Search

Use the search input to filter state by:
- Key names
- Path names
- Primitive values

## Agent Trace Tab

Displays LangGraph agent execution traces:

### Node Visualization

- Shows execution order of LangGraph nodes
- Color-coded status (completed, running, pending, error, skipped)
- Duration display for each node

### Views

- **List View**: Expandable list with details
- **Timeline View**: Gantt chart-style visualization

### Token Usage

Displays input, output, and total token counts.

## AI Insights Tab

Requires `devtools_ai_insights` feature flag.

### Features

- **Anomaly Detection**: Identifies unusual patterns in traces
- **Bottleneck Analysis**: Finds performance bottlenecks
- **Health Score**: Overall execution health metric
- **Cost Projection**: Estimated costs based on usage
- **Optimization Suggestions**: AI-generated recommendations

## Integration with StudioShellLayout

DevTools is integrated into the StudioShellLayout:

```tsx
// In StudioShellLayout.tsx
<PanelGroup direction="vertical">
  <Panel id="main-content" defaultSize={devToolsCollapsed ? 100 : 80}>
    {/* Main content */}
  </Panel>

  {!devToolsCollapsed && (
    <>
      <ResizeHandle vertical />
      <Panel id="devtools" defaultSize={20} minSize={10} maxSize={50}>
        <DevToolsPanel />
      </Panel>
    </>
  )}
</PanelGroup>
```

## Testing

### Unit Tests

```bash
# Run DevTools tests
npm test -- --filter=DevTools

# Run specific tab tests
npm test -- src/components/DevTools/tabs/ConsoleTab.test.tsx
```

### E2E Tests

```bash
# Run DevTools E2E tests
npm run e2e -- e2e/devtools-integration.spec.ts
```

## Accessibility

- **Keyboard Navigation**: Full keyboard support for tab switching
- **ARIA Labels**: Proper labels for all interactive elements
- **Focus Management**: Logical focus order within the panel
- **Screen Reader Support**: Semantic HTML structure

## Performance

### Lazy Loading

Tabs are lazy-loaded to reduce initial bundle size:

```typescript
// In lazy.ts
export const ConsoleTab = lazy(() => import('./tabs/ConsoleTab'));
export const NetworkTab = lazy(() => import('./tabs/NetworkTab'));
// ...
```

### Virtualization

Long lists (console entries, network requests) use virtualization for performance.

### Memoization

Heavy computations are memoized to prevent unnecessary re-renders.

## Migration from Legacy Components

See [CONSOLIDATION.md](./CONSOLIDATION.md) for detailed migration guide from:

- `Layout/ActivityLog.tsx` -> `ConsoleTab`
- `Layout/ProblemsPanel.tsx` -> `ProblemsTab`
- `Layout/InspectorPanel.tsx` -> `StateTab`
- `Chat/AgentExecutionTracePanel.tsx` -> `AgentTraceTab`
- `Observability/TraceViewer.tsx` -> `AgentTraceTab`
- `Workflow/ExecutionTracePanel.tsx` -> `ExecutionTraceTab`
