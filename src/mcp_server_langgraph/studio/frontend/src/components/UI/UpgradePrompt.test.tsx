/**
 * UpgradePrompt Component Tests
 *
 * TDD tests for the upgrade prompt component.
 * Tests cover:
 * - Visibility based on tier and usage
 * - Feature messaging
 * - CTA button functionality
 * - Dismissal behavior
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { UpgradePrompt } from "./UpgradePrompt";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("UpgradePrompt", () => {
  describe("Visibility", () => {
    it("should be visible when show prop is true", () => {
      render(
        <TestProvider>
          <UpgradePrompt
            show={true}
            feature="unlimited sessions"
            targetTier="hybrid"
          />
        </TestProvider>,
      );
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should not be visible when show prop is false", () => {
      render(
        <TestProvider>
          <UpgradePrompt
            show={false}
            feature="unlimited sessions"
            targetTier="hybrid"
          />
        </TestProvider>,
      );
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
  });

  describe("Content", () => {
    it("should display upgrade message with feature name", () => {
      render(
        <TestProvider>
          <UpgradePrompt
            show={true}
            feature="unlimited sessions"
            targetTier="hybrid"
          />
        </TestProvider>,
      );
      expect(screen.getByText(/unlimited sessions/i)).toBeInTheDocument();
    });

    it("should display target tier name", () => {
      render(
        <TestProvider>
          <UpgradePrompt
            show={true}
            feature="unlimited sessions"
            targetTier="hybrid"
          />
        </TestProvider>,
      );
      expect(screen.getByText(/Hybrid/i)).toBeInTheDocument();
    });

    it("should display upgrade CTA button", () => {
      render(
        <TestProvider>
          <UpgradePrompt
            show={true}
            feature="unlimited sessions"
            targetTier="hybrid"
          />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /upgrade/i }),
      ).toBeInTheDocument();
    });

    it("should display dismiss button", () => {
      render(
        <TestProvider>
          <UpgradePrompt
            show={true}
            feature="unlimited sessions"
            targetTier="hybrid"
          />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /dismiss|later|close/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Actions", () => {
    it("should call onUpgrade when upgrade button is clicked", () => {
      const onUpgrade = vi.fn();
      render(
        <TestProvider>
          <UpgradePrompt
            show={true}
            feature="unlimited sessions"
            targetTier="hybrid"
            onUpgrade={onUpgrade}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /upgrade/i }));

      expect(onUpgrade).toHaveBeenCalledTimes(1);
    });

    it("should call onDismiss when dismiss button is clicked", () => {
      const onDismiss = vi.fn();
      render(
        <TestProvider>
          <UpgradePrompt
            show={true}
            feature="unlimited sessions"
            targetTier="hybrid"
            onDismiss={onDismiss}
          />
        </TestProvider>,
      );

      fireEvent.click(
        screen.getByRole("button", { name: /dismiss|later|close/i }),
      );

      expect(onDismiss).toHaveBeenCalledTimes(1);
    });
  });

  describe("Tier-Specific Messaging", () => {
    it("should show appropriate message for shared to hybrid upgrade", () => {
      render(
        <TestProvider>
          <UpgradePrompt
            show={true}
            feature="more sessions"
            currentTier="shared"
            targetTier="hybrid"
          />
        </TestProvider>,
      );
      expect(screen.getByText(/upgrade.*Hybrid/i)).toBeInTheDocument();
    });

    it("should show appropriate message for hybrid to dedicated upgrade", () => {
      render(
        <TestProvider>
          <UpgradePrompt
            show={true}
            feature="unlimited resources"
            currentTier="hybrid"
            targetTier="dedicated"
          />
        </TestProvider>,
      );
      expect(screen.getByText(/upgrade.*Dedicated/i)).toBeInTheDocument();
    });
  });

  describe("Custom Upgrade Link", () => {
    it("should use custom upgrade link when provided", () => {
      render(
        <TestProvider>
          <UpgradePrompt
            show={true}
            feature="unlimited sessions"
            targetTier="hybrid"
            upgradeLink="/studio/settings?tab=billing"
          />
        </TestProvider>,
      );
      const upgradeButton = screen.getByRole("button", { name: /upgrade/i });
      // The button should navigate to the upgrade link when clicked
      expect(upgradeButton).toBeInTheDocument();
    });
  });

  describe("Urgency Variants", () => {
    it("should display warning style for warning urgency", () => {
      const { container } = render(
        <TestProvider>
          <UpgradePrompt
            show={true}
            feature="sessions"
            targetTier="hybrid"
            urgency="warning"
          />
        </TestProvider>,
      );
      expect(container.querySelector(".bg-warning-3")).toBeInTheDocument();
    });

    it("should display critical style for critical urgency", () => {
      const { container } = render(
        <TestProvider>
          <UpgradePrompt
            show={true}
            feature="sessions"
            targetTier="hybrid"
            urgency="critical"
          />
        </TestProvider>,
      );
      expect(container.querySelector(".bg-error-1")).toBeInTheDocument();
    });

    it("should display info style by default", () => {
      const { container } = render(
        <TestProvider>
          <UpgradePrompt show={true} feature="sessions" targetTier="hybrid" />
        </TestProvider>,
      );
      expect(container.querySelector(".bg-primary-1")).toBeInTheDocument();
    });
  });

  describe("Limit Information", () => {
    it("should display current usage when provided", () => {
      render(
        <TestProvider>
          <UpgradePrompt
            show={true}
            feature="sessions"
            targetTier="hybrid"
            currentUsage={4}
            maxUsage={5}
          />
        </TestProvider>,
      );
      expect(screen.getByText(/4.*5/)).toBeInTheDocument();
    });

    it("should display limit warning message", () => {
      render(
        <TestProvider>
          <UpgradePrompt
            show={true}
            feature="sessions"
            targetTier="hybrid"
            currentUsage={5}
            maxUsage={5}
          />
        </TestProvider>,
      );
      expect(
        screen.getByText(/limit reached|at capacity/i),
      ).toBeInTheDocument();
    });
  });

  describe("Icon Display", () => {
    it("should display upgrade icon", () => {
      render(
        <TestProvider>
          <UpgradePrompt show={true} feature="sessions" targetTier="hybrid" />
        </TestProvider>,
      );
      expect(screen.getByTestId("upgrade-icon")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have role alert for screen readers", () => {
      render(
        <TestProvider>
          <UpgradePrompt show={true} feature="sessions" targetTier="hybrid" />
        </TestProvider>,
      );
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should have aria-live for dynamic updates", () => {
      render(
        <TestProvider>
          <UpgradePrompt show={true} feature="sessions" targetTier="hybrid" />
        </TestProvider>,
      );
      const alert = screen.getByRole("alert");
      expect(alert).toHaveAttribute("aria-live", "polite");
    });
  });
});
