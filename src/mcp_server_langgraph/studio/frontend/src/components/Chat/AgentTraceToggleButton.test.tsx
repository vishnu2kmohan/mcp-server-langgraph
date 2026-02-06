/**
 * AgentTraceToggleButton Component Tests
 *
 * TDD: Tests written FIRST before implementation.
 * This component provides a toggle button for showing/hiding
 * the agent execution trace panel.
 */

import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { AgentTraceToggleButton } from "./AgentTraceToggleButton";

describe("AgentTraceToggleButton", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders button with correct aria-label", () => {
      render(<AgentTraceToggleButton isExpanded={false} onToggle={() => {}} />);

      expect(
        screen.getByRole("button", { name: /toggle agent execution trace/i }),
      ).toBeInTheDocument();
    });

    it("renders GitBranch icon", () => {
      render(<AgentTraceToggleButton isExpanded={false} onToggle={() => {}} />);

      const button = screen.getByRole("button");
      // GitBranch icon from lucide-react
      expect(button.querySelector("svg")).toBeInTheDocument();
    });
  });

  describe("expanded state", () => {
    it("has aria-expanded=true when isExpanded is true", () => {
      render(<AgentTraceToggleButton isExpanded={true} onToggle={() => {}} />);

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-expanded", "true");
    });

    it("has aria-expanded=false when isExpanded is false", () => {
      render(<AgentTraceToggleButton isExpanded={false} onToggle={() => {}} />);

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-expanded", "false");
    });

    it("shows 'Hide execution trace' title when expanded", () => {
      render(<AgentTraceToggleButton isExpanded={true} onToggle={() => {}} />);

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("title", "Hide execution trace");
    });

    it("shows 'Show execution trace' title when collapsed", () => {
      render(<AgentTraceToggleButton isExpanded={false} onToggle={() => {}} />);

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("title", "Show execution trace");
    });

    it("has aria-expanded=true when expanded", () => {
      render(<AgentTraceToggleButton isExpanded={true} onToggle={() => {}} />);

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-expanded", "true");
      expect(button).toHaveAttribute("title", "Hide execution trace");
    });

    it("has aria-expanded=false when collapsed", () => {
      render(<AgentTraceToggleButton isExpanded={false} onToggle={() => {}} />);

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-expanded", "false");
      expect(button).toHaveAttribute("title", "Show execution trace");
    });
  });

  describe("interaction", () => {
    it("calls onToggle when clicked", () => {
      const handleToggle = vi.fn();
      render(
        <AgentTraceToggleButton isExpanded={false} onToggle={handleToggle} />,
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      expect(handleToggle).toHaveBeenCalledTimes(1);
    });

    it("calls onToggle on each click", () => {
      const handleToggle = vi.fn();
      render(
        <AgentTraceToggleButton isExpanded={false} onToggle={handleToggle} />,
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);
      fireEvent.click(button);
      fireEvent.click(button);

      expect(handleToggle).toHaveBeenCalledTimes(3);
    });
  });

  describe("accessibility", () => {
    it("is focusable", () => {
      render(<AgentTraceToggleButton isExpanded={false} onToggle={() => {}} />);

      const button = screen.getByRole("button");
      button.focus();

      expect(document.activeElement).toBe(button);
    });
  });
});
