/**
 * Toggle Component Tests
 *
 * TDD: Tests written first to define expected behavior.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Toggle } from "./Toggle";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("Toggle", () => {
  describe("rendering", () => {
    it("renders as a button with switch role", () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      expect(screen.getByRole("switch")).toBeInTheDocument();
    });

    it("renders with label when provided", () => {
      render(
        <Toggle checked={false} onChange={() => {}} label="Enable feature" />,
      );
      expect(screen.getByText("Enable feature")).toBeInTheDocument();
    });

    it("renders with description when provided", () => {
      render(
        <Toggle
          checked={false}
          onChange={() => {}}
          label="Enable feature"
          description="This enables the feature"
        />,
      );
      expect(screen.getByText("This enables the feature")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      render(
        <Toggle checked={false} onChange={() => {}} className="custom-class" />,
      );
      expect(screen.getByRole("switch").parentElement).toHaveClass(
        "custom-class",
      );
    });
  });

  describe("checked state", () => {
    it("has aria-checked false when unchecked", () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      expect(screen.getByRole("switch")).toHaveAttribute(
        "aria-checked",
        "false",
      );
    });

    it("has aria-checked true when checked", () => {
      render(<Toggle checked={true} onChange={() => {}} />);
      expect(screen.getByRole("switch")).toHaveAttribute(
        "aria-checked",
        "true",
      );
    });

    it("applies checked visual styles when checked", () => {
      render(<Toggle checked={true} onChange={() => {}} />);
      const toggle = screen.getByRole("switch");
      expect(toggle).toHaveClass("bg-primary-500");
    });

    it("applies unchecked visual styles when unchecked", () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      const toggle = screen.getByRole("switch");
      expect(toggle).toHaveClass("bg-neutral-200");
    });
  });

  describe("interaction", () => {
    it("calls onChange when clicked", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<Toggle checked={false} onChange={onChange} />);

      await user.click(screen.getByRole("switch"));
      expect(onChange).toHaveBeenCalledWith(true);
    });

    it("calls onChange with false when checked toggle is clicked", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<Toggle checked={true} onChange={onChange} />);

      await user.click(screen.getByRole("switch"));
      expect(onChange).toHaveBeenCalledWith(false);
    });

    it("can be toggled with keyboard space", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<Toggle checked={false} onChange={onChange} />);

      const toggle = screen.getByRole("switch");
      toggle.focus();
      await user.keyboard(" ");

      expect(onChange).toHaveBeenCalledWith(true);
    });

    it("can be toggled with keyboard enter", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<Toggle checked={false} onChange={onChange} />);

      const toggle = screen.getByRole("switch");
      toggle.focus();
      await user.keyboard("{Enter}");

      expect(onChange).toHaveBeenCalledWith(true);
    });
  });

  describe("disabled state", () => {
    it("does not call onChange when disabled", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<Toggle checked={false} onChange={onChange} disabled />);

      await user.click(screen.getByRole("switch"));
      expect(onChange).not.toHaveBeenCalled();
    });

    it("applies disabled styles", () => {
      render(<Toggle checked={false} onChange={() => {}} disabled />);
      const toggle = screen.getByRole("switch");
      expect(toggle).toHaveClass("cursor-not-allowed");
      expect(toggle).toHaveClass("opacity-50");
    });

    it("has aria-disabled when disabled", () => {
      render(<Toggle checked={false} onChange={() => {}} disabled />);
      expect(screen.getByRole("switch")).toHaveAttribute(
        "aria-disabled",
        "true",
      );
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(<Toggle checked={false} onChange={() => {}} size="sm" />);
      const toggle = screen.getByRole("switch");
      expect(toggle).toHaveClass("h-5");
      expect(toggle).toHaveClass("w-9");
    });

    it("renders medium size (default)", () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      const toggle = screen.getByRole("switch");
      expect(toggle).toHaveClass("h-6");
      expect(toggle).toHaveClass("w-11");
    });

    it("renders large size", () => {
      render(<Toggle checked={false} onChange={() => {}} size="lg" />);
      const toggle = screen.getByRole("switch");
      expect(toggle).toHaveClass("h-7");
      expect(toggle).toHaveClass("w-14");
    });
  });

  describe("accessibility", () => {
    it("supports aria-label", () => {
      render(
        <Toggle
          checked={false}
          onChange={() => {}}
          aria-label="Toggle dark mode"
        />,
      );
      expect(screen.getByRole("switch")).toHaveAttribute(
        "aria-label",
        "Toggle dark mode",
      );
    });

    it("supports aria-describedby", () => {
      render(
        <>
          <Toggle checked={false} onChange={() => {}} aria-describedby="desc" />
          <span id="desc">Additional description</span>
        </>,
      );
      expect(screen.getByRole("switch")).toHaveAttribute(
        "aria-describedby",
        "desc",
      );
    });

    it("is focusable", () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      const toggle = screen.getByRole("switch");
      toggle.focus();
      expect(toggle).toHaveFocus();
    });
  });
});
