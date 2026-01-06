# Alert Slice Test Suite

This test suite has been split into multiple shards to maintain files under 1,000 lines and improve test organization.

## Test Files

### `alertSlice.fixtures.ts` (90 lines)
Shared test utilities and fixtures:
- Store factory (`createTestStore`)
- Mock alert factory (`createMockAlert`)
- Mock remediation factory (`createMockRemediation`)
- Alert/Remediation type exports

### `alertSlice.actions.test.ts` (362 lines, 26 tests)
Tests for alert slice actions and reducers:
- addAlert action (prepend, deduplication, lastCriticalAlertTime)
- updateAlert action
- removeAlert action (with selection cleanup)
- setSelectedAlertId action
- Remediation actions (add, update, remove)
- Sound actions (toggle, setSoundEnabled)
- Filter actions (setFilters, merge behavior)
- Clear actions (clearAlerts, clearResolvedAlerts)
- Backend compatibility tests (camelCase transformation)

### `alertSlice.selectors.test.ts` (427 lines, 19 tests)
Tests for alert slice selectors and filtering:
- selectSelectedAlert
- selectCriticalAlertCount
- selectWarningAlertCount
- selectFilteredAlerts (by severity, state, both)
- Alert grouping selectors (Phase 6):
  - selectAlertGroups (group by service+alertname)
  - selectFilteredAlertGroups
  - selectAlertGroupCount
  - Highest severity aggregation
  - Firing state aggregation
  - Most recent alert identification

### `alertSlice.test.ts` (125 lines, 8 tests)
Tests for alert slice localStorage persistence:
- loadSoundPreference
- saveSoundPreference
- toggleSound with persistence
- setSoundEnabled with persistence
- initializeSoundFromStorage action

## Total Coverage
- **53 tests** across 3 shards + main file
- **1,004 lines** total (including fixtures)
- Main file: 125 lines (well under 1,000 line target)
- Average shard size: ~395 lines

## Running Tests

```bash
# Run all alert tests
npm test -- alertSlice --run

# Run specific shard
npm test -- alertSlice.test.ts --run                     # localStorage persistence
npm test -- alertSlice.actions.test.ts --run             # Actions and reducers
npm test -- alertSlice.selectors.test.ts --run           # Selectors and grouping
```

## Test Organization

Tests follow the sessionSlice pattern:
- Shared fixtures extracted to `alertSlice.fixtures.ts`
- Functional grouping by feature area
- All original tests preserved (53 tests total)
- No test behavior changes

## Migration History

**Date**: 2026-01-05
**Original**: `alertSlice.test.ts` (1,348 lines)
**Reason**: Reduce file size to under 1,000 lines
**Strategy**:
1. Extract shared fixtures to `alertSlice.fixtures.ts`
2. Split actions/reducers into `alertSlice.actions.test.ts`
3. Split selectors/grouping into `alertSlice.selectors.test.ts`
4. Keep localStorage tests in main file (125 lines)
