/**
 * useMCPKeyboardShortcuts Hook Tests (TDD)
 *
 * Tests for keyboard shortcut handling in MCP components.
 *
 * Shortcuts covered:
 * - Cmd+M: Open MCP connections panel (toggle)
 * - Cmd+T: Open tool invocation dialog
 * - Cmd+R: Open resource viewer
 * - Cmd+P: Open prompt tester
 * - Escape: Close active MCP dialog
 *
 * Following TDD: RED phase - write failing tests first
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { useMCPKeyboardShortcuts } from "./useMCPKeyboardShortcuts";

// =============================================================================
// Mock Callbacks
// =============================================================================

const createMockCallbacks = () => ({
  onToggleMCPPanel: vi.fn(),
  onOpenToolDialog: vi.fn(),
  onOpenResourceViewer: vi.fn(),
  onOpenPromptTester: vi.fn(),
  onCloseActiveDialog: vi.fn(),
});

// =============================================================================
// Keyboard Event Helper
// =============================================================================

const createKeyboardEvent = (
  key: string,
  options: Partial<KeyboardEvent> = {},
) => {
  return new KeyboardEvent("keydown", {
    key,
    bubbles: true,
    cancelable: true,
    ...options,
  });
};

// =============================================================================
// Tests
// =============================================================================

describe("useMCPKeyboardShortcuts", () => {
  let callbacks: ReturnType<typeof createMockCallbacks>;

  beforeEach(() => {
    callbacks = createMockCallbacks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Cmd+M - Toggle MCP Panel", () => {
    it("calls onToggleMCPPanel when Cmd+M is pressed", () => {
      renderHook(() => useMCPKeyboardShortcuts(callbacks));

      act(() => {
        document.dispatchEvent(createKeyboardEvent("m", { metaKey: true }));
      });

      expect(callbacks.onToggleMCPPanel).toHaveBeenCalledTimes(1);
    });

    it("calls onToggleMCPPanel when Ctrl+M is pressed (Windows)", () => {
      renderHook(() => useMCPKeyboardShortcuts(callbacks));

      act(() => {
        document.dispatchEvent(createKeyboardEvent("m", { ctrlKey: true }));
      });

      expect(callbacks.onToggleMCPPanel).toHaveBeenCalledTimes(1);
    });

    it("does not call onToggleMCPPanel when only M is pressed", () => {
      renderHook(() => useMCPKeyboardShortcuts(callbacks));

      act(() => {
        document.dispatchEvent(createKeyboardEvent("m"));
      });

      expect(callbacks.onToggleMCPPanel).not.toHaveBeenCalled();
    });
  });

  describe("Cmd+T - Open Tool Dialog", () => {
    it("calls onOpenToolDialog when Cmd+Shift+T is pressed", () => {
      renderHook(() => useMCPKeyboardShortcuts(callbacks));

      act(() => {
        document.dispatchEvent(
          createKeyboardEvent("t", { metaKey: true, shiftKey: true }),
        );
      });

      expect(callbacks.onOpenToolDialog).toHaveBeenCalledTimes(1);
    });

    it("calls onOpenToolDialog when Ctrl+Shift+T is pressed (Windows)", () => {
      renderHook(() => useMCPKeyboardShortcuts(callbacks));

      act(() => {
        document.dispatchEvent(
          createKeyboardEvent("t", { ctrlKey: true, shiftKey: true }),
        );
      });

      expect(callbacks.onOpenToolDialog).toHaveBeenCalledTimes(1);
    });
  });

  describe("Cmd+Shift+R - Open Resource Viewer", () => {
    it("calls onOpenResourceViewer when Cmd+Shift+R is pressed", () => {
      renderHook(() => useMCPKeyboardShortcuts(callbacks));

      act(() => {
        document.dispatchEvent(
          createKeyboardEvent("r", { metaKey: true, shiftKey: true }),
        );
      });

      expect(callbacks.onOpenResourceViewer).toHaveBeenCalledTimes(1);
    });
  });

  describe("Cmd+Shift+P - Open Prompt Tester", () => {
    it("calls onOpenPromptTester when Cmd+Shift+P is pressed", () => {
      renderHook(() => useMCPKeyboardShortcuts(callbacks));

      act(() => {
        document.dispatchEvent(
          createKeyboardEvent("p", { metaKey: true, shiftKey: true }),
        );
      });

      expect(callbacks.onOpenPromptTester).toHaveBeenCalledTimes(1);
    });
  });

  describe("Escape - Close Active Dialog", () => {
    it("calls onCloseActiveDialog when Escape is pressed", () => {
      renderHook(() => useMCPKeyboardShortcuts(callbacks));

      act(() => {
        document.dispatchEvent(createKeyboardEvent("Escape"));
      });

      expect(callbacks.onCloseActiveDialog).toHaveBeenCalledTimes(1);
    });
  });

  describe("Hook Lifecycle", () => {
    it("removes event listeners on unmount", () => {
      const removeEventListenerSpy = vi.spyOn(document, "removeEventListener");

      const { unmount } = renderHook(() => useMCPKeyboardShortcuts(callbacks));
      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function),
      );

      removeEventListenerSpy.mockRestore();
    });
  });

  describe("Disabled State", () => {
    it("does not respond to shortcuts when disabled", () => {
      renderHook(() =>
        useMCPKeyboardShortcuts({ ...callbacks, disabled: true }),
      );

      act(() => {
        document.dispatchEvent(createKeyboardEvent("m", { metaKey: true }));
      });

      expect(callbacks.onToggleMCPPanel).not.toHaveBeenCalled();
    });
  });

  describe("Focus in Input", () => {
    it("does not respond to shortcuts when focus is in an input", () => {
      renderHook(() => useMCPKeyboardShortcuts(callbacks));

      // Create and focus an input element
      const input = document.createElement("input");
      document.body.appendChild(input);
      input.focus();

      act(() => {
        input.dispatchEvent(createKeyboardEvent("m", { metaKey: true }));
      });

      expect(callbacks.onToggleMCPPanel).not.toHaveBeenCalled();

      document.body.removeChild(input);
    });
  });
});
