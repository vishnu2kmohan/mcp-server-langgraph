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

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Input", () => {
  describe("rendering", () => {
    it("renders with default props", () => {
      render(
        <TestProvider>
          <Input />
        </TestProvider>,
      );
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    it("renders with placeholder", () => {
      render(
        <TestProvider>
          <Input placeholder="Enter text..." />
        </TestProvider>,
      );
      expect(screen.getByPlaceholderText("Enter text...")).toBeInTheDocument();
    });

    it("renders with value", () => {
      render(
        <TestProvider>
          <Input defaultValue="Hello" />
        </TestProvider>,
      );
      expect(screen.getByDisplayValue("Hello")).toBeInTheDocument();
    });

    it("renders with controlled value", () => {
      const { rerender } = render(
        <TestProvider>
          <Input value="Initial" onChange={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByDisplayValue("Initial")).toBeInTheDocument();

      rerender(<Input value="Updated" onChange={() => {}} />);
      expect(screen.getByDisplayValue("Updated")).toBeInTheDocument();
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(
        <TestProvider>
          <Input size="sm" data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("text-xs");
      expect(input).toHaveClass("py-1.5");
    });

    it("renders medium size (default)", () => {
      render(
        <TestProvider>
          <Input size="md" data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("text-sm");
      expect(input).toHaveClass("py-2");
    });

    it("renders large size", () => {
      render(
        <TestProvider>
          <Input size="lg" data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("text-base");
      expect(input).toHaveClass("py-2.5");
    });
  });

  describe("variants", () => {
    it("renders default variant", () => {
      render(
        <TestProvider>
          <Input variant="default" data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("border-neutral-5");
    });

    it("renders error variant", () => {
      render(
        <TestProvider>
          <Input variant="error" data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("border-error-9");
    });

    it("renders success variant", () => {
      render(
        <TestProvider>
          <Input variant="success" data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("border-success-9");
    });
  });

  describe("states", () => {
    it("renders disabled state", () => {
      render(
        <TestProvider>
          <Input disabled data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toBeDisabled();
      expect(input).toHaveClass("cursor-not-allowed");
    });

    it("renders readonly state", () => {
      render(
        <TestProvider>
          <Input readOnly data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("readonly");
    });

    it("renders required state", () => {
      render(
        <TestProvider>
          <Input required data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toBeRequired();
    });
  });

  describe("icons", () => {
    it("renders with left icon", () => {
      render(
        <TestProvider>
          <Input leftIcon={<Search data-testid="left-icon" />} />
        </TestProvider>,
      );
      expect(screen.getByTestId("left-icon")).toBeInTheDocument();
    });

    it("renders with right icon", () => {
      render(
        <TestProvider>
          <Input rightIcon={<Mail data-testid="right-icon" />} />
        </TestProvider>,
      );
      expect(screen.getByTestId("right-icon")).toBeInTheDocument();
    });

    it("renders with both icons", () => {
      render(
        <TestProvider>
          <Input
            leftIcon={<Search data-testid="left-icon" />}
            rightIcon={<Mail data-testid="right-icon" />}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("left-icon")).toBeInTheDocument();
      expect(screen.getByTestId("right-icon")).toBeInTheDocument();
    });

    it("adds padding for left icon", () => {
      render(
        <TestProvider>
          <Input leftIcon={<Search />} data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("pl-10");
    });

    it("adds padding for right icon", () => {
      render(
        <TestProvider>
          <Input rightIcon={<Mail />} data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("pr-10");
    });
  });

  describe("fullWidth", () => {
    it("renders full width when prop is true", () => {
      render(
        <TestProvider>
          <Input fullWidth data-testid="input" />
        </TestProvider>,
      );
      const wrapper = screen.getByTestId("input").parentElement;
      expect(wrapper).toHaveClass("w-full");
    });

    it("renders auto width when fullWidth is false", () => {
      render(
        <TestProvider>
          <Input fullWidth={false} data-testid="input" />
        </TestProvider>,
      );
      const wrapper = screen.getByTestId("input").parentElement;
      expect(wrapper).not.toHaveClass("w-full");
    });
  });

  describe("events", () => {
    it("calls onChange when value changes", async () => {
      const handleChange = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <Input onChange={handleChange} />
        </TestProvider>,
      );
      const input = screen.getByRole("textbox");

      await user.type(input, "Hello");
      expect(handleChange).toHaveBeenCalled();
    });

    it("calls onFocus when focused", async () => {
      const handleFocus = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <Input onFocus={handleFocus} />
        </TestProvider>,
      );
      const input = screen.getByRole("textbox");

      await user.click(input);
      expect(handleFocus).toHaveBeenCalledTimes(1);
    });

    it("calls onBlur when blurred", async () => {
      const handleBlur = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <Input onBlur={handleBlur} />
        </TestProvider>,
      );
      const input = screen.getByRole("textbox");

      await user.click(input);
      await user.tab();
      expect(handleBlur).toHaveBeenCalledTimes(1);
    });
  });

  describe("input types", () => {
    it("renders text type by default", () => {
      render(
        <TestProvider>
          <Input data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("type", "text");
    });

    it("renders email type", () => {
      render(
        <TestProvider>
          <Input type="email" data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("type", "email");
    });

    it("renders password type", () => {
      render(
        <TestProvider>
          <Input type="password" data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("type", "password");
    });

    it("renders number type", () => {
      render(
        <TestProvider>
          <Input type="number" data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("type", "number");
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(
        <TestProvider>
          <Input className="custom-class" data-testid="input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("input");
      expect(input).toHaveClass("custom-class");
    });

    it("passes through additional props", () => {
      render(
        <TestProvider>
          <Input data-testid="custom-input" aria-label="Custom input" />
        </TestProvider>,
      );
      const input = screen.getByTestId("custom-input");
      expect(input).toHaveAttribute("aria-label", "Custom input");
    });

    it("forwards ref to input element", () => {
      const ref = vi.fn();
      render(
        <TestProvider>
          <Input ref={ref} />
        </TestProvider>,
      );
      expect(ref).toHaveBeenCalled();
      expect(ref.mock.calls[0][0]).toBeInstanceOf(HTMLInputElement);
    });
  });

  describe("accessibility", () => {
    it("associates label with input using id", () => {
      render(
        <TestProvider>
          <>
            <label htmlFor="test-input">Test Label</label>
            <Input id="test-input" />
          </>
        </TestProvider>,
      );
      const input = screen.getByLabelText("Test Label");
      expect(input).toBeInTheDocument();
    });

    it("supports aria-describedby for error messages", () => {
      render(
        <TestProvider>
          <>
            <Input aria-describedby="error-message" variant="error" />
            <span id="error-message">This field is required</span>
          </>
        </TestProvider>,
      );
      const input = screen.getByRole("textbox");
      expect(input).toHaveAttribute("aria-describedby", "error-message");
    });

    it("has proper focus ring styles", () => {
      render(
        <TestProvider>
          <Input data-testid="input" />
        </TestProvider>,
      );
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
