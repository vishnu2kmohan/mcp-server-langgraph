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
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import { server } from "../mocks/server";

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

// Mock localStorage
beforeAll(() => {
  const localStorageMock: Storage = {
    length: 0,
    clear: vi.fn(),
    getItem: vi.fn(() => null),
    key: vi.fn(() => null),
    removeItem: vi.fn(),
    setItem: vi.fn(),
  };
  Object.defineProperty(window, "localStorage", {
    value: localStorageMock,
  });
});

// Mock sessionStorage
beforeAll(() => {
  const sessionStorageMock: Storage = {
    length: 0,
    clear: vi.fn(),
    getItem: vi.fn(() => null),
    key: vi.fn(() => null),
    removeItem: vi.fn(),
    setItem: vi.fn(),
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
