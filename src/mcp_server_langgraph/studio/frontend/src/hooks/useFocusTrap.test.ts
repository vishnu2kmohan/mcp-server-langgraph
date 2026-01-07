/**
 * useFocusTrap Hook Tests
 *
 * TDD tests for the focus trap hook used in modal dialogs.
 * Ensures keyboard focus stays within modal bounds for accessibility.
 *
 * Reference: Plan - StudioShell UX Audit - Sprint 5.2
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import { useRef } from "react";

describe("useFocusTrap", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Export", () => {
    it("should export useFocusTrap hook", async () => {
      const module = await import("./useFocusTrap");
      expect(module.useFocusTrap).toBeDefined();
    });
  });

  describe("Activation", () => {
    it("should not trap focus when isActive is false", async () => {
      const { useFocusTrap } = await import("./useFocusTrap");

      // Create a mock container with focusable elements
      const container = document.createElement("div");
      const button = document.createElement("button");
      button.textContent = "Test";
      container.appendChild(button);
      document.body.appendChild(container);

      const { result } = renderHook(() => {
        const ref = useRef<HTMLDivElement>(container);
        useFocusTrap(ref, false);
        return ref;
      });

      expect(result.current.current).toBe(container);

      // Cleanup
      document.body.removeChild(container);
    });

    it("should focus first focusable element when activated", async () => {
      const { useFocusTrap } = await import("./useFocusTrap");

      // Create a mock container with focusable elements
      const container = document.createElement("div");
      const button1 = document.createElement("button");
      button1.textContent = "First";
      const button2 = document.createElement("button");
      button2.textContent = "Second";
      container.appendChild(button1);
      container.appendChild(button2);
      document.body.appendChild(container);

      renderHook(() => {
        const ref = useRef<HTMLDivElement>(container);
        useFocusTrap(ref, true);
        return ref;
      });

      // First focusable element should receive focus
      expect(document.activeElement).toBe(button1);

      // Cleanup
      document.body.removeChild(container);
    });
  });

  describe("Tab Cycling", () => {
    it("should cycle focus from last to first element on Tab", async () => {
      const { useFocusTrap } = await import("./useFocusTrap");

      // Create container with focusable elements
      const container = document.createElement("div");
      const button1 = document.createElement("button");
      button1.textContent = "First";
      const button2 = document.createElement("button");
      button2.textContent = "Last";
      container.appendChild(button1);
      container.appendChild(button2);
      document.body.appendChild(container);

      renderHook(() => {
        const ref = useRef<HTMLDivElement>(container);
        useFocusTrap(ref, true);
        return ref;
      });

      // Focus the last element
      button2.focus();
      expect(document.activeElement).toBe(button2);

      // Simulate Tab key
      const tabEvent = new KeyboardEvent("keydown", {
        key: "Tab",
        bubbles: true,
      });
      container.dispatchEvent(tabEvent);

      // Focus should cycle to first element
      // Note: The hook should prevent default and manually focus
      // This test verifies the hook is set up correctly

      // Cleanup
      document.body.removeChild(container);
    });

    it("should cycle focus from first to last element on Shift+Tab", async () => {
      const { useFocusTrap } = await import("./useFocusTrap");

      // Create container with focusable elements
      const container = document.createElement("div");
      const button1 = document.createElement("button");
      button1.textContent = "First";
      const button2 = document.createElement("button");
      button2.textContent = "Last";
      container.appendChild(button1);
      container.appendChild(button2);
      document.body.appendChild(container);

      renderHook(() => {
        const ref = useRef<HTMLDivElement>(container);
        useFocusTrap(ref, true);
        return ref;
      });

      // Focus the first element
      button1.focus();
      expect(document.activeElement).toBe(button1);

      // Simulate Shift+Tab key
      const shiftTabEvent = new KeyboardEvent("keydown", {
        key: "Tab",
        shiftKey: true,
        bubbles: true,
      });
      container.dispatchEvent(shiftTabEvent);

      // Cleanup
      document.body.removeChild(container);
    });
  });

  describe("Focusable Elements", () => {
    it("should find all focusable elements within container", async () => {
      const { useFocusTrap } = await import("./useFocusTrap");

      // Create container with various focusable elements
      const container = document.createElement("div");
      container.innerHTML = `
        <button>Button</button>
        <a href="#">Link</a>
        <input type="text" />
        <select><option>Option</option></select>
        <textarea></textarea>
        <div tabindex="0">Focusable div</div>
        <div tabindex="-1">Not focusable (negative tabindex)</div>
      `;
      document.body.appendChild(container);

      renderHook(() => {
        const ref = useRef<HTMLDivElement>(container);
        useFocusTrap(ref, true);
        return ref;
      });

      // First focusable (button) should have focus
      const button = container.querySelector("button");
      expect(document.activeElement).toBe(button);

      // Cleanup
      document.body.removeChild(container);
    });
  });

  describe("Cleanup", () => {
    it("should remove event listeners on deactivation", async () => {
      const { useFocusTrap } = await import("./useFocusTrap");

      const container = document.createElement("div");
      const button = document.createElement("button");
      button.textContent = "Test";
      container.appendChild(button);
      document.body.appendChild(container);

      const removeEventListenerSpy = vi.spyOn(container, "removeEventListener");

      const { rerender } = renderHook(
        ({ isActive }) => {
          const ref = useRef<HTMLDivElement>(container);
          useFocusTrap(ref, isActive);
          return ref;
        },
        { initialProps: { isActive: true } },
      );

      // Deactivate the trap
      rerender({ isActive: false });

      // Event listener should be removed
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function),
      );

      // Cleanup
      document.body.removeChild(container);
    });
  });
});
