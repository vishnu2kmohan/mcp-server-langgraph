/**
 * Checkbox Component Tests
 *
 * TDD: Tests written FIRST to define expected behavior.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Checkbox } from "./Checkbox";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("Checkbox", () => {
  describe("rendering", () => {
    it("renders as a checkbox input", () => {
      render(
        <TestProvider>
          <Checkbox checked={false} onChange={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByRole("checkbox")).toBeInTheDocument();
    });

    it("renders with label when provided", () => {
      render(
        <TestProvider>
          <Checkbox checked={false} onChange={() => {}} label="Accept terms" />
        </TestProvider>,
      );
      expect(screen.getByText("Accept terms")).toBeInTheDocument();
    });

    it("renders with description when provided", () => {
      render(
        <TestProvider>
          <Checkbox
            checked={false}
            onChange={() => {}}
            label="Accept terms"
            description="You must accept the terms to continue"
          />
        </TestProvider>,
      );
      expect(
        screen.getByText("You must accept the terms to continue"),
      ).toBeInTheDocument();
    });

    it("applies custom className", () => {
      render(
        <TestProvider>
          <Checkbox
            checked={false}
            onChange={() => {}}
            className="custom-class"
          />
        </TestProvider>,
      );
      expect(screen.getByRole("checkbox").closest("label")).toHaveClass(
        "custom-class",
      );
    });
  });

  describe("checked state", () => {
    it("is unchecked when checked is false", () => {
      render(
        <TestProvider>
          <Checkbox checked={false} onChange={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByRole("checkbox")).not.toBeChecked();
    });

    it("is checked when checked is true", () => {
      render(
        <TestProvider>
          <Checkbox checked={true} onChange={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByRole("checkbox")).toBeChecked();
    });
  });

  describe("interaction", () => {
    it("calls onChange with true when unchecked checkbox is clicked", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <Checkbox checked={false} onChange={onChange} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("checkbox"));
      expect(onChange).toHaveBeenCalledWith(true);
    });

    it("calls onChange with false when checked checkbox is clicked", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <Checkbox checked={true} onChange={onChange} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("checkbox"));
      expect(onChange).toHaveBeenCalledWith(false);
    });

    it("can be toggled by clicking the label", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <Checkbox checked={false} onChange={onChange} label="Click me" />
        </TestProvider>,
      );

      await user.click(screen.getByText("Click me"));
      expect(onChange).toHaveBeenCalledWith(true);
    });

    it("can be toggled with keyboard space", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <Checkbox checked={false} onChange={onChange} />
        </TestProvider>,
      );

      const checkbox = screen.getByRole("checkbox");
      checkbox.focus();
      await user.keyboard(" ");

      expect(onChange).toHaveBeenCalledWith(true);
    });
  });

  describe("disabled state", () => {
    it("does not call onChange when disabled", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <Checkbox checked={false} onChange={onChange} disabled />
        </TestProvider>,
      );

      await user.click(screen.getByRole("checkbox"));
      expect(onChange).not.toHaveBeenCalled();
    });

    it("has disabled attribute when disabled", () => {
      render(
        <TestProvider>
          <Checkbox checked={false} onChange={() => {}} disabled />
        </TestProvider>,
      );
      expect(screen.getByRole("checkbox")).toBeDisabled();
    });

    it("applies disabled styles to label", () => {
      render(
        <TestProvider>
          <Checkbox
            checked={false}
            onChange={() => {}}
            disabled
            label="Disabled"
          />
        </TestProvider>,
      );
      expect(screen.getByText("Disabled")).toHaveClass("opacity-50");
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(
        <TestProvider>
          <Checkbox checked={false} onChange={() => {}} size="sm" />
        </TestProvider>,
      );
      const checkbox = screen.getByRole("checkbox");
      expect(checkbox).toHaveClass("h-4");
      expect(checkbox).toHaveClass("w-4");
    });

    it("renders medium size (default)", () => {
      render(
        <TestProvider>
          <Checkbox checked={false} onChange={() => {}} />
        </TestProvider>,
      );
      const checkbox = screen.getByRole("checkbox");
      expect(checkbox).toHaveClass("h-5");
      expect(checkbox).toHaveClass("w-5");
    });

    it("renders large size", () => {
      render(
        <TestProvider>
          <Checkbox checked={false} onChange={() => {}} size="lg" />
        </TestProvider>,
      );
      const checkbox = screen.getByRole("checkbox");
      expect(checkbox).toHaveClass("h-6");
      expect(checkbox).toHaveClass("w-6");
    });
  });

  describe("indeterminate state", () => {
    it("supports indeterminate state", () => {
      render(
        <TestProvider>
          <Checkbox checked={false} onChange={() => {}} indeterminate />
        </TestProvider>,
      );
      const checkbox = screen.getByRole("checkbox") as HTMLInputElement;
      expect(checkbox.indeterminate).toBe(true);
    });
  });

  describe("accessibility", () => {
    it("supports aria-label", () => {
      render(
        <TestProvider>
          <Checkbox
            checked={false}
            onChange={() => {}}
            aria-label="Select all"
          />
        </TestProvider>,
      );
      expect(screen.getByRole("checkbox")).toHaveAttribute(
        "aria-label",
        "Select all",
      );
    });

    it("associates label with checkbox via htmlFor", () => {
      render(
        <TestProvider>
          <Checkbox
            checked={false}
            onChange={() => {}}
            label="My checkbox"
            id="my-cb"
          />
        </TestProvider>,
      );
      const label = screen.getByText("My checkbox").closest("label");
      expect(label).toHaveAttribute("for", "my-cb");
    });

    it("is focusable", () => {
      render(
        <TestProvider>
          <Checkbox checked={false} onChange={() => {}} />
        </TestProvider>,
      );
      const checkbox = screen.getByRole("checkbox");
      checkbox.focus();
      expect(checkbox).toHaveFocus();
    });
  });
});
