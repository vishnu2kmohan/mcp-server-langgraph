/**
 * Badge Component Tests
 *
 * Tests for the Badge primitive component variants, sizes, and accessibility.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Badge } from "./Badge";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Badge", () => {
  describe("rendering", () => {
    it("renders with default props", () => {
      render(<Badge>Default</Badge>);
      expect(screen.getByText("Default")).toBeInTheDocument();
    });

    it("renders children correctly", () => {
      render(<Badge>Test Label</Badge>);
      expect(screen.getByText("Test Label")).toBeInTheDocument();
    });
  });

  describe("variants", () => {
    it("renders default variant", () => {
      render(<Badge variant="default">Default</Badge>);
      const badge = screen.getByText("Default");
      expect(badge).toHaveClass("bg-neutral-2");
    });

    it("renders primary variant", () => {
      render(<Badge variant="primary">Primary</Badge>);
      const badge = screen.getByText("Primary");
      expect(badge).toHaveClass("bg-brand-primary");
    });

    it("renders success variant", () => {
      render(<Badge variant="success">Success</Badge>);
      const badge = screen.getByText("Success");
      expect(badge).toHaveClass("bg-success-9");
    });

    it("renders warning variant", () => {
      render(<Badge variant="warning">Warning</Badge>);
      const badge = screen.getByText("Warning");
      expect(badge).toHaveClass("bg-warning-9");
    });

    it("renders error variant", () => {
      render(<Badge variant="error">Error</Badge>);
      const badge = screen.getByText("Error");
      expect(badge).toHaveClass("bg-error-9");
    });

    it("renders outline variant", () => {
      render(<Badge variant="outline">Outline</Badge>);
      const badge = screen.getByText("Outline");
      expect(badge).toHaveClass("border");
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(<Badge size="sm">Small</Badge>);
      const badge = screen.getByText("Small");
      expect(badge).toHaveClass("text-xs");
    });

    it("renders medium size (default)", () => {
      render(<Badge size="md">Medium</Badge>);
      const badge = screen.getByText("Medium");
      expect(badge).toHaveClass("text-sm");
    });

    it("renders large size", () => {
      render(<Badge size="lg">Large</Badge>);
      const badge = screen.getByText("Large");
      expect(badge).toHaveClass("text-base");
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(<Badge className="custom-class">Custom</Badge>);
      const badge = screen.getByText("Custom");
      expect(badge).toHaveClass("custom-class");
    });

    it("passes through additional props", () => {
      render(<Badge data-testid="custom-badge">Props</Badge>);
      expect(screen.getByTestId("custom-badge")).toBeInTheDocument();
    });
  });

  describe("with icon", () => {
    it("renders with left icon", () => {
      render(<Badge icon={<span data-testid="icon">★</span>}>With Icon</Badge>);
      expect(screen.getByTestId("icon")).toBeInTheDocument();
      expect(screen.getByText("With Icon")).toBeInTheDocument();
    });
  });

  describe("pill style", () => {
    it("renders as pill when pill prop is true", () => {
      render(<Badge pill>Pill</Badge>);
      const badge = screen.getByText("Pill");
      expect(badge).toHaveClass("rounded-full");
    });

    it("renders with default rounding when pill is false", () => {
      render(<Badge pill={false}>Not Pill</Badge>);
      const badge = screen.getByText("Not Pill");
      expect(badge).not.toHaveClass("rounded-full");
    });
  });

  describe("CVA integration", () => {
    it("exports badgeVariants function for external use", async () => {
      // This test verifies that CVA variants are properly exported
      // for composition with other components
      const { badgeVariants } = await import("./Badge");
      expect(typeof badgeVariants).toBe("function");
    });
  });
});
