/**
 * NudgeTooltip Component Tests
 *
 * Sprint 3 - Phase 1.3: Nudge System
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { NudgeTooltip } from "./NudgeTooltip";
import type { Nudge } from "../../hooks/useNudges";

import { TestProvider } from "@/test-utils";

const mockNudge: Nudge = {
  id: "keyboard-shortcuts",
  type: "tooltip",
  targetElement: "[data-testid='search-input']",
  message: "Pro tip: Press Cmd+K for quick search",
  priority: "medium",
  category: "productivity",
};

describe("NudgeTooltip", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders nudge message", () => {
    render(
      <TestProvider>
        <NudgeTooltip nudge={mockNudge} onDismiss={() => {}} />
      </TestProvider>,
    );

    expect(screen.getByText(/pro tip/i)).toBeInTheDocument();
  });

  it("calls onDismiss when dismiss button clicked", () => {
    const onDismiss = vi.fn();
    render(
      <TestProvider>
        <NudgeTooltip nudge={mockNudge} onDismiss={onDismiss} />
      </TestProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));
    expect(onDismiss).toHaveBeenCalled();
  });

  it("calls onAccept when action button clicked", () => {
    const onAccept = vi.fn();
    render(
      <TestProvider>
        <NudgeTooltip
          nudge={mockNudge}
          onDismiss={() => {}}
          onAccept={onAccept}
        />
      </TestProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /got it/i }));
    expect(onAccept).toHaveBeenCalled();
  });

  it("shows priority badge for high priority nudges", () => {
    const highPriorityNudge = { ...mockNudge, priority: "high" as const };
    render(
      <TestProvider>
        <NudgeTooltip nudge={highPriorityNudge} onDismiss={() => {}} />
      </TestProvider>,
    );

    expect(screen.getByText(/high/i)).toBeInTheDocument();
  });

  it("has accessible structure", () => {
    render(
      <TestProvider>
        <NudgeTooltip nudge={mockNudge} onDismiss={() => {}} />
      </TestProvider>,
    );

    expect(screen.getByRole("tooltip")).toBeInTheDocument();
  });

  describe("Accessibility - Touch Targets (WCAG 2.5.8)", () => {
    it("dismiss button meets minimum 24x24px touch target", () => {
      render(
        <TestProvider>
          <NudgeTooltip nudge={mockNudge} onDismiss={() => {}} />
        </TestProvider>,
      );

      const dismissButton = screen.getByRole("button", { name: /dismiss/i });
      // Check for min-h-6 min-w-6 (24px) classes
      expect(dismissButton.className).toMatch(/min-h-6|h-6/);
      expect(dismissButton.className).toMatch(/min-w-6|w-6/);
    });

    it("action button meets minimum 24x24px touch target when present", () => {
      render(
        <TestProvider>
          <NudgeTooltip
            nudge={mockNudge}
            onDismiss={() => {}}
            onAccept={() => {}}
          />
        </TestProvider>,
      );

      const actionButton = screen.getByRole("button", { name: /got it/i });
      // Button component uses size="sm" which has min-h-6 (24px)
      expect(actionButton.className).toMatch(/min-h-6|min-h-\[24px\]/);
    });
  });
});
