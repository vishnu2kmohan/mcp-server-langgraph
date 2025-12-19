/**
 * useAccessibility Tests
 *
 * TDD tests for the Accessibility hook.
 * Tests cover:
 * - Screen reader mode toggle
 * - Reduced motion preference
 * - High contrast mode
 * - Font size adjustment
 * - Focus indicator enhancement
 * - Respecting system preferences
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAccessibility } from "./useAccessibility";

// Mock matchMedia for system preferences
const mockMatchMedia = (matches: boolean) => {
  return vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
};

describe("useAccessibility", () => {
  let originalMatchMedia: typeof window.matchMedia;
  let originalLocalStorage: Storage;

  beforeEach(() => {
    vi.clearAllMocks();
    originalMatchMedia = window.matchMedia;
    originalLocalStorage = window.localStorage;

    // Mock localStorage
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

    // Default matchMedia mock
    window.matchMedia = mockMatchMedia(false);
  });

  afterEach(() => {
    window.matchMedia = originalMatchMedia;
    Object.defineProperty(window, "localStorage", {
      value: originalLocalStorage,
    });
  });

  // ===========================================================================
  // Screen Reader Mode Tests
  // ===========================================================================

  describe("screen reader mode", () => {
    it("should default to false", () => {
      const { result } = renderHook(() => useAccessibility());

      expect(result.current.screenReaderMode).toBe(false);
    });

    it("should toggle screen reader mode", () => {
      const { result } = renderHook(() => useAccessibility());

      act(() => {
        result.current.setScreenReaderMode(true);
      });

      expect(result.current.screenReaderMode).toBe(true);
    });

    it("should persist screen reader mode to localStorage", () => {
      const { result } = renderHook(() => useAccessibility());

      act(() => {
        result.current.setScreenReaderMode(true);
      });

      expect(window.localStorage.setItem).toHaveBeenCalledWith(
        "studio-accessibility",
        expect.stringContaining('"screenReaderMode":true'),
      );
    });
  });

  // ===========================================================================
  // Reduced Motion Tests
  // ===========================================================================

  describe("reduced motion", () => {
    it("should respect system prefers-reduced-motion", () => {
      window.matchMedia = mockMatchMedia(true);

      const { result } = renderHook(() => useAccessibility());

      expect(result.current.reducedMotion).toBe(true);
    });

    it("should allow manual override of reduced motion", () => {
      const { result } = renderHook(() => useAccessibility());

      act(() => {
        result.current.setReducedMotion(true);
      });

      expect(result.current.reducedMotion).toBe(true);
    });
  });

  // ===========================================================================
  // High Contrast Mode Tests
  // ===========================================================================

  describe("high contrast mode", () => {
    it("should default to false", () => {
      const { result } = renderHook(() => useAccessibility());

      expect(result.current.highContrast).toBe(false);
    });

    it("should toggle high contrast mode", () => {
      const { result } = renderHook(() => useAccessibility());

      act(() => {
        result.current.setHighContrast(true);
      });

      expect(result.current.highContrast).toBe(true);
    });

    it("should add high-contrast class to document", () => {
      const { result } = renderHook(() => useAccessibility());

      act(() => {
        result.current.setHighContrast(true);
      });

      expect(document.documentElement.classList.contains("high-contrast")).toBe(
        true,
      );
    });
  });

  // ===========================================================================
  // Font Size Tests
  // ===========================================================================

  describe("font size", () => {
    it("should default to medium", () => {
      const { result } = renderHook(() => useAccessibility());

      expect(result.current.fontSize).toBe("medium");
    });

    it("should allow setting font size to small", () => {
      const { result } = renderHook(() => useAccessibility());

      act(() => {
        result.current.setFontSize("small");
      });

      expect(result.current.fontSize).toBe("small");
    });

    it("should allow setting font size to large", () => {
      const { result } = renderHook(() => useAccessibility());

      act(() => {
        result.current.setFontSize("large");
      });

      expect(result.current.fontSize).toBe("large");
    });

    it("should apply font size CSS variable to document", () => {
      const { result } = renderHook(() => useAccessibility());

      act(() => {
        result.current.setFontSize("large");
      });

      expect(
        document.documentElement.style.getPropertyValue("--font-size-base"),
      ).toBeTruthy();
    });
  });

  // ===========================================================================
  // Enhanced Focus Indicators Tests
  // ===========================================================================

  describe("enhanced focus indicators", () => {
    it("should default to false", () => {
      const { result } = renderHook(() => useAccessibility());

      expect(result.current.enhancedFocus).toBe(false);
    });

    it("should toggle enhanced focus indicators", () => {
      const { result } = renderHook(() => useAccessibility());

      act(() => {
        result.current.setEnhancedFocus(true);
      });

      expect(result.current.enhancedFocus).toBe(true);
    });

    it("should add enhanced-focus class to document", () => {
      const { result } = renderHook(() => useAccessibility());

      act(() => {
        result.current.setEnhancedFocus(true);
      });

      expect(
        document.documentElement.classList.contains("enhanced-focus"),
      ).toBe(true);
    });
  });

  // ===========================================================================
  // Persistence Tests
  // ===========================================================================

  describe("persistence", () => {
    it("should load settings from localStorage on mount", () => {
      const savedSettings = JSON.stringify({
        screenReaderMode: true,
        reducedMotion: true,
        highContrast: true,
        fontSize: "large",
        enhancedFocus: true,
      });

      (
        window.localStorage.getItem as ReturnType<typeof vi.fn>
      ).mockReturnValueOnce(savedSettings);

      const { result } = renderHook(() => useAccessibility());

      expect(result.current.screenReaderMode).toBe(true);
      expect(result.current.highContrast).toBe(true);
      expect(result.current.fontSize).toBe("large");
      expect(result.current.enhancedFocus).toBe(true);
    });

    it("should handle corrupted localStorage gracefully", () => {
      (
        window.localStorage.getItem as ReturnType<typeof vi.fn>
      ).mockReturnValueOnce("invalid json");

      const { result } = renderHook(() => useAccessibility());

      // Should use defaults
      expect(result.current.screenReaderMode).toBe(false);
      expect(result.current.fontSize).toBe("medium");
    });
  });

  // ===========================================================================
  // Reset Tests
  // ===========================================================================

  describe("reset", () => {
    it("should reset all settings to defaults", () => {
      const { result } = renderHook(() => useAccessibility());

      // Set custom values
      act(() => {
        result.current.setScreenReaderMode(true);
        result.current.setHighContrast(true);
        result.current.setFontSize("large");
        result.current.setEnhancedFocus(true);
      });

      // Reset
      act(() => {
        result.current.resetToDefaults();
      });

      expect(result.current.screenReaderMode).toBe(false);
      expect(result.current.highContrast).toBe(false);
      expect(result.current.fontSize).toBe("medium");
      expect(result.current.enhancedFocus).toBe(false);
    });
  });

  // ===========================================================================
  // Announce Function Tests
  // ===========================================================================

  describe("announce function", () => {
    it("should provide announce function for screen readers", () => {
      const { result } = renderHook(() => useAccessibility());

      expect(typeof result.current.announce).toBe("function");
    });

    it("should create aria-live region when announcing", () => {
      const { result } = renderHook(() => useAccessibility());

      act(() => {
        result.current.announce("Test announcement");
      });

      // Check that an aria-live region exists
      const liveRegion = document.querySelector("[aria-live]");
      expect(liveRegion).toBeInTheDocument();
    });
  });
});
