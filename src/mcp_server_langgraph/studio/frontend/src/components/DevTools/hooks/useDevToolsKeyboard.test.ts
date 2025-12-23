/**
 * useDevToolsKeyboard Hook Tests
 *
 * TDD tests for keyboard shortcuts in DevTools.
 * Supports Cmd+Shift+I (toggle), Cmd+K (clear), tab navigation.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useDevToolsKeyboard } from "./useDevToolsKeyboard";

// =============================================================================
// Mock Dependencies
// =============================================================================

const mockDispatch = vi.fn();
const mockGetState = vi.fn();

vi.mock("../../../store/hooks", () => ({
  useAppDispatch: () => mockDispatch,
  useAppSelector: (selector: (state: unknown) => unknown) => selector(mockGetState()),
}));

vi.mock("../../../store/slices/devToolsSlice", () => ({
  toggleDevTools: vi.fn(() => ({ type: "devTools/toggleDevTools" })),
  setActiveTab: vi.fn((tab: string) => ({ type: "devTools/setActiveTab", payload: tab })),
  selectActiveTab: (state: { devTools: { activeTab: string } }) => state.devTools.activeTab,
  selectAvailableTabs: () => ["console", "problems", "network", "state"],
}));

// =============================================================================
// Helper Functions
// =============================================================================

function createKeyboardEvent(
  key: string,
  options: {
    metaKey?: boolean;
    ctrlKey?: boolean;
    shiftKey?: boolean;
    altKey?: boolean;
  } = {}
): KeyboardEvent {
  return new KeyboardEvent("keydown", {
    key,
    metaKey: options.metaKey ?? false,
    ctrlKey: options.ctrlKey ?? false,
    shiftKey: options.shiftKey ?? false,
    altKey: options.altKey ?? false,
    bubbles: true,
    cancelable: true,
  });
}

// =============================================================================
// Tests
// =============================================================================

describe("useDevToolsKeyboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetState.mockReturnValue({
      devTools: {
        activeTab: "console",
        collapsed: false,
      },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initialization", () => {
    it("should register keyboard listeners on mount", () => {
      const addEventListenerSpy = vi.spyOn(document, "addEventListener");

      renderHook(() => useDevToolsKeyboard({ enabled: true }));

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function)
      );
    });

    it("should cleanup listeners on unmount", () => {
      const removeEventListenerSpy = vi.spyOn(document, "removeEventListener");

      const { unmount } = renderHook(() => useDevToolsKeyboard({ enabled: true }));
      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function)
      );
    });

    it("should not register listeners when disabled", () => {
      const addEventListenerSpy = vi.spyOn(document, "addEventListener");

      renderHook(() => useDevToolsKeyboard({ enabled: false }));

      expect(addEventListenerSpy).not.toHaveBeenCalledWith(
        "keydown",
        expect.any(Function)
      );
    });
  });

  describe("toggle DevTools (Cmd+Shift+I)", () => {
    it("should toggle DevTools on Cmd+Shift+I (Mac)", () => {
      renderHook(() => useDevToolsKeyboard({ enabled: true }));

      act(() => {
        document.dispatchEvent(
          createKeyboardEvent("i", { metaKey: true, shiftKey: true })
        );
      });

      expect(mockDispatch).toHaveBeenCalled();
    });

    it("should toggle DevTools on Ctrl+Shift+I (Windows/Linux)", () => {
      renderHook(() => useDevToolsKeyboard({ enabled: true }));

      act(() => {
        document.dispatchEvent(
          createKeyboardEvent("i", { ctrlKey: true, shiftKey: true })
        );
      });

      expect(mockDispatch).toHaveBeenCalled();
    });

    it("should not toggle without modifier keys", () => {
      renderHook(() => useDevToolsKeyboard({ enabled: true }));

      act(() => {
        document.dispatchEvent(createKeyboardEvent("i"));
      });

      expect(mockDispatch).not.toHaveBeenCalled();
    });
  });

  describe("clear console (Cmd+K)", () => {
    it("should call onClearConsole on Cmd+K", () => {
      const onClearConsole = vi.fn();
      renderHook(() =>
        useDevToolsKeyboard({ enabled: true, onClearConsole })
      );

      act(() => {
        document.dispatchEvent(createKeyboardEvent("k", { metaKey: true }));
      });

      expect(onClearConsole).toHaveBeenCalled();
    });

    it("should call onClearConsole on Ctrl+K (Windows/Linux)", () => {
      const onClearConsole = vi.fn();
      renderHook(() =>
        useDevToolsKeyboard({ enabled: true, onClearConsole })
      );

      act(() => {
        document.dispatchEvent(createKeyboardEvent("k", { ctrlKey: true }));
      });

      expect(onClearConsole).toHaveBeenCalled();
    });

    it("should not clear without modifier", () => {
      const onClearConsole = vi.fn();
      renderHook(() =>
        useDevToolsKeyboard({ enabled: true, onClearConsole })
      );

      act(() => {
        document.dispatchEvent(createKeyboardEvent("k"));
      });

      expect(onClearConsole).not.toHaveBeenCalled();
    });
  });

  describe("tab navigation (Cmd+] and Cmd+[)", () => {
    it("should navigate to next tab on Cmd+]", () => {
      mockGetState.mockReturnValue({
        devTools: {
          activeTab: "console",
          collapsed: false,
        },
      });

      renderHook(() => useDevToolsKeyboard({ enabled: true }));

      act(() => {
        document.dispatchEvent(createKeyboardEvent("]", { metaKey: true }));
      });

      expect(mockDispatch).toHaveBeenCalled();
    });

    it("should navigate to previous tab on Cmd+[", () => {
      mockGetState.mockReturnValue({
        devTools: {
          activeTab: "problems",
          collapsed: false,
        },
      });

      renderHook(() => useDevToolsKeyboard({ enabled: true }));

      act(() => {
        document.dispatchEvent(createKeyboardEvent("[", { metaKey: true }));
      });

      expect(mockDispatch).toHaveBeenCalled();
    });

    it("should wrap to first tab when at last", () => {
      mockGetState.mockReturnValue({
        devTools: {
          activeTab: "state", // Last tab
          collapsed: false,
        },
      });

      renderHook(() => useDevToolsKeyboard({ enabled: true }));

      act(() => {
        document.dispatchEvent(createKeyboardEvent("]", { metaKey: true }));
      });

      expect(mockDispatch).toHaveBeenCalled();
    });

    it("should wrap to last tab when at first", () => {
      mockGetState.mockReturnValue({
        devTools: {
          activeTab: "console", // First tab
          collapsed: false,
        },
      });

      renderHook(() => useDevToolsKeyboard({ enabled: true }));

      act(() => {
        document.dispatchEvent(createKeyboardEvent("[", { metaKey: true }));
      });

      expect(mockDispatch).toHaveBeenCalled();
    });
  });

  describe("focus console (Cmd+Shift+C)", () => {
    it("should focus console tab on Cmd+Shift+C", () => {
      renderHook(() => useDevToolsKeyboard({ enabled: true }));

      act(() => {
        document.dispatchEvent(
          createKeyboardEvent("c", { metaKey: true, shiftKey: true })
        );
      });

      expect(mockDispatch).toHaveBeenCalled();
    });
  });

  describe("return value", () => {
    it("should return keyboard shortcuts map", () => {
      const { result } = renderHook(() =>
        useDevToolsKeyboard({ enabled: true })
      );

      expect(result.current.shortcuts).toBeDefined();
      expect(result.current.shortcuts).toContainEqual(
        expect.objectContaining({
          key: "i",
          description: expect.stringMatching(/toggle/i),
        })
      );
    });

    it("should return isEnabled status", () => {
      const { result } = renderHook(() =>
        useDevToolsKeyboard({ enabled: true })
      );

      expect(result.current.isEnabled).toBe(true);
    });
  });

  describe("prevent default behavior", () => {
    it("should prevent default on handled shortcuts", () => {
      renderHook(() => useDevToolsKeyboard({ enabled: true }));

      const event = createKeyboardEvent("i", { metaKey: true, shiftKey: true });
      const preventDefaultSpy = vi.spyOn(event, "preventDefault");

      act(() => {
        document.dispatchEvent(event);
      });

      expect(preventDefaultSpy).toHaveBeenCalled();
    });
  });
});
