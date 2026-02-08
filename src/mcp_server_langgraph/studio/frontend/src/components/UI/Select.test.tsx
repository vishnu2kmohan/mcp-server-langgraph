/**
 * Select Component Tests
 *
 * Tests for the Select primitive component variants, sizes, states, and accessibility.
 * TDD: These tests were written FIRST before implementation.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Select } from "./Select";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Select", () => {
  const defaultOptions = [
    { value: "1", label: "Option 1" },
    { value: "2", label: "Option 2" },
    { value: "3", label: "Option 3" },
  ];

  describe("rendering", () => {
    it("renders with default props", () => {
      render(
        <TestProvider>
          <Select options={defaultOptions} />
        </TestProvider>,
      );
      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("renders all options", () => {
      render(
        <TestProvider>
          <Select options={defaultOptions} />
        </TestProvider>,
      );
      const select = screen.getByRole("combobox");
      expect(select.querySelectorAll("option").length).toBe(3);
    });

    it("renders with placeholder option", () => {
      render(
        <TestProvider>
          <Select options={defaultOptions} placeholder="Select an option" />
        </TestProvider>,
      );
      const options = screen.getAllByRole("option");
      expect(options[0]).toHaveTextContent("Select an option");
      expect(options[0]).toHaveValue("");
    });

    it("renders with selected value", () => {
      render(
        <TestProvider>
          <Select options={defaultOptions} value="2" onChange={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByRole("combobox")).toHaveValue("2");
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(
        <TestProvider>
          <Select options={defaultOptions} size="sm" data-testid="select" />
        </TestProvider>,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("text-xs");
      expect(select).toHaveClass("py-1.5");
    });

    it("renders medium size (default)", () => {
      render(
        <TestProvider>
          <Select options={defaultOptions} size="md" data-testid="select" />
        </TestProvider>,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("text-sm");
      expect(select).toHaveClass("py-2");
    });

    it("renders large size", () => {
      render(
        <TestProvider>
          <Select options={defaultOptions} size="lg" data-testid="select" />
        </TestProvider>,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("text-base");
      expect(select).toHaveClass("py-2.5");
    });
  });

  describe("variants", () => {
    it("renders default variant", () => {
      render(
        <TestProvider>
          <Select
            options={defaultOptions}
            variant="default"
            data-testid="select"
          />
        </TestProvider>,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("border-neutral-5");
    });

    it("renders error variant", () => {
      render(
        <TestProvider>
          <Select
            options={defaultOptions}
            variant="error"
            data-testid="select"
          />
        </TestProvider>,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("border-error-9");
    });

    it("renders success variant", () => {
      render(
        <TestProvider>
          <Select
            options={defaultOptions}
            variant="success"
            data-testid="select"
          />
        </TestProvider>,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("border-success-9");
    });
  });

  describe("states", () => {
    it("renders disabled state", () => {
      render(
        <TestProvider>
          <Select options={defaultOptions} disabled data-testid="select" />
        </TestProvider>,
      );
      const select = screen.getByTestId("select");
      expect(select).toBeDisabled();
      expect(select).toHaveClass("cursor-not-allowed");
    });

    it("renders required state", () => {
      render(
        <TestProvider>
          <Select options={defaultOptions} required data-testid="select" />
        </TestProvider>,
      );
      const select = screen.getByTestId("select");
      expect(select).toBeRequired();
    });
  });

  describe("fullWidth", () => {
    it("renders full width when prop is true", () => {
      render(
        <TestProvider>
          <Select options={defaultOptions} fullWidth data-testid="select" />
        </TestProvider>,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("w-full");
    });

    it("renders auto width when fullWidth is false", () => {
      render(
        <TestProvider>
          <Select
            options={defaultOptions}
            fullWidth={false}
            data-testid="select"
          />
        </TestProvider>,
      );
      const select = screen.getByTestId("select");
      expect(select).not.toHaveClass("w-full");
    });
  });

  describe("events", () => {
    it("calls onChange when selection changes", async () => {
      const handleChange = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <Select options={defaultOptions} onChange={handleChange} />
        </TestProvider>,
      );
      const select = screen.getByRole("combobox");

      await user.selectOptions(select, "2");
      expect(handleChange).toHaveBeenCalled();
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(
        <TestProvider>
          <Select
            options={defaultOptions}
            className="custom-class"
            data-testid="select"
          />
        </TestProvider>,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("custom-class");
    });

    it("passes through additional props", () => {
      render(
        <TestProvider>
          <Select
            options={defaultOptions}
            data-testid="custom-select"
            aria-label="Custom select"
          />
        </TestProvider>,
      );
      const select = screen.getByTestId("custom-select");
      expect(select).toHaveAttribute("aria-label", "Custom select");
    });

    it("forwards ref to select element", () => {
      const ref = vi.fn();
      render(
        <TestProvider>
          <Select options={defaultOptions} ref={ref} />
        </TestProvider>,
      );
      expect(ref).toHaveBeenCalled();
      expect(ref.mock.calls[0][0]).toBeInstanceOf(HTMLSelectElement);
    });
  });

  describe("accessibility", () => {
    it("associates label with select using id", () => {
      render(
        <TestProvider>
          <>
            <label htmlFor="test-select">Test Label</label>
            <Select options={defaultOptions} id="test-select" />
          </>
        </TestProvider>,
      );
      const select = screen.getByLabelText("Test Label");
      expect(select).toBeInTheDocument();
    });

    it("supports aria-describedby for error messages", () => {
      render(
        <TestProvider>
          <>
            <Select
              options={defaultOptions}
              aria-describedby="error-message"
              variant="error"
            />
            <span id="error-message">Please select an option</span>
          </>
        </TestProvider>,
      );
      const select = screen.getByRole("combobox");
      expect(select).toHaveAttribute("aria-describedby", "error-message");
    });

    it("has proper focus ring styles", () => {
      render(
        <TestProvider>
          <Select options={defaultOptions} data-testid="select" />
        </TestProvider>,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("focus:ring-2");
    });
  });

  describe("option groups", () => {
    it("renders options with disabled state", () => {
      const optionsWithDisabled = [
        { value: "1", label: "Option 1" },
        { value: "2", label: "Option 2", disabled: true },
        { value: "3", label: "Option 3" },
      ];
      render(
        <TestProvider>
          <Select options={optionsWithDisabled} />
        </TestProvider>,
      );
      const options = screen.getAllByRole("option");
      expect(options[1]).toBeDisabled();
    });
  });

  describe("CVA integration", () => {
    it("exports selectVariants function for external use", async () => {
      const { selectVariants } = await import("./Select");
      expect(typeof selectVariants).toBe("function");
    });
  });
});
