/**
 * Button Component Tests
 *
 * Tests for the CVA-based Button component to ensure:
 * - All variants render correctly
 * - All sizes render correctly
 * - Loading state works
 * - Icons render properly
 * - Accessibility requirements are met
 */

import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, afterEach, vi } from "vitest";
import { Button } from "./Button";

describe("Button", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders with default props", () => {
      render(<Button>Click me</Button>);
      const button = screen.getByRole("button", { name: /click me/i });
      expect(button).toBeInTheDocument();
    });

    it("renders children correctly", () => {
      render(<Button>Test Button</Button>);
      expect(screen.getByText("Test Button")).toBeInTheDocument();
    });

    it("forwards ref correctly", () => {
      const ref = { current: null as HTMLButtonElement | null };
      render(<Button ref={ref}>Button</Button>);
      expect(ref.current).toBeInstanceOf(HTMLButtonElement);
    });
  });

  describe("variants", () => {
    it("applies primary variant classes by default", () => {
      render(<Button>Primary</Button>);
      const button = screen.getByRole("button");
      expect(button.className).toContain("bg-brand-primary");
    });

    it("applies secondary variant classes", () => {
      render(<Button variant="secondary">Secondary</Button>);
      const button = screen.getByRole("button");
      // Should have gray/neutral background classes
      expect(button.className).toMatch(/bg-(gray|neutral)-/);
    });

    it("applies ghost variant classes", () => {
      render(<Button variant="ghost">Ghost</Button>);
      const button = screen.getByRole("button");
      expect(button.className).toContain("bg-transparent");
    });

    it("applies danger variant classes", () => {
      render(<Button variant="danger">Danger</Button>);
      const button = screen.getByRole("button");
      expect(button.className).toContain("bg-error-500");
    });

    it("applies success variant classes", () => {
      render(<Button variant="success">Success</Button>);
      const button = screen.getByRole("button");
      expect(button.className).toContain("bg-success-500");
    });

    it("applies outline variant classes", () => {
      render(<Button variant="outline">Outline</Button>);
      const button = screen.getByRole("button");
      expect(button.className).toContain("border");
      expect(button.className).toContain("bg-transparent");
    });
  });

  describe("sizes", () => {
    it("applies medium size classes by default", () => {
      render(<Button>Medium</Button>);
      const button = screen.getByRole("button");
      expect(button.className).toContain("px-4");
      expect(button.className).toContain("py-2");
      expect(button.className).toContain("text-sm");
    });

    it("applies small size classes", () => {
      render(<Button size="sm">Small</Button>);
      const button = screen.getByRole("button");
      expect(button.className).toContain("px-3");
      expect(button.className).toContain("text-xs");
    });

    it("applies large size classes", () => {
      render(<Button size="lg">Large</Button>);
      const button = screen.getByRole("button");
      expect(button.className).toContain("px-6");
      expect(button.className).toContain("py-3");
      expect(button.className).toContain("text-base");
    });
  });

  describe("loading state", () => {
    it("shows loading spinner when loading is true", () => {
      render(<Button loading>Loading</Button>);
      const spinner = document.querySelector("svg.animate-spin");
      expect(spinner).toBeInTheDocument();
    });

    it("disables button when loading", () => {
      render(<Button loading>Loading</Button>);
      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
    });

    it("applies opacity class when loading", () => {
      render(<Button loading>Loading</Button>);
      const button = screen.getByRole("button");
      expect(button.className).toContain("opacity-50");
    });

    it("hides left icon when loading", () => {
      render(
        <Button loading leftIcon={<span data-testid="left-icon">Icon</span>}>
          Text
        </Button>,
      );
      expect(screen.queryByTestId("left-icon")).not.toBeInTheDocument();
    });
  });

  describe("icons", () => {
    it("renders left icon", () => {
      render(
        <Button leftIcon={<span data-testid="left-icon">L</span>}>Text</Button>,
      );
      expect(screen.getByTestId("left-icon")).toBeInTheDocument();
    });

    it("renders right icon", () => {
      render(
        <Button rightIcon={<span data-testid="right-icon">R</span>}>
          Text
        </Button>,
      );
      expect(screen.getByTestId("right-icon")).toBeInTheDocument();
    });

    it("renders both icons", () => {
      render(
        <Button
          leftIcon={<span data-testid="left-icon">L</span>}
          rightIcon={<span data-testid="right-icon">R</span>}
        >
          Text
        </Button>,
      );
      expect(screen.getByTestId("left-icon")).toBeInTheDocument();
      expect(screen.getByTestId("right-icon")).toBeInTheDocument();
    });
  });

  describe("fullWidth", () => {
    it("applies full width class when fullWidth is true", () => {
      render(<Button fullWidth>Full Width</Button>);
      const button = screen.getByRole("button");
      expect(button.className).toContain("w-full");
    });

    it("does not apply full width class by default", () => {
      render(<Button>Normal</Button>);
      const button = screen.getByRole("button");
      expect(button.className).not.toContain("w-full");
    });
  });

  describe("disabled state", () => {
    it("is disabled when disabled prop is true", () => {
      render(<Button disabled>Disabled</Button>);
      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
    });

    it("applies disabled styling", () => {
      render(<Button disabled>Disabled</Button>);
      const button = screen.getByRole("button");
      expect(button.className).toContain("opacity-50");
      expect(button.className).toContain("cursor-not-allowed");
    });
  });

  describe("interactions", () => {
    it("calls onClick when clicked", async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Click</Button>);
      await user.click(screen.getByRole("button"));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("does not call onClick when disabled", async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      render(
        <Button disabled onClick={handleClick}>
          Click
        </Button>,
      );
      await user.click(screen.getByRole("button"));
      expect(handleClick).not.toHaveBeenCalled();
    });

    it("does not call onClick when loading", async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      render(
        <Button loading onClick={handleClick}>
          Click
        </Button>,
      );
      await user.click(screen.getByRole("button"));
      expect(handleClick).not.toHaveBeenCalled();
    });
  });

  describe("accessibility", () => {
    it("has focus ring styles for keyboard navigation", () => {
      render(<Button>Focus</Button>);
      const button = screen.getByRole("button");
      expect(button.className).toContain("focus:ring-2");
    });

    it("supports custom aria-label", () => {
      render(<Button aria-label="Custom label">Icon</Button>);
      const button = screen.getByRole("button", { name: /custom label/i });
      expect(button).toBeInTheDocument();
    });

    it("supports type attribute", () => {
      render(<Button type="submit">Submit</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("type", "submit");
    });
  });

  describe("className prop", () => {
    it("merges custom className with default classes", () => {
      render(<Button className="custom-class">Custom</Button>);
      const button = screen.getByRole("button");
      expect(button.className).toContain("custom-class");
      expect(button.className).toContain("inline-flex");
    });
  });

  describe("CVA integration", () => {
    it("exports buttonVariants function for external use", async () => {
      // This test verifies that CVA variants are properly exported
      // for composition with other components
      const { buttonVariants } = await import("./Button");
      expect(typeof buttonVariants).toBe("function");
    });
  });
});
