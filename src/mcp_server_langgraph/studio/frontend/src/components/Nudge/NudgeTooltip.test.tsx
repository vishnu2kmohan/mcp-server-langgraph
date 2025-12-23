/**
 * NudgeTooltip Component Tests
 *
 * Sprint 3 - Phase 1.3: Nudge System
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { NudgeTooltip } from "./NudgeTooltip";
import type { Nudge } from "../../hooks/useNudges";

const mockNudge: Nudge = {
  id: "keyboard-shortcuts",
  type: "tooltip",
  targetElement: "[data-testid='search-input']",
  message: "Pro tip: Press Cmd+K for quick search",
  priority: "medium",
  category: "productivity",
};

describe("NudgeTooltip", () => {
  it("renders nudge message", () => {
    render(<NudgeTooltip nudge={mockNudge} onDismiss={() => {}} />);

    expect(screen.getByText(/pro tip/i)).toBeInTheDocument();
  });

  it("calls onDismiss when dismiss button clicked", () => {
    const onDismiss = vi.fn();
    render(<NudgeTooltip nudge={mockNudge} onDismiss={onDismiss} />);

    fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));
    expect(onDismiss).toHaveBeenCalled();
  });

  it("calls onAccept when action button clicked", () => {
    const onAccept = vi.fn();
    render(
      <NudgeTooltip
        nudge={mockNudge}
        onDismiss={() => {}}
        onAccept={onAccept}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /got it/i }));
    expect(onAccept).toHaveBeenCalled();
  });

  it("shows priority badge for high priority nudges", () => {
    const highPriorityNudge = { ...mockNudge, priority: "high" as const };
    render(<NudgeTooltip nudge={highPriorityNudge} onDismiss={() => {}} />);

    expect(screen.getByText(/high/i)).toBeInTheDocument();
  });

  it("has accessible structure", () => {
    render(<NudgeTooltip nudge={mockNudge} onDismiss={() => {}} />);

    expect(screen.getByRole("tooltip")).toBeInTheDocument();
  });
});
