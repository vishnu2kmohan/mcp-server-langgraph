/**
 * Input Component Tests
 *
 * Tests for the Input primitive component variants, sizes, states, and accessibility.
 * TDD: These tests were written FIRST before implementation.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Input } from "./Input";
import { Search, Mail } from "lucide-react";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Input", () => {
  describe("rendering", () => {
    it("renders with default props", () => {
      render(<Input />);
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    it("renders with placeholder", () => {
      render(<Input placeholder="Enter text..." />);
      expect(screen.getByPlaceholderText("Enter text...")).toBeInTheDocument();
    });

    it("renders with value", () => {
      render(<Input defaultValue="Hello" />);
      expect(screen.getByDisplayValue("Hello")).toBeInTheDocument();
    });

    it("renders with controlled value", () => {
      const { rerender } = render(
        <Input value="Initial" onChange={() => {}} />,
      );
      expect(screen.getByDisplayValue("Initial")).toBeInTheDocument();

      rerender(<Input value="Updated" onChange={() => {}} />);
      expect(screen.getByDisplayValue("Updated")).toBeInTheDocument();
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(<Input size="sm" data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("text-xs");
      expect(input).toHaveClass("py-1.5");
    });

    it("renders medium size (default)", () => {
      render(<Input size="md" data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("text-sm");
      expect(input).toHaveClass("py-2");
    });

    it("renders large size", () => {
      render(<Input size="lg" data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("text-base");
      expect(input).toHaveClass("py-2.5");
    });
  });

  describe("variants", () => {
    it("renders default variant", () => {
      render(<Input variant="default" data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("border-neutral-300");
    });

    it("renders error variant", () => {
      render(<Input variant="error" data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("border-error-500");
    });

    it("renders success variant", () => {
      render(<Input variant="success" data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("border-success-500");
    });
  });

  describe("states", () => {
    it("renders disabled state", () => {
      render(<Input disabled data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toBeDisabled();
      expect(input).toHaveClass("cursor-not-allowed");
    });

    it("renders readonly state", () => {
      render(<Input readOnly data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("readonly");
    });

    it("renders required state", () => {
      render(<Input required data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toBeRequired();
    });
  });

  describe("icons", () => {
    it("renders with left icon", () => {
      render(<Input leftIcon={<Search data-testid="left-icon" />} />);
      expect(screen.getByTestId("left-icon")).toBeInTheDocument();
    });

    it("renders with right icon", () => {
      render(<Input rightIcon={<Mail data-testid="right-icon" />} />);
      expect(screen.getByTestId("right-icon")).toBeInTheDocument();
    });

    it("renders with both icons", () => {
      render(
        <Input
          leftIcon={<Search data-testid="left-icon" />}
          rightIcon={<Mail data-testid="right-icon" />}
        />,
      );
      expect(screen.getByTestId("left-icon")).toBeInTheDocument();
      expect(screen.getByTestId("right-icon")).toBeInTheDocument();
    });

    it("adds padding for left icon", () => {
      render(<Input leftIcon={<Search />} data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("pl-10");
    });

    it("adds padding for right icon", () => {
      render(<Input rightIcon={<Mail />} data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("pr-10");
    });
  });

  describe("fullWidth", () => {
    it("renders full width when prop is true", () => {
      render(<Input fullWidth data-testid="input" />);
      const wrapper = screen.getByTestId("input").parentElement;
      expect(wrapper).toHaveClass("w-full");
    });

    it("renders auto width when fullWidth is false", () => {
      render(<Input fullWidth={false} data-testid="input" />);
      const wrapper = screen.getByTestId("input").parentElement;
      expect(wrapper).not.toHaveClass("w-full");
    });
  });

  describe("events", () => {
    it("calls onChange when value changes", async () => {
      const handleChange = vi.fn();
      const user = userEvent.setup();

      render(<Input onChange={handleChange} />);
      const input = screen.getByRole("textbox");

      await user.type(input, "Hello");
      expect(handleChange).toHaveBeenCalled();
    });

    it("calls onFocus when focused", async () => {
      const handleFocus = vi.fn();
      const user = userEvent.setup();

      render(<Input onFocus={handleFocus} />);
      const input = screen.getByRole("textbox");

      await user.click(input);
      expect(handleFocus).toHaveBeenCalledTimes(1);
    });

    it("calls onBlur when blurred", async () => {
      const handleBlur = vi.fn();
      const user = userEvent.setup();

      render(<Input onBlur={handleBlur} />);
      const input = screen.getByRole("textbox");

      await user.click(input);
      await user.tab();
      expect(handleBlur).toHaveBeenCalledTimes(1);
    });
  });

  describe("input types", () => {
    it("renders text type by default", () => {
      render(<Input data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("type", "text");
    });

    it("renders email type", () => {
      render(<Input type="email" data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("type", "email");
    });

    it("renders password type", () => {
      render(<Input type="password" data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("type", "password");
    });

    it("renders number type", () => {
      render(<Input type="number" data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("type", "number");
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(<Input className="custom-class" data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("custom-class");
    });

    it("passes through additional props", () => {
      render(<Input data-testid="custom-input" aria-label="Custom input" />);
      const input = screen.getByTestId("custom-input");
      expect(input).toHaveAttribute("aria-label", "Custom input");
    });

    it("forwards ref to input element", () => {
      const ref = vi.fn();
      render(<Input ref={ref} />);
      expect(ref).toHaveBeenCalled();
      expect(ref.mock.calls[0][0]).toBeInstanceOf(HTMLInputElement);
    });
  });

  describe("accessibility", () => {
    it("associates label with input using id", () => {
      render(
        <>
          <label htmlFor="test-input">Test Label</label>
          <Input id="test-input" />
        </>,
      );
      const input = screen.getByLabelText("Test Label");
      expect(input).toBeInTheDocument();
    });

    it("supports aria-describedby for error messages", () => {
      render(
        <>
          <Input aria-describedby="error-message" variant="error" />
          <span id="error-message">This field is required</span>
        </>,
      );
      const input = screen.getByRole("textbox");
      expect(input).toHaveAttribute("aria-describedby", "error-message");
    });

    it("has proper focus ring styles", () => {
      render(<Input data-testid="input" />);
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("focus:ring-2");
    });
  });

  describe("CVA integration", () => {
    it("exports inputVariants function for external use", async () => {
      const { inputVariants } = await import("./Input");
      expect(typeof inputVariants).toBe("function");
    });
  });
});
