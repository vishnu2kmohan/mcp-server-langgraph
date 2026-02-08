/**
 * TierUsageBar Component Tests
 *
 * TDD tests for the tier usage indicator component.
 * Tests cover:
 * - Usage display (current/max)
 * - Progress bar visualization
 * - Warning states when approaching limits
 * - Tier-specific styling
 * - Unlimited tier handling
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { TierUsageBar } from "./TierUsageBar";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("TierUsageBar", () => {
  describe("Basic Display", () => {
    it("should display the usage label", () => {
      render(
        <TestProvider>
          <TierUsageBar current={2} max={5} label="Active Sessions" />
        </TestProvider>,
      );
      expect(screen.getByText("Active Sessions")).toBeInTheDocument();
    });

    it("should display current usage count", () => {
      render(
        <TestProvider>
          <TierUsageBar current={3} max={5} label="Sessions" />
        </TestProvider>,
      );
      expect(screen.getByText(/3/)).toBeInTheDocument();
    });

    it("should display max limit", () => {
      render(
        <TestProvider>
          <TierUsageBar current={3} max={5} label="Sessions" />
        </TestProvider>,
      );
      expect(screen.getByText(/5/)).toBeInTheDocument();
    });

    it("should display usage as fraction", () => {
      render(
        <TestProvider>
          <TierUsageBar current={2} max={5} label="Sessions" />
        </TestProvider>,
      );
      expect(screen.getByText("2 / 5")).toBeInTheDocument();
    });

    it("should have a progress bar element", () => {
      render(
        <TestProvider>
          <TierUsageBar current={2} max={5} label="Sessions" />
        </TestProvider>,
      );
      expect(screen.getByRole("progressbar")).toBeInTheDocument();
    });

    it("should set aria-valuenow on progress bar", () => {
      render(
        <TestProvider>
          <TierUsageBar current={2} max={5} label="Sessions" />
        </TestProvider>,
      );
      const progressBar = screen.getByRole("progressbar");
      expect(progressBar).toHaveAttribute("aria-valuenow", "2");
    });

    it("should set aria-valuemax on progress bar", () => {
      render(
        <TestProvider>
          <TierUsageBar current={2} max={5} label="Sessions" />
        </TestProvider>,
      );
      const progressBar = screen.getByRole("progressbar");
      expect(progressBar).toHaveAttribute("aria-valuemax", "5");
    });
  });

  describe("Progress Bar Width", () => {
    it("should show 40% width for 2/5 usage", () => {
      render(
        <TestProvider>
          <TierUsageBar current={2} max={5} label="Sessions" />
        </TestProvider>,
      );
      const progressBar = screen.getByTestId("tier-usage-fill");
      expect(progressBar).toHaveStyle({ "--progress": "40%" });
    });

    it("should show 100% progress when at max", () => {
      render(
        <TestProvider>
          <TierUsageBar current={5} max={5} label="Sessions" />
        </TestProvider>,
      );
      const progressBar = screen.getByTestId("tier-usage-fill");
      expect(progressBar).toHaveStyle({ "--progress": "100%" });
    });

    it("should show 0% progress when current is 0", () => {
      render(
        <TestProvider>
          <TierUsageBar current={0} max={5} label="Sessions" />
        </TestProvider>,
      );
      const progressBar = screen.getByTestId("tier-usage-fill");
      expect(progressBar).toHaveStyle({ "--progress": "0%" });
    });
  });

  describe("Warning States", () => {
    it("should show normal styling when usage is below 70%", () => {
      render(
        <TestProvider>
          <TierUsageBar current={2} max={5} label="Sessions" />
        </TestProvider>,
      );
      const progressBar = screen.getByTestId("tier-usage-fill");
      expect(progressBar).toHaveClass("bg-primary-9");
    });

    it("should show warning styling when usage is at 80%", () => {
      render(
        <TestProvider>
          <TierUsageBar current={4} max={5} label="Sessions" />
        </TestProvider>,
      );
      const progressBar = screen.getByTestId("tier-usage-fill");
      expect(progressBar).toHaveClass("bg-warning-9");
    });

    it("should show danger styling when at 100%", () => {
      render(
        <TestProvider>
          <TierUsageBar current={5} max={5} label="Sessions" />
        </TestProvider>,
      );
      const progressBar = screen.getByTestId("tier-usage-fill");
      expect(progressBar).toHaveClass("bg-error-9");
    });

    it("should show warning icon when approaching limit", () => {
      render(
        <TestProvider>
          <TierUsageBar current={4} max={5} label="Sessions" />
        </TestProvider>,
      );
      expect(screen.getByTestId("usage-warning-icon")).toBeInTheDocument();
    });

    it("should not show warning icon when usage is low", () => {
      render(
        <TestProvider>
          <TierUsageBar current={2} max={5} label="Sessions" />
        </TestProvider>,
      );
      expect(
        screen.queryByTestId("usage-warning-icon"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Unlimited Tier", () => {
    it("should display 'Unlimited' when max is -1", () => {
      render(
        <TestProvider>
          <TierUsageBar current={50} max={-1} label="Sessions" />
        </TestProvider>,
      );
      expect(screen.getByText(/Unlimited/)).toBeInTheDocument();
    });

    it("should show current usage with unlimited tier", () => {
      render(
        <TestProvider>
          <TierUsageBar current={50} max={-1} label="Sessions" />
        </TestProvider>,
      );
      expect(screen.getByText("50")).toBeInTheDocument();
    });

    it("should show full progress bar for unlimited tier", () => {
      render(
        <TestProvider>
          <TierUsageBar current={50} max={-1} label="Sessions" />
        </TestProvider>,
      );
      const progressBar = screen.getByTestId("tier-usage-fill");
      expect(progressBar).toHaveClass("bg-success-9");
    });

    it("should not show warning for unlimited tier", () => {
      render(
        <TestProvider>
          <TierUsageBar current={1000} max={-1} label="Sessions" />
        </TestProvider>,
      );
      expect(
        screen.queryByTestId("usage-warning-icon"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Tier Badge", () => {
    it("should display tier name when provided", () => {
      render(
        <TestProvider>
          <TierUsageBar current={2} max={5} label="Sessions" tier="shared" />
        </TestProvider>,
      );
      expect(screen.getByText("Shared")).toBeInTheDocument();
    });

    it("should display hybrid tier badge", () => {
      render(
        <TestProvider>
          <TierUsageBar current={10} max={20} label="Sessions" tier="hybrid" />
        </TestProvider>,
      );
      expect(screen.getByText("Hybrid")).toBeInTheDocument();
    });

    it("should display dedicated tier badge", () => {
      render(
        <TestProvider>
          <TierUsageBar
            current={50}
            max={-1}
            label="Sessions"
            tier="dedicated"
          />
        </TestProvider>,
      );
      expect(screen.getByText("Dedicated")).toBeInTheDocument();
    });
  });

  describe("Compact Variant", () => {
    it("should hide label in compact mode", () => {
      render(
        <TestProvider>
          <TierUsageBar
            current={2}
            max={5}
            label="Active Sessions"
            variant="compact"
          />
        </TestProvider>,
      );
      expect(screen.queryByText("Active Sessions")).not.toBeInTheDocument();
    });

    it("should still show usage count in compact mode", () => {
      render(
        <TestProvider>
          <TierUsageBar
            current={2}
            max={5}
            label="Sessions"
            variant="compact"
          />
        </TestProvider>,
      );
      expect(screen.getByText("2 / 5")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible progress bar", () => {
      render(
        <TestProvider>
          <TierUsageBar current={2} max={5} label="Sessions" />
        </TestProvider>,
      );
      const progressBar = screen.getByRole("progressbar");
      expect(progressBar).toHaveAttribute("aria-label", "Sessions usage");
    });
  });
});
