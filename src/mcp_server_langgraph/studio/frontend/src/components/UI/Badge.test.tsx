/**
 * Badge Component Tests
 *
 * Tests for the Badge primitive component variants, sizes, and accessibility.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Badge } from "./Badge";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Badge", () => {
  describe("rendering", () => {
    it("renders with default props", () => {
      render(
        <TestProvider>
          <Badge>Default</Badge>
        </TestProvider>,
      );
      expect(screen.getByText("Default")).toBeInTheDocument();
    });

    it("renders children correctly", () => {
      render(
        <TestProvider>
          <Badge>Test Label</Badge>
        </TestProvider>,
      );
      expect(screen.getByText("Test Label")).toBeInTheDocument();
    });
  });

  describe("variants", () => {
    it("renders default variant", () => {
      render(
        <TestProvider>
          <Badge variant="default">Default</Badge>
        </TestProvider>,
      );
      const badge = screen.getByText("Default");
      expect(badge).toHaveClass("bg-neutral-2");
    });

    it("renders primary variant", () => {
      render(
        <TestProvider>
          <Badge variant="primary">Primary</Badge>
        </TestProvider>,
      );
      const badge = screen.getByText("Primary");
      expect(badge).toHaveClass("bg-brand-primary");
    });

    it("renders success variant", () => {
      render(
        <TestProvider>
          <Badge variant="success">Success</Badge>
        </TestProvider>,
      );
      const badge = screen.getByText("Success");
      expect(badge).toHaveClass("bg-success-9");
    });

    it("renders warning variant", () => {
      render(
        <TestProvider>
          <Badge variant="warning">Warning</Badge>
        </TestProvider>,
      );
      const badge = screen.getByText("Warning");
      expect(badge).toHaveClass("bg-warning-9");
    });

    it("renders error variant", () => {
      render(
        <TestProvider>
          <Badge variant="error">Error</Badge>
        </TestProvider>,
      );
      const badge = screen.getByText("Error");
      expect(badge).toHaveClass("bg-error-9");
    });

    it("renders outline variant", () => {
      render(
        <TestProvider>
          <Badge variant="outline">Outline</Badge>
        </TestProvider>,
      );
      const badge = screen.getByText("Outline");
      expect(badge).toHaveClass("border");
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(
        <TestProvider>
          <Badge size="sm">Small</Badge>
        </TestProvider>,
      );
      const badge = screen.getByText("Small");
      expect(badge).toHaveClass("text-xs");
    });

    it("renders medium size (default)", () => {
      render(
        <TestProvider>
          <Badge size="md">Medium</Badge>
        </TestProvider>,
      );
      const badge = screen.getByText("Medium");
      expect(badge).toHaveClass("text-sm");
    });

    it("renders large size", () => {
      render(
        <TestProvider>
          <Badge size="lg">Large</Badge>
        </TestProvider>,
      );
      const badge = screen.getByText("Large");
      expect(badge).toHaveClass("text-base");
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(
        <TestProvider>
          <Badge className="custom-class">Custom</Badge>
        </TestProvider>,
      );
      const badge = screen.getByText("Custom");
      expect(badge).toHaveClass("custom-class");
    });

    it("passes through additional props", () => {
      render(
        <TestProvider>
          <Badge data-testid="custom-badge">Props</Badge>
        </TestProvider>,
      );
      expect(screen.getByTestId("custom-badge")).toBeInTheDocument();
    });
  });

  describe("with icon", () => {
    it("renders with left icon", () => {
      render(
        <TestProvider>
          <Badge icon={<span data-testid="icon">★</span>}>With Icon</Badge>
        </TestProvider>,
      );
      expect(screen.getByTestId("icon")).toBeInTheDocument();
      expect(screen.getByText("With Icon")).toBeInTheDocument();
    });
  });

  describe("pill style", () => {
    it("renders as pill when pill prop is true", () => {
      render(
        <TestProvider>
          <Badge pill>Pill</Badge>
        </TestProvider>,
      );
      const badge = screen.getByText("Pill");
      expect(badge).toHaveClass("rounded-full");
    });

    it("renders with default rounding when pill is false", () => {
      render(
        <TestProvider>
          <Badge pill={false}>Not Pill</Badge>
        </TestProvider>,
      );
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
