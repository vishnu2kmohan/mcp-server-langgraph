/**
 * Tests for Storage Mock Utilities
 */

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createStorageMock,
  createStorageMockFactory,
  createStorageWithValuesMock,
  DEFAULT_MOCK_TOKEN,
} from "./storageMocks";

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

// Mock the actual storage module for testing the mock utilities
const mockActualStorage = {
  storage: {
    get: vi.fn(),
    set: vi.fn(),
    remove: vi.fn(),
    clear: vi.fn(),
    keys: vi.fn(),
    stats: vi.fn(),
    setWithTTL: vi.fn(),
    getWithTTL: vi.fn(),
    migrate: vi.fn(),
    getQuotaInfo: vi.fn(),
    isNearQuota: vi.fn(),
    cleanup: vi.fn(),
  },
  sessionStore: {
    get: vi.fn(),
    set: vi.fn(),
    remove: vi.fn(),
    clear: vi.fn(),
    keys: vi.fn(),
    setWithTTL: vi.fn(),
    getWithTTL: vi.fn(),
  },
  getAuthToken: vi.fn(() => "actual-token"),
  setAuthTokens: vi.fn(),
  clearAuthTokens: vi.fn(),
  STORAGE_KEYS: {
    ACCESS_TOKEN: "access_token",
    AUTH_TOKEN: "auth_token",
    THEME: "studio-theme",
  },
} as unknown as typeof import("../utils/storage");

describe("storageMocks", () => {
  describe("createStorageMock", () => {
    it("should preserve all exports from actual module", () => {
      const mock = createStorageMock(mockActualStorage);

      // Should have STORAGE_KEYS from actual
      expect(mock.STORAGE_KEYS).toBeDefined();
      expect(mock.STORAGE_KEYS.ACCESS_TOKEN).toBe("access_token");
    });

    it("should override getAuthToken with mock", () => {
      const mock = createStorageMock(mockActualStorage);

      expect(mock.getAuthToken).toBeDefined();
      expect(mock.getAuthToken()).toBe(DEFAULT_MOCK_TOKEN);
    });

    it("should use custom token when provided", () => {
      const mock = createStorageMock(mockActualStorage, "custom-token");

      expect(mock.getAuthToken()).toBe("custom-token");
    });

    it("should return null token when specified", () => {
      const mock = createStorageMock(mockActualStorage, null);

      expect(mock.getAuthToken()).toBeNull();
    });
  });

  describe("createStorageWithValuesMock", () => {
    it("should return provided values from storage.get", () => {
      const mock = createStorageWithValuesMock(mockActualStorage, {
        values: { "studio-theme": "dark", "studio-sidebar-collapsed": true },
      });

      expect(mock.storage.get("studio-theme")).toBe("dark");
      expect(mock.storage.get("studio-sidebar-collapsed")).toBe(true);
    });

    it("should return default value when key not found", () => {
      const mock = createStorageWithValuesMock(mockActualStorage, {
        values: {},
      });

      expect(mock.storage.get("missing-key", "default")).toBe("default");
    });

    it("should use custom token", () => {
      const mock = createStorageWithValuesMock(mockActualStorage, {
        token: "custom-token",
      });

      expect(mock.getAuthToken()).toBe("custom-token");
    });
  });

  describe("createStorageMockFactory", () => {
    it("should create a factory with all mock functions", () => {
      const factory = createStorageMockFactory();

      expect(factory.getAuthToken).toBeDefined();
      expect(factory.setAuthTokens).toBeDefined();
      expect(factory.clearAuthTokens).toBeDefined();
      expect(factory.storage).toBeDefined();
      expect(factory.sessionStore).toBeDefined();
    });

    it("should return default mock token", () => {
      const factory = createStorageMockFactory();

      expect(factory.getAuthToken()).toBe(DEFAULT_MOCK_TOKEN);
    });

    it("should allow setting and getting mock values", () => {
      const factory = createStorageMockFactory();

      factory.setMockValue("test-key", "test-value");
      expect(factory.storage.get("test-key")).toBe("test-value");
    });

    it("should allow setting mock token", () => {
      const factory = createStorageMockFactory();

      factory.setMockToken("new-token");
      expect(factory.getAuthToken()).toBe("new-token");
    });

    it("should allow clearing mock values", () => {
      const factory = createStorageMockFactory();

      factory.setMockValue("test-key", "test-value");
      factory.clearMockValues();
      expect(factory.storage.get("test-key")).toBeUndefined();
    });

    it("should store values via storage.set", () => {
      const factory = createStorageMockFactory();

      factory.storage.set("key1", "value1");
      expect(factory.storage.get("key1")).toBe("value1");
    });

    it("should remove values via storage.remove", () => {
      const factory = createStorageMockFactory();

      factory.setMockValue("key1", "value1");
      factory.storage.remove("key1");
      expect(factory.storage.get("key1")).toBeUndefined();
    });

    it("should clear values via storage.clear", () => {
      const factory = createStorageMockFactory();

      factory.setMockValue("key1", "value1");
      factory.setMockValue("key2", "value2");
      factory.storage.clear();
      expect(factory.storage.get("key1")).toBeUndefined();
      expect(factory.storage.get("key2")).toBeUndefined();
    });
  });
});
