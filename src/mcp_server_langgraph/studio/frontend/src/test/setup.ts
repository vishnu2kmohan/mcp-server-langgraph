/**
 * Vitest test setup file
 *
 * This file runs before each test file and sets up:
 * - Testing library matchers
 * - Browser API mocks
 * - MSW server for realistic API mocking
 * - Memory monitoring for leak detection
 * - Global test utilities
 *
 * =============================================================================
 * BEST PRACTICES FOR MOCKING GLOBAL FUNCTIONS (fetch, etc.)
 * =============================================================================
 *
 * When testing code that uses global functions like `fetch`, prefer vi.spyOn
 * over direct assignment to properly intercept calls:
 *
 * PREFERRED (works with wrappers like authenticatedFetch):
 *   const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue({...} as Response);
 *
 * AVOID (may not intercept if module captures reference at import time):
 *   global.fetch = vi.fn().mockResolvedValue({...});
 *
 * Why: Modules like `authenticatedFetch` may capture the reference to `fetch`
 * at import time. Direct assignment after module load doesn't intercept these.
 * vi.spyOn properly intercepts the function regardless of when it was imported.
 *
 * See: StudioShellLayout.test.tsx "AI Interpretation Fetch Verification" tests
 * =============================================================================
 */

import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll, vi, expect } from "vitest";
import { cleanup } from "@testing-library/react";
import { server } from "../mocks/server";
import { toHaveNoViolations } from "jest-axe";
import { memoryMonitor } from "./memoryMonitor";
import {
  clearStorageMocks,
  clearAllMocks,
  logIsolationWarningIfDirty,
} from "./testIsolation";
import { MemoryTrendReporter } from "./memoryTrendReporter";

// Memory trend reporter for CI integration
const memoryTrendReporter = new MemoryTrendReporter({
  commit: process.env.GITHUB_SHA?.slice(0, 8),
  branch: process.env.GITHUB_REF_NAME,
  testSuite: "frontend",
});

// Extend Vitest's expect with jest-axe matchers
expect.extend(toHaveNoViolations);

// =============================================================================
// Memory Monitoring (enable with DEBUG=true or VITEST_MEMORY_MONITOR=true)
// =============================================================================
// Take a snapshot at test suite start for overall memory tracking
beforeAll(() => {
  memoryMonitor.snapshot("suite-start");

  // Also record for CI trend tracking
  if (typeof process !== "undefined" && process.memoryUsage) {
    memoryTrendReporter.recordEntry("suite-start", process.memoryUsage());
  }
});

// Report memory usage at end if there's significant growth
afterAll(() => {
  memoryMonitor.snapshot("suite-end");
  const result = memoryMonitor.checkThresholds();

  // Log warnings if any thresholds exceeded
  if (result.warnings.length > 0) {
    console.warn("[MemoryMonitor] Warnings:", result.warnings);
  }
  if (result.errors.length > 0) {
    console.error("[MemoryMonitor] Errors:", result.errors);
  }

  // In verbose mode, always print the full report
  if (process.env.VITEST_MEMORY_VERBOSE === "true") {
    console.log(memoryMonitor.generateReport());
  }

  // Record final memory for CI trend tracking and output if in CI
  if (typeof process !== "undefined" && process.memoryUsage) {
    memoryTrendReporter.recordEntry("suite-end", process.memoryUsage());

    // Output memory trend data for CI to capture
    if (
      process.env.CI === "true" ||
      process.env.VITEST_MEMORY_TREND === "true"
    ) {
      const report = memoryTrendReporter.generateReport();
      // Output as a special marker that CI can grep for
      console.log("::memory-trend-start::");
      console.log(JSON.stringify(report, null, 2));
      console.log("::memory-trend-end::");
    }
  }
});

// =============================================================================
// Global Error Handlers to Prevent Worker Crashes
// =============================================================================
// Prevent unhandled promise rejections from crashing the test worker.
// These often happen with AbortSignal errors from MSW v2 / jsdom incompatibility.
process.on("unhandledRejection", (reason) => {
  // Silently ignore AbortSignal-related errors (known MSW v2 issue)
  const message = String(reason);
  if (
    message.includes("AbortSignal") ||
    message.includes("RequestInit: Expected signal") ||
    // jsdom 27 / CSS-in-JS compatibility (Stitches, Sandpack)
    message.includes("Failed to parse the rule")
  ) {
    return; // Ignore these known issues
  }
  // Log other unhandled rejections but don't crash
  console.warn("Unhandled Rejection (suppressed):", reason);
});

// Similarly handle uncaught exceptions
process.on("uncaughtException", (error) => {
  const message = String(error);
  if (
    message.includes("AbortSignal") ||
    message.includes("RequestInit: Expected signal") ||
    // jsdom 27 / CSS-in-JS compatibility (Stitches, Sandpack)
    message.includes("Failed to parse the rule")
  ) {
    return;
  }
  console.warn("Uncaught Exception (suppressed):", error);
});

// =============================================================================
// MSW Server Setup
// =============================================================================
// NOTE: There are known AbortSignal compatibility warnings in stderr when using
// MSW v2 with Node.js native fetch and RTK Query. This is a type mismatch
// between jsdom's AbortSignal and Node.js's internal undici validation.
// See: https://github.com/mswjs/msw/issues/1644
//
// These warnings do NOT affect test functionality - tests pass correctly.
// The warnings occur in MSW's interceptor before any fetch wrapper can help.

// Start MSW server before all tests
beforeAll(() => {
  server.listen({
    // Warn about unhandled requests instead of erroring
    // This allows tests that mock their own endpoints to work
    onUnhandledRequest: "warn",
  });
});

// Reset handlers after each test to ensure test isolation
afterEach(() => {
  server.resetHandlers();
});

// Close server after all tests
afterAll(() => {
  server.close();
});

// =============================================================================
// Test Isolation Cleanup
// =============================================================================
// Comprehensive cleanup after each test to prevent state leakage between tests.
// This is critical for test reliability in parallel execution.
afterEach(() => {
  // React Testing Library cleanup (unmounts components)
  cleanup();

  // Clear storage mocks (localStorage, sessionStorage) - prevents data leakage
  clearStorageMocks();

  // Clear all mock call history - prevents assertion pollution
  clearAllMocks();

  // Log isolation warnings in CI if state is dirty (helps debug flaky tests)
  logIsolationWarningIfDirty();

  // Force garbage collection if available (helps prevent OOM in large test suites)
  // Requires running node with --expose-gc flag
  if (typeof global.gc === "function") {
    global.gc();
  }
});

// =============================================================================
// jsdom 27 CSS Compatibility Workaround
// =============================================================================
// jsdom 27 uses @acemir/cssom which has stricter CSS parsing and fails on
// certain CSS-in-JS library syntax (e.g., Stitches uses '--sxs{--sxs:6}').
// We need to patch the CSSOM module's insertRule method.

// This runs immediately (not in beforeAll) to patch before any imports happen
(() => {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const cssom = require("@acemir/cssom");
    if (cssom?.CSSStyleSheet?.prototype?.insertRule) {
      const originalInsertRule = cssom.CSSStyleSheet.prototype.insertRule;
      cssom.CSSStyleSheet.prototype.insertRule = function (
        rule: string,
        index?: number,
      ): number {
        try {
          return originalInsertRule.call(this, rule, index);
        } catch (error) {
          // Silently ignore CSS-in-JS library internal rules that jsdom can't parse
          if (
            error instanceof Error &&
            error.message.includes("Failed to parse the rule")
          ) {
            return index ?? 0;
          }
          throw error;
        }
      };
    }
  } catch {
    // cssom module not found - not an issue, jsdom might use native implementation
  }
})();

// Also patch the native CSSStyleSheet for completeness
beforeAll(() => {
  const originalInsertRule = CSSStyleSheet.prototype.insertRule;
  CSSStyleSheet.prototype.insertRule = function (
    rule: string,
    index?: number,
  ): number {
    try {
      return originalInsertRule.call(this, rule, index);
    } catch (error) {
      // Silently ignore CSS-in-JS library internal rules that jsdom can't parse
      // These are typically harmless tracking rules like '--sxs{--sxs:X}'
      if (
        error instanceof Error &&
        error.message.includes("Failed to parse the rule")
      ) {
        return index ?? 0;
      }
      throw error;
    }
  };
});

// Mock ResizeObserver
// Vitest 4 requires class/function syntax for constructor mocks (arrow functions don't work with `new`)
beforeAll(() => {
  class MockResizeObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
  }
  global.ResizeObserver =
    MockResizeObserver as unknown as typeof ResizeObserver;
});

// =============================================================================
// Mock getBoundingClientRect for Chart Components
// =============================================================================
// recharts ResponsiveContainer uses getBoundingClientRect to measure container
// dimensions. jsdom returns 0 for all dimensions by default, causing -1 width/height
// errors. We mock getBoundingClientRect to return sensible defaults.
beforeAll(() => {
  const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
  Element.prototype.getBoundingClientRect = function () {
    const rect = originalGetBoundingClientRect.call(this);
    // If jsdom returned 0 dimensions (no layout), provide sensible defaults
    if (rect.width === 0 && rect.height === 0) {
      return {
        ...rect,
        width: 800,
        height: 400,
        top: 0,
        left: 0,
        right: 800,
        bottom: 400,
        x: 0,
        y: 0,
      };
    }
    return rect;
  };
});

// Mock window.matchMedia
beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
});

// =============================================================================
// localStorage Mock (runs immediately before any module imports)
// =============================================================================
// Must be synchronous and at module level because authSlice accesses
// localStorage at import time, before any beforeAll hooks run.
(() => {
  let store: Record<string, string> = {};
  const localStorageMock: Storage = {
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
  Object.defineProperty(window, "localStorage", {
    value: localStorageMock,
    writable: true,
    configurable: true,
  });
})();

// =============================================================================
// sessionStorage Mock (runs immediately before any module imports)
// =============================================================================
// Same pattern as localStorage for consistency.
(() => {
  let store: Record<string, string> = {};
  const sessionStorageMock: Storage = {
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
  Object.defineProperty(window, "sessionStorage", {
    value: sessionStorageMock,
    writable: true,
    configurable: true,
  });
})();

// Mock scrollTo
beforeAll(() => {
  window.scrollTo = vi.fn();
});

// Mock IntersectionObserver
// Vitest 4 requires class/function syntax for constructor mocks (arrow functions don't work with `new`)
beforeAll(() => {
  class MockIntersectionObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
    root = null;
    rootMargin = "";
    thresholds: number[] = [];
    takeRecords = vi.fn(() => []);
  }
  global.IntersectionObserver =
    MockIntersectionObserver as unknown as typeof IntersectionObserver;
});

// =============================================================================
// Service Worker Mock
// =============================================================================
// jsdom doesn't support service workers. Mock navigator.serviceWorker to prevent
// crashes when PWA code tries to register/unregister service workers.
beforeAll(() => {
  const mockServiceWorkerContainer = {
    register: vi.fn().mockResolvedValue({
      installing: null,
      waiting: null,
      active: null,
      scope: "/",
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
      update: vi.fn().mockResolvedValue(undefined),
      unregister: vi.fn().mockResolvedValue(true),
    }),
    getRegistration: vi.fn().mockResolvedValue(undefined),
    getRegistrations: vi.fn().mockResolvedValue([]),
    ready: Promise.resolve({
      installing: null,
      waiting: null,
      active: null,
      scope: "/",
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
      update: vi.fn().mockResolvedValue(undefined),
      unregister: vi.fn().mockResolvedValue(true),
    }),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
    controller: null,
    oncontrollerchange: null,
    onmessage: null,
    onmessageerror: null,
    startMessages: vi.fn(),
  };

  Object.defineProperty(navigator, "serviceWorker", {
    value: mockServiceWorkerContainer,
    writable: true,
    configurable: true,
  });
});
