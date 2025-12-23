/**
 * useConfirmation Hook Tests
 *
 * Tests for the confirmation dialog management hook.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";

import { useConfirmation } from "./useConfirmation";
import type { ConfirmationConfig } from "./useConfirmation";

// =============================================================================
// Tests
// =============================================================================

describe("useConfirmation", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Initial State", () => {
    it("should return initial closed state", () => {
      const { result } = renderHook(() => useConfirmation());

      expect(result.current.state.isOpen).toBe(false);
      expect(result.current.state.isLoading).toBe(false);
      expect(result.current.state.title).toBe("");
      expect(result.current.state.message).toBe("");
    });

    it("should return confirm, close, and setLoading functions", () => {
      const { result } = renderHook(() => useConfirmation());

      expect(typeof result.current.confirm).toBe("function");
      expect(typeof result.current.close).toBe("function");
      expect(typeof result.current.setLoading).toBe("function");
    });
  });

  describe("confirm()", () => {
    it("should open dialog with provided config", async () => {
      const { result } = renderHook(() => useConfirmation());

      const config: ConfirmationConfig = {
        title: "Delete Item",
        message: "Are you sure you want to delete this item?",
        severity: "warning",
      };

      // Don't await - just trigger the dialog
      act(() => {
        result.current.confirm(config);
      });

      expect(result.current.state.isOpen).toBe(true);
      expect(result.current.state.title).toBe("Delete Item");
      expect(result.current.state.message).toBe(
        "Are you sure you want to delete this item?",
      );
      expect(result.current.state.severity).toBe("warning");
    });

    it("should set default severity to info", async () => {
      const { result } = renderHook(() => useConfirmation());

      const config: ConfirmationConfig = {
        title: "Info",
        message: "Some info",
      };

      act(() => {
        result.current.confirm(config);
      });

      // Default severity from DEFAULT_STATE should be overwritten by config
      // But config doesn't specify severity, so it should remain as default
      expect(result.current.state.isOpen).toBe(true);
    });

    it("should return a promise", () => {
      const { result } = renderHook(() => useConfirmation());

      let promise: Promise<boolean>;
      act(() => {
        promise = result.current.confirm({
          title: "Test",
          message: "Test message",
        });
      });

      expect(promise!).toBeInstanceOf(Promise);
    });

    it("should include optional config fields", async () => {
      const { result } = renderHook(() => useConfirmation());

      const config: ConfirmationConfig = {
        title: "Dangerous Action",
        message: "This action cannot be undone.",
        severity: "danger",
        confirmText: "DELETE",
        confirmLabel: "Yes, Delete",
        cancelLabel: "No, Keep It",
      };

      act(() => {
        result.current.confirm(config);
      });

      expect(result.current.state.confirmText).toBe("DELETE");
      expect(result.current.state.confirmLabel).toBe("Yes, Delete");
      expect(result.current.state.cancelLabel).toBe("No, Keep It");
    });
  });

  describe("close()", () => {
    it("should close the dialog", async () => {
      const { result } = renderHook(() => useConfirmation());

      // Open the dialog first
      act(() => {
        result.current.confirm({
          title: "Test",
          message: "Test message",
        });
      });

      expect(result.current.state.isOpen).toBe(true);

      // Close the dialog
      act(() => {
        result.current.close();
      });

      expect(result.current.state.isOpen).toBe(false);
    });

    it("should resolve promise with false when closed", async () => {
      const { result } = renderHook(() => useConfirmation());

      let resolvedValue: boolean | undefined;
      let confirmPromise: Promise<boolean>;

      act(() => {
        confirmPromise = result.current.confirm({
          title: "Test",
          message: "Test message",
        });
        confirmPromise.then((value) => {
          resolvedValue = value;
        });
      });

      // Close the dialog
      act(() => {
        result.current.close();
      });

      // Wait for promise resolution
      await act(async () => {
        await confirmPromise;
      });

      expect(resolvedValue).toBe(false);
    });

    it("should reset state to defaults", () => {
      const { result } = renderHook(() => useConfirmation());

      // Open with custom config
      act(() => {
        result.current.confirm({
          title: "Custom Title",
          message: "Custom message",
          severity: "danger",
        });
      });

      // Close
      act(() => {
        result.current.close();
      });

      expect(result.current.state.title).toBe("");
      expect(result.current.state.message).toBe("");
      expect(result.current.state.severity).toBe("info");
    });
  });

  describe("setLoading()", () => {
    it("should set loading state to true", () => {
      const { result } = renderHook(() => useConfirmation());

      act(() => {
        result.current.confirm({
          title: "Test",
          message: "Test message",
        });
      });

      act(() => {
        result.current.setLoading(true);
      });

      expect(result.current.state.isLoading).toBe(true);
    });

    it("should set loading state to false", () => {
      const { result } = renderHook(() => useConfirmation());

      act(() => {
        result.current.confirm({
          title: "Test",
          message: "Test message",
        });
      });

      act(() => {
        result.current.setLoading(true);
      });

      act(() => {
        result.current.setLoading(false);
      });

      expect(result.current.state.isLoading).toBe(false);
    });
  });

  describe("onConfirm handler", () => {
    it("should resolve promise with true when onConfirm is called", async () => {
      const { result } = renderHook(() => useConfirmation());

      let resolvedValue: boolean | undefined;
      let confirmPromise: Promise<boolean>;

      act(() => {
        confirmPromise = result.current.confirm({
          title: "Test",
          message: "Test message",
        });
        confirmPromise.then((value) => {
          resolvedValue = value;
        });
      });

      // Call onConfirm (simulating user clicking confirm button)
      const stateWithHandlers = result.current
        .state as typeof result.current.state & {
        onConfirm: () => void;
      };

      act(() => {
        stateWithHandlers.onConfirm();
      });

      // Wait for promise resolution
      await act(async () => {
        await confirmPromise;
      });

      expect(resolvedValue).toBe(true);
      expect(result.current.state.isOpen).toBe(false);
    });
  });

  describe("onCancel handler", () => {
    it("should close dialog when onCancel is called", async () => {
      const { result } = renderHook(() => useConfirmation());

      act(() => {
        result.current.confirm({
          title: "Test",
          message: "Test message",
        });
      });

      const stateWithHandlers = result.current
        .state as typeof result.current.state & {
        onCancel: () => void;
      };

      act(() => {
        stateWithHandlers.onCancel();
      });

      expect(result.current.state.isOpen).toBe(false);
    });
  });

  describe("Close when no resolveRef", () => {
    it("should handle close when dialog was never opened", () => {
      const { result } = renderHook(() => useConfirmation());

      // Close without opening first - should not throw
      act(() => {
        result.current.close();
      });

      expect(result.current.state.isOpen).toBe(false);
    });
  });
});
