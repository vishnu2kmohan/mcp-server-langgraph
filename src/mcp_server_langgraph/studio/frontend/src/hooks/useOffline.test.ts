/**
 * useOffline Hook Tests
 *
 * TDD tests for offline detection hook used in PWA support.
 * Tests cover:
 * - Online/offline state detection
 * - Event listener cleanup
 * - Initial state
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useOffline } from "./useOffline";

describe("useOffline", () => {
  let originalOnLine: boolean;

  beforeEach(() => {
    originalOnLine = navigator.onLine;
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Restore original onLine value
    Object.defineProperty(navigator, "onLine", {
      value: originalOnLine,
      configurable: true,
      writable: true,
    });
  });

  it("should return false when online", () => {
    Object.defineProperty(navigator, "onLine", {
      value: true,
      configurable: true,
    });

    const { result } = renderHook(() => useOffline());
    expect(result.current).toBe(false);
  });

  it("should return true when offline", () => {
    Object.defineProperty(navigator, "onLine", {
      value: false,
      configurable: true,
    });

    const { result } = renderHook(() => useOffline());
    expect(result.current).toBe(true);
  });

  it("should update when going offline", () => {
    Object.defineProperty(navigator, "onLine", {
      value: true,
      configurable: true,
    });

    const { result } = renderHook(() => useOffline());
    expect(result.current).toBe(false);

    // Simulate going offline
    Object.defineProperty(navigator, "onLine", {
      value: false,
      configurable: true,
    });

    act(() => {
      window.dispatchEvent(new Event("offline"));
    });

    expect(result.current).toBe(true);
  });

  it("should update when going online", () => {
    Object.defineProperty(navigator, "onLine", {
      value: false,
      configurable: true,
    });

    const { result } = renderHook(() => useOffline());
    expect(result.current).toBe(true);

    // Simulate going online
    Object.defineProperty(navigator, "onLine", {
      value: true,
      configurable: true,
    });

    act(() => {
      window.dispatchEvent(new Event("online"));
    });

    expect(result.current).toBe(false);
  });

  it("should cleanup event listeners on unmount", () => {
    const addEventListenerSpy = vi.spyOn(window, "addEventListener");
    const removeEventListenerSpy = vi.spyOn(window, "removeEventListener");

    const { unmount } = renderHook(() => useOffline());

    expect(addEventListenerSpy).toHaveBeenCalledWith(
      "online",
      expect.any(Function),
    );
    expect(addEventListenerSpy).toHaveBeenCalledWith(
      "offline",
      expect.any(Function),
    );

    unmount();

    expect(removeEventListenerSpy).toHaveBeenCalledWith(
      "online",
      expect.any(Function),
    );
    expect(removeEventListenerSpy).toHaveBeenCalledWith(
      "offline",
      expect.any(Function),
    );

    addEventListenerSpy.mockRestore();
    removeEventListenerSpy.mockRestore();
  });
});
