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

describe("storage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe("get", () => {
    it("returns undefined for non-existent key", () => {
      const result = storage.get("nonexistent");
      expect(result).toBeUndefined();
    });

    it("returns default value for non-existent key", () => {
      const result = storage.get("nonexistent", "default");
      expect(result).toBe("default");
    });

    it("parses JSON objects", () => {
      localStorage.setItem("studio-test", JSON.stringify({ foo: "bar" }));
      const result = storage.get<{ foo: string }>("test");
      expect(result).toEqual({ foo: "bar" });
    });

    it("parses JSON arrays", () => {
      localStorage.setItem("studio-test", JSON.stringify([1, 2, 3]));
      const result = storage.get<number[]>("test");
      expect(result).toEqual([1, 2, 3]);
    });

    it("returns string values as-is when not valid JSON", () => {
      localStorage.setItem("studio-test", "plain-string");
      const result = storage.get<string>("test");
      expect(result).toBe("plain-string");
    });

    it("handles prefixed keys", () => {
      localStorage.setItem("studio-theme", "dark");
      const result = storage.get<string>("studio-theme");
      expect(result).toBe("dark");
    });

    it("supports legacy keys without prefix", () => {
      localStorage.setItem("legacy-key", "value");
      const result = storage.get<string>("legacy-key");
      expect(result).toBe("value");
    });

    describe("with options object", () => {
      it("accepts defaultValue in options", () => {
        const result = storage.get("missing", { defaultValue: "fallback" });
        expect(result).toBe("fallback");
      });

      it("uses validator to validate value", () => {
        localStorage.setItem("studio-num", JSON.stringify(42));
        const isNumber = (v: unknown): v is number => typeof v === "number";
        const result = storage.get<number>("num", { validator: isNumber });
        expect(result).toBe(42);
      });

      it("returns defaultValue when validator fails", () => {
        localStorage.setItem("studio-num", JSON.stringify("not-a-number"));
        const isNumber = (v: unknown): v is number => typeof v === "number";
        const result = storage.get<number>("num", {
          validator: isNumber,
          defaultValue: 0,
        });
        expect(result).toBe(0);
      });

      it("returns defaultValue when expectObject but value is string", () => {
        localStorage.setItem("studio-pref", JSON.stringify("string-value"));
        const result = storage.get<object>("pref", {
          expectObject: true,
          defaultValue: {},
        });
        expect(result).toEqual({});
      });

      it("returns defaultValue when expectObject but value is null", () => {
        localStorage.setItem("studio-pref", JSON.stringify(null));
        const result = storage.get<object>("pref", {
          expectObject: true,
          defaultValue: { empty: true },
        });
        expect(result).toEqual({ empty: true });
      });

      it("returns parsed object when expectObject is true", () => {
        localStorage.setItem("studio-pref", JSON.stringify({ theme: "dark" }));
        const result = storage.get<{ theme: string }>("pref", {
          expectObject: true,
        });
        expect(result).toEqual({ theme: "dark" });
      });

      it("returns defaultValue when expectObject and JSON parse fails", () => {
        localStorage.setItem("studio-broken", "not-json");
        const result = storage.get<object>("broken", {
          expectObject: true,
          defaultValue: { empty: true },
        });
        expect(result).toEqual({ empty: true });
      });
    });
  });

  describe("set", () => {
    it("stores string values", () => {
      const success = storage.set("test", "value");
      expect(success).toBe(true);
      expect(localStorage.getItem("studio-test")).toBe("value");
    });

    it("stores object values as JSON", () => {
      const success = storage.set("test", { foo: "bar" });
      expect(success).toBe(true);
      expect(localStorage.getItem("studio-test")).toBe('{"foo":"bar"}');
    });

    it("stores array values as JSON", () => {
      const success = storage.set("test", [1, 2, 3]);
      expect(success).toBe(true);
      expect(localStorage.getItem("studio-test")).toBe("[1,2,3]");
    });

    it("handles prefixed keys correctly", () => {
      storage.set("studio-theme", "dark");
      expect(localStorage.getItem("studio-theme")).toBe("dark");
    });

    it("stores boolean values", () => {
      storage.set("test", true);
      expect(localStorage.getItem("studio-test")).toBe("true");
    });

    it("stores number values", () => {
      storage.set("test", 42);
      expect(localStorage.getItem("studio-test")).toBe("42");
    });

    it("handles quota exceeded error", () => {
      const originalSetItem = localStorage.setItem;
      localStorage.setItem = vi.fn(() => {
        const error = new DOMException("Quota exceeded", "QuotaExceededError");
        throw error;
      });

      const result = storage.set("big-data", "x".repeat(10000));
      expect(result).toBe(false);

      localStorage.setItem = originalSetItem;
    });

    it("handles NS_ERROR_DOM_QUOTA_REACHED error", () => {
      const originalSetItem = localStorage.setItem;
      localStorage.setItem = vi.fn(() => {
        const error = new DOMException("Quota", "NS_ERROR_DOM_QUOTA_REACHED");
        throw error;
      });

      const result = storage.set("test", "value");
      expect(result).toBe(false);

      localStorage.setItem = originalSetItem;
    });

    it("handles other storage errors", () => {
      const originalSetItem = localStorage.setItem;
      localStorage.setItem = vi.fn(() => {
        throw new Error("Unknown error");
      });

      const result = storage.set("test", "value");
      expect(result).toBe(false);

      localStorage.setItem = originalSetItem;
    });
  });

  describe("remove", () => {
    it("removes prefixed key", () => {
      localStorage.setItem("studio-test", "value");
      storage.remove("test");
      expect(localStorage.getItem("studio-test")).toBeNull();
    });

    it("removes key with explicit prefix", () => {
      localStorage.setItem("studio-theme", "dark");
      storage.remove("studio-theme");
      expect(localStorage.getItem("studio-theme")).toBeNull();
    });

    it("handles non-existent key gracefully", () => {
      expect(() => storage.remove("nonexistent")).not.toThrow();
    });

    it("removes legacy key when key does not start with studio-", () => {
      localStorage.setItem("studio-legacy", "prefixed");
      localStorage.setItem("legacy", "not-prefixed");

      storage.remove("legacy");

      expect(localStorage.getItem("studio-legacy")).toBeNull();
      expect(localStorage.getItem("legacy")).toBeNull();
    });
  });

  describe("clear", () => {
    it("clears all studio-prefixed keys", () => {
      localStorage.setItem("studio-a", "1");
      localStorage.setItem("studio-b", "2");
      localStorage.setItem("other", "3");

      storage.clear();

      expect(localStorage.getItem("studio-a")).toBeNull();
      expect(localStorage.getItem("studio-b")).toBeNull();
      expect(localStorage.getItem("other")).toBe("3");
    });

    it("optionally clears auth tokens", () => {
      localStorage.setItem("access_token", "token");
      localStorage.setItem("refresh_token", "refresh");
      localStorage.setItem("auth_token", "auth");

      storage.clear(true);

      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
      expect(localStorage.getItem("auth_token")).toBeNull();
    });

    it("preserves auth tokens by default", () => {
      localStorage.setItem("access_token", "token");
      localStorage.setItem("studio-test", "value");

      storage.clear();

      expect(localStorage.getItem("access_token")).toBe("token");
    });
  });

  describe("keys", () => {
    it("returns empty array when no keys", () => {
      expect(storage.keys()).toEqual([]);
    });

    it("returns only studio-prefixed keys", () => {
      localStorage.setItem("studio-a", "1");
      localStorage.setItem("studio-b", "2");
      localStorage.setItem("other", "3");

      const keys = storage.keys();

      expect(keys).toContain("studio-a");
      expect(keys).toContain("studio-b");
      expect(keys).not.toContain("other");
    });
  });

  describe("stats", () => {
    it("returns zero stats when empty", () => {
      const stats = storage.stats();
      expect(stats).toEqual({ usedBytes: 0, keyCount: 0 });
    });

    it("counts only studio-prefixed keys", () => {
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
  it("has consistent prefixes", () => {
    // Most keys should have studio- prefix
    expect(STORAGE_KEYS.THEME).toMatch(/^studio-/);
    expect(STORAGE_KEYS.PREFERENCES).toMatch(/^studio-/);
    expect(STORAGE_KEYS.WORKSPACE).toMatch(/^studio-/);
    expect(STORAGE_KEYS.ONBOARDING).toMatch(/^studio-/);
  });

  it("has legacy auth keys without prefix", () => {
    // Auth tokens are legacy and don't have prefix
    expect(STORAGE_KEYS.ACCESS_TOKEN).not.toMatch(/^studio-/);
    expect(STORAGE_KEYS.REFRESH_TOKEN).not.toMatch(/^studio-/);
    expect(STORAGE_KEYS.AUTH_TOKEN).not.toMatch(/^studio-/);
  });
});

describe("getAuthToken", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("returns null when no tokens", () => {
    expect(getAuthToken()).toBeNull();
  });

  it("returns access_token when available", () => {
    localStorage.setItem("access_token", "test-token");
    expect(getAuthToken()).toBe("test-token");
  });

  it("falls back to auth_token", () => {
    localStorage.setItem("auth_token", "legacy-token");
    expect(getAuthToken()).toBe("legacy-token");
  });

  it("prefers access_token over auth_token", () => {
    localStorage.setItem("access_token", "new-token");
    localStorage.setItem("auth_token", "old-token");
    expect(getAuthToken()).toBe("new-token");
  });
});

describe("setAuthTokens", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("sets access_token and auth_token", () => {
    setAuthTokens("token123");

    expect(localStorage.getItem("access_token")).toBe("token123");
    expect(localStorage.getItem("auth_token")).toBe("token123");
  });

  it("optionally sets refresh_token", () => {
    setAuthTokens("access", "refresh");

    expect(localStorage.getItem("access_token")).toBe("access");
    expect(localStorage.getItem("refresh_token")).toBe("refresh");
  });
});

describe("clearAuthTokens", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("removes all auth tokens", () => {
    localStorage.setItem("access_token", "a");
    localStorage.setItem("refresh_token", "r");
    localStorage.setItem("auth_token", "l");

    clearAuthTokens();

    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
    expect(localStorage.getItem("auth_token")).toBeNull();
  });
});

// =============================================================================
// Enhanced STORAGE_KEYS Tests
// =============================================================================

describe("STORAGE_KEYS - comprehensive", () => {
  it("includes keys for all migrated hooks", () => {
    // Progressive disclosure
    expect(STORAGE_KEYS.DISCLOSURE_STATE).toBeDefined();
    expect(STORAGE_KEYS.DISCLOSURE_STATE).toMatch(/^studio-/);

    // Nudges
    expect(STORAGE_KEYS.NUDGE_HISTORY).toBeDefined();
    expect(STORAGE_KEYS.NUDGE_HISTORY).toMatch(/^studio-/);

    // Offline queue
    expect(STORAGE_KEYS.OFFLINE_QUEUE).toBeDefined();
    expect(STORAGE_KEYS.OFFLINE_QUEUE).toMatch(/^studio-/);
  });

  it("includes keys for canvas state", () => {
    expect(STORAGE_KEYS.CANVAS_LAYOUT).toBeDefined();
    expect(STORAGE_KEYS.CANVAS_ZOOM).toBeDefined();
  });

  it("includes keys for AI features", () => {
    expect(STORAGE_KEYS.AI_SUGGESTIONS_CACHE).toBeDefined();
    expect(STORAGE_KEYS.AI_CONTEXT_HISTORY).toBeDefined();
  });

  it("provides type safety - StorageKeyEnum type", () => {
    // These should be valid StorageKey values
    const key: StorageKey = STORAGE_KEYS.THEME;
    expect(key).toBe("studio-theme");
  });
});

// =============================================================================
// TTL/Expiration Support Tests
// =============================================================================

describe("storage.setWithTTL and getWithTTL", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    localStorage.clear();
    vi.useRealTimers();
  });

  describe("setWithTTL", () => {
    it("stores value with expiration metadata", () => {
      storage.setWithTTL("cache-key", { data: "test" }, 60000); // 60 seconds

      const stored = localStorage.getItem("studio-cache-key");
      expect(stored).toBeTruthy();

      const parsed = JSON.parse(stored!);
      expect(parsed.__value).toEqual({ data: "test" });
      expect(parsed.__expiresAt).toBeDefined();
      expect(typeof parsed.__expiresAt).toBe("number");
    });

    it("calculates correct expiration timestamp", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      storage.setWithTTL("test", "value", 5000); // 5 seconds

      const stored = JSON.parse(localStorage.getItem("studio-test")!);
      expect(stored.__expiresAt).toBe(now + 5000);
    });

    it("returns true on success", () => {
      const result = storage.setWithTTL("key", "value", 1000);
      expect(result).toBe(true);
    });

    it("handles complex objects", () => {
      const complexData = {
        users: [{ id: 1, name: "Test" }],
        metadata: { version: 2 },
      };
      storage.setWithTTL("complex", complexData, 10000);

      const stored = JSON.parse(localStorage.getItem("studio-complex")!);
      expect(stored.__value).toEqual(complexData);
    });
  });

  describe("getWithTTL", () => {
    it("returns value when not expired", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      storage.setWithTTL("fresh", "fresh-value", 60000);

      // Advance 30 seconds (still valid)
      vi.advanceTimersByTime(30000);

      const result = storage.getWithTTL<string>("fresh");
      expect(result).toBe("fresh-value");
    });

    it("returns undefined when expired", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      storage.setWithTTL("expiring", "will-expire", 5000);

      // Advance 6 seconds (expired)
      vi.advanceTimersByTime(6000);

      const result = storage.getWithTTL<string>("expiring");
      expect(result).toBeUndefined();
    });

    it("returns default value when expired", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      storage.setWithTTL("expiring", "old", 1000);
      vi.advanceTimersByTime(2000);

      const result = storage.getWithTTL<string>("expiring", "default");
      expect(result).toBe("default");
    });

    it("removes expired key from storage", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      storage.setWithTTL("cleanup", "data", 1000);
      vi.advanceTimersByTime(2000);

      storage.getWithTTL("cleanup");

      // Key should be cleaned up
      expect(localStorage.getItem("studio-cleanup")).toBeNull();
    });

    it("returns undefined for non-existent key", () => {
      const result = storage.getWithTTL("nonexistent");
      expect(result).toBeUndefined();
    });

    it("returns undefined for non-TTL value (no __expiresAt)", () => {
      // Regular storage.set (not setWithTTL)
      storage.set("regular", { data: "test" });

      const result = storage.getWithTTL("regular");
      expect(result).toBeUndefined();
    });

    it("handles malformed TTL data gracefully", () => {
      localStorage.setItem(
        "studio-malformed",
        JSON.stringify({ broken: true }),
      );

      const result = storage.getWithTTL("malformed", "fallback");
      expect(result).toBe("fallback");
    });
  });

  describe("TTL edge cases", () => {
    it("handles zero TTL (immediately expires)", () => {
      storage.setWithTTL("instant", "gone", 0);

      vi.advanceTimersByTime(1);

      const result = storage.getWithTTL("instant");
      expect(result).toBeUndefined();
    });

    it("handles very long TTL", () => {
      const oneYear = 365 * 24 * 60 * 60 * 1000;
      storage.setWithTTL("long-term", "persistent", oneYear);

      vi.advanceTimersByTime(oneYear - 1000);

      const result = storage.getWithTTL<string>("long-term");
      expect(result).toBe("persistent");
    });
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

  afterEach(() => {
    sessionStorage.clear();
  });

  describe("get", () => {
    it("returns undefined for non-existent key", () => {
      const result = sessionStore.get("missing");
      expect(result).toBeUndefined();
    });

    it("returns default value for non-existent key", () => {
      const result = sessionStore.get("missing", "default");
      expect(result).toBe("default");
    });

    it("parses JSON objects", () => {
      sessionStorage.setItem(
        "studio-session-test",
        JSON.stringify({ foo: "bar" }),
      );
      const result = sessionStore.get<{ foo: string }>("session-test");
      expect(result).toEqual({ foo: "bar" });
    });

    it("returns string values as-is", () => {
      sessionStorage.setItem("studio-session-str", "plain-string");
      const result = sessionStore.get<string>("session-str");
      expect(result).toBe("plain-string");
    });

    it("handles prefixed keys", () => {
      sessionStorage.setItem("studio-session-data", "value");
      const result = sessionStore.get<string>("studio-session-data");
      expect(result).toBe("value");
    });

    it("returns default value and logs warning when getItem throws", () => {
      // First call allows availability check to pass (uses setItem/removeItem with "__session_test__")
      // Then mock getItem to throw
      const getItemSpy = vi
        .spyOn(sessionStorage, "getItem")
        .mockImplementation(() => {
          throw new Error("Storage error");
        });

      const result = sessionStore.get<string>("test", "fallback");

      expect(result).toBe("fallback");
      getItemSpy.mockRestore();
    });
  });

  describe("set", () => {
    it("stores string values", () => {
      const success = sessionStore.set("test", "value");
      expect(success).toBe(true);
      expect(sessionStorage.getItem("studio-test")).toBe("value");
    });

    it("stores object values as JSON", () => {
      sessionStore.set("obj", { key: "value" });
      expect(sessionStorage.getItem("studio-obj")).toBe('{"key":"value"}');
    });

    it("stores arrays as JSON", () => {
      sessionStore.set("arr", [1, 2, 3]);
      expect(sessionStorage.getItem("studio-arr")).toBe("[1,2,3]");
    });

    it("returns false and logs error when setItem throws", () => {
      // First call allows availability check to pass (uses "__session_test__" key)
      // Second call is the actual set operation which throws
      const setItemSpy = vi
        .spyOn(sessionStorage, "setItem")
        .mockImplementationOnce(() => undefined) // Allow availability check
        .mockImplementationOnce(() => {
          throw new Error("QuotaExceededError");
        });

      const result = sessionStore.set("test", "value");

      expect(result).toBe(false);
      setItemSpy.mockRestore();
    });
  });

  describe("remove", () => {
    it("removes session storage key", () => {
      sessionStorage.setItem("studio-test", "value");
      sessionStore.remove("test");
      expect(sessionStorage.getItem("studio-test")).toBeNull();
    });

    it("handles errors gracefully when removeItem throws", () => {
      // Setup initial state
      sessionStorage.setItem("studio-test", "value");

      // First call allows availability check to pass
      // Second call is the actual remove operation which throws
      const removeItemSpy = vi
        .spyOn(sessionStorage, "removeItem")
        .mockImplementationOnce(() => undefined) // Allow availability check
        .mockImplementationOnce(() => {
          throw new Error("Storage error");
        });

      // Should not throw
      expect(() => sessionStore.remove("test")).not.toThrow();

      removeItemSpy.mockRestore();
    });
  });

  describe("clear", () => {
    it("clears all studio-prefixed session keys", () => {
      sessionStorage.setItem("studio-a", "1");
      sessionStorage.setItem("studio-b", "2");
      sessionStorage.setItem("other", "3");

      sessionStore.clear();

      expect(sessionStorage.getItem("studio-a")).toBeNull();
      expect(sessionStorage.getItem("studio-b")).toBeNull();
      expect(sessionStorage.getItem("other")).toBe("3");
    });

    it("handles errors gracefully during clear", () => {
      // Setup initial state
      sessionStorage.setItem("studio-test", "1");

      // First call allows availability check to pass
      // Subsequent calls are actual removes which throw
      const removeItemSpy = vi
        .spyOn(sessionStorage, "removeItem")
        .mockImplementationOnce(() => undefined) // Allow availability check
        .mockImplementation(() => {
          throw new Error("Storage quota exceeded");
        });

      // Should not throw
      expect(() => sessionStore.clear()).not.toThrow();

      // Restore spy properly to avoid polluting other tests
      removeItemSpy.mockRestore();
    });
  });

  describe("keys", () => {
    it("returns only studio-prefixed session keys", () => {
      sessionStorage.setItem("studio-x", "1");
      sessionStorage.setItem("studio-y", "2");
      sessionStorage.setItem("other", "3");

      const keys = sessionStore.keys();

      expect(keys).toContain("studio-x");
      expect(keys).toContain("studio-y");
      expect(keys).not.toContain("other");
    });
  });
});

// =============================================================================
// Session Storage with TTL Tests
// =============================================================================

describe("sessionStore TTL support", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    sessionStorage.clear();
    vi.useRealTimers();
  });

  it("supports setWithTTL", () => {
    sessionStore.setWithTTL("session-cache", { temp: "data" }, 30000);

    const stored = sessionStorage.getItem("studio-session-cache");
    expect(stored).toBeTruthy();

    const parsed = JSON.parse(stored!);
    expect(parsed.__value).toEqual({ temp: "data" });
    expect(parsed.__expiresAt).toBeDefined();
  });

  it("supports getWithTTL - returns value when fresh", () => {
    sessionStore.setWithTTL("fresh", "data", 10000);

    vi.advanceTimersByTime(5000);

    const result = sessionStore.getWithTTL<string>("fresh");
    expect(result).toBe("data");
  });

  it("supports getWithTTL - returns undefined when expired", () => {
    sessionStore.setWithTTL("expiring", "data", 5000);

    vi.advanceTimersByTime(6000);

    const result = sessionStore.getWithTTL("expiring");
    expect(result).toBeUndefined();
  });

  it("getWithTTL returns default value when data is not a TTL wrapper", () => {
    // Store a plain value (not a TTL wrapper)
    sessionStorage.setItem(
      "studio-plain-value",
      JSON.stringify({ foo: "bar" }),
    );

    const result = sessionStore.getWithTTL<string>(
      "plain-value",
      "default-val",
    );
    expect(result).toBe("default-val");
  });

  it("getWithTTL returns default value on JSON parse error", () => {
    // Store invalid JSON
    sessionStorage.setItem("studio-invalid-json", "not-valid-json{");

    const result = sessionStore.getWithTTL<string>("invalid-json", "fallback");
    expect(result).toBe("fallback");
  });

  it("getWithTTL returns data when using already-prefixed key", () => {
    // Store directly with prefixed key
    const wrapper = {
      __value: "prefixed-data",
      __expiresAt: Date.now() + 10000,
    };
    sessionStorage.setItem("studio-prefixed-ttl", JSON.stringify(wrapper));

    // getWithTTL should find it when passed the prefixed key
    const result = sessionStore.getWithTTL<string>("studio-prefixed-ttl");
    expect(result).toBe("prefixed-data");
  });
});

// =============================================================================
// Hook Storage Key Integration Tests
// =============================================================================

describe("STORAGE_KEYS - hook integration", () => {
  it("STORAGE_KEYS.NUDGE_HISTORY matches expected key format", () => {
    // useNudges should use this key
    expect(STORAGE_KEYS.NUDGE_HISTORY).toBe("studio-nudge_history");
  });

  it("STORAGE_KEYS.DISCLOSURE_STATE matches expected key format", () => {
    // useProgressiveDisclosure should use this key
    expect(STORAGE_KEYS.DISCLOSURE_STATE).toBe("studio-disclosure_state");
  });

  it("STORAGE_KEYS.OFFLINE_QUEUE matches expected key format", () => {
    // useOfflineQueue should use this key as default
    expect(STORAGE_KEYS.OFFLINE_QUEUE).toBe("studio-offline_queue");
  });

  it("STORAGE_KEYS.AI_SUGGESTIONS_CACHE matches expected format", () => {
    // AI suggestions should use TTL cache with this key
    expect(STORAGE_KEYS.AI_SUGGESTIONS_CACHE).toBe(
      "studio-ai-suggestions-cache",
    );
  });

  it("STORAGE_KEYS.SESSION_SYNC_STATE matches expected format", () => {
    // useSessionSync can use sessionStore with this key for temporary data
    expect(STORAGE_KEYS.SESSION_SYNC_STATE).toBe("studio-session-sync-state");
  });
});

// =============================================================================
// AI Suggestions Cache with TTL Tests
// =============================================================================

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

  it("can cache AI suggestions with 5-minute TTL", () => {
    const suggestions = [
      {
        id: "1",
        type: "completion",
        content: "test suggestion",
        confidence: 0.9,
      },
    ];

    // Cache with 5 min TTL
    const TTL_5_MIN = 5 * 60 * 1000;
    storage.setWithTTL(
      STORAGE_KEYS.AI_SUGGESTIONS_CACHE,
      suggestions,
      TTL_5_MIN,
    );

    // Should be available immediately
    const cached = storage.getWithTTL<typeof suggestions>(
      STORAGE_KEYS.AI_SUGGESTIONS_CACHE,
    );
    expect(cached).toEqual(suggestions);
  });

  it("AI suggestions cache expires after TTL", () => {
    const suggestions = [{ id: "1", content: "test" }];
    const TTL_5_MIN = 5 * 60 * 1000;

    storage.setWithTTL(
      STORAGE_KEYS.AI_SUGGESTIONS_CACHE,
      suggestions,
      TTL_5_MIN,
    );

    // Advance time past TTL
    vi.advanceTimersByTime(TTL_5_MIN + 1000);

    const cached = storage.getWithTTL(STORAGE_KEYS.AI_SUGGESTIONS_CACHE);
    expect(cached).toBeUndefined();
  });

  it("sessionStore is suitable for per-session AI context", () => {
    const context = { sessionId: "123", artifactId: "456" };

    sessionStore.set(STORAGE_KEYS.AI_CONTEXT_HISTORY, context);

    const retrieved = sessionStore.get<typeof context>(
      STORAGE_KEYS.AI_CONTEXT_HISTORY,
    );
    expect(retrieved).toEqual(context);
  });

  it("sessionStore with TTL for temporary AI preferences", () => {
    const tempPrefs = { autoSuggest: true, model: "claude-3" };
    const TTL_30_MIN = 30 * 60 * 1000;

    sessionStore.setWithTTL(STORAGE_KEYS.AI_PREFERENCES, tempPrefs, TTL_30_MIN);

    // Still valid at 25 min
    vi.advanceTimersByTime(25 * 60 * 1000);
    const prefs = sessionStore.getWithTTL<typeof tempPrefs>(
      STORAGE_KEYS.AI_PREFERENCES,
    );
    expect(prefs).toEqual(tempPrefs);

    // Expired at 35 min
    vi.advanceTimersByTime(10 * 60 * 1000);
    const expired = sessionStore.getWithTTL(STORAGE_KEYS.AI_PREFERENCES);
    expect(expired).toBeUndefined();
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

  afterEach(() => {
    localStorage.clear();
  });

  it("migrates value from legacy key to new key", () => {
    // Set up legacy key (without prefix)
    localStorage.setItem("old_preferences", JSON.stringify({ theme: "dark" }));

    // Migrate to new key
    const migrated = storage.migrate(
      "old_preferences",
      STORAGE_KEYS.PREFERENCES,
    );

    expect(migrated).toBe(true);

    // New key should have the value
    const newValue = storage.get<{ theme: string }>(STORAGE_KEYS.PREFERENCES);
    expect(newValue).toEqual({ theme: "dark" });

    // Legacy key should be removed
    expect(localStorage.getItem("old_preferences")).toBeNull();
  });

  it("returns false if legacy key does not exist", () => {
    const migrated = storage.migrate(
      "nonexistent_key",
      STORAGE_KEYS.PREFERENCES,
    );

    expect(migrated).toBe(false);
  });

  it("does not overwrite if target key already exists", () => {
    // Set up both keys
    localStorage.setItem("old_key", JSON.stringify({ old: true }));
    storage.set(STORAGE_KEYS.PREFERENCES, { new: true });

    // Attempt migration
    const migrated = storage.migrate("old_key", STORAGE_KEYS.PREFERENCES);

    expect(migrated).toBe(false);

    // New key should keep original value
    const value = storage.get<{ new: boolean }>(STORAGE_KEYS.PREFERENCES);
    expect(value).toEqual({ new: true });
  });

  it("supports force option to overwrite target", () => {
    // Set up both keys
    localStorage.setItem("old_key", JSON.stringify({ old: true }));
    storage.set(STORAGE_KEYS.PREFERENCES, { new: true });

    // Force migration
    const migrated = storage.migrate("old_key", STORAGE_KEYS.PREFERENCES, {
      force: true,
    });

    expect(migrated).toBe(true);

    // New key should have old value
    const value = storage.get<{ old: boolean }>(STORAGE_KEYS.PREFERENCES);
    expect(value).toEqual({ old: true });
  });

  it("handles string values (non-JSON)", () => {
    localStorage.setItem("old_theme", "dark");

    const migrated = storage.migrate("old_theme", STORAGE_KEYS.THEME);

    expect(migrated).toBe(true);
    expect(storage.get<string>(STORAGE_KEYS.THEME)).toBe("dark");
  });

  it("returns false when localStorage throws during migration", () => {
    // Set up legacy key
    localStorage.setItem("old_key", JSON.stringify({ value: "data" }));

    // Save original and track call count
    const originalSetItem = window.localStorage.setItem.bind(
      window.localStorage,
    );
    let callCount = 0;

    // First call allows availability check, second call (the actual setItem) throws
    window.localStorage.setItem = vi.fn((key: string, value: string) => {
      callCount++;
      if (callCount === 1) {
        // Allow availability check (uses "__storage_test__")
        return originalSetItem(key, value);
      }
      // Throw on subsequent calls (the migration setItem)
      throw new Error("QuotaExceededError");
    });

    const migrated = storage.migrate("old_key", STORAGE_KEYS.PREFERENCES);

    expect(migrated).toBe(false);

    // Restore
    window.localStorage.setItem = originalSetItem;
  });
});

// =============================================================================
// Storage Quota Monitoring Tests
// =============================================================================

describe("storage.getQuotaInfo", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("returns current usage statistics", () => {
    // Add some data
    storage.set("test1", { data: "value1" });
    storage.set("test2", { data: "value2" });

    const quota = storage.getQuotaInfo();

    expect(quota.usedBytes).toBeGreaterThan(0);
    expect(quota.keyCount).toBeGreaterThanOrEqual(2);
    expect(quota.percentUsed).toBeGreaterThanOrEqual(0);
    expect(quota.percentUsed).toBeLessThanOrEqual(100);
  });

  it("returns estimated available space", () => {
    const quota = storage.getQuotaInfo();

    expect(quota.estimatedQuota).toBeGreaterThan(0);
    expect(quota.availableBytes).toBeGreaterThan(0);
  });

  it("identifies largest keys", () => {
    // Add data of varying sizes
    storage.set("small", "a");
    storage.set("medium", "a".repeat(100));
    storage.set("large", "a".repeat(1000));

    const quota = storage.getQuotaInfo();

    expect(quota.largestKeys).toBeDefined();
    expect(quota.largestKeys.length).toBeGreaterThan(0);
    expect(quota.largestKeys[0].key).toBe("studio-large");
  });

  it("returns empty quota info when localStorage is unavailable", () => {
    // Mock window.localStorage.setItem to throw on availability check
    const originalSetItem = window.localStorage.setItem;
    window.localStorage.setItem = vi.fn(() => {
      throw new Error("localStorage disabled");
    });

    const quota = storage.getQuotaInfo();

    expect(quota.usedBytes).toBe(0);
    expect(quota.keyCount).toBe(0);
    expect(quota.percentUsed).toBe(0);
    expect(quota.largestKeys).toEqual([]);

    // Restore
    window.localStorage.setItem = originalSetItem;
  });
});

describe("storage.isNearQuota", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("returns false when storage is mostly empty", () => {
    storage.set("small", "test");

    const nearQuota = storage.isNearQuota();

    expect(nearQuota).toBe(false);
  });

  it("accepts custom threshold percentage", () => {
    // Verify the API works with custom threshold
    const nearQuota = storage.isNearQuota(0.001); // 0.1% threshold

    // Even a small amount of data could trigger this
    expect(typeof nearQuota).toBe("boolean");
  });

  it("uses default 90% threshold", () => {
    // With mostly empty storage, should be false
    const nearQuota = storage.isNearQuota();
    expect(nearQuota).toBe(false);
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

  it("removes expired TTL entries", () => {
    const now = Date.now();
    vi.setSystemTime(now);

    // Set up some TTL entries
    storage.setWithTTL("fresh", "still-valid", 60000); // 60s TTL
    storage.setWithTTL("stale", "should-expire", 1000); // 1s TTL

    // Advance time past the shorter TTL
    vi.advanceTimersByTime(5000);

    // Run cleanup
    const result = storage.cleanup();

    expect(result.removedCount).toBeGreaterThanOrEqual(1);
    expect(result.freedBytes).toBeGreaterThan(0);

    // Fresh entry should still exist
    const fresh = storage.getWithTTL<string>("fresh");
    expect(fresh).toBe("still-valid");

    // Stale entry should be gone
    const stale = storage.getWithTTL<string>("stale");
    expect(stale).toBeUndefined();
  });

  it("returns cleanup result shape", () => {
    // Verify the API exists and returns expected shape
    const result = storage.cleanup({ maxAge: 1000 });

    expect(result).toHaveProperty("removedCount");
    expect(result).toHaveProperty("freedBytes");
  });

  it("returns zero when no expired entries", () => {
    const now = Date.now();
    vi.setSystemTime(now);

    // Set up non-expired entries
    storage.setWithTTL("valid1", "data1", 60000);
    storage.setWithTTL("valid2", "data2", 60000);

    const result = storage.cleanup();

    expect(result.removedCount).toBe(0);
    expect(result.freedBytes).toBe(0);
  });

  it("handles mixed expired and valid entries", () => {
    const now = Date.now();
    vi.setSystemTime(now);

    // Set up mixed entries
    storage.setWithTTL("valid", "still-good", 60000);
    storage.setWithTTL("expired1", "bye1", 1000);
    storage.setWithTTL("expired2", "bye2", 2000);

    // Advance past both short TTLs
    vi.advanceTimersByTime(3000);

    const result = storage.cleanup();

    expect(result.removedCount).toBe(2);
    expect(result.freedBytes).toBeGreaterThan(0);

    // Valid entry remains
    expect(storage.getWithTTL<string>("valid")).toBe("still-good");
  });

  it("returns zero counts when localStorage is unavailable", () => {
    // Mock localStorage.setItem to throw, making isLocalStorageAvailable() return false
    const setItemSpy = vi
      .spyOn(localStorage, "setItem")
      .mockImplementation(() => {
        throw new Error("localStorage disabled");
      });

    const result = storage.cleanup();

    expect(result).toEqual({ removedCount: 0, freedBytes: 0 });
    setItemSpy.mockRestore();
  });
});
