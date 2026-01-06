# Workspace Slice Test Suite

This test suite has been split into multiple shards to prevent OOM (Out of Memory) issues during parallel test execution with pytest-xdist.

## Test Files

### `workspaceSlice.fixtures.ts` (148 lines)
Shared test utilities and fixtures:
- Mock state factory (`createMockState`)
- Tab factory (`createTab`)
- Layout factories (`createHorizontalSplit`, `createVerticalSplit`, `createNestedLayout`)
- Test constants (`TEST_ACTIVITIES`, `TEST_BOTTOM_PANEL_TABS`)

### `workspaceSlice.layout.test.ts` (443 lines, 48 tests)
Tests for workspace layout state:
- Initial state
- Left sidebar actions (width, collapsed)
- Right sidebar actions (width, collapsed, pinned)
- Bottom panel actions (height, collapsed, active tab)
- Activity bar actions
- Focus mode actions
- Group expansion actions
- Property section expansion actions
- Scroll position actions
- Reset workspace action
- All layout-related selectors

### `workspaceSlice.tabs.test.ts` (746 lines, 31 tests)
Tests for workspace tab management:
- Dock layout actions (horizontal/vertical splits, nested layouts)
- Tab management (add, remove, reorder, set active)
- removeTabsByEntityId action
- splitTab action (horizontal, vertical, before/after)
- mergeSplits action
- updateSplitSizes action
- moveTabToGroup action and edge cases

### `workspaceSlice.persistence.test.ts` (489 lines, 26 tests)
Tests for workspace state persistence and edge cases:
- loadWorkspaceFromStorage action
- Persistence to localStorage
- workspacePersistenceMiddleware
- noUncheckedIndexedAccess edge cases:
  - reorderTabs with invalid indices
  - Dock layout path traversal
  - updateTabTitle edge cases
  - removeTab edge cases
  - removeTabsByEntityId with empty state
  - splitTab edge cases

## Total Coverage
- **105 tests** across 3 shards
- **1,826 lines** total (including fixtures)
- Average: ~612 lines per shard (excluding fixtures)

## Running Tests

```bash
# Run all workspace tests
npm test -- workspaceSlice --run

# Run specific shard
npm test -- workspaceSlice.layout.test.ts --run
npm test -- workspaceSlice.tabs.test.ts --run
npm test -- workspaceSlice.persistence.test.ts --run
```

## Memory Safety

These tests follow the OOM prevention pattern:
- ✅ Split into smaller shards (< 750 lines each)
- ✅ No `gc` calls needed (frontend tests don't use AsyncMock/MagicMock)
- ✅ Proper cleanup in `afterEach` hooks
- ✅ Shared fixtures to reduce duplication

## Migration History

**Date**: 2026-01-05
**Original**: `workspaceSlice.test.ts` (1,852 lines)
**Reason**: Split to prevent OOM during parallel test execution
**Strategy**: Split by functional area (layout, tabs, persistence)
