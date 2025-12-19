/**
 * useMobileOptimizations Tests
 *
 * TDD tests for mobile optimization utilities.
 * Tests cover:
 * - Device detection
 * - Touch optimization
 * - Viewport management
 * - Gesture support detection
 * - Responsive breakpoints
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useMobileOptimizations } from "./useMobileOptimizations";

describe("useMobileOptimizations", () => {
  let originalMatchMedia: typeof window.matchMedia;
  let originalTouchPoints: number;
  let originalUserAgent: string;

  beforeEach(() => {
    vi.clearAllMocks();

    // Store originals
    originalMatchMedia = window.matchMedia;
    originalTouchPoints = navigator.maxTouchPoints;
    originalUserAgent = navigator.userAgent;
  });

  afterEach(() => {
    // Restore originals
    window.matchMedia = originalMatchMedia;
    Object.defineProperty(navigator, "maxTouchPoints", {
      value: originalTouchPoints,
      writable: true,
      configurable: true,
    });
    Object.defineProperty(navigator, "userAgent", {
      value: originalUserAgent,
      writable: true,
      configurable: true,
    });
  });

  describe("device detection", () => {
    it("should detect mobile device from user agent", () => {
      Object.defineProperty(navigator, "userAgent", {
        value:
          "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.isMobile).toBe(true);
    });

    it("should detect desktop device", () => {
      Object.defineProperty(navigator, "userAgent", {
        value: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        writable: true,
        configurable: true,
      });
      Object.defineProperty(navigator, "maxTouchPoints", {
        value: 0,
        writable: true,
        configurable: true,
      });

      // Mock matchMedia to return desktop viewport
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query.includes("min-width: 768px"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.isMobile).toBe(false);
    });

    it("should detect tablet device", () => {
      Object.defineProperty(navigator, "userAgent", {
        value:
          "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.isTablet).toBe(true);
    });
  });

  describe("touch support", () => {
    it("should detect touch-capable device", () => {
      Object.defineProperty(navigator, "maxTouchPoints", {
        value: 5,
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.hasTouch).toBe(true);
    });

    it("should detect non-touch device", () => {
      Object.defineProperty(navigator, "maxTouchPoints", {
        value: 0,
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.hasTouch).toBe(false);
    });
  });

  describe("breakpoints", () => {
    it("should detect small screen (mobile)", () => {
      // Set viewport width to mobile size
      Object.defineProperty(window, "innerWidth", {
        value: 375,
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.breakpoint).toBe("sm");
    });

    it("should detect medium screen (tablet)", () => {
      // Set viewport width to tablet size
      Object.defineProperty(window, "innerWidth", {
        value: 800,
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.breakpoint).toBe("md");
    });

    it("should detect large screen (desktop)", () => {
      // Set viewport width to desktop size
      Object.defineProperty(window, "innerWidth", {
        value: 1200,
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.breakpoint).toBe("lg");
    });
  });

  describe("viewport dimensions", () => {
    it("should return viewport width", () => {
      Object.defineProperty(window, "innerWidth", {
        value: 375,
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.viewportWidth).toBe(375);
    });

    it("should return viewport height", () => {
      Object.defineProperty(window, "innerHeight", {
        value: 667,
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.viewportHeight).toBe(667);
    });

    it("should update on resize", async () => {
      Object.defineProperty(window, "innerWidth", {
        value: 375,
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.viewportWidth).toBe(375);

      // Simulate resize
      Object.defineProperty(window, "innerWidth", {
        value: 768,
        writable: true,
        configurable: true,
      });

      act(() => {
        window.dispatchEvent(new Event("resize"));
      });

      expect(result.current.viewportWidth).toBe(768);
    });
  });

  describe("orientation", () => {
    it("should detect portrait orientation", () => {
      Object.defineProperty(window, "innerWidth", {
        value: 375,
        writable: true,
        configurable: true,
      });
      Object.defineProperty(window, "innerHeight", {
        value: 667,
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.isPortrait).toBe(true);
    });

    it("should detect landscape orientation", () => {
      Object.defineProperty(window, "innerWidth", {
        value: 667,
        writable: true,
        configurable: true,
      });
      Object.defineProperty(window, "innerHeight", {
        value: 375,
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.isPortrait).toBe(false);
      expect(result.current.isLandscape).toBe(true);
    });
  });

  describe("safe area insets", () => {
    it("should provide safe area insets", () => {
      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.safeAreaInsets).toBeDefined();
      expect(typeof result.current.safeAreaInsets.top).toBe("number");
      expect(typeof result.current.safeAreaInsets.bottom).toBe("number");
      expect(typeof result.current.safeAreaInsets.left).toBe("number");
      expect(typeof result.current.safeAreaInsets.right).toBe("number");
    });
  });

  describe("touch target size", () => {
    it("should return recommended touch target size for mobile", () => {
      Object.defineProperty(navigator, "userAgent", {
        value:
          "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useMobileOptimizations());
      // WCAG recommends minimum 44x44px touch targets
      expect(result.current.touchTargetSize).toBeGreaterThanOrEqual(44);
    });

    it("should return smaller target size for desktop", () => {
      Object.defineProperty(navigator, "userAgent", {
        value: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        writable: true,
        configurable: true,
      });
      Object.defineProperty(navigator, "maxTouchPoints", {
        value: 0,
        writable: true,
        configurable: true,
      });

      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query.includes("min-width: 1024px"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.touchTargetSize).toBeLessThan(44);
    });
  });

  describe("keyboard visibility", () => {
    it("should provide keyboard visibility state", () => {
      const { result } = renderHook(() => useMobileOptimizations());
      // On mobile, when keyboard opens, viewport height shrinks significantly
      // In test environment, this is always false since visualViewport is not available
      expect(typeof result.current.isKeyboardVisible).toBe("boolean");
      expect(result.current.isKeyboardVisible).toBe(false);
    });
  });

  describe("standalone mode detection", () => {
    it("should detect PWA standalone mode", () => {
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query.includes("display-mode: standalone"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.isStandalone).toBe(true);
    });

    it("should detect browser mode", () => {
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: !query.includes("display-mode: standalone"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.isStandalone).toBe(false);
    });
  });

  describe("reduced motion", () => {
    it("should detect reduced motion preference", () => {
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query.includes("prefers-reduced-motion: reduce"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.prefersReducedMotion).toBe(true);
    });

    it("should return false when motion is preferred", () => {
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: !query.includes("prefers-reduced-motion"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      const { result } = renderHook(() => useMobileOptimizations());
      expect(result.current.prefersReducedMotion).toBe(false);
    });
  });
});
