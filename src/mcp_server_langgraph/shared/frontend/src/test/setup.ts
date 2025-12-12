/**
 * Test Setup for Shared Frontend Library
 */

import '@testing-library/jest-dom';
import { vi, beforeEach, afterEach } from 'vitest';

// =============================================================================
// localStorage Mock with Spy Functions
// =============================================================================

let localStorageStore: Record<string, string> = {};

export const localStorageMock = {
  getItem: vi.fn((key: string) => localStorageStore[key] ?? null),
  setItem: vi.fn((key: string, value: string) => {
    localStorageStore[key] = value;
  }),
  removeItem: vi.fn((key: string) => {
    delete localStorageStore[key];
  }),
  clear: vi.fn(() => {
    localStorageStore = {};
  }),
  get length() {
    return Object.keys(localStorageStore).length;
  },
  key: vi.fn((index: number) => Object.keys(localStorageStore)[index] || null),
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

// =============================================================================
// matchMedia Mock
// =============================================================================

export interface MockMediaQueryList {
  matches: boolean;
  media: string;
  onchange: ((this: MediaQueryList, ev: MediaQueryListEvent) => void) | null;
  addListener: ReturnType<typeof vi.fn>;
  removeListener: ReturnType<typeof vi.fn>;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  dispatchEvent: ReturnType<typeof vi.fn>;
}

export const createMatchMediaMock = (
  defaultMatches: boolean = false
): ((query: string) => MockMediaQueryList) => {
  return (query: string) => ({
    matches: defaultMatches,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  });
};

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: createMatchMediaMock(false),
});

// =============================================================================
// Test Lifecycle Hooks
// =============================================================================

beforeEach(() => {
  // Clear localStorage store and reset mocks
  localStorageStore = {};
  localStorageMock.getItem.mockClear();
  localStorageMock.setItem.mockClear();
  localStorageMock.removeItem.mockClear();
  localStorageMock.clear.mockClear();
  localStorageMock.key.mockClear();

  // Reset matchMedia to default
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: createMatchMediaMock(false),
  });
});

afterEach(() => {
  // Clear localStorage store
  localStorageStore = {};

  // Clean up DOM
  document.documentElement.classList.remove('dark');
  document.body.innerHTML = '';
});
