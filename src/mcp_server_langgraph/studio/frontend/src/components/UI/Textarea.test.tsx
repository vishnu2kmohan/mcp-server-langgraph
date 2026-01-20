/**
 * Textarea Component Tests
 *
 * Tests for the Textarea primitive component variants, sizes, states, and accessibility.
 * TDD: These tests were written FIRST before implementation.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Textarea } from "./Textarea";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Textarea", () => {
  describe("rendering", () => {
    it("renders with default props", () => {
      render(<Textarea />);
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    it("renders with placeholder", () => {
      render(<Textarea placeholder="Enter text..." />);
      expect(screen.getByPlaceholderText("Enter text...")).toBeInTheDocument();
    });

    it("renders with value", () => {
      render(<Textarea defaultValue="Hello World" />);
      expect(screen.getByDisplayValue("Hello World")).toBeInTheDocument();
    });

    it("renders with controlled value", () => {
      const { rerender } = render(
        <Textarea value="Initial" onChange={() => {}} />,
      );
      expect(screen.getByDisplayValue("Initial")).toBeInTheDocument();

      rerender(<Textarea value="Updated" onChange={() => {}} />);
      expect(screen.getByDisplayValue("Updated")).toBeInTheDocument();
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(<Textarea size="sm" data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("text-xs");
      expect(textarea).toHaveClass("p-2");
    });

    it("renders medium size (default)", () => {
      render(<Textarea size="md" data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("text-sm");
      expect(textarea).toHaveClass("p-3");
    });

    it("renders large size", () => {
      render(<Textarea size="lg" data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("text-base");
      expect(textarea).toHaveClass("p-4");
    });
  });

  describe("variants", () => {
    it("renders default variant", () => {
      render(<Textarea variant="default" data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("border-neutral-5");
    });

    it("renders error variant", () => {
      render(<Textarea variant="error" data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("border-error-9");
    });

    it("renders success variant", () => {
      render(<Textarea variant="success" data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("border-success-9");
    });
  });

  describe("states", () => {
    it("renders disabled state", () => {
      render(<Textarea disabled data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toBeDisabled();
      expect(textarea).toHaveClass("cursor-not-allowed");
    });

    it("renders readonly state", () => {
      render(<Textarea readOnly data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveAttribute("readonly");
    });

    it("renders required state", () => {
      render(<Textarea required data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toBeRequired();
    });
  });

  describe("resize", () => {
    it("allows vertical resize by default", () => {
      render(<Textarea data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("resize-y");
    });

    it("allows no resize when resize is none", () => {
      render(<Textarea resize="none" data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("resize-none");
    });

    it("allows both directions when resize is both", () => {
      render(<Textarea resize="both" data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("resize");
    });
  });

  describe("rows", () => {
    it("renders with default rows", () => {
      render(<Textarea data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveAttribute("rows", "3");
    });

    it("renders with custom rows", () => {
      render(<Textarea rows={5} data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveAttribute("rows", "5");
    });
  });

  describe("fullWidth", () => {
    it("renders full width when prop is true", () => {
      render(<Textarea fullWidth data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("w-full");
    });

    it("renders auto width when fullWidth is false", () => {
      render(<Textarea fullWidth={false} data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).not.toHaveClass("w-full");
    });
  });

  describe("events", () => {
    it("calls onChange when value changes", async () => {
      const handleChange = vi.fn();
      const user = userEvent.setup();

      render(<Textarea onChange={handleChange} />);
      const textarea = screen.getByRole("textbox");

      await user.type(textarea, "Hello");
      expect(handleChange).toHaveBeenCalled();
    });

    it("calls onFocus when focused", async () => {
      const handleFocus = vi.fn();
      const user = userEvent.setup();

      render(<Textarea onFocus={handleFocus} />);
      const textarea = screen.getByRole("textbox");

      await user.click(textarea);
      expect(handleFocus).toHaveBeenCalledTimes(1);
    });

    it("calls onBlur when blurred", async () => {
      const handleBlur = vi.fn();
      const user = userEvent.setup();

      render(<Textarea onBlur={handleBlur} />);
      const textarea = screen.getByRole("textbox");

      await user.click(textarea);
      await user.tab();
      expect(handleBlur).toHaveBeenCalledTimes(1);
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(<Textarea className="custom-class" data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("custom-class");
    });

    it("passes through additional props", () => {
      render(
        <Textarea data-testid="custom-textarea" aria-label="Custom textarea" />,
      );
      const textarea = screen.getByTestId("custom-textarea");
      expect(textarea).toHaveAttribute("aria-label", "Custom textarea");
    });

    it("forwards ref to textarea element", () => {
      const ref = vi.fn();
      render(<Textarea ref={ref} />);
      expect(ref).toHaveBeenCalled();
      expect(ref.mock.calls[0][0]).toBeInstanceOf(HTMLTextAreaElement);
    });
  });

  describe("accessibility", () => {
    it("associates label with textarea using id", () => {
      render(
        <>
          <label htmlFor="test-textarea">Test Label</label>
          <Textarea id="test-textarea" />
        </>,
      );
      const textarea = screen.getByLabelText("Test Label");
      expect(textarea).toBeInTheDocument();
    });

    it("supports aria-describedby for error messages", () => {
      render(
        <>
          <Textarea aria-describedby="error-message" variant="error" />
          <span id="error-message">This field is required</span>
        </>,
      );
      const textarea = screen.getByRole("textbox");
      expect(textarea).toHaveAttribute("aria-describedby", "error-message");
    });

    it("has proper focus ring styles", () => {
      render(<Textarea data-testid="textarea" />);
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("focus:ring-2");
    });
  });

  describe("CVA integration", () => {
    it("exports textareaVariants function for external use", async () => {
      const { textareaVariants } = await import("./Textarea");
      expect(typeof textareaVariants).toBe("function");
    });
  });
});
