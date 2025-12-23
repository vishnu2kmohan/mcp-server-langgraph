/**
 * Test Cleanup Utilities
 *
 * Provides standardized cleanup patterns to prevent memory leaks and OOM issues.
 * Use these utilities in all test files to ensure proper resource cleanup.
 *
 * @example
 * ```typescript
 * import { vi, beforeEach, afterEach } from "vitest";
 * import { cleanup } from "@testing-library/react";
 * import { standardCleanup, standardBeforeEach } from "@/test/cleanup";
 *
 * describe("MyComponent", () => {
 *   beforeEach(() => {
 *     standardBeforeEach();
 *   });
 *
 *   afterEach(() => {
 *     standardCleanup();
 *   });
 * });
 * ```
 */

import { vi } from "vitest";
import { cleanup } from "@testing-library/react";

/**
 * Standard beforeEach cleanup for all test files.
 * Call this at the start of each test to ensure clean state.
 */
export function standardBeforeEach(): void {
  vi.clearAllMocks();
}

/**
 * Standard afterEach cleanup for all test files.
 * Call this after each test to prevent memory accumulation.
 */
export function standardCleanup(): void {
  // React Testing Library cleanup
  cleanup();

  // Clear all mock state
  vi.clearAllMocks();
  vi.restoreAllMocks();

  // Reset fake timers if they were used
  try {
    // Check if fake timers are active and restore real timers
    // This is wrapped in try-catch as vi.isFakeTimers() may not exist in all versions
    if (typeof vi.isFakeTimers === "function" && vi.isFakeTimers()) {
      vi.useRealTimers();
    }
  } catch {
    // If isFakeTimers doesn't exist, just try to restore timers
    // This is safe even if real timers are already in use
    try {
      vi.useRealTimers();
    } catch {
      // Ignore - timers are already real
    }
  }
}

/**
 * Cleanup for tests using fake timers.
 * Use this instead of standardCleanup when your test uses vi.useFakeTimers().
 */
export function cleanupWithTimers(): void {
  cleanup();
  vi.useRealTimers();
  vi.clearAllMocks();
  vi.restoreAllMocks();
}

/**
 * Setup for tests using fake timers.
 * Call this in beforeEach when your test needs fake timers.
 */
export function setupWithTimers(): void {
  vi.clearAllMocks();
  vi.useFakeTimers();
}

/**
 * Creates a complete test lifecycle object for use with beforeEach/afterEach.
 *
 * @param options.useFakeTimers - Whether to use fake timers (default: false)
 * @param options.customBeforeEach - Additional setup to run in beforeEach
 * @param options.customAfterEach - Additional cleanup to run in afterEach
 *
 * @example
 * ```typescript
 * const lifecycle = createTestLifecycle({ useFakeTimers: true });
 *
 * describe("MyTest", () => {
 *   beforeEach(lifecycle.beforeEach);
 *   afterEach(lifecycle.afterEach);
 * });
 * ```
 */
export function createTestLifecycle(
  options: {
    useFakeTimers?: boolean;
    customBeforeEach?: () => void;
    customAfterEach?: () => void;
  } = {},
): {
  beforeEach: () => void;
  afterEach: () => void;
} {
  const { useFakeTimers = false, customBeforeEach, customAfterEach } = options;

  return {
    beforeEach: () => {
      vi.clearAllMocks();
      if (useFakeTimers) {
        vi.useFakeTimers();
      }
      customBeforeEach?.();
    },
    afterEach: () => {
      customAfterEach?.();
      cleanup();
      if (useFakeTimers) {
        vi.useRealTimers();
      }
      vi.clearAllMocks();
      vi.restoreAllMocks();
    },
  };
}
