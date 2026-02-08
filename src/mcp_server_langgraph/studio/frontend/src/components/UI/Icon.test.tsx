/**
 * Icon Component Tests
 *
 * Tests for the Icon wrapper component that provides standardized sizing
 * and accessibility features for Lucide icons.
 */

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Icon } from "./Icon";
import { Check, AlertCircle, Settings, Loader2 } from "lucide-react";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Icon", () => {
  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("renders the icon component", () => {
      render(
        <TestProvider>
          <Icon icon={Check} data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toBeInTheDocument();
    });

    it("renders with default size (md)", () => {
      render(
        <TestProvider>
          <Icon icon={Check} data-testid="icon" />
        </TestProvider>,
      );

      const icon = screen.getByTestId("icon");
      // md size is w-4 h-4 (16px)
      expect(icon).toHaveClass("w-4", "h-4");
    });

    it("renders different Lucide icons", () => {
      const { rerender } = render(
        <TestProvider>
          <Icon icon={Check} data-testid="check-icon" />
        </TestProvider>,
      );
      expect(screen.getByTestId("check-icon")).toBeInTheDocument();

      rerender(<Icon icon={AlertCircle} data-testid="alert-icon" />);
      expect(screen.getByTestId("alert-icon")).toBeInTheDocument();

      rerender(<Icon icon={Settings} data-testid="settings-icon" />);
      expect(screen.getByTestId("settings-icon")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Size Tests
  // ===========================================================================

  describe("sizes", () => {
    it("renders xs size (12px)", () => {
      render(
        <TestProvider>
          <Icon icon={Check} size="xs" data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveClass("w-3", "h-3");
    });

    it("renders sm size (14px)", () => {
      render(
        <TestProvider>
          <Icon icon={Check} size="sm" data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveClass("w-3.5", "h-3.5");
    });

    it("renders md size (16px)", () => {
      render(
        <TestProvider>
          <Icon icon={Check} size="md" data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveClass("w-4", "h-4");
    });

    it("renders lg size (20px)", () => {
      render(
        <TestProvider>
          <Icon icon={Check} size="lg" data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveClass("w-5", "h-5");
    });

    it("renders xl size (24px)", () => {
      render(
        <TestProvider>
          <Icon icon={Check} size="xl" data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveClass("w-6", "h-6");
    });

    it("renders 2xl size (32px)", () => {
      render(
        <TestProvider>
          <Icon icon={Check} size="2xl" data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveClass("w-8", "h-8");
    });

    it("renders 3xl size (48px)", () => {
      render(
        <TestProvider>
          <Icon icon={Check} size="3xl" data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveClass("w-12", "h-12");
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("accessibility", () => {
    it("is hidden from screen readers by default (decorative)", () => {
      render(
        <TestProvider>
          <Icon icon={Check} data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveAttribute("aria-hidden", "true");
    });

    it("has aria-label when provided (meaningful icon)", () => {
      render(
        <TestProvider>
          <Icon icon={AlertCircle} aria-label="Warning" data-testid="icon" />
        </TestProvider>,
      );

      const icon = screen.getByTestId("icon");
      expect(icon).toHaveAttribute("aria-label", "Warning");
      expect(icon).toHaveAttribute("aria-hidden", "false");
      expect(icon).toHaveAttribute("role", "img");
    });

    it("sets role=img when aria-label is provided", () => {
      render(
        <TestProvider>
          <Icon icon={Check} aria-label="Success" data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveAttribute("role", "img");
    });

    it("does not set role when decorative", () => {
      render(
        <TestProvider>
          <Icon icon={Check} data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).not.toHaveAttribute("role");
    });
  });

  // ===========================================================================
  // Custom Class Tests
  // ===========================================================================

  describe("custom className", () => {
    it("applies custom className", () => {
      render(
        <TestProvider>
          <Icon icon={Check} className="text-success-9" data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveClass("text-success-9");
    });

    it("merges custom className with size classes", () => {
      render(
        <TestProvider>
          <Icon
            icon={Check}
            size="lg"
            className="text-primary-9"
            data-testid="icon"
          />
        </TestProvider>,
      );

      const icon = screen.getByTestId("icon");
      expect(icon).toHaveClass("w-5", "h-5", "text-primary-9");
    });

    it("applies shrink-0 by default to prevent flex shrinking", () => {
      render(
        <TestProvider>
          <Icon icon={Check} data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveClass("shrink-0");
    });
  });

  // ===========================================================================
  // Semantic Color Usage Tests
  // ===========================================================================

  describe("semantic color usage", () => {
    it("works with success color", () => {
      render(
        <TestProvider>
          <Icon icon={Check} className="text-success-9" data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveClass("text-success-9");
    });

    it("works with error color", () => {
      render(
        <TestProvider>
          <Icon
            icon={AlertCircle}
            className="text-error-9"
            data-testid="icon"
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveClass("text-error-9");
    });

    it("works with warning color", () => {
      render(
        <TestProvider>
          <Icon
            icon={AlertCircle}
            className="text-warning-9"
            data-testid="icon"
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveClass("text-warning-9");
    });
  });

  // ===========================================================================
  // Animation Tests
  // ===========================================================================

  describe("animation", () => {
    it("applies spin animation class when provided", () => {
      render(
        <TestProvider>
          <Icon icon={Loader2} className="animate-spin" data-testid="icon" />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon")).toHaveClass("animate-spin");
    });
  });
});
