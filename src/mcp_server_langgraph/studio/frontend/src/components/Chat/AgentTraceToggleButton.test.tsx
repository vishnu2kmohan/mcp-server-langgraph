/**
 * AgentTraceToggleButton Component Tests
 *
 * TDD: Tests written FIRST before implementation.
 * This component provides a toggle button for showing/hiding
 * the agent execution trace panel.
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AgentTraceToggleButton } from "./AgentTraceToggleButton";

describe("AgentTraceToggleButton", () => {
  describe("rendering", () => {
    it("renders button with correct aria-label", () => {
      render(<AgentTraceToggleButton isExpanded={false} onToggle={() => {}} />);

      expect(
        screen.getByRole("button", { name: /toggle agent execution trace/i })
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

    it("applies active styling when expanded", () => {
      render(<AgentTraceToggleButton isExpanded={true} onToggle={() => {}} />);

      const button = screen.getByRole("button");
      expect(button).toHaveClass("bg-blue-100");
      expect(button).toHaveClass("text-blue-600");
    });

    it("applies inactive styling when collapsed", () => {
      render(<AgentTraceToggleButton isExpanded={false} onToggle={() => {}} />);

      const button = screen.getByRole("button");
      expect(button).toHaveClass("text-gray-400");
      expect(button).not.toHaveClass("bg-blue-100");
    });
  });

  describe("interaction", () => {
    it("calls onToggle when clicked", () => {
      const handleToggle = vi.fn();
      render(
        <AgentTraceToggleButton isExpanded={false} onToggle={handleToggle} />
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      expect(handleToggle).toHaveBeenCalledTimes(1);
    });

    it("calls onToggle on each click", () => {
      const handleToggle = vi.fn();
      render(
        <AgentTraceToggleButton isExpanded={false} onToggle={handleToggle} />
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
