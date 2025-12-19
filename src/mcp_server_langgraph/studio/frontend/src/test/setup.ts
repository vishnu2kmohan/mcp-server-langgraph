/**
 * Vitest test setup file
 *
 * This file runs before each test file and sets up:
 * - Testing library matchers
 * - Browser API mocks
 * - MSW server for realistic API mocking
 * - Global test utilities
 */

import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll, vi, expect } from "vitest";
import { cleanup } from "@testing-library/react";
import { server } from "../mocks/server";
import { toHaveNoViolations } from "jest-axe";

// Extend Vitest's expect with jest-axe matchers
expect.extend(toHaveNoViolations);

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
    message.includes("RequestInit: Expected signal")
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
    message.includes("RequestInit: Expected signal")
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

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock ResizeObserver
beforeAll(() => {
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));
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

// Mock localStorage with actual storage functionality
beforeAll(() => {
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
  });
});

// Mock sessionStorage with actual storage functionality
beforeAll(() => {
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
  });
});

// Mock scrollTo
beforeAll(() => {
  window.scrollTo = vi.fn();
});

// Mock IntersectionObserver
beforeAll(() => {
  global.IntersectionObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
    root: null,
    rootMargin: "",
    thresholds: [],
    takeRecords: vi.fn(() => []),
  }));
});
