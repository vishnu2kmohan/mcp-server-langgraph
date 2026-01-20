/**
 * PWA Update Hook Tests
 *
 * TDD tests for the usePWAUpdate hook that manages
 * service worker updates and offline readiness.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePWAUpdate } from "./usePWAUpdate";

// Mock the virtual:pwa-register/react module
const mockUpdateServiceWorker = vi.fn().mockResolvedValue(undefined);
const mockUseRegisterSW = vi.fn();

vi.mock("virtual:pwa-register/react", () => ({
  useRegisterSW: (options?: {
    onNeedRefresh?: () => void;
    onOfflineReady?: () => void;
    onRegistered?: (
      registration: ServiceWorkerRegistration | undefined,
    ) => void;
    onRegisterError?: (error: Error) => void;
  }) => {
    mockUseRegisterSW(options);
    return {
      needRefresh: [false, vi.fn()],
      offlineReady: [false, vi.fn()],
      updateServiceWorker: mockUpdateServiceWorker,
    };
  },
}));

describe("usePWAUpdate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Initial State", () => {
    it("should return initial state with no update needed", () => {
      const { result } = renderHook(() => usePWAUpdate());

      expect(result.current.needsUpdate).toBe(false);
      expect(result.current.isOfflineReady).toBe(false);
      expect(result.current.isUpdating).toBe(false);
    });

    it("should expose updateApp function", () => {
      const { result } = renderHook(() => usePWAUpdate());

      expect(typeof result.current.updateApp).toBe("function");
    });

    it("should expose dismissUpdate function", () => {
      const { result } = renderHook(() => usePWAUpdate());

      expect(typeof result.current.dismissUpdate).toBe("function");
    });
  });

  describe("Update Flow", () => {
    it("should call updateServiceWorker when updateApp is called", async () => {
      const { result } = renderHook(() => usePWAUpdate());

      await act(async () => {
        await result.current.updateApp();
      });

      expect(mockUpdateServiceWorker).toHaveBeenCalledWith(true);
    });

    it("should set isUpdating to true during update", async () => {
      // Create a delayed update to test isUpdating
      mockUpdateServiceWorker.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100)),
      );

      const { result } = renderHook(() => usePWAUpdate());

      let updatePromise: Promise<void>;
      act(() => {
        updatePromise = result.current.updateApp();
      });

      // Check isUpdating is true during update
      expect(result.current.isUpdating).toBe(true);

      await act(async () => {
        await updatePromise;
      });
    });

    it("should handle update errors gracefully", async () => {
      const error = new Error("Update failed");
      mockUpdateServiceWorker.mockRejectedValueOnce(error);

      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const { result } = renderHook(() => usePWAUpdate());

      await act(async () => {
        await result.current.updateApp();
      });

      expect(consoleSpy).toHaveBeenCalledWith(
        "[PWAUpdate] Failed to update service worker:",
        error,
      );

      consoleSpy.mockRestore();
    });
  });

  describe("Dismiss Update", () => {
    it("should reset needsUpdate when dismissUpdate is called", async () => {
      const { result } = renderHook(() => usePWAUpdate());

      act(() => {
        result.current.dismissUpdate();
      });

      // The hook should track dismissed state
      expect(result.current.updateDismissed).toBe(true);
    });
  });

  describe("Registration", () => {
    it("should register with onNeedRefresh callback", () => {
      renderHook(() => usePWAUpdate());

      expect(mockUseRegisterSW).toHaveBeenCalledWith(
        expect.objectContaining({
          onNeedRefresh: expect.any(Function),
        }),
      );
    });

    it("should register with onOfflineReady callback", () => {
      renderHook(() => usePWAUpdate());

      expect(mockUseRegisterSW).toHaveBeenCalledWith(
        expect.objectContaining({
          onOfflineReady: expect.any(Function),
        }),
      );
    });

    it("should register with onRegistered callback", () => {
      renderHook(() => usePWAUpdate());

      expect(mockUseRegisterSW).toHaveBeenCalledWith(
        expect.objectContaining({
          onRegistered: expect.any(Function),
        }),
      );
    });

    it("should register with onRegisterError callback", () => {
      renderHook(() => usePWAUpdate());

      expect(mockUseRegisterSW).toHaveBeenCalledWith(
        expect.objectContaining({
          onRegisterError: expect.any(Function),
        }),
      );
    });
  });
});
