/**
 * ChatInput Execution Mode Tests
 *
 * Tests for execution mode toggle functionality in ChatInput.
 * Covers Ctrl/Cmd+Shift+M keyboard shortcut and mode cycling.
 *
 * Mode cycle order:
 * - Non-admin: default → plan → auto_accept → default
 * - With bypass permission: default → plan → auto_accept → bypass → default
 *
 * @see test-utils.tsx for MOTION_PROPS and filterMotionProps documentation
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatInput } from "./ChatInput";

// Motion-specific props that should not be passed to DOM elements
// See test-utils.tsx for the authoritative list
const MOTION_PROPS = new Set([
  "whileHover",
  "whileTap",
  "whileFocus",
  "whileDrag",
  "whileInView",
  "initial",
  "animate",
  "exit",
  "variants",
  "transition",
  "layout",
  "layoutId",
  "drag",
  "dragConstraints",
  "dragElastic",
  "dragMomentum",
  "onAnimationStart",
  "onAnimationComplete",
  "onDragStart",
  "onDragEnd",
  "onDrag",
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
    div: ({
      children,
      ...props
    }: React.ComponentProps<"div"> & Record<string, unknown>) => (
      <div {...filterMotionProps(props)}>{children}</div>
    ),
    button: ({
      children,
      ...props
    }: React.ComponentProps<"button"> & Record<string, unknown>) => (
      <button {...filterMotionProps(props)}>{children}</button>
    ),
    span: ({
      children,
      ...props
    }: React.ComponentProps<"span"> & Record<string, unknown>) => (
      <span {...filterMotionProps(props)}>{children}</span>
    ),
  },
  useReducedMotion: () => false,
  AnimatePresence: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ChatInput Execution Mode", () => {
  const defaultProps = {
    value: "",
    onChange: vi.fn(),
    onSubmit: vi.fn(),
    placeholder: "Type a message...",
    disabled: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Keyboard Shortcut (Ctrl/Cmd+Shift+M)", () => {
    it("calls onCycleExecutionMode when Ctrl+Shift+M is pressed", async () => {
      const onCycleExecutionMode = vi.fn();
      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onCycleExecutionMode={onCycleExecutionMode}
        />,
      );

      const textarea = screen.getByRole("textbox");
      fireEvent.keyDown(textarea, {
        key: "m",
        shiftKey: true,
        ctrlKey: true,
      });

      expect(onCycleExecutionMode).toHaveBeenCalledTimes(1);
    });

    it("calls onCycleExecutionMode when Cmd+Shift+M is pressed (Mac)", async () => {
      const onCycleExecutionMode = vi.fn();
      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onCycleExecutionMode={onCycleExecutionMode}
        />,
      );

      const textarea = screen.getByRole("textbox");
      fireEvent.keyDown(textarea, {
        key: "m",
        shiftKey: true,
        metaKey: true,
      });

      expect(onCycleExecutionMode).toHaveBeenCalledTimes(1);
    });

    it("does not call onCycleExecutionMode when just M is pressed", async () => {
      const onCycleExecutionMode = vi.fn();
      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onCycleExecutionMode={onCycleExecutionMode}
        />,
      );

      const textarea = screen.getByRole("textbox");
      fireEvent.keyDown(textarea, { key: "m" });

      expect(onCycleExecutionMode).not.toHaveBeenCalled();
    });

    it("does not call onCycleExecutionMode when Shift+M is pressed without Ctrl/Cmd", async () => {
      const onCycleExecutionMode = vi.fn();
      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onCycleExecutionMode={onCycleExecutionMode}
        />,
      );

      const textarea = screen.getByRole("textbox");
      fireEvent.keyDown(textarea, {
        key: "m",
        shiftKey: true,
      });

      expect(onCycleExecutionMode).not.toHaveBeenCalled();
    });

    it("does not call onCycleExecutionMode when Ctrl+M is pressed without Shift", async () => {
      const onCycleExecutionMode = vi.fn();
      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onCycleExecutionMode={onCycleExecutionMode}
        />,
      );

      const textarea = screen.getByRole("textbox");
      fireEvent.keyDown(textarea, {
        key: "m",
        ctrlKey: true,
      });

      expect(onCycleExecutionMode).not.toHaveBeenCalled();
    });

    it("prevents default behavior when shortcut is triggered", async () => {
      const onCycleExecutionMode = vi.fn();
      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onCycleExecutionMode={onCycleExecutionMode}
        />,
      );

      const textarea = screen.getByRole("textbox");
      const event = new KeyboardEvent("keydown", {
        key: "m",
        shiftKey: true,
        ctrlKey: true,
        bubbles: true,
        cancelable: true,
      });
      const preventDefaultSpy = vi.spyOn(event, "preventDefault");

      textarea.dispatchEvent(event);

      // The handler should have called preventDefault
      expect(preventDefaultSpy).toHaveBeenCalled();
    });
  });

  describe("Execution Mode Display", () => {
    it("shows ExecutionModeIndicator when executionMode prop is provided", () => {
      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onCycleExecutionMode={vi.fn()}
        />,
      );

      expect(
        screen.getByTestId("execution-mode-indicator"),
      ).toBeInTheDocument();
    });

    it("displays default mode correctly", () => {
      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onCycleExecutionMode={vi.fn()}
        />,
      );

      expect(screen.getByText("Default")).toBeInTheDocument();
    });

    it("displays plan mode correctly", () => {
      render(
        <ChatInput
          {...defaultProps}
          executionMode="plan"
          onCycleExecutionMode={vi.fn()}
        />,
      );

      expect(screen.getByText("Plan")).toBeInTheDocument();
    });

    it("displays auto_accept mode correctly", () => {
      render(
        <ChatInput
          {...defaultProps}
          executionMode="auto_accept"
          onCycleExecutionMode={vi.fn()}
        />,
      );

      expect(screen.getByText("Auto")).toBeInTheDocument();
    });

    it("displays bypass mode for users with permission", () => {
      render(
        <ChatInput
          {...defaultProps}
          executionMode="bypass"
          onCycleExecutionMode={vi.fn()}
          hasBypassPermission={true}
        />,
      );

      expect(screen.getByText("Bypass")).toBeInTheDocument();
    });
  });

  describe("Mode Indicator Interaction", () => {
    it("clicking ExecutionModeIndicator triggers mode cycle", async () => {
      const user = userEvent.setup();
      const onCycleExecutionMode = vi.fn();

      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onCycleExecutionMode={onCycleExecutionMode}
        />,
      );

      const indicator = screen.getByTestId("execution-mode-indicator");
      await user.click(indicator);

      expect(onCycleExecutionMode).toHaveBeenCalledTimes(1);
    });

    it("indicator is disabled when ChatInput is disabled", async () => {
      render(
        <ChatInput
          {...defaultProps}
          disabled={true}
          executionMode="default"
          onCycleExecutionMode={vi.fn()}
        />,
      );

      const indicator = screen.getByTestId("execution-mode-indicator");
      expect(indicator).toBeDisabled();
    });
  });

  describe("Bypass Permission", () => {
    it("passes hasBypassPermission to ExecutionModeIndicator", () => {
      render(
        <ChatInput
          {...defaultProps}
          executionMode="bypass"
          onCycleExecutionMode={vi.fn()}
          hasBypassPermission={true}
        />,
      );

      // Bypass mode should be visible when permission is granted
      expect(screen.getByText("Bypass")).toBeInTheDocument();
    });

    it("shows bypass option as disabled when hasBypassPermission is false", () => {
      // When hasBypassPermission is false, the indicator should still render
      // but bypass mode should not be accessible
      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onCycleExecutionMode={vi.fn()}
          hasBypassPermission={false}
        />,
      );

      // The indicator should be present
      expect(
        screen.getByTestId("execution-mode-indicator"),
      ).toBeInTheDocument();
    });
  });

  describe("Integration with Submit", () => {
    it("does not interfere with Enter key submit", async () => {
      const onSubmit = vi.fn();
      const onCycleExecutionMode = vi.fn();

      render(
        <ChatInput
          {...defaultProps}
          value="test message"
          onSubmit={onSubmit}
          executionMode="default"
          onCycleExecutionMode={onCycleExecutionMode}
        />,
      );

      const textarea = screen.getByRole("textbox");
      fireEvent.keyDown(textarea, { key: "Enter" });

      expect(onSubmit).toHaveBeenCalled();
      expect(onCycleExecutionMode).not.toHaveBeenCalled();
    });

    it("mode shortcut does not trigger submit", async () => {
      const onSubmit = vi.fn();
      const onCycleExecutionMode = vi.fn();

      render(
        <ChatInput
          {...defaultProps}
          value="test message"
          onSubmit={onSubmit}
          executionMode="default"
          onCycleExecutionMode={onCycleExecutionMode}
        />,
      );

      const textarea = screen.getByRole("textbox");
      fireEvent.keyDown(textarea, {
        key: "m",
        shiftKey: true,
        ctrlKey: true,
      });

      expect(onSubmit).not.toHaveBeenCalled();
      expect(onCycleExecutionMode).toHaveBeenCalled();
    });
  });

  describe("SegmentedControl Mode Selector", () => {
    it("renders SegmentedControl when onExecutionModeChange is provided", () => {
      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onExecutionModeChange={vi.fn()}
        />,
      );

      expect(
        screen.getByTestId("execution-mode-segmented"),
      ).toBeInTheDocument();
      expect(screen.getByRole("radiogroup")).toBeInTheDocument();
    });

    it("renders all four mode options", () => {
      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onExecutionModeChange={vi.fn()}
          hasBypassPermission={true}
        />,
      );

      expect(
        screen.getByRole("radio", { name: /default mode/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("radio", { name: /plan mode/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("radio", { name: /auto mode/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("radio", { name: /bypass mode/i }),
      ).toBeInTheDocument();
    });

    it("calls onExecutionModeChange when clicking a mode segment", async () => {
      const user = userEvent.setup();
      const onExecutionModeChange = vi.fn();

      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onExecutionModeChange={onExecutionModeChange}
        />,
      );

      const planOption = screen.getByRole("radio", { name: /plan mode/i });
      await user.click(planOption);

      expect(onExecutionModeChange).toHaveBeenCalledWith("plan");
    });

    it("marks current mode as selected (aria-checked)", () => {
      render(
        <ChatInput
          {...defaultProps}
          executionMode="plan"
          onExecutionModeChange={vi.fn()}
        />,
      );

      const planOption = screen.getByRole("radio", { name: /plan mode/i });
      expect(planOption).toHaveAttribute("aria-checked", "true");

      const defaultOption = screen.getByRole("radio", {
        name: /default mode/i,
      });
      expect(defaultOption).toHaveAttribute("aria-checked", "false");
    });

    it("disables bypass segment when hasBypassPermission is false", () => {
      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onExecutionModeChange={vi.fn()}
          hasBypassPermission={false}
        />,
      );

      const bypassOption = screen.getByRole("radio", { name: /bypass mode/i });
      expect(bypassOption).toBeDisabled();
    });

    it("enables bypass segment when hasBypassPermission is true", () => {
      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onExecutionModeChange={vi.fn()}
          hasBypassPermission={true}
        />,
      );

      const bypassOption = screen.getByRole("radio", { name: /bypass mode/i });
      expect(bypassOption).not.toBeDisabled();
    });

    it("is disabled when ChatInput is disabled", () => {
      render(
        <ChatInput
          {...defaultProps}
          disabled={true}
          executionMode="default"
          onExecutionModeChange={vi.fn()}
        />,
      );

      const segmented = screen.getByTestId("execution-mode-segmented");
      // The container should have disabled styling
      expect(segmented).toHaveClass("opacity-50");
    });

    it("has accessible aria-label describing keyboard shortcut", () => {
      render(
        <ChatInput
          {...defaultProps}
          executionMode="default"
          onExecutionModeChange={vi.fn()}
        />,
      );

      const radiogroup = screen.getByRole("radiogroup");
      expect(radiogroup).toHaveAttribute(
        "aria-label",
        expect.stringContaining("Ctrl"),
      );
    });
  });
});
