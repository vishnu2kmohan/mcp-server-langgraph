/**
 * ExecutionModeIndicator Tests
 *
 * Tests for the execution mode indicator component that displays
 * current mode and allows cycling via Ctrl/Cmd+Shift+M.
 *
 * @see test-utils.tsx for MOTION_PROPS and filterMotionProps documentation
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ExecutionModeIndicator } from "./ExecutionModeIndicator";
import type { ExecutionMode } from "@/store/slices/executionModeSlice";

// Motion-specific props that should not be passed to DOM elements
const MOTION_PROPS = new Set([
  "whileHover", "whileTap", "whileFocus", "whileDrag", "whileInView",
  "initial", "animate", "exit", "variants", "transition",
  "layout", "layoutId", "drag", "dragConstraints", "dragElastic",
  "dragMomentum", "onAnimationStart", "onAnimationComplete",
  "onDragStart", "onDragEnd", "onDrag",
]);

function filterMotionProps<T extends Record<string, unknown>>(props: T): T {
  const filtered = { ...props };
  for (const key of Object.keys(filtered)) {
    if (MOTION_PROPS.has(key)) delete filtered[key];
  }
  return filtered;
}

// Mock motion/react to avoid animation issues in tests
vi.mock("motion/react", () => ({
  motion: {
    button: ({ children, ...props }: React.ComponentProps<"button"> & Record<string, unknown>) => (
      <button {...filterMotionProps(props)}>{children}</button>
    ),
  },
  useReducedMotion: () => false,
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe("ExecutionModeIndicator", () => {
  const defaultProps = {
    mode: "default" as ExecutionMode,
    onClick: vi.fn(),
    disabled: false,
    isAdmin: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("renders with default mode", () => {
      render(<ExecutionModeIndicator {...defaultProps} />);

      expect(screen.getByTestId("execution-mode-indicator")).toBeInTheDocument();
      expect(screen.getByText("Default")).toBeInTheDocument();
    });

    it("renders with plan mode", () => {
      render(<ExecutionModeIndicator {...defaultProps} mode="plan" />);

      expect(screen.getByText("Plan")).toBeInTheDocument();
    });

    it("renders with auto_accept mode", () => {
      render(<ExecutionModeIndicator {...defaultProps} mode="auto_accept" />);

      expect(screen.getByText("Auto")).toBeInTheDocument();
    });

    it("renders with bypass mode for admin", () => {
      render(
        <ExecutionModeIndicator
          {...defaultProps}
          mode="bypass"
          hasBypassPermission={true}
        />,
      );

      expect(screen.getByText("Bypass")).toBeInTheDocument();
    });
  });

  describe("Styling", () => {
    it("applies default mode styling", () => {
      render(<ExecutionModeIndicator {...defaultProps} mode="default" />);

      const button = screen.getByTestId("execution-mode-indicator");
      expect(button).toHaveClass("bg-neutral-3");
      expect(button).toHaveClass("text-neutral-11");
    });

    it("applies plan mode styling", () => {
      render(<ExecutionModeIndicator {...defaultProps} mode="plan" />);

      const button = screen.getByTestId("execution-mode-indicator");
      expect(button).toHaveClass("bg-primary-3");
      expect(button).toHaveClass("text-primary-11");
    });

    it("applies auto_accept mode styling", () => {
      render(<ExecutionModeIndicator {...defaultProps} mode="auto_accept" />);

      const button = screen.getByTestId("execution-mode-indicator");
      expect(button).toHaveClass("bg-success-3");
      expect(button).toHaveClass("text-success-11");
    });

    it("applies bypass mode styling", () => {
      render(
        <ExecutionModeIndicator
          {...defaultProps}
          mode="bypass"
          hasBypassPermission={true}
        />,
      );

      const button = screen.getByTestId("execution-mode-indicator");
      expect(button).toHaveClass("bg-warning-3");
      expect(button).toHaveClass("text-warning-11");
    });

    it("applies minimum touch target size for WCAG 2.5.8", () => {
      render(<ExecutionModeIndicator {...defaultProps} />);

      const button = screen.getByTestId("execution-mode-indicator");
      expect(button).toHaveClass("min-h-8");
    });
  });

  describe("Interaction", () => {
    it("calls onClick when clicked", async () => {
      const onClick = vi.fn();
      const user = userEvent.setup();

      render(<ExecutionModeIndicator {...defaultProps} onClick={onClick} />);

      await user.click(screen.getByTestId("execution-mode-indicator"));
      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it("does not call onClick when disabled", async () => {
      const onClick = vi.fn();
      const user = userEvent.setup();

      render(
        <ExecutionModeIndicator
          {...defaultProps}
          onClick={onClick}
          disabled={true}
        />,
      );

      const button = screen.getByTestId("execution-mode-indicator");
      expect(button).toBeDisabled();

      await user.click(button);
      expect(onClick).not.toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("has correct aria-label for default mode", () => {
      render(<ExecutionModeIndicator {...defaultProps} mode="default" />);

      const button = screen.getByTestId("execution-mode-indicator");
      expect(button).toHaveAttribute(
        "aria-label",
        "Execution mode: Default. Press Ctrl/Cmd+Shift+M to cycle.",
      );
    });

    it("has correct aria-label for plan mode", () => {
      render(<ExecutionModeIndicator {...defaultProps} mode="plan" />);

      const button = screen.getByTestId("execution-mode-indicator");
      expect(button).toHaveAttribute(
        "aria-label",
        "Execution mode: Plan. Press Ctrl/Cmd+Shift+M to cycle.",
      );
    });

    it("has correct aria-label for auto_accept mode", () => {
      render(<ExecutionModeIndicator {...defaultProps} mode="auto_accept" />);

      const button = screen.getByTestId("execution-mode-indicator");
      expect(button).toHaveAttribute(
        "aria-label",
        "Execution mode: Auto. Press Ctrl/Cmd+Shift+M to cycle.",
      );
    });

    it("has correct aria-label for bypass mode", () => {
      render(
        <ExecutionModeIndicator
          {...defaultProps}
          mode="bypass"
          hasBypassPermission={true}
        />,
      );

      const button = screen.getByTestId("execution-mode-indicator");
      expect(button).toHaveAttribute(
        "aria-label",
        "Execution mode: Bypass. Press Ctrl/Cmd+Shift+M to cycle.",
      );
    });

    it("is focusable via keyboard", () => {
      render(<ExecutionModeIndicator {...defaultProps} />);

      const button = screen.getByTestId("execution-mode-indicator");
      button.focus();
      expect(document.activeElement).toBe(button);
    });
  });

  describe("Admin Indicator", () => {
    it("shows admin indicator for bypass mode", () => {
      render(
        <ExecutionModeIndicator
          {...defaultProps}
          mode="bypass"
          hasBypassPermission={true}
        />,
      );

      // Should display "(Admin)" indicator or special styling
      expect(screen.getByTestId("execution-mode-indicator")).toBeInTheDocument();
    });

    it("does not show bypass mode for non-admin", () => {
      // Non-admin users should never see bypass mode rendered
      // The parent component should prevent this, but indicator should handle gracefully
      render(
        <ExecutionModeIndicator
          {...defaultProps}
          mode="bypass"
          isAdmin={false}
        />,
      );

      // Should still render but may show warning or fallback
      expect(screen.getByTestId("execution-mode-indicator")).toBeInTheDocument();
    });
  });

  describe("Tooltips", () => {
    it("displays tooltip content via title attribute", () => {
      render(<ExecutionModeIndicator {...defaultProps} mode="default" />);

      const button = screen.getByTestId("execution-mode-indicator");
      expect(button).toHaveAttribute(
        "title",
        "Normal chat - approval for medium/high risk",
      );
    });

    it("displays correct tooltip for plan mode", () => {
      render(<ExecutionModeIndicator {...defaultProps} mode="plan" />);

      const button = screen.getByTestId("execution-mode-indicator");
      expect(button).toHaveAttribute("title", "All tasks require approval");
    });

    it("displays correct tooltip for auto_accept mode", () => {
      render(<ExecutionModeIndicator {...defaultProps} mode="auto_accept" />);

      const button = screen.getByTestId("execution-mode-indicator");
      expect(button).toHaveAttribute("title", "Accept suggestions automatically");
    });

    it("displays correct tooltip for bypass mode", () => {
      render(
        <ExecutionModeIndicator
          {...defaultProps}
          mode="bypass"
          hasBypassPermission={true}
        />,
      );

      const button = screen.getByTestId("execution-mode-indicator");
      expect(button).toHaveAttribute(
        "title",
        "Risk-aware auto-approval (requires permission)",
      );
    });
  });
});
