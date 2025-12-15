/**
 * useDebounce Hook Tests
 *
 * TDD tests for the debounce hook used to optimize API calls
 * by delaying execution until user stops typing.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDebounce, useDebouncedCallback } from "./useDebounce";

describe("useDebounce", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("value debouncing", () => {
    it("should return initial value immediately", () => {
      const { result } = renderHook(() => useDebounce("initial", 300));

      expect(result.current).toBe("initial");
    });

    it("should not update value before delay", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: "initial" } },
      );

      expect(result.current).toBe("initial");

      rerender({ value: "updated" });

      // Advance time less than the delay
      act(() => {
        vi.advanceTimersByTime(100);
      });

      expect(result.current).toBe("initial");
    });

    it("should update value after delay", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: "initial" } },
      );

      rerender({ value: "updated" });

      act(() => {
        vi.advanceTimersByTime(300);
      });

      expect(result.current).toBe("updated");
    });

    it("should reset timer on new value before delay completes", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: "initial" } },
      );

      rerender({ value: "first update" });

      act(() => {
        vi.advanceTimersByTime(200);
      });

      rerender({ value: "second update" });

      act(() => {
        vi.advanceTimersByTime(200);
      });

      // Should still be initial because timer was reset
      expect(result.current).toBe("initial");

      act(() => {
        vi.advanceTimersByTime(100);
      });

      // Now 300ms have passed since second update
      expect(result.current).toBe("second update");
    });

    it("should work with default delay of 300ms", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value),
        { initialProps: { value: "initial" } },
      );

      rerender({ value: "updated" });

      act(() => {
        vi.advanceTimersByTime(299);
      });

      expect(result.current).toBe("initial");

      act(() => {
        vi.advanceTimersByTime(1);
      });

      expect(result.current).toBe("updated");
    });

    it("should work with different data types", () => {
      // Number
      const { result: numResult, rerender: numRerender } = renderHook(
        ({ value }) => useDebounce(value, 100),
        { initialProps: { value: 42 } },
      );

      numRerender({ value: 100 });
      act(() => {
        vi.advanceTimersByTime(100);
      });
      expect(numResult.current).toBe(100);

      // Object
      const obj1 = { name: "test" };
      const obj2 = { name: "updated" };
      const { result: objResult, rerender: objRerender } = renderHook(
        ({ value }) => useDebounce(value, 100),
        { initialProps: { value: obj1 } },
      );

      objRerender({ value: obj2 });
      act(() => {
        vi.advanceTimersByTime(100);
      });
      expect(objResult.current).toEqual(obj2);
    });
  });

  describe("cleanup", () => {
    it("should clean up timer on unmount", () => {
      const clearTimeoutSpy = vi.spyOn(global, "clearTimeout");

      const { unmount } = renderHook(() => useDebounce("value", 300));

      unmount();

      expect(clearTimeoutSpy).toHaveBeenCalled();
    });
  });
});

describe("useDebouncedCallback", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("should not call callback immediately", () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback, 300));

    act(() => {
      result.current("arg1");
    });

    expect(callback).not.toHaveBeenCalled();
  });

  it("should call callback after delay", () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback, 300));

    act(() => {
      result.current("arg1", "arg2");
    });

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith("arg1", "arg2");
  });

  it("should reset timer on repeated calls", () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback, 300));

    act(() => {
      result.current("first");
    });

    act(() => {
      vi.advanceTimersByTime(200);
    });

    act(() => {
      result.current("second");
    });

    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(callback).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(100);
    });

    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith("second");
  });

  it("should have cancel method", () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback, 300));

    act(() => {
      result.current("value");
    });

    act(() => {
      result.current.cancel();
    });

    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(callback).not.toHaveBeenCalled();
  });

  it("should have flush method to execute immediately", () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback, 300));

    act(() => {
      result.current("value");
    });

    act(() => {
      result.current.flush();
    });

    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith("value");
  });

  it("should update callback reference without losing pending calls", () => {
    const callback1 = vi.fn();
    const callback2 = vi.fn();

    const { result, rerender } = renderHook(
      ({ cb }) => useDebouncedCallback(cb, 300),
      { initialProps: { cb: callback1 } },
    );

    act(() => {
      result.current("value");
    });

    rerender({ cb: callback2 });

    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Should call the new callback, not the old one
    expect(callback1).not.toHaveBeenCalled();
    expect(callback2).toHaveBeenCalledWith("value");
  });
});
