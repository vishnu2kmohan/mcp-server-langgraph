/**
 * Tests for unified storage layer
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  storage,
  sessionStore,
  STORAGE_KEYS,
  type StorageKey,
  getAuthToken,
  setAuthTokens,
  clearAuthTokens,
} from "./storage";
import {
  mockData,
  timeConstants,
  setupQuotaExceededError,
  setupNSErrorQuotaReached,
  setupGenericError,
  setupStorageError,
  setupQuotaExceededErrorForMigration as _setupQuotaExceededErrorForMigration,
  setupLocalStorageDisabledError,
  setupStorageQuotaExceededError,
} from "./storage.fixtures";

describe("storage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe("get", () => {
    it("returns undefined or default for non-existent key", () => {
      expect(storage.get("nonexistent")).toBeUndefined();
      expect(storage.get("nonexistent", "default")).toBe("default");
    });

    it("parses JSON objects and arrays", () => {
      localStorage.setItem(
        "studio-test",
        JSON.stringify(mockData.simpleObject),
      );
      expect(storage.get<{ foo: string }>("test")).toEqual(
        mockData.simpleObject,
      );
      localStorage.setItem("studio-test", JSON.stringify(mockData.simpleArray));
      expect(storage.get<number[]>("test")).toEqual(mockData.simpleArray);
    });

    it("handles string values and legacy keys", () => {
      localStorage.setItem("studio-test", "plain-string");
      expect(storage.get<string>("test")).toBe("plain-string");
      localStorage.setItem("studio-theme", "dark");
      expect(storage.get<string>("studio-theme")).toBe("dark");
      localStorage.setItem("legacy-key", "value");
      expect(storage.get<string>("legacy-key")).toBe("value");
    });

    describe("with options object", () => {
      it("accepts defaultValue and validator", () => {
        expect(storage.get("missing", { defaultValue: "fallback" })).toBe(
          "fallback",
        );
        localStorage.setItem("studio-num", JSON.stringify(42));
        const isNumber = (v: unknown): v is number => typeof v === "number";
        expect(storage.get<number>("num", { validator: isNumber })).toBe(42);
        localStorage.setItem("studio-num", JSON.stringify("not-a-number"));
        expect(
          storage.get<number>("num", { validator: isNumber, defaultValue: 0 }),
        ).toBe(0);
      });

      it("handles expectObject option", () => {
        localStorage.setItem("studio-pref", JSON.stringify("string-value"));
        expect(
          storage.get<object>("pref", { expectObject: true, defaultValue: {} }),
        ).toEqual({});
        localStorage.setItem("studio-pref", JSON.stringify(null));
        expect(
          storage.get<object>("pref", {
            expectObject: true,
            defaultValue: { empty: true },
          }),
        ).toEqual({ empty: true });
        localStorage.setItem("studio-pref", JSON.stringify({ theme: "dark" }));
        expect(
          storage.get<{ theme: string }>("pref", { expectObject: true }),
        ).toEqual({ theme: "dark" });
        localStorage.setItem("studio-broken", "not-json");
        expect(
          storage.get<object>("broken", {
            expectObject: true,
            defaultValue: { empty: true },
          }),
        ).toEqual({ empty: true });
      });
    });
  });

  describe("set", () => {
    it("stores various value types", () => {
      expect(storage.set("test", "value")).toBe(true);
      expect(localStorage.getItem("studio-test")).toBe("value");
      expect(storage.set("test", mockData.simpleObject)).toBe(true);
      expect(localStorage.getItem("studio-test")).toBe('{"foo":"bar"}');
      expect(storage.set("test", mockData.simpleArray)).toBe(true);
      expect(localStorage.getItem("studio-test")).toBe("[1,2,3]");
      storage.set("studio-theme", "dark");
      expect(localStorage.getItem("studio-theme")).toBe("dark");
      storage.set("test", true);
      expect(localStorage.getItem("studio-test")).toBe("true");
      storage.set("test", 42);
      expect(localStorage.getItem("studio-test")).toBe("42");
    });

    it("handles storage errors", () => {
      const original = localStorage.setItem;
      localStorage.setItem = vi.fn(setupQuotaExceededError);
      expect(storage.set("big-data", "x".repeat(10000))).toBe(false);
      localStorage.setItem = vi.fn(setupNSErrorQuotaReached);
      expect(storage.set("test", "value")).toBe(false);
      localStorage.setItem = vi.fn(setupGenericError);
      expect(storage.set("test", "value")).toBe(false);
      localStorage.setItem = original;
    });
  });

  describe("remove", () => {
    it("removes keys with and without prefix", () => {
      localStorage.setItem("studio-test", "value");
      storage.remove("test");
      expect(localStorage.getItem("studio-test")).toBeNull();
      localStorage.setItem("studio-theme", "dark");
      storage.remove("studio-theme");
      expect(localStorage.getItem("studio-theme")).toBeNull();
      expect(() => storage.remove("nonexistent")).not.toThrow();
      localStorage.setItem("studio-legacy", "prefixed");
      localStorage.setItem("legacy", "not-prefixed");
      storage.remove("legacy");
      expect(localStorage.getItem("studio-legacy")).toBeNull();
      expect(localStorage.getItem("legacy")).toBeNull();
    });
  });

  describe("clear", () => {
    it("clears studio keys and handles auth tokens", () => {
      localStorage.setItem("studio-a", "1");
      localStorage.setItem("studio-b", "2");
      localStorage.setItem("other", "3");
      storage.clear();
      expect(localStorage.getItem("studio-a")).toBeNull();
      expect(localStorage.getItem("studio-b")).toBeNull();
      expect(localStorage.getItem("other")).toBe("3");
      localStorage.setItem("access_token", "token");
      localStorage.setItem("refresh_token", "refresh");
      localStorage.setItem("auth_token", "auth");
      storage.clear(true);
      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
      expect(localStorage.getItem("auth_token")).toBeNull();
      localStorage.setItem("access_token", "token");
      localStorage.setItem("studio-test", "value");
      storage.clear();
      expect(localStorage.getItem("access_token")).toBe("token");
    });
  });

  describe("keys and stats", () => {
    it("keys returns studio-prefixed keys only", () => {
      expect(storage.keys()).toEqual([]);
      localStorage.setItem("studio-a", "1");
      localStorage.setItem("studio-b", "2");
      localStorage.setItem("other", "3");
      const keys = storage.keys();
      expect(keys).toContain("studio-a");
      expect(keys).toContain("studio-b");
      expect(keys).not.toContain("other");
    });

    it("stats counts studio keys only", () => {
      expect(storage.stats()).toEqual({ usedBytes: 0, keyCount: 0 });
      localStorage.setItem("studio-a", "1");
      localStorage.setItem("studio-b", "22");
      localStorage.setItem("other", "333");
      const stats = storage.stats();
      expect(stats.keyCount).toBe(2);
      expect(stats.usedBytes).toBeGreaterThan(0);
    });
  });
});

describe("STORAGE_KEYS", () => {
  it("has consistent prefixes and legacy auth keys", () => {
    expect(STORAGE_KEYS.THEME).toMatch(/^studio-/);
    expect(STORAGE_KEYS.PREFERENCES).toMatch(/^studio-/);
    expect(STORAGE_KEYS.WORKSPACE).toMatch(/^studio-/);
    expect(STORAGE_KEYS.ONBOARDING).toMatch(/^studio-/);
    expect(STORAGE_KEYS.ACCESS_TOKEN).not.toMatch(/^studio-/);
    expect(STORAGE_KEYS.REFRESH_TOKEN).not.toMatch(/^studio-/);
    expect(STORAGE_KEYS.AUTH_TOKEN).not.toMatch(/^studio-/);
  });
});

describe("Auth token helpers", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => localStorage.clear());

  it("getAuthToken returns tokens with fallback", () => {
    expect(getAuthToken()).toBeNull();
    localStorage.setItem("access_token", "test-token");
    expect(getAuthToken()).toBe("test-token");
    localStorage.clear();
    localStorage.setItem("auth_token", "legacy-token");
    expect(getAuthToken()).toBe("legacy-token");
    localStorage.setItem("access_token", "new-token");
    expect(getAuthToken()).toBe("new-token");
  });

  it("setAuthTokens sets tokens", () => {
    setAuthTokens("token123");
    expect(localStorage.getItem("access_token")).toBe("token123");
    expect(localStorage.getItem("auth_token")).toBe("token123");
    setAuthTokens("access", "refresh");
    expect(localStorage.getItem("access_token")).toBe("access");
    expect(localStorage.getItem("refresh_token")).toBe("refresh");
  });

  it("clearAuthTokens removes all tokens", () => {
    localStorage.setItem("access_token", "a");
    localStorage.setItem("refresh_token", "r");
    localStorage.setItem("auth_token", "l");
    clearAuthTokens();
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
    expect(localStorage.getItem("auth_token")).toBeNull();
  });
});

describe("STORAGE_KEYS - comprehensive", () => {
  it("includes all required keys with proper prefixes", () => {
    expect(STORAGE_KEYS.DISCLOSURE_STATE).toBeDefined();
    expect(STORAGE_KEYS.DISCLOSURE_STATE).toMatch(/^studio-/);
    expect(STORAGE_KEYS.NUDGE_HISTORY).toBeDefined();
    expect(STORAGE_KEYS.NUDGE_HISTORY).toMatch(/^studio-/);
    expect(STORAGE_KEYS.OFFLINE_QUEUE).toBeDefined();
    expect(STORAGE_KEYS.OFFLINE_QUEUE).toMatch(/^studio-/);
    expect(STORAGE_KEYS.CANVAS_LAYOUT).toBeDefined();
    expect(STORAGE_KEYS.CANVAS_ZOOM).toBeDefined();
    expect(STORAGE_KEYS.AI_SUGGESTIONS_CACHE).toBeDefined();
    expect(STORAGE_KEYS.AI_CONTEXT_HISTORY).toBeDefined();
    const key: StorageKey = STORAGE_KEYS.THEME;
    expect(key).toBe("studio-theme");
  });
});

describe("storage TTL support", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
  });
  afterEach(() => {
    localStorage.clear();
    vi.useRealTimers();
  });

  it("setWithTTL stores with expiration metadata", () => {
    storage.setWithTTL("cache-key", { data: "test" }, timeConstants.ONE_MINUTE);
    const stored = localStorage.getItem("studio-cache-key");
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed.__value).toEqual({ data: "test" });
    expect(parsed.__expiresAt).toBeDefined();
    expect(typeof parsed.__expiresAt).toBe("number");
    const now = Date.now();
    vi.setSystemTime(now);
    storage.setWithTTL("test", "value", timeConstants.FIVE_SECONDS);
    const stored2 = JSON.parse(localStorage.getItem("studio-test")!);
    expect(stored2.__expiresAt).toBe(now + timeConstants.FIVE_SECONDS);
    expect(storage.setWithTTL("key", "value", timeConstants.ONE_SECOND)).toBe(
      true,
    );
    storage.setWithTTL(
      "complex",
      mockData.complexObject,
      timeConstants.TEN_SECONDS,
    );
    expect(JSON.parse(localStorage.getItem("studio-complex")!).__value).toEqual(
      mockData.complexObject,
    );
  });

  it("getWithTTL handles expiration correctly", () => {
    const now = Date.now();
    vi.setSystemTime(now);
    storage.setWithTTL("fresh", "fresh-value", timeConstants.ONE_MINUTE);
    vi.advanceTimersByTime(timeConstants.THIRTY_SECONDS);
    expect(storage.getWithTTL<string>("fresh")).toBe("fresh-value");
    storage.setWithTTL("expiring", "will-expire", timeConstants.FIVE_SECONDS);
    vi.advanceTimersByTime(6000);
    expect(storage.getWithTTL<string>("expiring")).toBeUndefined();
    storage.setWithTTL("expiring2", "old", timeConstants.ONE_SECOND);
    vi.advanceTimersByTime(2000);
    expect(storage.getWithTTL<string>("expiring2", "default")).toBe("default");
    storage.setWithTTL("cleanup", "data", timeConstants.ONE_SECOND);
    vi.advanceTimersByTime(2000);
    storage.getWithTTL("cleanup");
    expect(localStorage.getItem("studio-cleanup")).toBeNull();
    expect(storage.getWithTTL("nonexistent")).toBeUndefined();
    storage.set("regular", { data: "test" });
    expect(storage.getWithTTL("regular")).toBeUndefined();
    localStorage.setItem("studio-malformed", JSON.stringify({ broken: true }));
    expect(storage.getWithTTL("malformed", "fallback")).toBe("fallback");
  });

  it("handles TTL edge cases", () => {
    storage.setWithTTL("instant", "gone", 0);
    vi.advanceTimersByTime(1);
    expect(storage.getWithTTL("instant")).toBeUndefined();
    storage.setWithTTL("long-term", "persistent", timeConstants.ONE_YEAR);
    vi.advanceTimersByTime(timeConstants.ONE_YEAR - 1000);
    expect(storage.getWithTTL<string>("long-term")).toBe("persistent");
  });
});

// =============================================================================
// Session Storage Variant Tests
// =============================================================================

describe("sessionStore", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
  });
  afterEach(() => sessionStorage.clear());

  it("get handles various scenarios", () => {
    expect(sessionStore.get("missing")).toBeUndefined();
    expect(sessionStore.get("missing", "default")).toBe("default");
    sessionStorage.setItem(
      "studio-session-test",
      JSON.stringify(mockData.simpleObject),
    );
    expect(sessionStore.get<{ foo: string }>("session-test")).toEqual(
      mockData.simpleObject,
    );
    sessionStorage.setItem("studio-session-str", "plain-string");
    expect(sessionStore.get<string>("session-str")).toBe("plain-string");
    sessionStorage.setItem("studio-session-data", "value");
    expect(sessionStore.get<string>("studio-session-data")).toBe("value");
    const getItemSpy = vi
      .spyOn(sessionStorage, "getItem")
      .mockImplementation(setupStorageError);
    expect(sessionStore.get<string>("test", "fallback")).toBe("fallback");
    getItemSpy.mockRestore();
  });

  it("set stores values and handles errors", () => {
    expect(sessionStore.set("test", "value")).toBe(true);
    expect(sessionStorage.getItem("studio-test")).toBe("value");
    sessionStore.set("obj", { key: "value" });
    expect(sessionStorage.getItem("studio-obj")).toBe('{"key":"value"}');
    sessionStore.set("arr", mockData.simpleArray);
    expect(sessionStorage.getItem("studio-arr")).toBe("[1,2,3]");
    const setItemSpy = vi
      .spyOn(sessionStorage, "setItem")
      .mockImplementationOnce(() => undefined)
      .mockImplementationOnce(() => {
        throw new Error("QuotaExceededError");
      });
    expect(sessionStore.set("test", "value")).toBe(false);
    setItemSpy.mockRestore();
  });

  it("remove and clear handle keys correctly", () => {
    sessionStorage.setItem("studio-test", "value");
    sessionStore.remove("test");
    expect(sessionStorage.getItem("studio-test")).toBeNull();
    sessionStorage.setItem("studio-test", "value");
    const removeItemSpy = vi
      .spyOn(sessionStorage, "removeItem")
      .mockImplementationOnce(() => undefined)
      .mockImplementationOnce(setupStorageError);
    expect(() => sessionStore.remove("test")).not.toThrow();
    removeItemSpy.mockRestore();
    sessionStorage.setItem("studio-a", "1");
    sessionStorage.setItem("studio-b", "2");
    sessionStorage.setItem("other", "3");
    sessionStore.clear();
    expect(sessionStorage.getItem("studio-a")).toBeNull();
    expect(sessionStorage.getItem("studio-b")).toBeNull();
    expect(sessionStorage.getItem("other")).toBe("3");
    sessionStorage.setItem("studio-test", "1");
    const removeItemSpy2 = vi
      .spyOn(sessionStorage, "removeItem")
      .mockImplementationOnce(() => undefined)
      .mockImplementation(setupStorageQuotaExceededError);
    expect(() => sessionStore.clear()).not.toThrow();
    removeItemSpy2.mockRestore();
  });

  it("keys returns studio-prefixed keys only", () => {
    sessionStorage.setItem("studio-x", "1");
    sessionStorage.setItem("studio-y", "2");
    sessionStorage.setItem("other", "3");
    const keys = sessionStore.keys();
    expect(keys).toContain("studio-x");
    expect(keys).toContain("studio-y");
    expect(keys).not.toContain("other");
  });
});

describe("sessionStore TTL support", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.useFakeTimers();
  });
  afterEach(() => {
    sessionStorage.clear();
    vi.useRealTimers();
  });

  it("supports TTL operations", () => {
    sessionStore.setWithTTL(
      "session-cache",
      { temp: "data" },
      timeConstants.THIRTY_SECONDS,
    );
    const stored = sessionStorage.getItem("studio-session-cache");
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed.__value).toEqual({ temp: "data" });
    expect(parsed.__expiresAt).toBeDefined();
    sessionStore.setWithTTL("fresh", "data", timeConstants.TEN_SECONDS);
    vi.advanceTimersByTime(timeConstants.FIVE_SECONDS);
    expect(sessionStore.getWithTTL<string>("fresh")).toBe("data");
    sessionStore.setWithTTL("expiring", "data", timeConstants.FIVE_SECONDS);
    vi.advanceTimersByTime(6000);
    expect(sessionStore.getWithTTL("expiring")).toBeUndefined();
    sessionStorage.setItem(
      "studio-plain-value",
      JSON.stringify(mockData.simpleObject),
    );
    expect(sessionStore.getWithTTL<string>("plain-value", "default-val")).toBe(
      "default-val",
    );
    sessionStorage.setItem("studio-invalid-json", "not-valid-json{");
    expect(sessionStore.getWithTTL<string>("invalid-json", "fallback")).toBe(
      "fallback",
    );
    const wrapper = {
      __value: "prefixed-data",
      __expiresAt: Date.now() + timeConstants.TEN_SECONDS,
    };
    sessionStorage.setItem("studio-prefixed-ttl", JSON.stringify(wrapper));
    expect(sessionStore.getWithTTL<string>("studio-prefixed-ttl")).toBe(
      "prefixed-data",
    );
  });
});

describe("STORAGE_KEYS - hook integration", () => {
  it("validates hook storage key formats", () => {
    expect(STORAGE_KEYS.NUDGE_HISTORY).toBe("studio-nudge_history");
    expect(STORAGE_KEYS.DISCLOSURE_STATE).toBe("studio-disclosure_state");
    expect(STORAGE_KEYS.OFFLINE_QUEUE).toBe("studio-offline_queue");
    expect(STORAGE_KEYS.AI_SUGGESTIONS_CACHE).toBe(
      "studio-ai-suggestions-cache",
    );
    expect(STORAGE_KEYS.SESSION_SYNC_STATE).toBe("studio-session-sync-state");
  });
});

describe("AI suggestions cache pattern", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.useFakeTimers();
  });
  afterEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.useRealTimers();
  });

  it("caches AI suggestions with TTL and expiration", () => {
    storage.setWithTTL(
      STORAGE_KEYS.AI_SUGGESTIONS_CACHE,
      mockData.aiSuggestions,
      timeConstants.FIVE_MINUTES,
    );
    expect(
      storage.getWithTTL<typeof mockData.aiSuggestions>(
        STORAGE_KEYS.AI_SUGGESTIONS_CACHE,
      ),
    ).toEqual(mockData.aiSuggestions);
    storage.setWithTTL(
      STORAGE_KEYS.AI_SUGGESTIONS_CACHE,
      mockData.aiSuggestionSimple,
      timeConstants.FIVE_MINUTES,
    );
    vi.advanceTimersByTime(timeConstants.FIVE_MINUTES + 1000);
    expect(
      storage.getWithTTL(STORAGE_KEYS.AI_SUGGESTIONS_CACHE),
    ).toBeUndefined();
    sessionStore.set(STORAGE_KEYS.AI_CONTEXT_HISTORY, mockData.aiContext);
    expect(
      sessionStore.get<typeof mockData.aiContext>(
        STORAGE_KEYS.AI_CONTEXT_HISTORY,
      ),
    ).toEqual(mockData.aiContext);
    sessionStore.setWithTTL(
      STORAGE_KEYS.AI_PREFERENCES,
      mockData.aiPreferences,
      timeConstants.THIRTY_MINUTES,
    );
    vi.advanceTimersByTime(timeConstants.TWENTY_FIVE_MINUTES);
    expect(
      sessionStore.getWithTTL<typeof mockData.aiPreferences>(
        STORAGE_KEYS.AI_PREFERENCES,
      ),
    ).toEqual(mockData.aiPreferences);
    vi.advanceTimersByTime(timeConstants.TEN_MINUTES);
    expect(
      sessionStore.getWithTTL(STORAGE_KEYS.AI_PREFERENCES),
    ).toBeUndefined();
  });
});

// =============================================================================
// Storage Migration Utility Tests
// =============================================================================

describe("storage.migrate", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });
  afterEach(() => localStorage.clear());

  it("migrates legacy keys and handles edge cases", () => {
    localStorage.setItem(
      "old_preferences",
      JSON.stringify(mockData.legacyPreferences),
    );
    expect(storage.migrate("old_preferences", STORAGE_KEYS.PREFERENCES)).toBe(
      true,
    );
    expect(storage.get<{ theme: string }>(STORAGE_KEYS.PREFERENCES)).toEqual(
      mockData.legacyPreferences,
    );
    expect(localStorage.getItem("old_preferences")).toBeNull();
    expect(storage.migrate("nonexistent_key", STORAGE_KEYS.PREFERENCES)).toBe(
      false,
    );
    localStorage.setItem("old_key", JSON.stringify(mockData.oldKeyData));
    storage.set(STORAGE_KEYS.PREFERENCES, mockData.newKeyData);
    expect(storage.migrate("old_key", STORAGE_KEYS.PREFERENCES)).toBe(false);
    expect(storage.get<{ new: boolean }>(STORAGE_KEYS.PREFERENCES)).toEqual(
      mockData.newKeyData,
    );
    expect(
      storage.migrate("old_key", STORAGE_KEYS.PREFERENCES, { force: true }),
    ).toBe(true);
    expect(storage.get<{ old: boolean }>(STORAGE_KEYS.PREFERENCES)).toEqual(
      mockData.oldKeyData,
    );
    localStorage.setItem("old_theme", "dark");
    expect(storage.migrate("old_theme", STORAGE_KEYS.THEME)).toBe(true);
    expect(storage.get<string>(STORAGE_KEYS.THEME)).toBe("dark");
    localStorage.setItem("old_key", JSON.stringify(mockData.migrationData));
    const original = window.localStorage.setItem.bind(window.localStorage);
    let callCount = 0;
    window.localStorage.setItem = vi.fn((key: string, value: string) => {
      callCount++;
      if (callCount === 1) return original(key, value);
      throw new Error("QuotaExceededError");
    });
    expect(storage.migrate("old_key", STORAGE_KEYS.PREFERENCES)).toBe(false);
    window.localStorage.setItem = original;
  });
});

describe("storage quota monitoring", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => localStorage.clear());

  it("getQuotaInfo returns usage statistics", () => {
    storage.set("test1", { data: "value1" });
    storage.set("test2", { data: "value2" });
    const quota = storage.getQuotaInfo();
    expect(quota.usedBytes).toBeGreaterThan(0);
    expect(quota.keyCount).toBeGreaterThanOrEqual(2);
    expect(quota.percentUsed).toBeGreaterThanOrEqual(0);
    expect(quota.percentUsed).toBeLessThanOrEqual(100);
    expect(quota.estimatedQuota).toBeGreaterThan(0);
    expect(quota.availableBytes).toBeGreaterThan(0);
    storage.set("small", "a");
    storage.set("medium", "a".repeat(100));
    storage.set("large", "a".repeat(1000));
    const quota2 = storage.getQuotaInfo();
    expect(quota2.largestKeys).toBeDefined();
    expect(quota2.largestKeys.length).toBeGreaterThan(0);
    expect(quota2.largestKeys[0].key).toBe("studio-large");
    const original = window.localStorage.setItem;
    window.localStorage.setItem = vi.fn(setupLocalStorageDisabledError);
    const quota3 = storage.getQuotaInfo();
    expect(quota3.usedBytes).toBe(0);
    expect(quota3.keyCount).toBe(0);
    expect(quota3.percentUsed).toBe(0);
    expect(quota3.largestKeys).toEqual([]);
    window.localStorage.setItem = original;
  });

  it("isNearQuota checks quota thresholds", () => {
    storage.set("small", "test");
    expect(storage.isNearQuota()).toBe(false);
    expect(typeof storage.isNearQuota(0.001)).toBe("boolean");
    expect(storage.isNearQuota()).toBe(false);
  });
});

describe("storage.cleanup", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
  });
  afterEach(() => {
    localStorage.clear();
    vi.useRealTimers();
  });

  it("removes expired TTL entries and handles edge cases", () => {
    const now = Date.now();
    vi.setSystemTime(now);
    storage.setWithTTL("fresh", "still-valid", timeConstants.ONE_MINUTE);
    storage.setWithTTL("stale", "should-expire", timeConstants.ONE_SECOND);
    vi.advanceTimersByTime(timeConstants.FIVE_SECONDS);
    const result = storage.cleanup();
    expect(result.removedCount).toBeGreaterThanOrEqual(1);
    expect(result.freedBytes).toBeGreaterThan(0);
    expect(storage.getWithTTL<string>("fresh")).toBe("still-valid");
    expect(storage.getWithTTL<string>("stale")).toBeUndefined();
    const result2 = storage.cleanup({ maxAge: 1000 });
    expect(result2).toHaveProperty("removedCount");
    expect(result2).toHaveProperty("freedBytes");
    vi.setSystemTime(now);
    storage.setWithTTL("valid1", "data1", timeConstants.ONE_MINUTE);
    storage.setWithTTL("valid2", "data2", timeConstants.ONE_MINUTE);
    const result3 = storage.cleanup();
    expect(result3.removedCount).toBe(0);
    expect(result3.freedBytes).toBe(0);
    vi.setSystemTime(now);
    storage.setWithTTL("valid", "still-good", timeConstants.ONE_MINUTE);
    storage.setWithTTL("expired1", "bye1", timeConstants.ONE_SECOND);
    storage.setWithTTL("expired2", "bye2", 2000);
    vi.advanceTimersByTime(3000);
    const result4 = storage.cleanup();
    expect(result4.removedCount).toBe(2);
    expect(result4.freedBytes).toBeGreaterThan(0);
    expect(storage.getWithTTL<string>("valid")).toBe("still-good");
    const setItemSpy = vi
      .spyOn(localStorage, "setItem")
      .mockImplementation(setupLocalStorageDisabledError);
    expect(storage.cleanup()).toEqual({ removedCount: 0, freedBytes: 0 });
    setItemSpy.mockRestore();
  });
});
