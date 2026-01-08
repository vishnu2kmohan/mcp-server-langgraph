import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useAutoTail } from "./useAutoTail";

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("useAutoTail", () => {
  it("auto-scrolls when enabled and entries change", () => {
    const div = document.createElement("div");
    div.style.height = "100px";
    div.style.overflow = "auto";
    div.appendChild(document.createElement("div")).style.height = "200px";

    const ref = { current: div };
    const onEntriesChange = vi.fn();

    const { result, rerender } = renderHook(
      (props) => useAutoTail({ containerRef: ref, ...props }),
      { initialProps: { enabled: true, onEntriesChange } },
    );

    act(() => {
      rerender({ enabled: true, onEntriesChange });
    });

    expect(result.current.isAutoTailing).toBe(true);
    expect(onEntriesChange).toHaveBeenCalled();
  });

  it("pauses when toggled off", () => {
    const ref = { current: document.createElement("div") };
    const { result } = renderHook(() => useAutoTail({ containerRef: ref }));

    act(() => result.current.toggle());
    expect(result.current.isAutoTailing).toBe(false);
  });
});
