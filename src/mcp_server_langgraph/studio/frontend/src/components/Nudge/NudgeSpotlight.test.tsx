/**
 * NudgeSpotlight Component Tests
 *
 * TDD - Sprint 3 - Phase 1.3: Nudge System
 *
 * A spotlight overlay nudge for guided tours and feature discovery.
 * Creates a focused highlight around a target element.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { NudgeSpotlight } from "./NudgeSpotlight";
import type { Nudge } from "../../hooks/useNudges";

import { TestProvider } from "@/test-utils";

// =============================================================================
// Test Data
// =============================================================================

const mockNudge: Nudge = {
  id: "feature-discovery",
  type: "spotlight",
  targetElement: "[data-testid='new-feature-button']",
  message: "Check out this new feature! Click here to get started.",
  priority: "high",
  category: "feature-discovery",
};

const mockNudgeNoTarget: Nudge = {
  id: "general-spotlight",
  type: "spotlight",
  message: "Welcome to the app! Let us show you around.",
  priority: "medium",
  category: "onboarding",
};

// =============================================================================
// Tests
// =============================================================================

describe("NudgeSpotlight", () => {
  beforeEach(() => {
    // Create a target element in the DOM
    const targetElement = document.createElement("button");
    targetElement.setAttribute("data-testid", "new-feature-button");
    targetElement.textContent = "New Feature";
    document.body.appendChild(targetElement);
  });

  afterEach(() => {
    cleanup();
    // Clean up target element
    const target = document.querySelector("[data-testid='new-feature-button']");
    if (target) {
      document.body.removeChild(target);
    }
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("renders spotlight message", () => {
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudge} onDismiss={() => {}} />
        </TestProvider>,
      );

      expect(
        screen.getByText(/check out this new feature/i),
      ).toBeInTheDocument();
    });

    it("renders spotlight overlay", () => {
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudge} onDismiss={() => {}} />
        </TestProvider>,
      );

      expect(screen.getByTestId("spotlight-overlay")).toBeInTheDocument();
    });

    it("renders spotlight card", () => {
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudge} onDismiss={() => {}} />
        </TestProvider>,
      );

      expect(screen.getByTestId("spotlight-card")).toBeInTheDocument();
    });

    it("renders with correct nudge ID in data attribute", () => {
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudge} onDismiss={() => {}} />
        </TestProvider>,
      );

      const spotlight = screen.getByTestId(`nudge-spotlight-${mockNudge.id}`);
      expect(spotlight).toBeInTheDocument();
    });
  });

  describe("Interactions", () => {
    it("calls onDismiss when overlay clicked", () => {
      const onDismiss = vi.fn();
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudge} onDismiss={onDismiss} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("spotlight-overlay"));
      expect(onDismiss).toHaveBeenCalled();
    });

    it("calls onDismiss when close button clicked", () => {
      const onDismiss = vi.fn();
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudge} onDismiss={onDismiss} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /close/i }));
      expect(onDismiss).toHaveBeenCalled();
    });

    it("calls onAccept when action button clicked", () => {
      const onAccept = vi.fn();
      render(
        <TestProvider>
          <NudgeSpotlight
            nudge={mockNudge}
            onDismiss={() => {}}
            onAccept={onAccept}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /got it/i }));
      expect(onAccept).toHaveBeenCalled();
    });

    it("does not dismiss when card is clicked", () => {
      const onDismiss = vi.fn();
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudge} onDismiss={onDismiss} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("spotlight-card"));
      expect(onDismiss).not.toHaveBeenCalled();
    });
  });

  describe("Target Element Highlighting", () => {
    it("calculates spotlight position based on target element", () => {
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudge} onDismiss={() => {}} />
        </TestProvider>,
      );

      // The spotlight cutout should exist
      const overlay = screen.getByTestId("spotlight-overlay");
      expect(overlay).toHaveClass("spotlight-overlay");
    });

    it("handles missing target element gracefully", () => {
      // Remove the target element
      const target = document.querySelector(
        "[data-testid='new-feature-button']",
      );
      if (target) {
        document.body.removeChild(target);
      }

      // Should still render without crashing
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudge} onDismiss={() => {}} />
        </TestProvider>,
      );

      expect(
        screen.getByText(/check out this new feature/i),
      ).toBeInTheDocument();
    });

    it("renders centered when no target element specified", () => {
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudgeNoTarget} onDismiss={() => {}} />
        </TestProvider>,
      );

      const card = screen.getByTestId("spotlight-card");
      expect(card).toHaveClass("spotlight-card-centered");
    });
  });

  describe("Priority Styling", () => {
    it("applies high priority styling", () => {
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudge} onDismiss={() => {}} />
        </TestProvider>,
      );

      const card = screen.getByTestId("spotlight-card");
      expect(card).toHaveClass("spotlight-priority-high");
    });

    it("applies medium priority styling", () => {
      const mediumNudge = { ...mockNudge, priority: "medium" as const };
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mediumNudge} onDismiss={() => {}} />
        </TestProvider>,
      );

      const card = screen.getByTestId("spotlight-card");
      expect(card).toHaveClass("spotlight-priority-medium");
    });

    it("applies low priority styling", () => {
      const lowNudge = { ...mockNudge, priority: "low" as const };
      render(
        <TestProvider>
          <NudgeSpotlight nudge={lowNudge} onDismiss={() => {}} />
        </TestProvider>,
      );

      const card = screen.getByTestId("spotlight-card");
      expect(card).toHaveClass("spotlight-priority-low");
    });
  });

  describe("Custom Actions", () => {
    it("renders custom action text", () => {
      render(
        <TestProvider>
          <NudgeSpotlight
            nudge={mockNudge}
            onDismiss={() => {}}
            onAccept={() => {}}
            actionText="Learn More"
          />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /learn more/i }),
      ).toBeInTheDocument();
    });

    it("renders secondary action when provided", () => {
      render(
        <TestProvider>
          <NudgeSpotlight
            nudge={mockNudge}
            onDismiss={() => {}}
            onAccept={() => {}}
            secondaryActionText="Skip Tour"
            onSecondaryAction={() => {}}
          />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /skip tour/i }),
      ).toBeInTheDocument();
    });

    it("calls onSecondaryAction when secondary button clicked", () => {
      const onSecondary = vi.fn();
      render(
        <TestProvider>
          <NudgeSpotlight
            nudge={mockNudge}
            onDismiss={() => {}}
            secondaryActionText="Skip"
            onSecondaryAction={onSecondary}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /skip/i }));
      expect(onSecondary).toHaveBeenCalled();
    });
  });

  describe("Step Indicators", () => {
    it("renders step indicator when step info provided", () => {
      render(
        <TestProvider>
          <NudgeSpotlight
            nudge={mockNudge}
            onDismiss={() => {}}
            currentStep={1}
            totalSteps={5}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/step 1 of 5/i)).toBeInTheDocument();
    });

    it("does not render step indicator when no step info", () => {
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudge} onDismiss={() => {}} />
        </TestProvider>,
      );

      expect(screen.queryByText(/step/i)).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has accessible dialog structure", () => {
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudge} onDismiss={() => {}} />
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("has aria-label for spotlight", () => {
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudge} onDismiss={() => {}} />
        </TestProvider>,
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-label");
    });

    it("traps focus within spotlight", () => {
      render(
        <TestProvider>
          <NudgeSpotlight
            nudge={mockNudge}
            onDismiss={() => {}}
            onAccept={() => {}}
          />
        </TestProvider>,
      );

      // First focusable element should be the close button
      const closeButton = screen.getByRole("button", { name: /close/i });
      expect(document.activeElement).toBe(closeButton);
    });

    it("handles Escape key to dismiss", () => {
      const onDismiss = vi.fn();
      render(
        <TestProvider>
          <NudgeSpotlight nudge={mockNudge} onDismiss={onDismiss} />
        </TestProvider>,
      );

      fireEvent.keyDown(document, { key: "Escape" });
      expect(onDismiss).toHaveBeenCalled();
    });
  });

  describe("Custom Styling", () => {
    it("applies custom className", () => {
      render(
        <TestProvider>
          <NudgeSpotlight
            nudge={mockNudge}
            onDismiss={() => {}}
            className="custom-class"
          />
        </TestProvider>,
      );

      const spotlight = screen.getByTestId(`nudge-spotlight-${mockNudge.id}`);
      expect(spotlight).toHaveClass("custom-class");
    });
  });
});
