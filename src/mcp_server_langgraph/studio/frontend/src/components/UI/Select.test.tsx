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
      render(<Select options={defaultOptions} />);
      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("renders all options", () => {
      render(<Select options={defaultOptions} />);
      const select = screen.getByRole("combobox");
      expect(select.querySelectorAll("option").length).toBe(3);
    });

    it("renders with placeholder option", () => {
      render(
        <Select options={defaultOptions} placeholder="Select an option" />,
      );
      const options = screen.getAllByRole("option");
      expect(options[0]).toHaveTextContent("Select an option");
      expect(options[0]).toHaveValue("");
    });

    it("renders with selected value", () => {
      render(<Select options={defaultOptions} value="2" onChange={() => {}} />);
      expect(screen.getByRole("combobox")).toHaveValue("2");
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(
        <Select options={defaultOptions} size="sm" data-testid="select" />,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("text-xs");
      expect(select).toHaveClass("py-1.5");
    });

    it("renders medium size (default)", () => {
      render(
        <Select options={defaultOptions} size="md" data-testid="select" />,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("text-sm");
      expect(select).toHaveClass("py-2");
    });

    it("renders large size", () => {
      render(
        <Select options={defaultOptions} size="lg" data-testid="select" />,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("text-base");
      expect(select).toHaveClass("py-2.5");
    });
  });

  describe("variants", () => {
    it("renders default variant", () => {
      render(
        <Select
          options={defaultOptions}
          variant="default"
          data-testid="select"
        />,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("border-neutral-5");
    });

    it("renders error variant", () => {
      render(
        <Select
          options={defaultOptions}
          variant="error"
          data-testid="select"
        />,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("border-error-9");
    });

    it("renders success variant", () => {
      render(
        <Select
          options={defaultOptions}
          variant="success"
          data-testid="select"
        />,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("border-success-9");
    });
  });

  describe("states", () => {
    it("renders disabled state", () => {
      render(<Select options={defaultOptions} disabled data-testid="select" />);
      const select = screen.getByTestId("select");
      expect(select).toBeDisabled();
      expect(select).toHaveClass("cursor-not-allowed");
    });

    it("renders required state", () => {
      render(<Select options={defaultOptions} required data-testid="select" />);
      const select = screen.getByTestId("select");
      expect(select).toBeRequired();
    });
  });

  describe("fullWidth", () => {
    it("renders full width when prop is true", () => {
      render(
        <Select options={defaultOptions} fullWidth data-testid="select" />,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("w-full");
    });

    it("renders auto width when fullWidth is false", () => {
      render(
        <Select
          options={defaultOptions}
          fullWidth={false}
          data-testid="select"
        />,
      );
      const select = screen.getByTestId("select");
      expect(select).not.toHaveClass("w-full");
    });
  });

  describe("events", () => {
    it("calls onChange when selection changes", async () => {
      const handleChange = vi.fn();
      const user = userEvent.setup();

      render(<Select options={defaultOptions} onChange={handleChange} />);
      const select = screen.getByRole("combobox");

      await user.selectOptions(select, "2");
      expect(handleChange).toHaveBeenCalled();
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(
        <Select
          options={defaultOptions}
          className="custom-class"
          data-testid="select"
        />,
      );
      const select = screen.getByTestId("select");
      expect(select).toHaveClass("custom-class");
    });

    it("passes through additional props", () => {
      render(
        <Select
          options={defaultOptions}
          data-testid="custom-select"
          aria-label="Custom select"
        />,
      );
      const select = screen.getByTestId("custom-select");
      expect(select).toHaveAttribute("aria-label", "Custom select");
    });

    it("forwards ref to select element", () => {
      const ref = vi.fn();
      render(<Select options={defaultOptions} ref={ref} />);
      expect(ref).toHaveBeenCalled();
      expect(ref.mock.calls[0][0]).toBeInstanceOf(HTMLSelectElement);
    });
  });

  describe("accessibility", () => {
    it("associates label with select using id", () => {
      render(
        <>
          <label htmlFor="test-select">Test Label</label>
          <Select options={defaultOptions} id="test-select" />
        </>,
      );
      const select = screen.getByLabelText("Test Label");
      expect(select).toBeInTheDocument();
    });

    it("supports aria-describedby for error messages", () => {
      render(
        <>
          <Select
            options={defaultOptions}
            aria-describedby="error-message"
            variant="error"
          />
          <span id="error-message">Please select an option</span>
        </>,
      );
      const select = screen.getByRole("combobox");
      expect(select).toHaveAttribute("aria-describedby", "error-message");
    });

    it("has proper focus ring styles", () => {
      render(<Select options={defaultOptions} data-testid="select" />);
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
      render(<Select options={optionsWithDisabled} />);
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
