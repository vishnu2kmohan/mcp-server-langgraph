# Test Isolation Utilities

**Last Updated**: 2025-12-21
**Location**: `src/test/testIsolation.ts`

## Overview

Test isolation utilities ensure proper cleanup between parallel workers and sequential test runs, preventing state leakage that causes flaky tests.

## Quick Start

The isolation utilities are automatically integrated into `src/test/setup.ts` and run after each test:

```typescript
// Already configured in setup.ts - no action needed for most tests
afterEach(() => {
  cleanup();           // React Testing Library
  clearStorageMocks(); // localStorage, sessionStorage
  clearAllMocks();     // vi mock call history
});
```

## Available Functions

### Storage Isolation

#### `clearStorageMocks()`

Clears localStorage and sessionStorage, including their internal stores and mock call history.

```typescript
import { clearStorageMocks } from "../test/testIsolation";

afterEach(() => {
  clearStorageMocks();
});
```

**What it clears:**
- All localStorage items
- All sessionStorage items
- Mock call history for `setItem`, `getItem`, `removeItem`, `clear`, `key`

#### `createIsolatedStorage()`

Creates an independent storage instance for testing. Useful when you need a fresh storage that doesn't affect global state.

```typescript
import { createIsolatedStorage } from "../test/testIsolation";

it("should persist user preferences", () => {
  const storage = createIsolatedStorage();

  storage.setItem("theme", "dark");
  expect(storage.getItem("theme")).toBe("dark");
  expect(storage.length).toBe(1);

  // Won't affect window.localStorage
  expect(window.localStorage.getItem("theme")).toBeNull();
});
```

**Features:**
- Full Storage interface (`length`, `setItem`, `getItem`, `key`, `removeItem`, `clear`)
- Trackable mock functions for assertions
- Independent from `window.localStorage` / `window.sessionStorage`

### Mock Isolation

#### `clearAllMocks()`

Clears all vi mock call history without resetting implementations.

```typescript
import { clearAllMocks } from "../test/testIsolation";

const mockFn = vi.fn().mockReturnValue("value");
mockFn();

clearAllMocks();

expect(mockFn).toHaveBeenCalledTimes(0);
expect(mockFn()).toBe("value"); // Implementation still works
```

### Timer Isolation

#### `clearTimers()`

Clears all pending timers and restores real timers.

```typescript
import { clearTimers } from "../test/testIsolation";

vi.useFakeTimers();
setTimeout(() => { /* leaked timer */ }, 1000);

clearTimers();

// Back to real timers, pending callbacks cleared
```

**Use cases:**
- Tests that use `vi.useFakeTimers()`
- Cleaning up after animation tests
- Preventing timer pollution between tests

### DOM Isolation

#### `clearDocumentBody()`

Removes all child elements and resets body attributes.

```typescript
import { clearDocumentBody } from "../test/testIsolation";

// After a test that modifies the DOM
clearDocumentBody();

expect(document.body.children.length).toBe(0);
expect(document.body.className).toBe("");
```

**What it clears:**
- All child elements
- All attributes (including `data-*` attributes)
- `className`

### Comprehensive Cleanup

#### `fullCleanup()`

Performs comprehensive test cleanup (storage, mocks, and DOM).

```typescript
import { fullCleanup } from "../test/testIsolation";

afterEach(() => {
  fullCleanup();
});
```

**Note:** Does not clear timers automatically. Call `clearTimers()` explicitly if needed.

## Isolation Reporting

### `getIsolationReport()`

Returns a detailed report of the current isolation state. Useful for debugging test pollution.

```typescript
import { getIsolationReport } from "../test/testIsolation";

const report = getIsolationReport();
console.log(report);
// {
//   localStorageCount: 2,
//   localStorageKeys: ["theme", "user"],
//   sessionStorageCount: 0,
//   sessionStorageKeys: [],
//   bodyChildCount: 1,
//   pendingTimers: 0,
//   isClean: false
// }
```

**Report fields:**
| Field | Description |
|-------|-------------|
| `localStorageCount` | Number of items in localStorage |
| `localStorageKeys` | Array of localStorage keys |
| `sessionStorageCount` | Number of items in sessionStorage |
| `sessionStorageKeys` | Array of sessionStorage keys |
| `bodyChildCount` | Number of child elements in document.body |
| `pendingTimers` | Number of pending timers (fake timers only) |
| `isClean` | `true` if all counts are 0 |

### `logIsolationWarningIfDirty(options?)`

Logs a warning if the test isolation state is dirty. By default, only logs in CI environments.

```typescript
import { logIsolationWarningIfDirty } from "../test/testIsolation";

// In afterEach (CI only - automatically skipped locally)
afterEach(() => {
  logIsolationWarningIfDirty();
});

// Force logging in local development
afterEach(() => {
  logIsolationWarningIfDirty({ force: true });
});
```

**Options:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `force` | `boolean` | `false` | Log warning even outside CI |

**Example output:**
```
[TestIsolation] Dirty state detected after test:
  - localStorage: 2 items [theme, user]
  - document.body: 3 children
```

## CI Integration

The isolation warning is designed for CI pipelines to detect test pollution:

1. **Automatic in CI**: When `process.env.CI === "true"`, warnings are logged automatically
2. **Silent locally**: No warnings in local development by default
3. **Force mode**: Use `{ force: true }` to debug locally

### Recommended CI Setup

```typescript
// In src/test/setup.ts
import { clearStorageMocks, clearAllMocks, logIsolationWarningIfDirty } from "./testIsolation";

afterEach(() => {
  cleanup();
  clearStorageMocks();
  clearAllMocks();
  logIsolationWarningIfDirty(); // Warns in CI if dirty
});
```

## Common Issues

### Issue: localStorage leaking between tests

**Symptom:** Tests pass individually but fail in parallel or sequence.

**Solution:**
```typescript
afterEach(() => {
  clearStorageMocks();
});
```

### Issue: DOM elements accumulating

**Symptom:** Multiple test elements rendered, conflicting selectors.

**Solution:**
```typescript
afterEach(() => {
  cleanup();           // React Testing Library
  clearDocumentBody(); // Extra cleanup if needed
});
```

### Issue: Fake timers affecting other tests

**Symptom:** Time-based tests fail unpredictably.

**Solution:**
```typescript
afterEach(() => {
  clearTimers(); // Restores real timers
});
```

### Issue: Mock assertions polluted by previous tests

**Symptom:** `toHaveBeenCalled()` assertions fail unexpectedly.

**Solution:**
```typescript
afterEach(() => {
  clearAllMocks();
});
```

## TypeScript Types

```typescript
export interface IsolationReport {
  localStorageCount: number;
  localStorageKeys: string[];
  sessionStorageCount: number;
  sessionStorageKeys: string[];
  bodyChildCount: number;
  pendingTimers: number;
  isClean: boolean;
}

export interface LogIsolationWarningOptions {
  force?: boolean;
}
```

## Related Files

- `src/test/setup.ts` - Global test setup (uses these utilities)
- `src/test/memoryMonitor.ts` - Memory leak detection
- `src/test/testIsolation.test.ts` - Unit tests for isolation utilities
