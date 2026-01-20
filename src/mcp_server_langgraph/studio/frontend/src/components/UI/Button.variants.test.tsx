/**
 * Button Variant Style Tests
 *
 * Tests that validate the Button component's CVA variants output expected
 * CSS classes. This prevents tests from breaking when design tokens change,
 * as these tests serve as the single source of truth for variant styling.
 *
 * These tests verify:
 * - Each variant produces the expected base classes
 * - Each size produces the expected sizing classes
 * - The buttonVariants function is properly exported
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button, buttonVariants } from "./Button";

describe("Button Variants", () => {
  describe("buttonVariants CVA function", () => {
    it("should export buttonVariants for style composition", () => {
      expect(buttonVariants).toBeDefined();
      expect(typeof buttonVariants).toBe("function");
    });

    describe("variant styles", () => {
      it("primary variant should include brand-primary background", () => {
        const classes = buttonVariants({ variant: "primary" });
        expect(classes).toContain("bg-brand-primary");
        expect(classes).toContain("text-neutral-12");
        expect(classes).toContain("hover:bg-primary-10");
      });

      it("secondary variant should include neutral background", () => {
        const classes = buttonVariants({ variant: "secondary" });
        expect(classes).toContain("bg-neutral-2");
        expect(classes).toContain("text-neutral-12");
        expect(classes).toContain("hover:bg-neutral-3");
      });

      it("ghost variant should be transparent", () => {
        const classes = buttonVariants({ variant: "ghost" });
        expect(classes).toContain("bg-transparent");
        expect(classes).toContain("text-neutral-11");
        expect(classes).toContain("hover:bg-neutral-2");
      });

      it("danger variant should include error colors", () => {
        const classes = buttonVariants({ variant: "danger" });
        expect(classes).toContain("bg-error-9");
        expect(classes).toContain("text-neutral-12");
        expect(classes).toContain("hover:bg-error-10");
      });

      it("success variant should include success colors", () => {
        const classes = buttonVariants({ variant: "success" });
        expect(classes).toContain("bg-success-9");
        expect(classes).toContain("text-neutral-12");
        expect(classes).toContain("hover:bg-success-10");
      });

      it("warning variant should include warning colors", () => {
        const classes = buttonVariants({ variant: "warning" });
        expect(classes).toContain("bg-warning-9");
        expect(classes).toContain("text-neutral-12");
        expect(classes).toContain("hover:bg-warning-9");
        expect(classes).toContain("active:bg-warning-10");
      });

      it("outline variant should have border and transparent background", () => {
        const classes = buttonVariants({ variant: "outline" });
        expect(classes).toContain("bg-transparent");
        expect(classes).toContain("border");
        expect(classes).toContain("border-neutral-5");
        expect(classes).toContain("text-neutral-11");
      });
    });

    describe("size styles", () => {
      it("sm size should have small padding and text", () => {
        const classes = buttonVariants({ size: "sm" });
        expect(classes).toContain("px-3");
        expect(classes).toContain("py-1.5");
        expect(classes).toContain("text-xs");
      });

      it("md size should have medium padding and text", () => {
        const classes = buttonVariants({ size: "md" });
        expect(classes).toContain("px-4");
        expect(classes).toContain("py-2");
        expect(classes).toContain("text-sm");
      });

      it("lg size should have large padding and text", () => {
        const classes = buttonVariants({ size: "lg" });
        expect(classes).toContain("px-6");
        expect(classes).toContain("py-3");
        expect(classes).toContain("text-base");
      });

      it("icon size should have square dimensions", () => {
        const classes = buttonVariants({ size: "icon" });
        expect(classes).toContain("p-2");
        expect(classes).toContain("h-9");
        expect(classes).toContain("w-9");
      });
    });

    describe("default variants", () => {
      it("should default to primary variant", () => {
        const classes = buttonVariants({});
        expect(classes).toContain("bg-brand-primary");
      });

      it("should default to md size", () => {
        const classes = buttonVariants({});
        expect(classes).toContain("px-4");
        expect(classes).toContain("py-2");
      });
    });

    describe("base styles", () => {
      it("should always include base layout styles", () => {
        const classes = buttonVariants({});
        expect(classes).toContain("inline-flex");
        expect(classes).toContain("items-center");
        expect(classes).toContain("justify-center");
        expect(classes).toContain("font-medium");
        expect(classes).toContain("rounded-md");
      });

      it("should always include focus ring styles", () => {
        const classes = buttonVariants({});
        expect(classes).toContain("focus:outline-none");
        expect(classes).toContain("focus:ring-2");
        expect(classes).toContain("focus:ring-offset-2");
      });

      it("should always include transition styles", () => {
        const classes = buttonVariants({});
        expect(classes).toContain("transition-colors");
        expect(classes).toContain("duration-fast");
      });
    });
  });

  describe("Button component rendering", () => {
    it("should render with primary variant classes by default", () => {
      render(<Button>Click me</Button>);
      const button = screen.getByRole("button", { name: /click me/i });
      expect(button).toHaveClass("bg-brand-primary");
      expect(button).toHaveClass("text-neutral-12");
    });

    it("should render with secondary variant classes", () => {
      render(<Button variant="secondary">Secondary</Button>);
      const button = screen.getByRole("button", { name: /secondary/i });
      expect(button).toHaveClass("bg-neutral-2");
      expect(button).toHaveClass("text-neutral-12");
    });

    it("should render with danger variant classes", () => {
      render(<Button variant="danger">Delete</Button>);
      const button = screen.getByRole("button", { name: /delete/i });
      expect(button).toHaveClass("bg-error-9");
      expect(button).toHaveClass("text-neutral-12");
    });

    it("should render with ghost variant classes", () => {
      render(<Button variant="ghost">Ghost</Button>);
      const button = screen.getByRole("button", { name: /ghost/i });
      expect(button).toHaveClass("bg-transparent");
      expect(button).toHaveClass("text-neutral-11");
    });

    it("should render with sm size classes", () => {
      render(<Button size="sm">Small</Button>);
      const button = screen.getByRole("button", { name: /small/i });
      expect(button).toHaveClass("px-3");
      expect(button).toHaveClass("py-1.5");
      expect(button).toHaveClass("text-xs");
    });

    it("should render with lg size classes", () => {
      render(<Button size="lg">Large</Button>);
      const button = screen.getByRole("button", { name: /large/i });
      expect(button).toHaveClass("px-6");
      expect(button).toHaveClass("py-3");
      expect(button).toHaveClass("text-base");
    });

    it("should apply disabled styling when disabled", () => {
      render(<Button disabled>Disabled</Button>);
      const button = screen.getByRole("button", { name: /disabled/i });
      expect(button).toBeDisabled();
      expect(button).toHaveClass("opacity-50");
      expect(button).toHaveClass("cursor-not-allowed");
    });

    it("should apply loading state styling", () => {
      render(<Button loading>Loading</Button>);
      const button = screen.getByRole("button", { name: /loading/i });
      expect(button).toBeDisabled();
      expect(button).toHaveClass("opacity-50");
      // Should have spinner
      expect(button.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("should apply fullWidth styling", () => {
      render(<Button fullWidth>Full Width</Button>);
      const button = screen.getByRole("button", { name: /full width/i });
      expect(button).toHaveClass("w-full");
    });

    it("should merge custom className with variant classes", () => {
      render(<Button className="custom-class">Custom</Button>);
      const button = screen.getByRole("button", { name: /custom/i });
      expect(button).toHaveClass("custom-class");
      expect(button).toHaveClass("bg-brand-primary"); // Still has variant
    });
  });

  describe("variant type safety", () => {
    it("should accept all defined variants", () => {
      const variants = [
        "primary",
        "secondary",
        "ghost",
        "danger",
        "success",
        "warning",
        "outline",
      ] as const;

      variants.forEach((variant) => {
        const classes = buttonVariants({ variant });
        expect(classes).toBeTruthy();
      });
    });

    it("should accept all defined sizes", () => {
      const sizes = ["sm", "md", "lg", "icon"] as const;

      sizes.forEach((size) => {
        const classes = buttonVariants({ size });
        expect(classes).toBeTruthy();
      });
    });
  });
});
