/**
 * Tests for unified storage layer
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  storage,
  STORAGE_KEYS,
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
