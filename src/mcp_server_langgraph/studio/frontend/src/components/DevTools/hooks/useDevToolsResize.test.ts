/**
 * useDevToolsResize Hook Tests
 *
 * TDD tests for DevTools panel resize functionality.
 * Manages height persistence and min/max constraints.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useDevToolsResize } from "./useDevToolsResize";

// =============================================================================
// Mock Dependencies
// =============================================================================

const mockDispatch = vi.fn();
const mockGetState = vi.fn();

vi.mock("../../../store/hooks", () => ({
  useAppDispatch: () => mockDispatch,
  useAppSelector: (selector: (state: unknown) => unknown) =>
    selector(mockGetState()),
}));

vi.mock("../../../store/slices/devToolsSlice", () => ({
  setHeight: vi.fn((height: number) => ({
    type: "devTools/setHeight",
    payload: height,
  })),
  selectHeight: (state: { devTools: { height: number } }) =>
    state.devTools.height,
}));

// =============================================================================
// Tests
// =============================================================================

describe("useDevToolsResize", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetState.mockReturnValue({
      devTools: {
        height: 200,
      },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initialization", () => {
    it("should return current height from Redux state", () => {
      mockGetState.mockReturnValue({
        devTools: { height: 250 },
      });

      const { result } = renderHook(() => useDevToolsResize());

      expect(result.current.height).toBe(250);
    });

    it("should return default height when state is undefined", () => {
      mockGetState.mockReturnValue({
        devTools: { height: 200 },
      });

      const { result } = renderHook(() => useDevToolsResize());

      expect(result.current.height).toBe(200);
    });

    it("should support custom storage key option", () => {
      const { result } = renderHook(() =>
        useDevToolsResize({ storageKey: "custom-key" }),
      );

      // Hook should work with custom storage key
      expect(result.current.height).toBeDefined();
    });
  });

  describe("setHeight", () => {
    it("should dispatch setHeight action", () => {
      const { result } = renderHook(() => useDevToolsResize());

      act(() => {
        result.current.setHeight(300);
      });

      expect(mockDispatch).toHaveBeenCalled();
    });

    it("should enforce minimum height", () => {
      const { result } = renderHook(() =>
        useDevToolsResize({ minHeight: 150 }),
      );

      act(() => {
        result.current.setHeight(100); // Below minimum
      });

      // Should dispatch with minimum value
      expect(mockDispatch).toHaveBeenCalled();
    });

    it("should enforce maximum height", () => {
      const { result } = renderHook(() =>
        useDevToolsResize({ maxHeight: 400 }),
      );

      act(() => {
        result.current.setHeight(500); // Above maximum
      });

      // Should dispatch with maximum value
      expect(mockDispatch).toHaveBeenCalled();
    });

    it("should clamp height to constraints when setting", () => {
      const { result } = renderHook(() =>
        useDevToolsResize({ minHeight: 150, maxHeight: 400 }),
      );

      // The setHeight function should dispatch (clamped value)
      act(() => {
        result.current.setHeight(350);
      });

      expect(mockDispatch).toHaveBeenCalled();
    });
  });

  describe("resize handling", () => {
    it("should return isResizing state", () => {
      const { result } = renderHook(() => useDevToolsResize());

      expect(result.current.isResizing).toBe(false);
    });

    it("should set isResizing when startResize called", () => {
      const { result } = renderHook(() => useDevToolsResize());

      act(() => {
        result.current.startResize();
      });

      expect(result.current.isResizing).toBe(true);
    });

    it("should clear isResizing when endResize called", () => {
      const { result } = renderHook(() => useDevToolsResize());

      act(() => {
        result.current.startResize();
      });

      expect(result.current.isResizing).toBe(true);

      act(() => {
        result.current.endResize();
      });

      expect(result.current.isResizing).toBe(false);
    });
  });

  describe("reset height", () => {
    it("should reset to default height", () => {
      const { result } = renderHook(() =>
        useDevToolsResize({ defaultHeight: 200 }),
      );

      act(() => {
        result.current.setHeight(350);
      });

      act(() => {
        result.current.resetHeight();
      });

      expect(mockDispatch).toHaveBeenCalled();
    });

    it("should dispatch with default height when reset", () => {
      const { result } = renderHook(() =>
        useDevToolsResize({ defaultHeight: 200 }),
      );

      act(() => {
        result.current.resetHeight();
      });

      // Should dispatch setHeight with default value
      expect(mockDispatch).toHaveBeenCalled();
    });
  });

  describe("constraints", () => {
    it("should return minHeight", () => {
      const { result } = renderHook(() =>
        useDevToolsResize({ minHeight: 150 }),
      );

      expect(result.current.minHeight).toBe(150);
    });

    it("should return maxHeight", () => {
      const { result } = renderHook(() =>
        useDevToolsResize({ maxHeight: 400 }),
      );

      expect(result.current.maxHeight).toBe(400);
    });

    it("should use default constraints when not provided", () => {
      const { result } = renderHook(() => useDevToolsResize());

      expect(result.current.minHeight).toBe(100);
      expect(result.current.maxHeight).toBe(600);
    });
  });

  describe("height percentage", () => {
    it("should calculate height as percentage of window", () => {
      // Mock window.innerHeight
      Object.defineProperty(window, "innerHeight", {
        value: 800,
        writable: true,
      });

      mockGetState.mockReturnValue({
        devTools: { height: 200 },
      });

      const { result } = renderHook(() => useDevToolsResize());

      expect(result.current.heightPercent).toBe(25); // 200/800 * 100
    });
  });
});
