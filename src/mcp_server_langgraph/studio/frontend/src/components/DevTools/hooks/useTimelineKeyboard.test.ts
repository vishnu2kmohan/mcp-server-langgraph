/**
 * useTimelineKeyboard Hook Tests
 *
 * TDD tests for timeline keyboard shortcuts.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import React from "react";

import { useTimelineKeyboard } from "./useTimelineKeyboard";

// =============================================================================
// Test Helpers
// =============================================================================

function fireKeyEvent(
  key: string,
  options: Partial<KeyboardEventInit> = {},
): void {
  const event = new KeyboardEvent("keydown", {
    key,
    bubbles: true,
    cancelable: true,
    ...options,
  });
  document.dispatchEvent(event);
}

// =============================================================================
// Tests
// =============================================================================

describe("useTimelineKeyboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initialization", () => {
    it("should return shortcuts list", () => {
      const { result } = renderHook(() =>
        useTimelineKeyboard({ enabled: true }),
      );

      expect(result.current.shortcuts).toBeDefined();
      expect(Array.isArray(result.current.shortcuts)).toBe(true);
    });

    it("should return isEnabled status", () => {
      const { result } = renderHook(() =>
        useTimelineKeyboard({ enabled: true }),
      );

      expect(result.current.isEnabled).toBe(true);
    });
  });

  describe("playback shortcuts", () => {
    it("should call onPlayPause when Space is pressed", () => {
      const onPlayPause = vi.fn();
      renderHook(() =>
        useTimelineKeyboard({ enabled: true, onPlayPause }),
      );

      act(() => {
        fireKeyEvent(" ");
      });

      expect(onPlayPause).toHaveBeenCalled();
    });

    it("should call onStepForward when ArrowRight is pressed", () => {
      const onStepForward = vi.fn();
      renderHook(() =>
        useTimelineKeyboard({ enabled: true, onStepForward }),
      );

      act(() => {
        fireKeyEvent("ArrowRight");
      });

      expect(onStepForward).toHaveBeenCalled();
    });

    it("should call onStepBackward when ArrowLeft is pressed", () => {
      const onStepBackward = vi.fn();
      renderHook(() =>
        useTimelineKeyboard({ enabled: true, onStepBackward }),
      );

      act(() => {
        fireKeyEvent("ArrowLeft");
      });

      expect(onStepBackward).toHaveBeenCalled();
    });
  });

  describe("navigation shortcuts", () => {
    it("should call onJumpToStart when Home is pressed", () => {
      const onJumpToStart = vi.fn();
      renderHook(() =>
        useTimelineKeyboard({ enabled: true, onJumpToStart }),
      );

      act(() => {
        fireKeyEvent("Home");
      });

      expect(onJumpToStart).toHaveBeenCalled();
    });

    it("should call onJumpToEnd when End is pressed", () => {
      const onJumpToEnd = vi.fn();
      renderHook(() =>
        useTimelineKeyboard({ enabled: true, onJumpToEnd }),
      );

      act(() => {
        fireKeyEvent("End");
      });

      expect(onJumpToEnd).toHaveBeenCalled();
    });
  });

  describe("bookmark shortcuts", () => {
    it("should call onAddBookmark when B is pressed", () => {
      const onAddBookmark = vi.fn();
      renderHook(() =>
        useTimelineKeyboard({ enabled: true, onAddBookmark }),
      );

      act(() => {
        fireKeyEvent("b");
      });

      expect(onAddBookmark).toHaveBeenCalled();
    });

    it("should call onNextBookmark when Shift+ArrowRight is pressed", () => {
      const onNextBookmark = vi.fn();
      renderHook(() =>
        useTimelineKeyboard({ enabled: true, onNextBookmark }),
      );

      act(() => {
        fireKeyEvent("ArrowRight", { shiftKey: true });
      });

      expect(onNextBookmark).toHaveBeenCalled();
    });

    it("should call onPrevBookmark when Shift+ArrowLeft is pressed", () => {
      const onPrevBookmark = vi.fn();
      renderHook(() =>
        useTimelineKeyboard({ enabled: true, onPrevBookmark }),
      );

      act(() => {
        fireKeyEvent("ArrowLeft", { shiftKey: true });
      });

      expect(onPrevBookmark).toHaveBeenCalled();
    });
  });

  describe("speed shortcuts", () => {
    it("should call onSetSpeed with 1 when 1 is pressed", () => {
      const onSetSpeed = vi.fn();
      renderHook(() =>
        useTimelineKeyboard({ enabled: true, onSetSpeed }),
      );

      act(() => {
        fireKeyEvent("1");
      });

      expect(onSetSpeed).toHaveBeenCalledWith(1);
    });

    it("should call onSetSpeed with 2 when 2 is pressed", () => {
      const onSetSpeed = vi.fn();
      renderHook(() =>
        useTimelineKeyboard({ enabled: true, onSetSpeed }),
      );

      act(() => {
        fireKeyEvent("2");
      });

      expect(onSetSpeed).toHaveBeenCalledWith(2);
    });

    it("should call onSetSpeed with 4 when 4 is pressed", () => {
      const onSetSpeed = vi.fn();
      renderHook(() =>
        useTimelineKeyboard({ enabled: true, onSetSpeed }),
      );

      act(() => {
        fireKeyEvent("4");
      });

      expect(onSetSpeed).toHaveBeenCalledWith(4);
    });
  });

  describe("disabled state", () => {
    it("should not call callbacks when disabled", () => {
      const onPlayPause = vi.fn();
      renderHook(() =>
        useTimelineKeyboard({ enabled: false, onPlayPause }),
      );

      act(() => {
        fireKeyEvent(" ");
      });

      expect(onPlayPause).not.toHaveBeenCalled();
    });
  });

  describe("input focus", () => {
    it("should not handle shortcuts when input is focused", () => {
      const onPlayPause = vi.fn();
      renderHook(() =>
        useTimelineKeyboard({ enabled: true, onPlayPause }),
      );

      // Create and focus an input
      const input = document.createElement("input");
      document.body.appendChild(input);
      input.focus();

      act(() => {
        const event = new KeyboardEvent("keydown", {
          key: " ",
          bubbles: true,
          cancelable: true,
        });
        input.dispatchEvent(event);
      });

      // Should not call because input is focused
      expect(onPlayPause).not.toHaveBeenCalled();

      // Cleanup
      document.body.removeChild(input);
    });
  });

  describe("cleanup", () => {
    it("should remove event listener on unmount", () => {
      const removeSpy = vi.spyOn(document, "removeEventListener");
      const { unmount } = renderHook(() =>
        useTimelineKeyboard({ enabled: true }),
      );

      unmount();

      expect(removeSpy).toHaveBeenCalledWith("keydown", expect.any(Function));
      removeSpy.mockRestore();
    });
  });
});
