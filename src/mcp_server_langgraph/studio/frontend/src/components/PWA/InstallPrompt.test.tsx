/**
 * PWA Install Prompt Component Tests
 *
 * TDD tests for the InstallPrompt component that shows
 * when the PWA can be installed.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { InstallPrompt } from "./InstallPrompt";

import { TestProvider } from "@/test-utils";

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

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Visibility", () => {
    it("should render when canInstall is true", () => {
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should not render when canInstall is false", () => {
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} canInstall={false} />
        </TestProvider>,
      );

      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("should display install message", () => {
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/install.*app/i)).toBeInTheDocument();
    });

    it("should display benefit text", () => {
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByText(/faster access and offline support/i),
      ).toBeInTheDocument();
    });
  });

  describe("Actions", () => {
    it("should have an install button", () => {
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /install/i }),
      ).toBeInTheDocument();
    });

    it("should have a dismiss button", () => {
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /later|dismiss|close|no thanks/i }),
      ).toBeInTheDocument();
    });

    it("should call onInstall when install button is clicked", () => {
      const onInstall = vi.fn();
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} onInstall={onInstall} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /install/i }));

      expect(onInstall).toHaveBeenCalledTimes(1);
    });

    it("should call onDismiss when dismiss button is clicked", () => {
      const onDismiss = vi.fn();
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} onDismiss={onDismiss} />
        </TestProvider>,
      );

      fireEvent.click(
        screen.getByRole("button", { name: /later|dismiss|close|no thanks/i }),
      );

      expect(onDismiss).toHaveBeenCalledTimes(1);
    });
  });

  describe("Loading State", () => {
    it("should show loading state when isInstalling is true", () => {
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} isInstalling={true} />
        </TestProvider>,
      );

      expect(screen.getByText(/installing/i)).toBeInTheDocument();
    });

    it("should disable install button when isInstalling is true", () => {
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} isInstalling={true} />
        </TestProvider>,
      );

      const installButton = screen.getByRole("button", { name: /install/i });
      expect(installButton).toBeDisabled();
    });

    it("should disable dismiss button when isInstalling is true", () => {
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} isInstalling={true} />
        </TestProvider>,
      );

      const dismissButton = screen.getByRole("button", {
        name: /later|dismiss|close|no thanks/i,
      });
      expect(dismissButton).toBeDisabled();
    });
  });

  describe("Accessibility", () => {
    it("should have role alert for screen readers", () => {
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should have aria-live for dynamic updates", () => {
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} />
        </TestProvider>,
      );

      const alert = screen.getByRole("alert");
      expect(alert).toHaveAttribute("aria-live", "polite");
    });

    it("should have proper button labels for screen readers", () => {
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} />
        </TestProvider>,
      );

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
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} />
        </TestProvider>,
      );

      const alert = screen.getByRole("alert");
      expect(alert).toHaveClass("fixed");
    });

    it("should have appropriate color scheme (different from update)", () => {
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} />
        </TestProvider>,
      );

      const alert = screen.getByRole("alert");
      // Should use a distinct color (e.g., green for install vs blue for update)
      expect(alert.className).toMatch(/bg-|green|emerald|teal|primary/i);
    });

    it("should have app icon or download icon", () => {
      render(
        <TestProvider>
          <InstallPrompt {...defaultProps} />
        </TestProvider>,
      );

      // Should have some visual indicator (icon)
      const alert = screen.getByRole("alert");
      expect(alert.querySelector("svg")).toBeInTheDocument();
    });
  });
});
