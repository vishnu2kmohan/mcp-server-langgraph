# Pages Test Suite

This directory contains split test files for page components. The tests have been organized into separate files by tab/concern to:

1. **Prevent OOM (Out of Memory)** issues during test runs
2. **Improve test isolation** and parallel execution
3. **Enhance maintainability** by grouping related tests
4. **Reduce context switching** for developers

---

## ObservabilityPage Test Suite

### File Structure

```
__tests__/
├── ObservabilityPage.setup.ts                   # Shared mocks, utilities, and fixtures
├── ObservabilityPage.core.test.tsx              # Header, tabs, URL sync, loading/error
├── ObservabilityPage.sessions.test.tsx          # Agent Sessions + Workflow Runs tabs
├── ObservabilityPage.traces.test.tsx            # Traces tab, pagination, filters
├── ObservabilityPage.traces-intelligence.test.tsx # AI-powered trace analysis
├── ObservabilityPage.logs.test.tsx              # Logs tab display and edge cases
├── ObservabilityPage.metrics.test.tsx           # Metrics tab display
└── ObservabilityPage.alerts.test.tsx            # Alerts tab, filters, edge cases
```

### Test Categories

| File | Tests | Description |
|------|-------|-------------|
| `core.test.tsx` | ~22 | Header, tabs, URL sync, loading/error states |
| `sessions.test.tsx` | ~9 | Agent Sessions + Workflow Runs tabs |
| `traces.test.tsx` | ~30 | Traces display, pagination, filters, selection |
| `traces-intelligence.test.tsx` | ~12 | AI summaries, anomalies, health scores |
| `logs.test.tsx` | ~10 | Logs display, level badges, edge cases |
| `metrics.test.tsx` | ~10 | Metrics display, empty state |
| `alerts.test.tsx` | ~27 | Alerts display, severity, state, filters |

**Total: ~120 tests** across 7 split files (down from 3,189 line monolith)

---

## ProjectDetailPage Test Suite

### File Structure

```
__tests__/
├── ProjectDetailPage.setup.ts                   # Shared mocks, utilities, and fixtures
├── ProjectDetailPage.core.test.tsx              # Loading, error, details, tabs, RTK Query
├── ProjectDetailPage.sessions.test.tsx          # Sessions tab, New Session, Remove Session
├── ProjectDetailPage.workflows.test.tsx         # Workflows tab, New Workflow, Remove Workflow
├── ProjectDetailPage.connections.test.tsx       # Connections tab, Add Connection
├── ProjectDetailPage.observability.test.tsx     # Observability tab, logs, alerts, errors
├── ProjectDetailPage.cost.test.tsx              # Cost tab, real data, error handling
├── ProjectDetailPage.members.test.tsx           # Members tab, Add/Remove Member
└── ProjectDetailPage.feature-flags.test.tsx     # Feature flag integration tests
```

### Test Categories

| File | Tests | Description |
|------|-------|-------------|
| `core.test.tsx` | ~20 | Loading, error, project details, tab navigation, RTK Query |
| `sessions.test.tsx` | ~10 | Sessions display, New Session dialog, Remove Session |
| `workflows.test.tsx` | ~8 | Workflows display, New Workflow dialog, Remove Workflow |
| `connections.test.tsx` | ~5 | Connections display, Add Connection dialog |
| `observability.test.tsx` | ~15 | Observability metrics, logs, alerts, error handling |
| `cost.test.tsx` | ~12 | Cost summary, model breakdown, error handling |
| `members.test.tsx` | ~10 | Members display, Add/Remove Member, role options |
| `feature-flags.test.tsx` | ~7 | Tab visibility based on feature flags |

**Total: ~87 tests** across 8 split files (down from 2,586 line monolith)

---

## Shared Setup Files

### ObservabilityPage.setup.ts

```typescript
import {
  mockTraces,
  mockLogs,
  mockMetrics,
  mockAlerts,
  mockSessions,
  mockWorkflows,
  mockRefetchTraces,
  mockRefetchLogs,
  resetAllMocks,
  setupDefaultMocks,
  mockTraceSummary,
  mockTraceAnomaly,
} from "./ObservabilityPage.setup";
```

### ProjectDetailPage.setup.ts

```typescript
import {
  mockProject,
  mockEmptyProject,
  mockObservabilityData,
  mockCostSummaryData,
  mockCostByModelData,
  mockRefetch,
  mockAddMember,
  mockRemoveMember,
  mockAddConnection,
  resetAllMocks,
  setupDefaultMocks,
  renderWithRouter,
} from "./ProjectDetailPage.setup";
```

---

## Running Tests

```bash
# Run all page split tests
npm test -- --run src/pages/__tests__/

# Run specific page tests
npm test -- --run src/pages/__tests__/ObservabilityPage
npm test -- --run src/pages/__tests__/ProjectDetailPage

# Run specific category
npm test -- --run src/pages/__tests__/ProjectDetailPage.sessions.test.tsx

# Run with coverage
npm test -- --run src/pages/__tests__/ --coverage
```

---

## Memory Optimization

The split test pattern prevents OOM issues by:

1. **Smaller per-file memory footprint**: Each file loads independently
2. **Shared mock infrastructure**: Reduces duplicate object creation
3. **Proper cleanup**: `afterEach` ensures no memory leaks
4. **Parallel execution**: Files can run in separate Vitest workers

---

## Original Files

The original monolith test files should be deleted after verifying all tests pass in the shard files:

- `ObservabilityPage.test.tsx` (3,189 lines) → 7 shard files
- `ProjectDetailPage.test.tsx` (2,586 lines) → 8 shard files
