/**
 * Performance Utilities Tests
 *
 * TDD tests for DevTools performance optimization utilities.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useRef } from "react";

import {
  useBatchedUpdates,
  useDebouncedValue,
  useThrottledCallback,
  useVirtualList,
  useMemoizedFilter,
  useStableCallback,
  useRenderCount,
  measureTime,
  useLazyInit,
  useIntersectionObserver,
} from "./performance";

// =============================================================================
// useBatchedUpdates Tests
// =============================================================================

describe("useBatchedUpdates", () => {
  it("should return first batch of items", () => {
    const items = Array.from({ length: 100 }, (_, i) => i);

    const { result } = renderHook(() => useBatchedUpdates(items, 20));

    expect(result.current.displayedItems).toHaveLength(20);
    expect(result.current.displayedItems[0]).toBe(0);
    expect(result.current.displayedItems[19]).toBe(19);
  });

  it("should indicate hasMore when more items exist", () => {
    const items = Array.from({ length: 100 }, (_, i) => i);

    const { result } = renderHook(() => useBatchedUpdates(items, 20));

    expect(result.current.hasMore).toBe(true);
  });

  it("should indicate no more items when all displayed", () => {
    const items = Array.from({ length: 10 }, (_, i) => i);

    const { result } = renderHook(() => useBatchedUpdates(items, 20));

    expect(result.current.hasMore).toBe(false);
  });

  it("should load more items when loadMore called", async () => {
    const items = Array.from({ length: 100 }, (_, i) => i);

    const { result } = renderHook(() => useBatchedUpdates(items, 20));

    expect(result.current.displayedItems).toHaveLength(20);

    act(() => {
      result.current.loadMore();
    });

    // Wait for requestAnimationFrame
    await waitFor(() => {
      expect(result.current.displayedItems.length).toBeGreaterThan(20);
    });
  });

  it("should not exceed total items", async () => {
    const items = Array.from({ length: 30 }, (_, i) => i);

    const { result } = renderHook(() => useBatchedUpdates(items, 20));

    act(() => {
      result.current.loadMore();
    });

    await waitFor(() => {
      expect(result.current.displayedItems).toHaveLength(30);
      expect(result.current.hasMore).toBe(false);
    });
  });

  it("should use default batch size of 50", () => {
    const items = Array.from({ length: 100 }, (_, i) => i);

    const { result } = renderHook(() => useBatchedUpdates(items));

    expect(result.current.displayedItems).toHaveLength(50);
  });
});

// =============================================================================
// useDebouncedValue Tests
// =============================================================================

describe("useDebouncedValue", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("should return initial value immediately", () => {
    const { result } = renderHook(() => useDebouncedValue("initial", 100));

    expect(result.current).toBe("initial");
  });

  it("should debounce value changes", () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebouncedValue(value, 100),
      { initialProps: { value: "initial" } },
    );

    rerender({ value: "updated" });

    // Value should not change immediately
    expect(result.current).toBe("initial");

    act(() => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current).toBe("updated");
  });

  it("should use default delay of 150ms", () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebouncedValue(value),
      { initialProps: { value: "initial" } },
    );

    rerender({ value: "updated" });

    act(() => {
      vi.advanceTimersByTime(149);
    });
    expect(result.current).toBe("initial");

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current).toBe("updated");
  });

  it("should cancel previous timer on rapid changes", () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebouncedValue(value, 100),
      { initialProps: { value: "a" } },
    );

    rerender({ value: "b" });
    act(() => {
      vi.advanceTimersByTime(50);
    });

    rerender({ value: "c" });
    act(() => {
      vi.advanceTimersByTime(50);
    });

    // Should still be "a" because timer was reset
    expect(result.current).toBe("a");

    act(() => {
      vi.advanceTimersByTime(50);
    });

    // Now should be "c" (the final value)
    expect(result.current).toBe("c");
  });
});

// =============================================================================
// useThrottledCallback Tests
// =============================================================================

describe("useThrottledCallback", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("should call callback immediately on first call", () => {
    const callback = vi.fn();

    const { result } = renderHook(() => useThrottledCallback(callback, 100));

    act(() => {
      result.current();
    });

    expect(callback).toHaveBeenCalledTimes(1);
  });

  it("should throttle subsequent calls", () => {
    const callback = vi.fn();

    const { result } = renderHook(() => useThrottledCallback(callback, 100));

    act(() => {
      result.current();
      result.current();
      result.current();
    });

    // Only first call should execute immediately
    expect(callback).toHaveBeenCalledTimes(1);

    act(() => {
      vi.advanceTimersByTime(100);
    });

    // One more should execute after delay
    expect(callback).toHaveBeenCalledTimes(2);
  });

  it("should pass arguments to callback", () => {
    const callback = vi.fn();

    const { result } = renderHook(() => useThrottledCallback(callback, 100));

    act(() => {
      result.current("arg1", "arg2");
    });

    expect(callback).toHaveBeenCalledWith("arg1", "arg2");
  });

  it("should use default delay of 100ms", () => {
    const callback = vi.fn();

    const { result } = renderHook(() => useThrottledCallback(callback));

    act(() => {
      result.current();
      result.current();
    });

    expect(callback).toHaveBeenCalledTimes(1);

    act(() => {
      vi.advanceTimersByTime(100);
    });

    expect(callback).toHaveBeenCalledTimes(2);
  });
});

// =============================================================================
// useVirtualList Tests
// =============================================================================

describe("useVirtualList", () => {
  it("should return virtual items for visible range", () => {
    const items = Array.from({ length: 100 }, (_, i) => `item-${i}`);

    const { result } = renderHook(() =>
      useVirtualList(items, 0, {
        itemHeight: 30,
        containerHeight: 300,
      }),
    );

    // Should show ~10 items (300/30) plus overscan
    expect(result.current.virtualItems.length).toBeGreaterThan(0);
    expect(result.current.virtualItems.length).toBeLessThan(20);
  });

  it("should calculate total height correctly", () => {
    const items = Array.from({ length: 100 }, (_, i) => `item-${i}`);

    const { result } = renderHook(() =>
      useVirtualList(items, 0, {
        itemHeight: 30,
        containerHeight: 300,
      }),
    );

    expect(result.current.totalHeight).toBe(3000); // 100 * 30
  });

  it("should update visible range when scrolling", () => {
    const items = Array.from({ length: 100 }, (_, i) => `item-${i}`);

    const { result, rerender } = renderHook(
      ({ scrollTop }) =>
        useVirtualList(items, scrollTop, {
          itemHeight: 30,
          containerHeight: 300,
        }),
      { initialProps: { scrollTop: 0 } },
    );

    const firstItemIndex = result.current.virtualItems[0]?.index;

    rerender({ scrollTop: 300 }); // Scroll down 10 items

    const newFirstItemIndex = result.current.virtualItems[0]?.index;

    expect(newFirstItemIndex).toBeGreaterThan(firstItemIndex!);
  });

  it("should include overscan items", () => {
    const items = Array.from({ length: 100 }, (_, i) => `item-${i}`);

    const { result } = renderHook(() =>
      useVirtualList(items, 300, {
        itemHeight: 30,
        containerHeight: 300,
        overscan: 5,
      }),
    );

    // First visible item would be index 10, but with overscan 5, should start at 5
    expect(result.current.virtualItems[0]?.index).toBeLessThanOrEqual(10);
  });

  it("should provide correct style for each item", () => {
    const items = ["a", "b", "c"];

    const { result } = renderHook(() =>
      useVirtualList(items, 0, {
        itemHeight: 50,
        containerHeight: 200,
      }),
    );

    const firstItem = result.current.virtualItems[0];
    expect(firstItem?.style.position).toBe("absolute");
    expect(firstItem?.style.height).toBe(50);
    expect(firstItem?.style.top).toBe(0);
  });
});

// =============================================================================
// useMemoizedFilter Tests
// =============================================================================

describe("useMemoizedFilter", () => {
  it("should filter items based on predicate", () => {
    const items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    const isEven = (n: number) => n % 2 === 0;

    const { result } = renderHook(() => useMemoizedFilter(items, isEven));

    expect(result.current).toEqual([2, 4, 6, 8, 10]);
  });

  it("should memoize result for same inputs", () => {
    const items = [1, 2, 3, 4, 5];
    const isEven = (n: number) => n % 2 === 0;

    const { result, rerender } = renderHook(() =>
      useMemoizedFilter(items, isEven),
    );

    const firstResult = result.current;
    rerender();
    const secondResult = result.current;

    expect(firstResult).toBe(secondResult); // Same reference
  });

  it("should update when items change", () => {
    const { result, rerender } = renderHook(
      ({ items }) => useMemoizedFilter(items, (n: number) => n > 2),
      { initialProps: { items: [1, 2, 3] } },
    );

    expect(result.current).toEqual([3]);

    rerender({ items: [1, 2, 3, 4, 5] });

    expect(result.current).toEqual([3, 4, 5]);
  });
});

// =============================================================================
// useStableCallback Tests
// =============================================================================

describe("useStableCallback", () => {
  it("should return stable function reference", () => {
    const callback = vi.fn();

    const { result, rerender } = renderHook(() => useStableCallback(callback));

    const firstRef = result.current;
    rerender();
    const secondRef = result.current;

    expect(firstRef).toBe(secondRef);
  });

  it("should call latest callback version", () => {
    let callCount = 0;
    const callback1 = vi.fn(() => "first");
    const callback2 = vi.fn(() => "second");

    const { result, rerender } = renderHook(
      ({ cb }) => useStableCallback(cb),
      { initialProps: { cb: callback1 } },
    );

    const stableCallback = result.current;

    rerender({ cb: callback2 });

    // Call the stable callback - should call callback2
    act(() => {
      stableCallback();
    });

    expect(callback1).not.toHaveBeenCalled();
    expect(callback2).toHaveBeenCalled();
  });

  it("should pass arguments through", () => {
    const callback = vi.fn();

    const { result } = renderHook(() => useStableCallback(callback));

    act(() => {
      result.current("a", "b", "c");
    });

    expect(callback).toHaveBeenCalledWith("a", "b", "c");
  });
});

// =============================================================================
// useRenderCount Tests
// =============================================================================

describe("useRenderCount", () => {
  it("should log render count in development", () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = "development";
    const consoleSpy = vi.spyOn(console, "debug").mockImplementation(() => {});

    const { rerender } = renderHook(() => useRenderCount("TestComponent"));

    rerender();
    rerender();

    expect(consoleSpy).toHaveBeenCalled();

    consoleSpy.mockRestore();
    process.env.NODE_ENV = originalEnv;
  });
});

// =============================================================================
// measureTime Tests
// =============================================================================

describe("measureTime", () => {
  it("should return operation result", () => {
    const result = measureTime(() => 42, "test");

    expect(result).toBe(42);
  });

  it("should log timing in development", () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = "development";
    const consoleSpy = vi.spyOn(console, "debug").mockImplementation(() => {});

    measureTime(() => "result", "test-operation");

    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining("[DevTools] test-operation"),
    );

    consoleSpy.mockRestore();
    process.env.NODE_ENV = originalEnv;
  });

  it("should not log in production", () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = "production";
    const consoleSpy = vi.spyOn(console, "debug").mockImplementation(() => {});

    measureTime(() => "result", "test");

    expect(consoleSpy).not.toHaveBeenCalled();

    consoleSpy.mockRestore();
    process.env.NODE_ENV = originalEnv;
  });
});

// =============================================================================
// useLazyInit Tests
// =============================================================================

describe("useLazyInit", () => {
  it("should initialize value lazily", () => {
    const factory = vi.fn(() => "initialized");

    const { result } = renderHook(() => useLazyInit(factory));

    expect(result.current).toBe("initialized");
    expect(factory).toHaveBeenCalledTimes(1);
  });

  it("should not reinitialize on rerender", () => {
    const factory = vi.fn(() => "initialized");

    const { result, rerender } = renderHook(() => useLazyInit(factory));

    rerender();
    rerender();

    expect(factory).toHaveBeenCalledTimes(1);
    expect(result.current).toBe("initialized");
  });

  it("should handle complex objects", () => {
    const factory = () => ({ key: "value", nested: { a: 1 } });

    const { result } = renderHook(() => useLazyInit(factory));

    expect(result.current).toEqual({ key: "value", nested: { a: 1 } });
  });
});

// =============================================================================
// useIntersectionObserver Tests
// =============================================================================

describe("useIntersectionObserver", () => {
  let mockObserve: ReturnType<typeof vi.fn>;
  let mockDisconnect: ReturnType<typeof vi.fn>;
  let observerCallback: IntersectionObserverCallback;

  beforeEach(() => {
    mockObserve = vi.fn();
    mockDisconnect = vi.fn();

    global.IntersectionObserver = vi.fn((callback) => {
      observerCallback = callback;
      return {
        observe: mockObserve,
        disconnect: mockDisconnect,
        unobserve: vi.fn(),
        root: null,
        rootMargin: "",
        thresholds: [],
        takeRecords: () => [],
      };
    }) as unknown as typeof IntersectionObserver;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should return false initially", () => {
    const ref = { current: document.createElement("div") };

    const { result } = renderHook(() => useIntersectionObserver(ref));

    expect(result.current).toBe(false);
  });

  it("should observe the element", () => {
    const element = document.createElement("div");
    const ref = { current: element };

    renderHook(() => useIntersectionObserver(ref));

    expect(mockObserve).toHaveBeenCalledWith(element);
  });

  it("should update when intersection changes", () => {
    const element = document.createElement("div");
    const ref = { current: element };

    const { result } = renderHook(() => useIntersectionObserver(ref));

    expect(result.current).toBe(false);

    act(() => {
      observerCallback(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      );
    });

    expect(result.current).toBe(true);
  });

  it("should disconnect on unmount", () => {
    const ref = { current: document.createElement("div") };

    const { unmount } = renderHook(() => useIntersectionObserver(ref));

    unmount();

    expect(mockDisconnect).toHaveBeenCalled();
  });

  it("should handle null ref", () => {
    const ref = { current: null };

    const { result } = renderHook(() => useIntersectionObserver(ref));

    expect(result.current).toBe(false);
    expect(mockObserve).not.toHaveBeenCalled();
  });
});
