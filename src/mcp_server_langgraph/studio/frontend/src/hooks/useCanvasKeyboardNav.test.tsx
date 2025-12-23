/**
 * useCanvasKeyboardNav Tests
 *
 * TDD tests for canvas keyboard navigation hook.
 * Tests focus management and panel navigation shortcuts.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { useCanvasKeyboardNav } from "./useCanvasKeyboardNav";
import canvasReducer from "../store/slices/canvasSlice";
import type { ReactNode } from "react";

// Create refs for testing focus
const createMockRefs = () => ({
  activityBarRef: { current: document.createElement("div") },
  sessionNavRef: { current: document.createElement("div") },
  conversationRef: { current: document.createElement("div") },
  canvasRef: { current: document.createElement("div") },
});

// Create test store
const createTestStore = () => {
  return configureStore({
    reducer: {
      canvas: canvasReducer,
    },
  });
};

// Wrapper with store
function createWrapper() {
  const store = createTestStore();
  return function Wrapper({ children }: { children: ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
}

// Helper to simulate keyboard event
function simulateKeyboard(
  key: string,
  modifiers: { meta?: boolean; ctrl?: boolean } = {},
) {
  const event = new KeyboardEvent("keydown", {
    key,
    code: `Key${key.toUpperCase()}`,
    metaKey: modifiers.meta ?? false,
    ctrlKey: modifiers.ctrl ?? false,
    bubbles: true,
  });
  document.dispatchEvent(event);
}

describe("useCanvasKeyboardNav", () => {
  let mockRefs: ReturnType<typeof createMockRefs>;

  beforeEach(() => {
    mockRefs = createMockRefs();
    // Add focus method to mock refs
    mockRefs.activityBarRef.current.focus = vi.fn();
    mockRefs.sessionNavRef.current.focus = vi.fn();
    mockRefs.conversationRef.current.focus = vi.fn();
    mockRefs.canvasRef.current.focus = vi.fn();
    // Add tabIndex for focusability
    mockRefs.activityBarRef.current.tabIndex = 0;
    mockRefs.sessionNavRef.current.tabIndex = 0;
    mockRefs.conversationRef.current.tabIndex = 0;
    mockRefs.canvasRef.current.tabIndex = 0;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("panel focus shortcuts", () => {
    it("should focus activity bar on Cmd+1", () => {
      renderHook(() => useCanvasKeyboardNav(mockRefs), {
        wrapper: createWrapper(),
      });

      act(() => {
        simulateKeyboard("1", { meta: true });
      });

      expect(mockRefs.activityBarRef.current.focus).toHaveBeenCalled();
    });

    it("should focus session nav on Cmd+2", () => {
      renderHook(() => useCanvasKeyboardNav(mockRefs), {
        wrapper: createWrapper(),
      });

      act(() => {
        simulateKeyboard("2", { meta: true });
      });

      expect(mockRefs.sessionNavRef.current.focus).toHaveBeenCalled();
    });

    it("should focus conversation on Cmd+3", () => {
      renderHook(() => useCanvasKeyboardNav(mockRefs), {
        wrapper: createWrapper(),
      });

      act(() => {
        simulateKeyboard("3", { meta: true });
      });

      expect(mockRefs.conversationRef.current.focus).toHaveBeenCalled();
    });

    it("should focus canvas on Cmd+4", () => {
      renderHook(() => useCanvasKeyboardNav(mockRefs), {
        wrapper: createWrapper(),
      });

      act(() => {
        simulateKeyboard("4", { meta: true });
      });

      expect(mockRefs.canvasRef.current.focus).toHaveBeenCalled();
    });

    it("should work with Ctrl on non-Mac", () => {
      renderHook(() => useCanvasKeyboardNav(mockRefs), {
        wrapper: createWrapper(),
      });

      act(() => {
        simulateKeyboard("1", { ctrl: true });
      });

      expect(mockRefs.activityBarRef.current.focus).toHaveBeenCalled();
    });
  });

  describe("cleanup", () => {
    it("should remove event listeners on unmount", () => {
      const removeEventListenerSpy = vi.spyOn(document, "removeEventListener");

      const { unmount } = renderHook(() => useCanvasKeyboardNav(mockRefs), {
        wrapper: createWrapper(),
      });

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function),
      );
    });
  });

  describe("null ref handling", () => {
    it("should not throw when refs are null", () => {
      const nullRefs = {
        activityBarRef: { current: null },
        sessionNavRef: { current: null },
        conversationRef: { current: null },
        canvasRef: { current: null },
      };

      expect(() => {
        renderHook(() => useCanvasKeyboardNav(nullRefs), {
          wrapper: createWrapper(),
        });
      }).not.toThrow();

      act(() => {
        simulateKeyboard("1", { meta: true });
      });
      // Should not throw
    });
  });
});
