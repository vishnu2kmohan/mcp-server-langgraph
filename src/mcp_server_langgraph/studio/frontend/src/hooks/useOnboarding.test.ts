/**
 * useOnboarding Hook Tests
 *
 * Tests for the onboarding state management hook.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useOnboarding } from "./useOnboarding";

describe("useOnboarding", () => {
  // Mock localStorage
  const localStorageMock = {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, "localStorage", {
      value: localStorageMock,
      writable: true,
    });
  });

  describe("Initial State", () => {
    it("should read from localStorage on mount", async () => {
      localStorageMock.getItem.mockReturnValue(null);
      renderHook(() => useOnboarding());

      // Should have called localStorage
      await waitFor(() => {
        expect(localStorageMock.getItem).toHaveBeenCalledWith(
          "langgraph_onboarding_completed",
        );
      });
    });

    it("should show modal when onboarding not completed", async () => {
      localStorageMock.getItem.mockReturnValue(null);
      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isCompleted).toBe(false);
      expect(result.current.shouldShowModal).toBe(true);
    });

    it("should not show modal when onboarding completed", async () => {
      localStorageMock.getItem.mockReturnValue("true");
      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isCompleted).toBe(true);
      expect(result.current.shouldShowModal).toBe(false);
    });
  });

  describe("complete()", () => {
    it("should mark onboarding as completed", async () => {
      localStorageMock.getItem.mockReturnValue(null);
      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      act(() => {
        result.current.complete();
      });

      expect(result.current.isCompleted).toBe(true);
      expect(result.current.shouldShowModal).toBe(false);
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "langgraph_onboarding_completed",
        "true",
      );
    });
  });

  describe("skip()", () => {
    it("should hide modal without persisting to localStorage", async () => {
      localStorageMock.getItem.mockReturnValue(null);
      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      act(() => {
        result.current.skip();
      });

      expect(result.current.isCompleted).toBe(true);
      expect(result.current.shouldShowModal).toBe(false);
      // Skip should not persist
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });
  });

  describe("reset()", () => {
    it("should reset onboarding state", async () => {
      localStorageMock.getItem.mockReturnValue("true");
      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      act(() => {
        result.current.reset();
      });

      expect(result.current.isCompleted).toBe(false);
      expect(result.current.shouldShowModal).toBe(true);
      expect(localStorageMock.removeItem).toHaveBeenCalledWith(
        "langgraph_onboarding_completed",
      );
    });
  });

  describe("localStorage Errors", () => {
    it("should handle localStorage getItem errors gracefully", async () => {
      localStorageMock.getItem.mockImplementation(() => {
        throw new Error("localStorage not available");
      });

      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should default to completed (don't show modal on error)
      expect(result.current.isCompleted).toBe(true);
    });

    it("should handle localStorage setItem errors gracefully", async () => {
      localStorageMock.getItem.mockReturnValue(null);
      localStorageMock.setItem.mockImplementation(() => {
        throw new Error("localStorage full");
      });

      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should not throw
      act(() => {
        result.current.complete();
      });

      // State should still update even if localStorage fails
      expect(result.current.isCompleted).toBe(true);
    });
  });
});
