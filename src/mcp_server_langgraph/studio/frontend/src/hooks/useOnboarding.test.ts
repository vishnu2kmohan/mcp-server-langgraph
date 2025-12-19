/**
 * useOnboarding Tests
 *
 * TDD tests for the Onboarding hook.
 * Tests cover:
 * - First-time user detection
 * - Onboarding completion tracking
 * - Step navigation
 * - Skip functionality
 * - Persistence
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useOnboarding } from "./useOnboarding";

describe("useOnboarding", () => {
  let originalLocalStorage: Storage;

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock localStorage
    originalLocalStorage = window.localStorage;
    const storage: Record<string, string> = {};
    const mockStorage = {
      getItem: vi.fn((key: string) => storage[key] || null),
      setItem: vi.fn((key: string, value: string) => {
        storage[key] = value;
      }),
      removeItem: vi.fn((key: string) => {
        delete storage[key];
      }),
      clear: vi.fn(() => {
        Object.keys(storage).forEach((key) => delete storage[key]);
      }),
      length: 0,
      key: vi.fn(),
    };
    Object.defineProperty(window, "localStorage", { value: mockStorage });
  });

  afterEach(() => {
    Object.defineProperty(window, "localStorage", {
      value: originalLocalStorage,
    });
  });

  describe("first-time user detection", () => {
    it("should detect first-time user", () => {
      const { result } = renderHook(() => useOnboarding());
      expect(result.current.isFirstTime).toBe(true);
    });

    it("should not be first-time if onboarding completed", () => {
      (
        window.localStorage.getItem as ReturnType<typeof vi.fn>
      ).mockReturnValueOnce(JSON.stringify({ completed: true }));
      const { result } = renderHook(() => useOnboarding());
      expect(result.current.isFirstTime).toBe(false);
    });
  });

  describe("onboarding state", () => {
    it("should start with showOnboarding false", () => {
      const { result } = renderHook(() => useOnboarding());
      expect(result.current.showOnboarding).toBe(false);
    });

    it("should start onboarding", () => {
      const { result } = renderHook(() => useOnboarding());
      act(() => {
        result.current.startOnboarding();
      });
      expect(result.current.showOnboarding).toBe(true);
    });

    it("should close onboarding", () => {
      const { result } = renderHook(() => useOnboarding());
      act(() => {
        result.current.startOnboarding();
      });
      act(() => {
        result.current.closeOnboarding();
      });
      expect(result.current.showOnboarding).toBe(false);
    });
  });

  describe("step navigation", () => {
    it("should start at step 0", () => {
      const { result } = renderHook(() => useOnboarding());
      act(() => {
        result.current.startOnboarding();
      });
      expect(result.current.currentStep).toBe(0);
    });

    it("should advance to next step", () => {
      const { result } = renderHook(() => useOnboarding());
      act(() => {
        result.current.startOnboarding();
      });
      act(() => {
        result.current.nextStep();
      });
      expect(result.current.currentStep).toBe(1);
    });

    it("should go back to previous step", () => {
      const { result } = renderHook(() => useOnboarding());
      act(() => {
        result.current.startOnboarding();
      });
      act(() => {
        result.current.nextStep();
        result.current.nextStep();
      });
      act(() => {
        result.current.previousStep();
      });
      expect(result.current.currentStep).toBe(1);
    });

    it("should not go below step 0", () => {
      const { result } = renderHook(() => useOnboarding());
      act(() => {
        result.current.startOnboarding();
      });
      act(() => {
        result.current.previousStep();
      });
      expect(result.current.currentStep).toBe(0);
    });

    it("should go to specific step", () => {
      const { result } = renderHook(() => useOnboarding());
      act(() => {
        result.current.startOnboarding();
      });
      act(() => {
        result.current.goToStep(2);
      });
      expect(result.current.currentStep).toBe(2);
    });
  });

  describe("completion", () => {
    it("should complete onboarding", () => {
      const { result } = renderHook(() => useOnboarding());
      act(() => {
        result.current.startOnboarding();
      });
      act(() => {
        result.current.completeOnboarding();
      });
      expect(result.current.showOnboarding).toBe(false);
      expect(result.current.isFirstTime).toBe(false);
    });

    it("should persist completion to localStorage", () => {
      const { result } = renderHook(() => useOnboarding());
      act(() => {
        result.current.completeOnboarding();
      });
      expect(window.localStorage.setItem).toHaveBeenCalledWith(
        "studio-onboarding",
        expect.stringContaining('"completed":true'),
      );
    });
  });

  describe("skip", () => {
    it("should skip onboarding", () => {
      const { result } = renderHook(() => useOnboarding());
      act(() => {
        result.current.startOnboarding();
      });
      act(() => {
        result.current.skipOnboarding();
      });
      expect(result.current.showOnboarding).toBe(false);
    });

    it("should mark as completed when skipping", () => {
      const { result } = renderHook(() => useOnboarding());
      act(() => {
        result.current.skipOnboarding();
      });
      expect(result.current.isFirstTime).toBe(false);
    });
  });

  describe("steps data", () => {
    it("should provide onboarding steps", () => {
      const { result } = renderHook(() => useOnboarding());
      expect(result.current.steps).toBeDefined();
      expect(result.current.steps.length).toBeGreaterThan(0);
    });

    it("should have step with title and description", () => {
      const { result } = renderHook(() => useOnboarding());
      const firstStep = result.current.steps[0];
      expect(firstStep.title).toBeDefined();
      expect(firstStep.description).toBeDefined();
    });

    it("should provide total steps count", () => {
      const { result } = renderHook(() => useOnboarding());
      expect(result.current.totalSteps).toBe(result.current.steps.length);
    });

    it("should track if on last step", () => {
      const { result } = renderHook(() => useOnboarding());
      act(() => {
        result.current.startOnboarding();
      });
      for (let i = 0; i < result.current.totalSteps - 1; i++) {
        act(() => {
          result.current.nextStep();
        });
      }
      expect(result.current.isLastStep).toBe(true);
    });
  });

  describe("reset", () => {
    it("should reset onboarding state", () => {
      const { result } = renderHook(() => useOnboarding());
      act(() => {
        result.current.completeOnboarding();
      });
      act(() => {
        result.current.resetOnboarding();
      });
      expect(result.current.isFirstTime).toBe(true);
    });
  });
});
