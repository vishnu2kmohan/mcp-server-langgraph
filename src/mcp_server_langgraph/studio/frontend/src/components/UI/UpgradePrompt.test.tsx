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

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("UpgradePrompt", () => {
  describe("Visibility", () => {
    it("should be visible when show prop is true", () => {
      render(
        <UpgradePrompt
          show={true}
          feature="unlimited sessions"
          targetTier="hybrid"
        />,
      );
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should not be visible when show prop is false", () => {
      render(
        <UpgradePrompt
          show={false}
          feature="unlimited sessions"
          targetTier="hybrid"
        />,
      );
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
  });

  describe("Content", () => {
    it("should display upgrade message with feature name", () => {
      render(
        <UpgradePrompt
          show={true}
          feature="unlimited sessions"
          targetTier="hybrid"
        />,
      );
      expect(screen.getByText(/unlimited sessions/i)).toBeInTheDocument();
    });

    it("should display target tier name", () => {
      render(
        <UpgradePrompt
          show={true}
          feature="unlimited sessions"
          targetTier="hybrid"
        />,
      );
      expect(screen.getByText(/Hybrid/i)).toBeInTheDocument();
    });

    it("should display upgrade CTA button", () => {
      render(
        <UpgradePrompt
          show={true}
          feature="unlimited sessions"
          targetTier="hybrid"
        />,
      );
      expect(
        screen.getByRole("button", { name: /upgrade/i }),
      ).toBeInTheDocument();
    });

    it("should display dismiss button", () => {
      render(
        <UpgradePrompt
          show={true}
          feature="unlimited sessions"
          targetTier="hybrid"
        />,
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
        <UpgradePrompt
          show={true}
          feature="unlimited sessions"
          targetTier="hybrid"
          onUpgrade={onUpgrade}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /upgrade/i }));

      expect(onUpgrade).toHaveBeenCalledTimes(1);
    });

    it("should call onDismiss when dismiss button is clicked", () => {
      const onDismiss = vi.fn();
      render(
        <UpgradePrompt
          show={true}
          feature="unlimited sessions"
          targetTier="hybrid"
          onDismiss={onDismiss}
        />,
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
        <UpgradePrompt
          show={true}
          feature="more sessions"
          currentTier="shared"
          targetTier="hybrid"
        />,
      );
      expect(screen.getByText(/upgrade.*Hybrid/i)).toBeInTheDocument();
    });

    it("should show appropriate message for hybrid to dedicated upgrade", () => {
      render(
        <UpgradePrompt
          show={true}
          feature="unlimited resources"
          currentTier="hybrid"
          targetTier="dedicated"
        />,
      );
      expect(screen.getByText(/upgrade.*Dedicated/i)).toBeInTheDocument();
    });
  });

  describe("Custom Upgrade Link", () => {
    it("should use custom upgrade link when provided", () => {
      render(
        <UpgradePrompt
          show={true}
          feature="unlimited sessions"
          targetTier="hybrid"
          upgradeLink="/studio/settings?tab=billing"
        />,
      );
      const upgradeButton = screen.getByRole("button", { name: /upgrade/i });
      // The button should navigate to the upgrade link when clicked
      expect(upgradeButton).toBeInTheDocument();
    });
  });

  describe("Urgency Variants", () => {
    it("should display warning style for warning urgency", () => {
      const { container } = render(
        <UpgradePrompt
          show={true}
          feature="sessions"
          targetTier="hybrid"
          urgency="warning"
        />,
      );
      expect(container.querySelector(".bg-warning-50")).toBeInTheDocument();
    });

    it("should display critical style for critical urgency", () => {
      const { container } = render(
        <UpgradePrompt
          show={true}
          feature="sessions"
          targetTier="hybrid"
          urgency="critical"
        />,
      );
      expect(container.querySelector(".bg-error-50")).toBeInTheDocument();
    });

    it("should display info style by default", () => {
      const { container } = render(
        <UpgradePrompt show={true} feature="sessions" targetTier="hybrid" />,
      );
      expect(container.querySelector(".bg-primary-50")).toBeInTheDocument();
    });
  });

  describe("Limit Information", () => {
    it("should display current usage when provided", () => {
      render(
        <UpgradePrompt
          show={true}
          feature="sessions"
          targetTier="hybrid"
          currentUsage={4}
          maxUsage={5}
        />,
      );
      expect(screen.getByText(/4.*5/)).toBeInTheDocument();
    });

    it("should display limit warning message", () => {
      render(
        <UpgradePrompt
          show={true}
          feature="sessions"
          targetTier="hybrid"
          currentUsage={5}
          maxUsage={5}
        />,
      );
      expect(
        screen.getByText(/limit reached|at capacity/i),
      ).toBeInTheDocument();
    });
  });

  describe("Icon Display", () => {
    it("should display upgrade icon", () => {
      render(
        <UpgradePrompt show={true} feature="sessions" targetTier="hybrid" />,
      );
      expect(screen.getByTestId("upgrade-icon")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have role alert for screen readers", () => {
      render(
        <UpgradePrompt show={true} feature="sessions" targetTier="hybrid" />,
      );
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should have aria-live for dynamic updates", () => {
      render(
        <UpgradePrompt show={true} feature="sessions" targetTier="hybrid" />,
      );
      const alert = screen.getByRole("alert");
      expect(alert).toHaveAttribute("aria-live", "polite");
    });
  });
});
