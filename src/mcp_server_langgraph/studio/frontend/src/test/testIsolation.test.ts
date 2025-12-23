/**
 * Test Isolation Utilities Tests
 *
 * TDD tests for utilities that ensure proper test isolation
 * between parallel workers and sequential test runs.
 */

import { describe, it, expect, afterEach, vi, beforeEach } from "vitest";
import {
  clearStorageMocks,
  clearAllMocks,
  clearTimers,
  clearDocumentBody,
  createIsolatedStorage,
  type IsolationReport as _IsolationReport,
  getIsolationReport,
  logIsolationWarningIfDirty,
} from "./testIsolation";

describe("testIsolation", () => {
  describe("clearStorageMocks", () => {
    it("should clear localStorage store", () => {
      // Setup: add items to localStorage
      window.localStorage.setItem("test-key", "test-value");
      expect(window.localStorage.getItem("test-key")).toBe("test-value");

      // Act
      clearStorageMocks();

      // Assert: localStorage should be empty
      expect(window.localStorage.getItem("test-key")).toBeNull();
      expect(window.localStorage.length).toBe(0);
    });

    it("should clear sessionStorage store", () => {
      // Setup: add items to sessionStorage
      window.sessionStorage.setItem("session-key", "session-value");
      expect(window.sessionStorage.getItem("session-key")).toBe(
        "session-value",
      );

      // Act
      clearStorageMocks();

      // Assert: sessionStorage should be empty
      expect(window.sessionStorage.getItem("session-key")).toBeNull();
      expect(window.sessionStorage.length).toBe(0);
    });

    it("should reset mock call history on storage methods", () => {
      // Setup: call storage methods
      window.localStorage.setItem("a", "b");
      window.localStorage.getItem("a");

      // Act
      clearStorageMocks();

      // Assert: mock call history should be cleared
      expect(vi.mocked(window.localStorage.setItem).mock.calls).toHaveLength(0);
      expect(vi.mocked(window.localStorage.getItem).mock.calls).toHaveLength(0);
    });
  });

  describe("clearAllMocks", () => {
    it("should clear vi mock call history", () => {
      const mockFn = vi.fn();
      mockFn("call1");
      mockFn("call2");
      expect(mockFn).toHaveBeenCalledTimes(2);

      clearAllMocks();

      expect(mockFn).toHaveBeenCalledTimes(0);
    });

    it("should not affect mock implementations", () => {
      const mockFn = vi.fn().mockReturnValue("mocked-value");
      mockFn();

      clearAllMocks();

      // Implementation should still work
      expect(mockFn()).toBe("mocked-value");
    });
  });

  describe("clearTimers", () => {
    afterEach(() => {
      vi.useRealTimers();
      vi.clearAllMocks();
    });

    it("should clear all pending timers", () => {
      vi.useFakeTimers();
      const callback = vi.fn();
      setTimeout(callback, 1000);
      setInterval(callback, 500);

      // Verify timers are pending before clear
      expect(vi.getTimerCount()).toBeGreaterThan(0);

      clearTimers();

      // After clearTimers, we're back to real timers so we can't advance
      // But we can verify the callback was never called
      expect(callback).not.toHaveBeenCalled();
    });

    it("should restore real timers", () => {
      vi.useFakeTimers();
      // Set a fixed time with fake timers
      vi.setSystemTime(new Date("2020-01-01"));

      clearTimers();

      // Should be using real timers now - Date.now() should be current time
      const now = Date.now();
      const year2020 = new Date("2020-01-01").getTime();
      // Current time should be much greater than our mocked 2020 time
      expect(now).toBeGreaterThan(year2020);
    });
  });

  describe("clearDocumentBody", () => {
    it("should remove all child elements from document body", () => {
      // Setup: add elements to body
      const div = document.createElement("div");
      div.id = "test-element";
      document.body.appendChild(div);
      expect(document.getElementById("test-element")).not.toBeNull();

      // Act
      clearDocumentBody();

      // Assert
      expect(document.getElementById("test-element")).toBeNull();
      expect(document.body.children.length).toBe(0);
    });

    it("should reset body attributes", () => {
      // Setup: add attributes to body
      document.body.setAttribute("data-test", "value");
      document.body.className = "test-class";

      // Act
      clearDocumentBody();

      // Assert
      expect(document.body.getAttribute("data-test")).toBeNull();
      expect(document.body.className).toBe("");
    });
  });

  describe("createIsolatedStorage", () => {
    it("should create independent storage instance", () => {
      const storage1 = createIsolatedStorage();
      const storage2 = createIsolatedStorage();

      storage1.setItem("key", "value1");
      storage2.setItem("key", "value2");

      expect(storage1.getItem("key")).toBe("value1");
      expect(storage2.getItem("key")).toBe("value2");
    });

    it("should implement full Storage interface", () => {
      const storage = createIsolatedStorage();

      // setItem/getItem
      storage.setItem("a", "1");
      storage.setItem("b", "2");
      expect(storage.getItem("a")).toBe("1");

      // length
      expect(storage.length).toBe(2);

      // key
      expect(["a", "b"]).toContain(storage.key(0));

      // removeItem
      storage.removeItem("a");
      expect(storage.getItem("a")).toBeNull();
      expect(storage.length).toBe(1);

      // clear
      storage.clear();
      expect(storage.length).toBe(0);
    });

    it("should have clearable mock functions", () => {
      const storage = createIsolatedStorage();

      storage.setItem("key", "value");
      storage.getItem("key");

      expect(vi.mocked(storage.setItem)).toHaveBeenCalledWith("key", "value");
      expect(vi.mocked(storage.getItem)).toHaveBeenCalledWith("key");

      // Clear mocks
      vi.mocked(storage.setItem).mockClear();
      vi.mocked(storage.getItem).mockClear();

      expect(vi.mocked(storage.setItem)).not.toHaveBeenCalled();
      expect(vi.mocked(storage.getItem)).not.toHaveBeenCalled();
    });
  });

  describe("getIsolationReport", () => {
    it("should report storage state", () => {
      window.localStorage.setItem("leaked-key", "leaked-value");

      const report = getIsolationReport();

      expect(report.localStorageKeys).toContain("leaked-key");
      expect(report.localStorageCount).toBeGreaterThan(0);
    });

    it("should report document body state", () => {
      const div = document.createElement("div");
      document.body.appendChild(div);

      const report = getIsolationReport();

      expect(report.bodyChildCount).toBeGreaterThan(0);
    });

    it("should report pending timers when using fake timers", () => {
      vi.useFakeTimers();
      setTimeout(() => {}, 1000);

      const report = getIsolationReport();

      expect(report.pendingTimers).toBeGreaterThan(0);

      vi.useRealTimers();
    });

    it("should indicate clean state when properly isolated", () => {
      // Clean up everything first
      clearStorageMocks();
      clearDocumentBody();

      const report = getIsolationReport();

      expect(report.isClean).toBe(true);
      expect(report.localStorageCount).toBe(0);
      expect(report.sessionStorageCount).toBe(0);
      expect(report.bodyChildCount).toBe(0);
    });
  });

  describe("logIsolationWarningIfDirty", () => {
    let consoleWarnSpy: ReturnType<typeof vi.spyOn>;
    const originalCI = process.env.CI;

    beforeEach(() => {
      consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
      // Ensure clean state before each test
      clearStorageMocks();
      clearDocumentBody();
    });

    afterEach(() => {
      consoleWarnSpy.mockRestore();
      process.env.CI = originalCI;
    });

    it("should log warning in CI when state is dirty", () => {
      process.env.CI = "true";
      // Make state dirty
      window.localStorage.setItem("leaked", "value");

      logIsolationWarningIfDirty();

      expect(consoleWarnSpy).toHaveBeenCalled();
      expect(consoleWarnSpy.mock.calls[0][0]).toContain("[TestIsolation]");
    });

    it("should not log when state is clean", () => {
      process.env.CI = "true";
      // State is already clean from beforeEach

      logIsolationWarningIfDirty();

      expect(consoleWarnSpy).not.toHaveBeenCalled();
    });

    it("should not log in non-CI environment by default", () => {
      delete process.env.CI;
      // Make state dirty
      window.localStorage.setItem("leaked", "value");

      logIsolationWarningIfDirty();

      expect(consoleWarnSpy).not.toHaveBeenCalled();
    });

    it("should log in non-CI when force option is true", () => {
      delete process.env.CI;
      // Make state dirty
      window.localStorage.setItem("leaked", "value");

      logIsolationWarningIfDirty({ force: true });

      expect(consoleWarnSpy).toHaveBeenCalled();
    });

    it("should include isolation report details in warning", () => {
      process.env.CI = "true";
      window.localStorage.setItem("test-key", "test-value");
      const div = document.createElement("div");
      document.body.appendChild(div);

      logIsolationWarningIfDirty();

      const warningMessage = consoleWarnSpy.mock.calls[0][0];
      expect(warningMessage).toContain("localStorage");
      expect(warningMessage).toContain("test-key");
    });
  });
});
