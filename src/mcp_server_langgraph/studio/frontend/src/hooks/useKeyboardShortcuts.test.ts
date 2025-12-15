/**
 * Tests for useKeyboardShortcuts hook
 */

import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  useKeyboardShortcuts,
  useShortcutDisplay,
  COMMON_SHORTCUTS,
} from "./useKeyboardShortcuts";

describe("useKeyboardShortcuts", () => {
  let addEventListenerSpy: ReturnType<typeof vi.spyOn>;
  let removeEventListenerSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    addEventListenerSpy = vi.spyOn(window, "addEventListener");
    removeEventListenerSpy = vi.spyOn(window, "removeEventListener");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("event listener management", () => {
    it("adds keydown listener on mount", () => {
      const handler = vi.fn();
      renderHook(() => useKeyboardShortcuts({ "ctrl+n": handler }));

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function),
      );
    });

    it("removes keydown listener on unmount", () => {
      const handler = vi.fn();
      const { unmount } = renderHook(() =>
        useKeyboardShortcuts({ "ctrl+n": handler }),
      );

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function),
      );
    });
  });

  describe("shortcut handling", () => {
    it("calls handler when shortcut is pressed", () => {
      const handler = vi.fn();
      renderHook(() => useKeyboardShortcuts({ n: handler }));

      const keydownHandler = addEventListenerSpy.mock.calls.find(
        (call) => call[0] === "keydown",
      )?.[1] as EventListener;

      const event = new KeyboardEvent("keydown", {
        key: "n",
        ctrlKey: false,
        altKey: false,
        shiftKey: false,
        metaKey: false,
      });

      act(() => {
        keydownHandler(event);
      });

      expect(handler).toHaveBeenCalled();
    });

    it("calls handler when ctrl+key shortcut is pressed", () => {
      const handler = vi.fn();
      renderHook(() => useKeyboardShortcuts({ "ctrl+n": handler }));

      const keydownHandler = addEventListenerSpy.mock.calls.find(
        (call) => call[0] === "keydown",
      )?.[1] as EventListener;

      const event = new KeyboardEvent("keydown", {
        key: "n",
        ctrlKey: true,
        altKey: false,
        shiftKey: false,
        metaKey: false,
      });

      act(() => {
        keydownHandler(event);
      });

      expect(handler).toHaveBeenCalled();
    });

    it("calls handler when alt+shift+key shortcut is pressed", () => {
      const handler = vi.fn();
      renderHook(() => useKeyboardShortcuts({ "alt+shift+d": handler }));

      const keydownHandler = addEventListenerSpy.mock.calls.find(
        (call) => call[0] === "keydown",
      )?.[1] as EventListener;

      const event = new KeyboardEvent("keydown", {
        key: "d",
        ctrlKey: false,
        altKey: true,
        shiftKey: true,
        metaKey: false,
      });

      act(() => {
        keydownHandler(event);
      });

      expect(handler).toHaveBeenCalled();
    });

    it("does not call handler when modifiers do not match", () => {
      const handler = vi.fn();
      renderHook(() => useKeyboardShortcuts({ "ctrl+n": handler }));

      const keydownHandler = addEventListenerSpy.mock.calls.find(
        (call) => call[0] === "keydown",
      )?.[1] as EventListener;

      // Press 'n' without Ctrl
      const event = new KeyboardEvent("keydown", {
        key: "n",
        ctrlKey: false,
        altKey: false,
        shiftKey: false,
        metaKey: false,
      });

      act(() => {
        keydownHandler(event);
      });

      expect(handler).not.toHaveBeenCalled();
    });

    it("prevents default when preventDefault option is true", () => {
      const handler = vi.fn();
      renderHook(() =>
        useKeyboardShortcuts({ "ctrl+s": handler }, { preventDefault: true }),
      );

      const keydownHandler = addEventListenerSpy.mock.calls.find(
        (call) => call[0] === "keydown",
      )?.[1] as EventListener;

      const event = new KeyboardEvent("keydown", {
        key: "s",
        ctrlKey: true,
        altKey: false,
        shiftKey: false,
        metaKey: false,
      });
      const preventDefaultSpy = vi.spyOn(event, "preventDefault");

      act(() => {
        keydownHandler(event);
      });

      expect(preventDefaultSpy).toHaveBeenCalled();
    });
  });

  describe("input handling", () => {
    it("ignores shortcuts when focused on input by default", () => {
      const handler = vi.fn();
      renderHook(() => useKeyboardShortcuts({ n: handler }));

      // Mock an input element as active
      const input = document.createElement("input");
      document.body.appendChild(input);
      input.focus();

      const keydownHandler = addEventListenerSpy.mock.calls.find(
        (call) => call[0] === "keydown",
      )?.[1] as EventListener;

      const event = new KeyboardEvent("keydown", {
        key: "n",
        ctrlKey: false,
        altKey: false,
        shiftKey: false,
        metaKey: false,
      });

      act(() => {
        keydownHandler(event);
      });

      expect(handler).not.toHaveBeenCalled();

      document.body.removeChild(input);
    });

    it("allows shortcuts in inputs when allowInInputs is true", () => {
      const handler = vi.fn();
      renderHook(() =>
        useKeyboardShortcuts({ "ctrl+n": handler }, { allowInInputs: true }),
      );

      // Mock an input element as active
      const input = document.createElement("input");
      document.body.appendChild(input);
      input.focus();

      const keydownHandler = addEventListenerSpy.mock.calls.find(
        (call) => call[0] === "keydown",
      )?.[1] as EventListener;

      const event = new KeyboardEvent("keydown", {
        key: "n",
        ctrlKey: true,
        altKey: false,
        shiftKey: false,
        metaKey: false,
      });

      act(() => {
        keydownHandler(event);
      });

      expect(handler).toHaveBeenCalled();

      document.body.removeChild(input);
    });
  });

  describe("enabled option", () => {
    it("does not call handler when disabled", () => {
      const handler = vi.fn();
      renderHook(() =>
        useKeyboardShortcuts({ n: handler }, { enabled: false }),
      );

      const keydownHandler = addEventListenerSpy.mock.calls.find(
        (call) => call[0] === "keydown",
      )?.[1] as EventListener;

      const event = new KeyboardEvent("keydown", {
        key: "n",
        ctrlKey: false,
        altKey: false,
        shiftKey: false,
        metaKey: false,
      });

      act(() => {
        keydownHandler(event);
      });

      expect(handler).not.toHaveBeenCalled();
    });
  });
});

describe("useShortcutDisplay", () => {
  beforeEach(() => {
    // Mock navigator.platform for consistent testing
    Object.defineProperty(navigator, "platform", {
      value: "Win32",
      writable: true,
    });
  });

  it("formats simple key", () => {
    const { result } = renderHook(() => useShortcutDisplay());
    expect(result.current.formatShortcut("n")).toBe("N");
  });

  it("formats ctrl shortcut on Windows", () => {
    const { result } = renderHook(() => useShortcutDisplay());
    expect(result.current.formatShortcut("ctrl+n")).toBe("Ctrl+N");
  });

  it("formats alt shortcut on Windows", () => {
    const { result } = renderHook(() => useShortcutDisplay());
    expect(result.current.formatShortcut("alt+n")).toBe("Alt+N");
  });

  it("formats shift shortcut on Windows", () => {
    const { result } = renderHook(() => useShortcutDisplay());
    expect(result.current.formatShortcut("shift+n")).toBe("Shift+N");
  });

  it("formats complex shortcut on Windows", () => {
    const { result } = renderHook(() => useShortcutDisplay());
    expect(result.current.formatShortcut("ctrl+shift+n")).toBe("Ctrl+Shift+N");
  });

  it("formats escape key", () => {
    const { result } = renderHook(() => useShortcutDisplay());
    expect(result.current.formatShortcut("escape")).toBe("Esc");
  });

  it("formats arrow keys", () => {
    const { result } = renderHook(() => useShortcutDisplay());
    expect(result.current.formatShortcut("arrowup")).toBe("↑");
    expect(result.current.formatShortcut("arrowdown")).toBe("↓");
    expect(result.current.formatShortcut("arrowleft")).toBe("←");
    expect(result.current.formatShortcut("arrowright")).toBe("→");
  });

  it("formats enter key", () => {
    const { result } = renderHook(() => useShortcutDisplay());
    expect(result.current.formatShortcut("enter")).toBe("↵");
  });

  describe("Mac formatting", () => {
    beforeEach(() => {
      Object.defineProperty(navigator, "platform", {
        value: "MacIntel",
        writable: true,
      });
    });

    it("uses Mac symbols for modifiers", () => {
      const { result } = renderHook(() => useShortcutDisplay());
      expect(result.current.isMac).toBe(true);
      // On Mac, modifiers are displayed as symbols without separators
      expect(result.current.formatShortcut("ctrl+n")).toBe("⌃N");
      expect(result.current.formatShortcut("alt+n")).toBe("⌥N");
      expect(result.current.formatShortcut("shift+n")).toBe("⇧N");
      expect(result.current.formatShortcut("meta+n")).toBe("⌘N");
    });

    it("formats delete key with Mac symbol", () => {
      const { result } = renderHook(() => useShortcutDisplay());
      expect(result.current.formatShortcut("delete")).toBe("⌫");
    });
  });
});

describe("COMMON_SHORTCUTS", () => {
  it("has expected shortcuts defined", () => {
    expect(COMMON_SHORTCUTS.SEARCH).toBe("ctrl+f");
    expect(COMMON_SHORTCUTS.NEW).toBe("ctrl+n");
    expect(COMMON_SHORTCUTS.SAVE).toBe("ctrl+s");
    expect(COMMON_SHORTCUTS.CLOSE).toBe("escape");
    expect(COMMON_SHORTCUTS.DELETE).toBe("delete");
    expect(COMMON_SHORTCUTS.REFRESH).toBe("ctrl+r");
    expect(COMMON_SHORTCUTS.UNDO).toBe("ctrl+z");
    expect(COMMON_SHORTCUTS.REDO).toBe("ctrl+shift+z");
  });
});
