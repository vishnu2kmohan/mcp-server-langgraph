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

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Textarea", () => {
  describe("rendering", () => {
    it("renders with default props", () => {
      render(
        <TestProvider>
          <Textarea />
        </TestProvider>,
      );
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    it("renders with placeholder", () => {
      render(
        <TestProvider>
          <Textarea placeholder="Enter text..." />
        </TestProvider>,
      );
      expect(screen.getByPlaceholderText("Enter text...")).toBeInTheDocument();
    });

    it("renders with value", () => {
      render(
        <TestProvider>
          <Textarea defaultValue="Hello World" />
        </TestProvider>,
      );
      expect(screen.getByDisplayValue("Hello World")).toBeInTheDocument();
    });

    it("renders with controlled value", () => {
      const { rerender } = render(
        <TestProvider>
          <Textarea value="Initial" onChange={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByDisplayValue("Initial")).toBeInTheDocument();

      rerender(<Textarea value="Updated" onChange={() => {}} />);
      expect(screen.getByDisplayValue("Updated")).toBeInTheDocument();
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(
        <TestProvider>
          <Textarea size="sm" data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("text-xs");
      expect(textarea).toHaveClass("p-2");
    });

    it("renders medium size (default)", () => {
      render(
        <TestProvider>
          <Textarea size="md" data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("text-sm");
      expect(textarea).toHaveClass("p-3");
    });

    it("renders large size", () => {
      render(
        <TestProvider>
          <Textarea size="lg" data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("text-base");
      expect(textarea).toHaveClass("p-4");
    });
  });

  describe("variants", () => {
    it("renders default variant", () => {
      render(
        <TestProvider>
          <Textarea variant="default" data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("border-neutral-5");
    });

    it("renders error variant", () => {
      render(
        <TestProvider>
          <Textarea variant="error" data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("border-error-9");
    });

    it("renders success variant", () => {
      render(
        <TestProvider>
          <Textarea variant="success" data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("border-success-9");
    });
  });

  describe("states", () => {
    it("renders disabled state", () => {
      render(
        <TestProvider>
          <Textarea disabled data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toBeDisabled();
      expect(textarea).toHaveClass("cursor-not-allowed");
    });

    it("renders readonly state", () => {
      render(
        <TestProvider>
          <Textarea readOnly data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveAttribute("readonly");
    });

    it("renders required state", () => {
      render(
        <TestProvider>
          <Textarea required data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toBeRequired();
    });
  });

  describe("resize", () => {
    it("allows vertical resize by default", () => {
      render(
        <TestProvider>
          <Textarea data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("resize-y");
    });

    it("allows no resize when resize is none", () => {
      render(
        <TestProvider>
          <Textarea resize="none" data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("resize-none");
    });

    it("allows both directions when resize is both", () => {
      render(
        <TestProvider>
          <Textarea resize="both" data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("resize");
    });
  });

  describe("rows", () => {
    it("renders with default rows", () => {
      render(
        <TestProvider>
          <Textarea data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveAttribute("rows", "3");
    });

    it("renders with custom rows", () => {
      render(
        <TestProvider>
          <Textarea rows={5} data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveAttribute("rows", "5");
    });
  });

  describe("fullWidth", () => {
    it("renders full width when prop is true", () => {
      render(
        <TestProvider>
          <Textarea fullWidth data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("w-full");
    });

    it("renders auto width when fullWidth is false", () => {
      render(
        <TestProvider>
          <Textarea fullWidth={false} data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).not.toHaveClass("w-full");
    });
  });

  describe("events", () => {
    it("calls onChange when value changes", async () => {
      const handleChange = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <Textarea onChange={handleChange} />
        </TestProvider>,
      );
      const textarea = screen.getByRole("textbox");

      await user.type(textarea, "Hello");
      expect(handleChange).toHaveBeenCalled();
    });

    it("calls onFocus when focused", async () => {
      const handleFocus = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <Textarea onFocus={handleFocus} />
        </TestProvider>,
      );
      const textarea = screen.getByRole("textbox");

      await user.click(textarea);
      expect(handleFocus).toHaveBeenCalledTimes(1);
    });

    it("calls onBlur when blurred", async () => {
      const handleBlur = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <Textarea onBlur={handleBlur} />
        </TestProvider>,
      );
      const textarea = screen.getByRole("textbox");

      await user.click(textarea);
      await user.tab();
      expect(handleBlur).toHaveBeenCalledTimes(1);
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(
        <TestProvider>
          <Textarea className="custom-class" data-testid="textarea" />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("textarea");
      expect(textarea).toHaveClass("custom-class");
    });

    it("passes through additional props", () => {
      render(
        <TestProvider>
          <Textarea
            data-testid="custom-textarea"
            aria-label="Custom textarea"
          />
        </TestProvider>,
      );
      const textarea = screen.getByTestId("custom-textarea");
      expect(textarea).toHaveAttribute("aria-label", "Custom textarea");
    });

    it("forwards ref to textarea element", () => {
      const ref = vi.fn();
      render(
        <TestProvider>
          <Textarea ref={ref} />
        </TestProvider>,
      );
      expect(ref).toHaveBeenCalled();
      expect(ref.mock.calls[0][0]).toBeInstanceOf(HTMLTextAreaElement);
    });
  });

  describe("accessibility", () => {
    it("associates label with textarea using id", () => {
      render(
        <TestProvider>
          <>
            <label htmlFor="test-textarea">Test Label</label>
            <Textarea id="test-textarea" />
          </>
        </TestProvider>,
      );
      const textarea = screen.getByLabelText("Test Label");
      expect(textarea).toBeInTheDocument();
    });

    it("supports aria-describedby for error messages", () => {
      render(
        <TestProvider>
          <>
            <Textarea aria-describedby="error-message" variant="error" />
            <span id="error-message">This field is required</span>
          </>
        </TestProvider>,
      );
      const textarea = screen.getByRole("textbox");
      expect(textarea).toHaveAttribute("aria-describedby", "error-message");
    });

    it("has proper focus ring styles", () => {
      render(
        <TestProvider>
          <Textarea data-testid="textarea" />
        </TestProvider>,
      );
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
