/**
 * Shared Storage Mock Utilities for Testing
 *
 * Provides standardized mock patterns for `utils/storage` module.
 * Use these helpers to avoid the common pitfall of incomplete mocks
 * that break when authSlice imports STORAGE_KEYS.
 *
 * @example
 * ```typescript
 * // In your test file
 * import { mockStorageWithAuth } from '@/testing/storageMocks';
 *
 * vi.mock("../utils/storage", async (importOriginal) =>
 *   mockStorageWithAuth(importOriginal)
 * );
 * ```
 *
 * @see src/hooks/useConnectionHealthWebSocket.test.ts for usage example
 */

import { vi } from "vitest";

// Default mock token for tests
export const DEFAULT_MOCK_TOKEN = "mock-test-token";

// Type for the importOriginal function provided by vitest
export type ImportOriginal<T> = () => Promise<T>;

/**
 * Create a storage mock that preserves all exports while overriding getAuthToken.
 *
 * This pattern is REQUIRED when mocking utils/storage because:
 * 1. authSlice imports STORAGE_KEYS from storage
 * 2. A partial mock (only getAuthToken) will break authSlice imports
 * 3. importOriginal() preserves all exports while allowing function overrides
 *
 * @param importOriginal - The importOriginal function from vi.mock callback
 * @param token - Optional token to return from getAuthToken (defaults to mock-test-token)
 * @returns Promise<MockedStorageModule> - Complete mocked module
 *
 * @example
 * ```typescript
 * vi.mock("../utils/storage", async (importOriginal) =>
 *   mockStorageWithAuth(importOriginal, "custom-token")
 * );
 * ```
 */
export async function mockStorageWithAuth(
  importOriginal: ImportOriginal<typeof import("../utils/storage")>,
  token: string | null = DEFAULT_MOCK_TOKEN,
): Promise<ReturnType<typeof createStorageMock>> {
  const actual = await importOriginal();
  return createStorageMock(actual, token);
}

/**
 * Create a mock from actual storage module with overridden getAuthToken.
 *
 * @param actual - The actual storage module
 * @param token - Token to return from getAuthToken
 * @returns Mocked storage module
 */
export function createStorageMock(
  actual: typeof import("../utils/storage"),
  token: string | null = DEFAULT_MOCK_TOKEN,
) {
  return {
    ...actual,
    getAuthToken: vi.fn(() => token),
  };
}

/**
 * Create a storage mock with no auth token (unauthenticated state).
 *
 * @param importOriginal - The importOriginal function from vi.mock callback
 * @returns Promise<MockedStorageModule>
 *
 * @example
 * ```typescript
 * vi.mock("../utils/storage", async (importOriginal) =>
 *   mockStorageUnauthenticated(importOriginal)
 * );
 * ```
 */
export async function mockStorageUnauthenticated(
  importOriginal: ImportOriginal<typeof import("../utils/storage")>,
): Promise<ReturnType<typeof createStorageMock>> {
  const actual = await importOriginal();
  return createStorageMock(actual, null);
}

/**
 * Create a storage mock with configurable storage.get and storage.set functions.
 *
 * Useful when you need to test components that read/write to storage.
 *
 * @param importOriginal - The importOriginal function from vi.mock callback
 * @param options - Configuration options
 * @returns Promise<MockedStorageModule>
 *
 * @example
 * ```typescript
 * vi.mock("../utils/storage", async (importOriginal) =>
 *   mockStorageWithValues(importOriginal, {
 *     values: { 'studio-theme': 'dark' },
 *     token: 'my-token',
 *   })
 * );
 * ```
 */
export async function mockStorageWithValues(
  importOriginal: ImportOriginal<typeof import("../utils/storage")>,
  options: {
    values?: Record<string, unknown>;
    token?: string | null;
  } = {},
): Promise<ReturnType<typeof createStorageWithValuesMock>> {
  const actual = await importOriginal();
  return createStorageWithValuesMock(actual, options);
}

/**
 * Create a storage mock with custom values.
 */
export function createStorageWithValuesMock(
  actual: typeof import("../utils/storage"),
  options: {
    values?: Record<string, unknown>;
    token?: string | null;
  } = {},
) {
  const { values = {}, token = DEFAULT_MOCK_TOKEN } = options;

  return {
    ...actual,
    getAuthToken: vi.fn(() => token),
    storage: {
      ...actual.storage,
      get: vi.fn(<T>(key: string, defaultValue?: T): T | undefined => {
        if (key in values) {
          return values[key] as T;
        }
        return defaultValue;
      }),
      set: vi.fn(() => true),
      remove: vi.fn(),
    },
  };
}

/**
 * Factory for creating a controlled storage mock with spies.
 *
 * Returns mocked functions that can be inspected and controlled.
 *
 * @returns Object with mock functions and helper methods
 */
export function createStorageMockFactory() {
  const mockValues = new Map<string, unknown>();

  const getAuthToken = vi.fn(() => DEFAULT_MOCK_TOKEN as string | null);
  const setAuthTokens = vi.fn();
  const clearAuthTokens = vi.fn(() => {
    mockValues.clear();
  });

  const storage = {
    get: vi.fn(<T>(key: string, defaultValue?: T): T | undefined => {
      if (mockValues.has(key)) {
        return mockValues.get(key) as T;
      }
      return defaultValue;
    }),
    set: vi.fn(<T>(key: string, value: T): boolean => {
      mockValues.set(key, value);
      return true;
    }),
    remove: vi.fn((key: string) => {
      mockValues.delete(key);
    }),
    clear: vi.fn(() => {
      mockValues.clear();
    }),
    keys: vi.fn(() => Array.from(mockValues.keys())),
    stats: vi.fn(() => ({ usedBytes: 0, keyCount: 0 })),
    setWithTTL: vi.fn(() => true),
    getWithTTL: vi.fn(() => undefined),
    migrate: vi.fn(() => true),
    getQuotaInfo: vi.fn(() => ({
      usedBytes: 0,
      keyCount: 0,
      estimatedQuota: 5 * 1024 * 1024,
      availableBytes: 5 * 1024 * 1024,
      percentUsed: 0,
      largestKeys: [],
    })),
    isNearQuota: vi.fn(() => false),
    cleanup: vi.fn(() => ({ removedCount: 0, freedBytes: 0 })),
  };

  const sessionStore = {
    get: vi.fn(() => undefined),
    set: vi.fn(() => true),
    remove: vi.fn(),
    clear: vi.fn(),
    keys: vi.fn(() => []),
    setWithTTL: vi.fn(() => true),
    getWithTTL: vi.fn(() => undefined),
  };

  return {
    // Mock functions
    getAuthToken,
    setAuthTokens,
    clearAuthTokens,
    storage,
    sessionStore,

    // Helpers
    setMockValue: <T>(key: string, value: T) => {
      mockValues.set(key, value);
    },
    clearMockValues: () => {
      mockValues.clear();
    },
    setMockToken: (token: string | null) => {
      getAuthToken.mockReturnValue(token);
    },
  };
}
