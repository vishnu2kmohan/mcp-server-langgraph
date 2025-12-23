/**
 * Test Isolation Utilities
 *
 * Utilities for ensuring proper test isolation between parallel workers
 * and sequential test runs. These help prevent state leakage that causes
 * flaky tests.
 *
 * Usage:
 *   import { clearStorageMocks, clearAllMocks } from './testIsolation';
 *
 *   afterEach(() => {
 *     clearStorageMocks();
 *     clearAllMocks();
 *   });
 */

import { vi } from "vitest";

// =============================================================================
// Types
// =============================================================================

export interface IsolationReport {
  /** Number of items in localStorage */
  localStorageCount: number;
  /** Keys present in localStorage */
  localStorageKeys: string[];
  /** Number of items in sessionStorage */
  sessionStorageCount: number;
  /** Keys present in sessionStorage */
  sessionStorageKeys: string[];
  /** Number of child elements in document.body */
  bodyChildCount: number;
  /** Number of pending timers (only accurate with fake timers) */
  pendingTimers: number;
  /** Whether the environment appears clean */
  isClean: boolean;
}

// =============================================================================
// Storage Isolation
// =============================================================================

/**
 * Clear localStorage and sessionStorage mocks, including their internal stores
 * and mock call history.
 */
export function clearStorageMocks(): void {
  // Clear localStorage
  if (window.localStorage) {
    window.localStorage.clear();
    // Clear mock call history if it's a vi mock
    if (vi.isMockFunction(window.localStorage.setItem)) {
      vi.mocked(window.localStorage.setItem).mockClear();
    }
    if (vi.isMockFunction(window.localStorage.getItem)) {
      vi.mocked(window.localStorage.getItem).mockClear();
    }
    if (vi.isMockFunction(window.localStorage.removeItem)) {
      vi.mocked(window.localStorage.removeItem).mockClear();
    }
    if (vi.isMockFunction(window.localStorage.clear)) {
      vi.mocked(window.localStorage.clear).mockClear();
    }
    if (vi.isMockFunction(window.localStorage.key)) {
      vi.mocked(window.localStorage.key).mockClear();
    }
  }

  // Clear sessionStorage
  if (window.sessionStorage) {
    window.sessionStorage.clear();
    // Clear mock call history if it's a vi mock
    if (vi.isMockFunction(window.sessionStorage.setItem)) {
      vi.mocked(window.sessionStorage.setItem).mockClear();
    }
    if (vi.isMockFunction(window.sessionStorage.getItem)) {
      vi.mocked(window.sessionStorage.getItem).mockClear();
    }
    if (vi.isMockFunction(window.sessionStorage.removeItem)) {
      vi.mocked(window.sessionStorage.removeItem).mockClear();
    }
    if (vi.isMockFunction(window.sessionStorage.clear)) {
      vi.mocked(window.sessionStorage.clear).mockClear();
    }
    if (vi.isMockFunction(window.sessionStorage.key)) {
      vi.mocked(window.sessionStorage.key).mockClear();
    }
  }
}

/**
 * Create an isolated storage instance for testing.
 * Useful when you need a fresh storage that doesn't affect global state.
 */
export function createIsolatedStorage(): Storage {
  let store: Record<string, string> = {};

  const storage: Storage = {
    get length() {
      return Object.keys(store).length;
    },
    clear: vi.fn(() => {
      store = {};
    }),
    getItem: vi.fn((key: string) => store[key] ?? null),
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
  };

  return storage;
}

// =============================================================================
// Mock Isolation
// =============================================================================

/**
 * Clear all vi mock call history without resetting implementations.
 * This is more thorough than vi.clearAllMocks() as it also handles
 * global mocks set up in beforeAll.
 */
export function clearAllMocks(): void {
  vi.clearAllMocks();
}

// =============================================================================
// Timer Isolation
// =============================================================================

/**
 * Clear all pending timers and restore real timers.
 * This prevents timer-related test pollution.
 */
export function clearTimers(): void {
  // Clear any pending timers
  vi.clearAllTimers();

  // Restore real timers to prevent fake timer pollution
  vi.useRealTimers();
}

// =============================================================================
// DOM Isolation
// =============================================================================

/**
 * Clear all modifications to document.body.
 * This removes all child elements and resets body attributes.
 */
export function clearDocumentBody(): void {
  // Remove all child elements
  while (document.body.firstChild) {
    document.body.removeChild(document.body.firstChild);
  }

  // Reset body attributes
  const attributeNames = Array.from(document.body.attributes).map(
    (attr) => attr.name,
  );
  attributeNames.forEach((name) => {
    document.body.removeAttribute(name);
  });

  // Reset className (which isn't an attribute in some contexts)
  document.body.className = "";
}

// =============================================================================
// Isolation Reporting
// =============================================================================

/**
 * Get a report of the current isolation state.
 * Useful for debugging test pollution issues.
 */
export function getIsolationReport(): IsolationReport {
  const localStorageKeys: string[] = [];
  const sessionStorageKeys: string[] = [];

  // Get localStorage keys
  try {
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (key) localStorageKeys.push(key);
    }
  } catch {
    // localStorage may not be available
  }

  // Get sessionStorage keys
  try {
    for (let i = 0; i < window.sessionStorage.length; i++) {
      const key = window.sessionStorage.key(i);
      if (key) sessionStorageKeys.push(key);
    }
  } catch {
    // sessionStorage may not be available
  }

  // Count pending timers (this is an approximation)
  // Vitest's vi.getTimerCount() returns the count when using fake timers
  let pendingTimers = 0;
  try {
    pendingTimers = vi.getTimerCount();
  } catch {
    // Not using fake timers or method not available
  }

  const bodyChildCount = document.body.children.length;

  const isClean =
    localStorageKeys.length === 0 &&
    sessionStorageKeys.length === 0 &&
    bodyChildCount === 0;

  return {
    localStorageCount: localStorageKeys.length,
    localStorageKeys,
    sessionStorageCount: sessionStorageKeys.length,
    sessionStorageKeys,
    bodyChildCount,
    pendingTimers,
    isClean,
  };
}

// =============================================================================
// Comprehensive Cleanup
// =============================================================================

/**
 * Perform comprehensive test cleanup.
 * Call this in afterEach to ensure maximum isolation.
 */
export function fullCleanup(): void {
  clearStorageMocks();
  clearAllMocks();
  clearDocumentBody();
  // Note: We don't call clearTimers() here because it would restore real timers
  // which might not be desired. Call it explicitly if needed.
}

// =============================================================================
// CI Integration
// =============================================================================

export interface LogIsolationWarningOptions {
  /** Force logging even outside CI environment */
  force?: boolean;
}

/**
 * Log a warning if the test isolation state is dirty.
 * By default, only logs in CI environments (process.env.CI === "true").
 * Use the force option to log in any environment.
 *
 * This is useful for detecting test pollution in CI pipelines.
 *
 * @param options - Configuration options
 * @param options.force - Force logging even outside CI
 */
export function logIsolationWarningIfDirty(
  options?: LogIsolationWarningOptions,
): void {
  const isCI = process.env.CI === "true";
  const shouldLog = isCI || options?.force;

  if (!shouldLog) {
    return;
  }

  const report = getIsolationReport();

  if (report.isClean) {
    return;
  }

  // Build warning message with details
  const details: string[] = [];

  if (report.localStorageCount > 0) {
    details.push(
      `localStorage: ${report.localStorageCount} items [${report.localStorageKeys.join(", ")}]`,
    );
  }

  if (report.sessionStorageCount > 0) {
    details.push(
      `sessionStorage: ${report.sessionStorageCount} items [${report.sessionStorageKeys.join(", ")}]`,
    );
  }

  if (report.bodyChildCount > 0) {
    details.push(`document.body: ${report.bodyChildCount} children`);
  }

  if (report.pendingTimers > 0) {
    details.push(`pending timers: ${report.pendingTimers}`);
  }

  const message = `[TestIsolation] Dirty state detected after test:\n  - ${details.join("\n  - ")}`;
  console.warn(message);
}
