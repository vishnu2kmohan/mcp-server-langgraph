/**
 * PWA Update Prompt Component Tests
 *
 * TDD tests for the UpdatePrompt component that shows
 * when a new service worker version is available.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { UpdatePrompt } from "./UpdatePrompt";

describe("UpdatePrompt", () => {
  const defaultProps = {
    needsUpdate: true,
    isUpdating: false,
    onUpdate: vi.fn(),
    onDismiss: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Visibility", () => {
    it("should render when needsUpdate is true", () => {
      render(<UpdatePrompt {...defaultProps} />);

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should not render when needsUpdate is false", () => {
      render(<UpdatePrompt {...defaultProps} needsUpdate={false} />);

      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("should display update message", () => {
      render(<UpdatePrompt {...defaultProps} />);

      expect(screen.getByText(/new version available/i)).toBeInTheDocument();
    });
  });

  describe("Actions", () => {
    it("should have an update button", () => {
      render(<UpdatePrompt {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /update/i }),
      ).toBeInTheDocument();
    });

    it("should have a dismiss button", () => {
      render(<UpdatePrompt {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /later|dismiss/i }),
      ).toBeInTheDocument();
    });

    it("should call onUpdate when update button is clicked", () => {
      const onUpdate = vi.fn();
      render(<UpdatePrompt {...defaultProps} onUpdate={onUpdate} />);

      fireEvent.click(screen.getByRole("button", { name: /update/i }));

      expect(onUpdate).toHaveBeenCalledTimes(1);
    });

    it("should call onDismiss when dismiss button is clicked", () => {
      const onDismiss = vi.fn();
      render(<UpdatePrompt {...defaultProps} onDismiss={onDismiss} />);

      fireEvent.click(screen.getByRole("button", { name: /later|dismiss/i }));

      expect(onDismiss).toHaveBeenCalledTimes(1);
    });
  });

  describe("Loading State", () => {
    it("should show loading state when isUpdating is true", () => {
      render(<UpdatePrompt {...defaultProps} isUpdating={true} />);

      expect(screen.getByText(/updating/i)).toBeInTheDocument();
    });

    it("should disable update button when isUpdating is true", () => {
      render(<UpdatePrompt {...defaultProps} isUpdating={true} />);

      const updateButton = screen.getByRole("button", { name: /update/i });
      expect(updateButton).toBeDisabled();
    });

    it("should disable dismiss button when isUpdating is true", () => {
      render(<UpdatePrompt {...defaultProps} isUpdating={true} />);

      const dismissButton = screen.getByRole("button", {
        name: /later|dismiss/i,
      });
      expect(dismissButton).toBeDisabled();
    });
  });

  describe("Accessibility", () => {
    it("should have role alert for screen readers", () => {
      render(<UpdatePrompt {...defaultProps} />);

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should have aria-live for dynamic updates", () => {
      render(<UpdatePrompt {...defaultProps} />);

      const alert = screen.getByRole("alert");
      expect(alert).toHaveAttribute("aria-live", "polite");
    });

    it("should have proper button labels for screen readers", () => {
      render(<UpdatePrompt {...defaultProps} />);

      const updateButton = screen.getByRole("button", { name: /update/i });
      const dismissButton = screen.getByRole("button", {
        name: /later|dismiss/i,
      });

      expect(updateButton).toHaveAccessibleName();
      expect(dismissButton).toHaveAccessibleName();
    });
  });

  describe("Styling", () => {
    it("should have toast-like styling at bottom of screen", () => {
      render(<UpdatePrompt {...defaultProps} />);

      const alert = screen.getByRole("alert");
      expect(alert).toHaveClass("fixed");
    });

    it("should have appropriate color scheme", () => {
      render(<UpdatePrompt {...defaultProps} />);

      const alert = screen.getByRole("alert");
      // Should use info/primary colors
      expect(alert.className).toMatch(/bg-|blue|primary/i);
    });
  });
});
