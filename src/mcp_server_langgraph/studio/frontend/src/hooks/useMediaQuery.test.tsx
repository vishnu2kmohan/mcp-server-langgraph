/**
 * useMediaQuery Hook Tests
 *
 * TDD tests for the responsive breakpoint hook.
 * Tests cover:
 * - Basic media query matching
 * - Breakpoint helpers (isMobile, isTablet, isDesktop)
 * - Dynamic updates on resize
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useMediaQuery, useBreakpoint } from "./useMediaQuery";

// Mock matchMedia
function createMatchMedia(matches: boolean) {
  return (query: string) => ({
    matches,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  });
}

describe("useMediaQuery", () => {
  let originalMatchMedia: typeof window.matchMedia;

  beforeEach(() => {
    originalMatchMedia = window.matchMedia;
  });

  afterEach(() => {
    window.matchMedia = originalMatchMedia;
  });

  describe("basic functionality", () => {
    it("should return true when media query matches", () => {
      window.matchMedia = createMatchMedia(true) as typeof window.matchMedia;

      const { result } = renderHook(() => useMediaQuery("(min-width: 768px)"));

      expect(result.current).toBe(true);
    });

    it("should return false when media query does not match", () => {
      window.matchMedia = createMatchMedia(false) as typeof window.matchMedia;

      const { result } = renderHook(() => useMediaQuery("(min-width: 768px)"));

      expect(result.current).toBe(false);
    });

    it("should handle different query strings", () => {
      window.matchMedia = createMatchMedia(true) as typeof window.matchMedia;

      const { result } = renderHook(() => useMediaQuery("(max-width: 640px)"));

      expect(result.current).toBe(true);
    });
  });

  describe("dynamic updates", () => {
    it("should add event listener on mount", () => {
      const addEventListener = vi.fn();
      window.matchMedia = vi.fn().mockReturnValue({
        matches: false,
        media: "",
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener,
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }) as typeof window.matchMedia;

      renderHook(() => useMediaQuery("(min-width: 768px)"));

      expect(addEventListener).toHaveBeenCalledWith(
        "change",
        expect.any(Function),
      );
    });

    it("should remove event listener on unmount", () => {
      const removeEventListener = vi.fn();
      window.matchMedia = vi.fn().mockReturnValue({
        matches: false,
        media: "",
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener,
        dispatchEvent: vi.fn(),
      }) as typeof window.matchMedia;

      const { unmount } = renderHook(() => useMediaQuery("(min-width: 768px)"));

      unmount();

      expect(removeEventListener).toHaveBeenCalledWith(
        "change",
        expect.any(Function),
      );
    });

    it("should update when media query changes", () => {
      let changeHandler: ((e: MediaQueryListEvent) => void) | null = null;

      window.matchMedia = vi.fn().mockReturnValue({
        matches: false,
        media: "(min-width: 768px)",
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: (
          _: string,
          handler: (e: MediaQueryListEvent) => void,
        ) => {
          changeHandler = handler;
        },
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }) as typeof window.matchMedia;

      const { result } = renderHook(() => useMediaQuery("(min-width: 768px)"));

      expect(result.current).toBe(false);

      // Simulate media query change
      act(() => {
        if (changeHandler) {
          changeHandler({ matches: true } as MediaQueryListEvent);
        }
      });

      expect(result.current).toBe(true);
    });
  });
});

describe("useBreakpoint", () => {
  let originalMatchMedia: typeof window.matchMedia;

  beforeEach(() => {
    originalMatchMedia = window.matchMedia;
  });

  afterEach(() => {
    window.matchMedia = originalMatchMedia;
  });

  describe("mobile detection", () => {
    it("should return isMobile true for small screens", () => {
      // Mobile: max-width: 639px
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query.includes("max-width: 639px"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })) as typeof window.matchMedia;

      const { result } = renderHook(() => useBreakpoint());

      expect(result.current.isMobile).toBe(true);
    });

    it("should return isMobile false for larger screens", () => {
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: !query.includes("max-width: 639px"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })) as typeof window.matchMedia;

      const { result } = renderHook(() => useBreakpoint());

      expect(result.current.isMobile).toBe(false);
    });
  });

  describe("tablet detection", () => {
    it("should return isTablet true for tablet-sized screens", () => {
      // Tablet: 640px - 1023px
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches:
          query.includes("min-width: 640px") &&
          query.includes("max-width: 1023px"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })) as typeof window.matchMedia;

      const { result } = renderHook(() => useBreakpoint());

      expect(result.current.isTablet).toBe(true);
    });
  });

  describe("desktop detection", () => {
    it("should return isDesktop true for large screens", () => {
      // Desktop: min-width: 1024px
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query.includes("min-width: 1024px"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })) as typeof window.matchMedia;

      const { result } = renderHook(() => useBreakpoint());

      expect(result.current.isDesktop).toBe(true);
    });
  });

  describe("breakpoint names", () => {
    it("should return current breakpoint name", () => {
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query.includes("max-width: 639px"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })) as typeof window.matchMedia;

      const { result } = renderHook(() => useBreakpoint());

      expect(result.current.breakpoint).toBe("mobile");
    });

    it("should return desktop when on large screens", () => {
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query.includes("min-width: 1024px"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })) as typeof window.matchMedia;

      const { result } = renderHook(() => useBreakpoint());

      expect(result.current.breakpoint).toBe("desktop");
    });
  });
});
