/**
 * Test setup file for Vitest + Testing Library
 *
 * This file runs before each test file and sets up:
 * - Testing Library matchers (@testing-library/jest-dom)
 * - Global mocks for browser APIs
 * - Cleanup after each test
 */

import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll, afterAll, vi } from 'vitest';

// Cleanup after each test to ensure isolation
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia for dark mode tests
beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
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

  // Mock localStorage with actual storage functionality
  const createLocalStorageMock = () => {
    let store: Record<string, string> = {};
    return {
      getItem: vi.fn((key: string) => store[key] ?? null),
      setItem: vi.fn((key: string, value: string) => {
        store[key] = String(value);
      }),
      removeItem: vi.fn((key: string) => {
        delete store[key];
      }),
      clear: vi.fn(() => {
        store = {};
      }),
      key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
      get length() {
        return Object.keys(store).length;
      },
    };
  };

  Object.defineProperty(window, 'localStorage', {
    value: createLocalStorageMock(),
    writable: true,
  });

  // Mock ResizeObserver
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));

  // Mock IntersectionObserver
  global.IntersectionObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
    root: null,
    rootMargin: '',
    thresholds: [],
  }));

  // Mock fetch for API tests
  global.fetch = vi.fn();

  // Mock scrollIntoView for chat auto-scroll tests
  Element.prototype.scrollIntoView = vi.fn();
});

afterAll(() => {
  vi.clearAllMocks();
});

// Suppress console errors/warnings in tests unless explicitly testing them
const originalError = console.error;
const originalWarn = console.warn;

beforeAll(() => {
  console.error = (...args: unknown[]) => {
    // Allow React act() warnings through
    if (
      typeof args[0] === 'string' &&
      args[0].includes('act(')
    ) {
      originalError(...args);
      return;
    }
    // Suppress other errors in tests
  };

  console.warn = (...args: unknown[]) => {
    // Suppress warnings in tests
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning:')
    ) {
      return;
    }
    originalWarn(...args);
  };
});

afterAll(() => {
  console.error = originalError;
  console.warn = originalWarn;
});
