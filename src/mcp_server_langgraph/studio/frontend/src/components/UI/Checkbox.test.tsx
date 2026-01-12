/**
 * Checkbox Component Tests
 *
 * TDD: Tests written FIRST to define expected behavior.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Checkbox } from "./Checkbox";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("Checkbox", () => {
  describe("rendering", () => {
    it("renders as a checkbox input", () => {
      render(<Checkbox checked={false} onChange={() => {}} />);
      expect(screen.getByRole("checkbox")).toBeInTheDocument();
    });

    it("renders with label when provided", () => {
      render(
        <Checkbox checked={false} onChange={() => {}} label="Accept terms" />,
      );
      expect(screen.getByText("Accept terms")).toBeInTheDocument();
    });

    it("renders with description when provided", () => {
      render(
        <Checkbox
          checked={false}
          onChange={() => {}}
          label="Accept terms"
          description="You must accept the terms to continue"
        />,
      );
      expect(
        screen.getByText("You must accept the terms to continue"),
      ).toBeInTheDocument();
    });

    it("applies custom className", () => {
      render(
        <Checkbox
          checked={false}
          onChange={() => {}}
          className="custom-class"
        />,
      );
      expect(screen.getByRole("checkbox").closest("label")).toHaveClass(
        "custom-class",
      );
    });
  });

  describe("checked state", () => {
    it("is unchecked when checked is false", () => {
      render(<Checkbox checked={false} onChange={() => {}} />);
      expect(screen.getByRole("checkbox")).not.toBeChecked();
    });

    it("is checked when checked is true", () => {
      render(<Checkbox checked={true} onChange={() => {}} />);
      expect(screen.getByRole("checkbox")).toBeChecked();
    });
  });

  describe("interaction", () => {
    it("calls onChange with true when unchecked checkbox is clicked", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<Checkbox checked={false} onChange={onChange} />);

      await user.click(screen.getByRole("checkbox"));
      expect(onChange).toHaveBeenCalledWith(true);
    });

    it("calls onChange with false when checked checkbox is clicked", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<Checkbox checked={true} onChange={onChange} />);

      await user.click(screen.getByRole("checkbox"));
      expect(onChange).toHaveBeenCalledWith(false);
    });

    it("can be toggled by clicking the label", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<Checkbox checked={false} onChange={onChange} label="Click me" />);

      await user.click(screen.getByText("Click me"));
      expect(onChange).toHaveBeenCalledWith(true);
    });

    it("can be toggled with keyboard space", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<Checkbox checked={false} onChange={onChange} />);

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
      render(<Checkbox checked={false} onChange={onChange} disabled />);

      await user.click(screen.getByRole("checkbox"));
      expect(onChange).not.toHaveBeenCalled();
    });

    it("has disabled attribute when disabled", () => {
      render(<Checkbox checked={false} onChange={() => {}} disabled />);
      expect(screen.getByRole("checkbox")).toBeDisabled();
    });

    it("applies disabled styles to label", () => {
      render(
        <Checkbox
          checked={false}
          onChange={() => {}}
          disabled
          label="Disabled"
        />,
      );
      expect(screen.getByText("Disabled")).toHaveClass("opacity-50");
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(<Checkbox checked={false} onChange={() => {}} size="sm" />);
      const checkbox = screen.getByRole("checkbox");
      expect(checkbox).toHaveClass("h-4");
      expect(checkbox).toHaveClass("w-4");
    });

    it("renders medium size (default)", () => {
      render(<Checkbox checked={false} onChange={() => {}} />);
      const checkbox = screen.getByRole("checkbox");
      expect(checkbox).toHaveClass("h-5");
      expect(checkbox).toHaveClass("w-5");
    });

    it("renders large size", () => {
      render(<Checkbox checked={false} onChange={() => {}} size="lg" />);
      const checkbox = screen.getByRole("checkbox");
      expect(checkbox).toHaveClass("h-6");
      expect(checkbox).toHaveClass("w-6");
    });
  });

  describe("indeterminate state", () => {
    it("supports indeterminate state", () => {
      render(<Checkbox checked={false} onChange={() => {}} indeterminate />);
      const checkbox = screen.getByRole("checkbox") as HTMLInputElement;
      expect(checkbox.indeterminate).toBe(true);
    });
  });

  describe("accessibility", () => {
    it("supports aria-label", () => {
      render(
        <Checkbox
          checked={false}
          onChange={() => {}}
          aria-label="Select all"
        />,
      );
      expect(screen.getByRole("checkbox")).toHaveAttribute(
        "aria-label",
        "Select all",
      );
    });

    it("associates label with checkbox via htmlFor", () => {
      render(
        <Checkbox
          checked={false}
          onChange={() => {}}
          label="My checkbox"
          id="my-cb"
        />,
      );
      const label = screen.getByText("My checkbox").closest("label");
      expect(label).toHaveAttribute("for", "my-cb");
    });

    it("is focusable", () => {
      render(<Checkbox checked={false} onChange={() => {}} />);
      const checkbox = screen.getByRole("checkbox");
      checkbox.focus();
      expect(checkbox).toHaveFocus();
    });
  });
});
