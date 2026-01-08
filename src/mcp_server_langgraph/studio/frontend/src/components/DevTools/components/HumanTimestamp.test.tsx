import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HumanTimestamp } from "./HumanTimestamp";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("HumanTimestamp", () => {
  it("renders formatted time and tooltip", () => {
    const ts = Date.UTC(2024, 0, 1, 12, 34, 56, 789);
    render(<HumanTimestamp timestamp={ts} />);

    const el = screen.getByTestId("human-timestamp");
    expect(el).toBeInTheDocument();
    expect(el).toHaveAttribute("title", "2024-01-01T12:34:56.789Z");
    expect(el.textContent).toMatch(/12:34:56\./);
  });

  it("returns null for invalid timestamp", () => {
    const { container } = render(<HumanTimestamp timestamp={"not-a-date"} />);
    expect(container.textContent).toBe("");
  });
});
