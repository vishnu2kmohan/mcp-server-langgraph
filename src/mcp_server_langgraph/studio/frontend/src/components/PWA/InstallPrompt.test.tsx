/**
 * PWA Install Prompt Component Tests
 *
 * TDD tests for the InstallPrompt component that shows
 * when the PWA can be installed.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { InstallPrompt } from "./InstallPrompt";

describe("InstallPrompt", () => {
  const defaultProps = {
    canInstall: true,
    isInstalling: false,
    onInstall: vi.fn(),
    onDismiss: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Visibility", () => {
    it("should render when canInstall is true", () => {
      render(<InstallPrompt {...defaultProps} />);

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should not render when canInstall is false", () => {
      render(<InstallPrompt {...defaultProps} canInstall={false} />);

      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("should display install message", () => {
      render(<InstallPrompt {...defaultProps} />);

      expect(screen.getByText(/install.*app/i)).toBeInTheDocument();
    });

    it("should display benefit text", () => {
      render(<InstallPrompt {...defaultProps} />);

      expect(
        screen.getByText(/faster access and offline support/i),
      ).toBeInTheDocument();
    });
  });

  describe("Actions", () => {
    it("should have an install button", () => {
      render(<InstallPrompt {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /install/i }),
      ).toBeInTheDocument();
    });

    it("should have a dismiss button", () => {
      render(<InstallPrompt {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /later|dismiss|close|no thanks/i }),
      ).toBeInTheDocument();
    });

    it("should call onInstall when install button is clicked", () => {
      const onInstall = vi.fn();
      render(<InstallPrompt {...defaultProps} onInstall={onInstall} />);

      fireEvent.click(screen.getByRole("button", { name: /install/i }));

      expect(onInstall).toHaveBeenCalledTimes(1);
    });

    it("should call onDismiss when dismiss button is clicked", () => {
      const onDismiss = vi.fn();
      render(<InstallPrompt {...defaultProps} onDismiss={onDismiss} />);

      fireEvent.click(
        screen.getByRole("button", { name: /later|dismiss|close|no thanks/i }),
      );

      expect(onDismiss).toHaveBeenCalledTimes(1);
    });
  });

  describe("Loading State", () => {
    it("should show loading state when isInstalling is true", () => {
      render(<InstallPrompt {...defaultProps} isInstalling={true} />);

      expect(screen.getByText(/installing/i)).toBeInTheDocument();
    });

    it("should disable install button when isInstalling is true", () => {
      render(<InstallPrompt {...defaultProps} isInstalling={true} />);

      const installButton = screen.getByRole("button", { name: /install/i });
      expect(installButton).toBeDisabled();
    });

    it("should disable dismiss button when isInstalling is true", () => {
      render(<InstallPrompt {...defaultProps} isInstalling={true} />);

      const dismissButton = screen.getByRole("button", {
        name: /later|dismiss|close|no thanks/i,
      });
      expect(dismissButton).toBeDisabled();
    });
  });

  describe("Accessibility", () => {
    it("should have role alert for screen readers", () => {
      render(<InstallPrompt {...defaultProps} />);

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should have aria-live for dynamic updates", () => {
      render(<InstallPrompt {...defaultProps} />);

      const alert = screen.getByRole("alert");
      expect(alert).toHaveAttribute("aria-live", "polite");
    });

    it("should have proper button labels for screen readers", () => {
      render(<InstallPrompt {...defaultProps} />);

      const installButton = screen.getByRole("button", { name: /install/i });
      const dismissButton = screen.getByRole("button", {
        name: /later|dismiss|close|no thanks/i,
      });

      expect(installButton).toHaveAccessibleName();
      expect(dismissButton).toHaveAccessibleName();
    });
  });

  describe("Styling", () => {
    it("should have toast-like styling at bottom of screen", () => {
      render(<InstallPrompt {...defaultProps} />);

      const alert = screen.getByRole("alert");
      expect(alert).toHaveClass("fixed");
    });

    it("should have appropriate color scheme (different from update)", () => {
      render(<InstallPrompt {...defaultProps} />);

      const alert = screen.getByRole("alert");
      // Should use a distinct color (e.g., green for install vs blue for update)
      expect(alert.className).toMatch(/bg-|green|emerald|teal|primary/i);
    });

    it("should have app icon or download icon", () => {
      render(<InstallPrompt {...defaultProps} />);

      // Should have some visual indicator (icon)
      const alert = screen.getByRole("alert");
      expect(alert.querySelector("svg")).toBeInTheDocument();
    });
  });
});
