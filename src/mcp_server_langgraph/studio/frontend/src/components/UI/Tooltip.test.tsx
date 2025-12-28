/**
 * Tooltip Component Tests
 *
 * TDD: Tests written FIRST (RED phase)
 *
 * The Tooltip component should:
 * 1. Show tooltip content on hover
 * 2. Hide tooltip when mouse leaves
 * 3. Support different positions (top, right, bottom, left)
 * 4. Have a delay before showing
 * 5. Be accessible with proper aria attributes
 */

import { render, screen, waitFor, act, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { Tooltip } from "./Tooltip";

describe("Tooltip", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("Basic Behavior", () => {
    it("renders children without tooltip initially", () => {
      render(
        <Tooltip content="Tooltip text">
          <button>Hover me</button>
        </Tooltip>,
      );

      expect(screen.getByRole("button")).toBeInTheDocument();
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    });

    it("shows tooltip on hover after delay", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(
        <Tooltip content="Tooltip text" delay={200}>
          <button>Hover me</button>
        </Tooltip>,
      );

      await user.hover(screen.getByRole("button"));

      // Tooltip not visible immediately
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();

      // Advance past delay
      await act(async () => {
        vi.advanceTimersByTime(250);
      });

      expect(screen.getByRole("tooltip")).toHaveTextContent("Tooltip text");
    });

    it("hides tooltip when mouse leaves", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(
        <Tooltip content="Tooltip text" delay={0}>
          <button>Hover me</button>
        </Tooltip>,
      );

      const button = screen.getByRole("button");
      await user.hover(button);

      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      expect(screen.getByRole("tooltip")).toBeInTheDocument();

      await user.unhover(button);

      await waitFor(() => {
        expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      });
    });

    it("does not show tooltip when disabled", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(
        <Tooltip content="Tooltip text" disabled delay={0}>
          <button>Hover me</button>
        </Tooltip>,
      );

      await user.hover(screen.getByRole("button"));

      await act(async () => {
        vi.advanceTimersByTime(100);
      });

      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    });
  });

  describe("Positioning", () => {
    it("positions tooltip on top by default", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(
        <Tooltip content="Tooltip text" delay={0}>
          <button>Hover me</button>
        </Tooltip>,
      );

      await user.hover(screen.getByRole("button"));

      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      const tooltip = screen.getByRole("tooltip");
      expect(tooltip).toHaveClass("tooltip-top");
    });

    it("supports bottom position", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(
        <Tooltip content="Tooltip text" position="bottom" delay={0}>
          <button>Hover me</button>
        </Tooltip>,
      );

      await user.hover(screen.getByRole("button"));

      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      const tooltip = screen.getByRole("tooltip");
      expect(tooltip).toHaveClass("tooltip-bottom");
    });

    it("supports left position", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(
        <Tooltip content="Tooltip text" position="left" delay={0}>
          <button>Hover me</button>
        </Tooltip>,
      );

      await user.hover(screen.getByRole("button"));

      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      const tooltip = screen.getByRole("tooltip");
      expect(tooltip).toHaveClass("tooltip-left");
    });

    it("supports right position", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(
        <Tooltip content="Tooltip text" position="right" delay={0}>
          <button>Hover me</button>
        </Tooltip>,
      );

      await user.hover(screen.getByRole("button"));

      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      const tooltip = screen.getByRole("tooltip");
      expect(tooltip).toHaveClass("tooltip-right");
    });
  });

  describe("Rich Content", () => {
    it("supports JSX content", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(
        <Tooltip
          content={
            <div>
              <strong>Title</strong>
              <p>Description</p>
            </div>
          }
          delay={0}
        >
          <button>Hover me</button>
        </Tooltip>,
      );

      await user.hover(screen.getByRole("button"));

      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      expect(screen.getByRole("tooltip")).toContainHTML(
        "<strong>Title</strong>",
      );
    });
  });

  describe("Accessibility", () => {
    it("has aria-describedby linking trigger to tooltip", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(
        <Tooltip content="Tooltip text" delay={0}>
          <button>Hover me</button>
        </Tooltip>,
      );

      const button = screen.getByRole("button");
      await user.hover(button);

      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      const tooltip = screen.getByRole("tooltip");
      expect(button).toHaveAttribute("aria-describedby", tooltip.id);
    });

    it("shows tooltip on focus for keyboard users", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(
        <Tooltip content="Tooltip text" delay={0}>
          <button>Focus me</button>
        </Tooltip>,
      );

      await user.tab();

      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      expect(screen.getByRole("tooltip")).toBeInTheDocument();
    });

    it("hides tooltip on blur", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(
        <>
          <Tooltip content="Tooltip text" delay={0}>
            <button>Focus me</button>
          </Tooltip>
          <button>Other button</button>
        </>,
      );

      // Focus the tooltip trigger
      await user.tab();

      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      expect(screen.getByRole("tooltip")).toBeInTheDocument();

      // Tab away
      await user.tab();

      await waitFor(() => {
        expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      });
    });
  });

  describe("Custom Styling", () => {
    it("applies custom className to tooltip", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(
        <Tooltip content="Tooltip text" className="custom-tooltip" delay={0}>
          <button>Hover me</button>
        </Tooltip>,
      );

      await user.hover(screen.getByRole("button"));

      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      expect(screen.getByRole("tooltip")).toHaveClass("custom-tooltip");
    });
  });
});
