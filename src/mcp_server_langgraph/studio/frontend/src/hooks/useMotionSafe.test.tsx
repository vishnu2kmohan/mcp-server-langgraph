/**
 * useMotionSafe Hook Tests
 *
 * Tests for reduced motion accessibility support in animations.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import {
  useMotionSafe,
  usePrefersReducedMotion,
  useMotionSafeVariants,
} from "./useMotionSafe";

// Note: motion/react is globally mocked in src/test/setup.ts with proper prop filtering

import { useReducedMotion } from "motion/react";

describe("useMotionSafe", () => {
  const mockedUseReducedMotion = vi.mocked(useReducedMotion);

  beforeEach(() => {
    mockedUseReducedMotion.mockReturnValue(false);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("useMotionSafe", () => {
    it("should return full motion props when reduced motion is not preferred", () => {
      mockedUseReducedMotion.mockReturnValue(false);

      const fullMotion = {
        initial: { opacity: 0, y: 20, scale: 0.9 },
        animate: { opacity: 1, y: 0, scale: 1 },
        exit: { opacity: 0, y: 20, scale: 0.9 },
        transition: { type: "spring", stiffness: 400 },
      };

      const { result } = renderHook(() => useMotionSafe(fullMotion));

      expect(result.current).toEqual(fullMotion);
    });

    it("should return reduced motion props when reduced motion is preferred", () => {
      mockedUseReducedMotion.mockReturnValue(true);

      const fullMotion = {
        initial: { opacity: 0, y: 20, scale: 0.9 },
        animate: { opacity: 1, y: 0, scale: 1 },
        exit: { opacity: 0, y: 20, scale: 0.9 },
        transition: { type: "spring", stiffness: 400 },
      };

      const { result } = renderHook(() => useMotionSafe(fullMotion));

      // Should have opacity-only animations with fast duration
      expect(result.current.initial).toEqual({ opacity: 0 });
      expect(result.current.animate).toEqual({ opacity: 1 });
      expect(result.current.exit).toEqual({ opacity: 0 });
      expect(result.current.transition).toEqual({ duration: 0.15 });
    });

    it("should allow custom reduced motion overrides", () => {
      mockedUseReducedMotion.mockReturnValue(true);

      const fullMotion = {
        initial: { opacity: 0, y: 20 },
        animate: { opacity: 1, y: 0 },
      };

      const reducedMotion = {
        transition: { duration: 0.25 },
      };

      const { result } = renderHook(() =>
        useMotionSafe(fullMotion, reducedMotion)
      );

      expect(result.current.transition).toEqual({ duration: 0.25 });
    });
  });

  describe("usePrefersReducedMotion", () => {
    it("should return false when reduced motion is not preferred", () => {
      mockedUseReducedMotion.mockReturnValue(false);

      const { result } = renderHook(() => usePrefersReducedMotion());

      expect(result.current).toBe(false);
    });

    it("should return true when reduced motion is preferred", () => {
      mockedUseReducedMotion.mockReturnValue(true);

      const { result } = renderHook(() => usePrefersReducedMotion());

      expect(result.current).toBe(true);
    });

    it("should return false when useReducedMotion returns null/undefined", () => {
      mockedUseReducedMotion.mockReturnValue(null as unknown as boolean);

      const { result } = renderHook(() => usePrefersReducedMotion());

      expect(result.current).toBe(false);
    });
  });

  describe("useMotionSafeVariants", () => {
    it("should return full variants when reduced motion is not preferred", () => {
      mockedUseReducedMotion.mockReturnValue(false);

      const variants = {
        hidden: { opacity: 0, x: -20, scale: 0.9 },
        visible: { opacity: 1, x: 0, scale: 1 },
        exit: { opacity: 0, x: 20, scale: 0.9 },
      };

      const { result } = renderHook(() => useMotionSafeVariants(variants));

      expect(result.current).toEqual(variants);
    });

    it("should return opacity-only variants when reduced motion is preferred", () => {
      mockedUseReducedMotion.mockReturnValue(true);

      const variants = {
        hidden: { opacity: 0, x: -20, scale: 0.9 },
        visible: { opacity: 1, x: 0, scale: 1 },
        exit: { opacity: 0, x: 20, scale: 0.9 },
      };

      const { result } = renderHook(() => useMotionSafeVariants(variants));

      // Hidden and exit should have opacity 0
      expect(result.current.hidden.opacity).toBe(0);
      expect(result.current.exit.opacity).toBe(0);
      // Visible should have opacity 1
      expect(result.current.visible.opacity).toBe(1);
      // All should have fast transition
      expect(result.current.hidden.transition).toEqual({ duration: 0.15 });
      expect(result.current.visible.transition).toEqual({ duration: 0.15 });
      expect(result.current.exit.transition).toEqual({ duration: 0.15 });
    });

    it("should preserve opacity values from original variants", () => {
      mockedUseReducedMotion.mockReturnValue(true);

      const variants = {
        faded: { opacity: 0.5, x: -20 },
        full: { opacity: 1, x: 0 },
      };

      const { result } = renderHook(() => useMotionSafeVariants(variants));

      // Should preserve the explicit opacity values
      expect(result.current.faded.opacity).toBe(0.5);
      expect(result.current.full.opacity).toBe(1);
    });

    it('should infer opacity 0 for variants with "collapsed" in name', () => {
      mockedUseReducedMotion.mockReturnValue(true);

      const variants = {
        collapsed: { height: 0, scale: 0.95 },
        expanded: { height: "auto", scale: 1 },
      };

      const { result } = renderHook(() => useMotionSafeVariants(variants));

      // Collapsed should infer opacity 0
      expect(result.current.collapsed.opacity).toBe(0);
      // Expanded should infer opacity 1
      expect(result.current.expanded.opacity).toBe(1);
    });
  });
});
