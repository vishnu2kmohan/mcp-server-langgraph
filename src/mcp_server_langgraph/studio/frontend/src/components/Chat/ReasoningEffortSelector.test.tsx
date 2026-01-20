/**
 * ReasoningEffortSelector Component Tests
 *
 * TDD tests for the reasoning effort/thinking budget selector.
 * Allows users to control the thinking depth for supported models:
 * - low: Quick responses, minimal reasoning
 * - medium: Balanced reasoning (default)
 * - high: Deep reasoning, comprehensive analysis
 *
 * Supported models (via LiteLLM):
 * - Claude Opus 4.5, Sonnet 4 (extended_thinking)
 * - Gemini 2.5 Pro/Flash (thinking_budget)
 * - OpenAI o1/o3 (reasoning_effort)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import {
  ReasoningEffortSelector,
  type ReasoningEffortLevel,
  type ReasoningEffortSelectorProps,
} from "./ReasoningEffortSelector";

describe("ReasoningEffortSelector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  const defaultProps: ReasoningEffortSelectorProps = {
    value: "medium",
    onChange: vi.fn(),
  };

  describe("rendering", () => {
    it("should render the selector container", () => {
      render(<ReasoningEffortSelector {...defaultProps} />);
      expect(
        screen.getByTestId("reasoning-effort-selector"),
      ).toBeInTheDocument();
    });

    it("should display label 'Thinking'", () => {
      render(<ReasoningEffortSelector {...defaultProps} />);
      expect(screen.getByText(/thinking/i)).toBeInTheDocument();
    });

    it("should render all five effort level options", () => {
      render(<ReasoningEffortSelector {...defaultProps} />);
      // All 5 levels: none, low, medium, high, ultra
      expect(
        screen.getByRole("button", { name: /^none$/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /^low$/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /medium/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /^high$/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /ultra/i }),
      ).toBeInTheDocument();
    });

    it("should highlight the selected option", () => {
      render(<ReasoningEffortSelector {...defaultProps} value="high" />);
      const highButton = screen.getByRole("button", { name: /high/i });
      // Selected state is indicated by aria-pressed attribute
      expect(highButton).toHaveAttribute("aria-pressed", "true");
      // Other buttons should not be pressed
      const lowButton = screen.getByRole("button", { name: /^low$/i });
      expect(lowButton).toHaveAttribute("aria-pressed", "false");
    });

    it("should show brain icon", () => {
      render(<ReasoningEffortSelector {...defaultProps} />);
      expect(screen.getByTestId("brain-icon")).toBeInTheDocument();
    });
  });

  describe("selection", () => {
    it("should call onChange with 'low' when low button clicked", () => {
      const onChange = vi.fn();
      render(<ReasoningEffortSelector {...defaultProps} onChange={onChange} />);

      fireEvent.click(screen.getByRole("button", { name: /low/i }));
      expect(onChange).toHaveBeenCalledWith("low");
    });

    it("should call onChange with 'medium' when medium button clicked", () => {
      const onChange = vi.fn();
      render(
        <ReasoningEffortSelector
          {...defaultProps}
          onChange={onChange}
          value="low"
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /medium/i }));
      expect(onChange).toHaveBeenCalledWith("medium");
    });

    it("should call onChange with 'high' when high button clicked", () => {
      const onChange = vi.fn();
      render(<ReasoningEffortSelector {...defaultProps} onChange={onChange} />);

      fireEvent.click(screen.getByRole("button", { name: /high/i }));
      expect(onChange).toHaveBeenCalledWith("high");
    });

    it("should not call onChange when clicking already selected option", () => {
      const onChange = vi.fn();
      render(
        <ReasoningEffortSelector
          {...defaultProps}
          onChange={onChange}
          value="medium"
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /medium/i }));
      expect(onChange).not.toHaveBeenCalled();
    });
  });

  describe("tooltips", () => {
    it("should show tooltip for low option", async () => {
      render(<ReasoningEffortSelector {...defaultProps} />);
      const lowButton = screen.getByRole("button", { name: /low/i });
      expect(lowButton).toHaveAttribute("title");
      expect(lowButton.getAttribute("title")).toMatch(/quick|fast|minimal/i);
    });

    it("should show tooltip for medium option", () => {
      render(<ReasoningEffortSelector {...defaultProps} />);
      const mediumButton = screen.getByRole("button", { name: /medium/i });
      expect(mediumButton.getAttribute("title")).toMatch(/balanced|default/i);
    });

    it("should show tooltip for high option", () => {
      render(<ReasoningEffortSelector {...defaultProps} />);
      const highButton = screen.getByRole("button", { name: /high/i });
      expect(highButton.getAttribute("title")).toMatch(
        /deep|comprehensive|thorough/i,
      );
    });
  });

  describe("disabled state", () => {
    it("should disable all buttons when disabled prop is true", () => {
      render(<ReasoningEffortSelector {...defaultProps} disabled={true} />);

      expect(screen.getByRole("button", { name: /low/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /medium/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /high/i })).toBeDisabled();
    });

    it("should not call onChange when disabled", () => {
      const onChange = vi.fn();
      render(
        <ReasoningEffortSelector
          {...defaultProps}
          onChange={onChange}
          disabled={true}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /high/i }));
      expect(onChange).not.toHaveBeenCalled();
    });

    it("should show disabled styling", () => {
      render(<ReasoningEffortSelector {...defaultProps} disabled={true} />);
      const container = screen.getByTestId("reasoning-effort-selector");
      expect(container).toHaveClass("opacity-50");
    });
  });

  describe("model compatibility", () => {
    it("should show 'Not supported' message when model doesn't support thinking", () => {
      render(
        <ReasoningEffortSelector
          {...defaultProps}
          modelSupportsThinking={false}
        />,
      );
      expect(screen.getByText(/not supported/i)).toBeInTheDocument();
    });

    it("should disable selector when model doesn't support thinking", () => {
      render(
        <ReasoningEffortSelector
          {...defaultProps}
          modelSupportsThinking={false}
        />,
      );
      expect(screen.getByRole("button", { name: /low/i })).toBeDisabled();
    });

    it("should show model name when provided", () => {
      render(
        <ReasoningEffortSelector
          {...defaultProps}
          modelName="claude-opus-4-5-20251101"
        />,
      );
      expect(screen.getByText(/claude-opus/i)).toBeInTheDocument();
    });
  });

  describe("compact mode", () => {
    it("should render in compact mode when compact prop is true", () => {
      render(<ReasoningEffortSelector {...defaultProps} compact={true} />);
      const container = screen.getByTestId("reasoning-effort-selector");
      expect(container).toHaveClass("gap-1");
    });

    it("should show abbreviated labels in compact mode", () => {
      render(<ReasoningEffortSelector {...defaultProps} compact={true} />);
      // Should show L/M/H instead of Low/Medium/High
      expect(screen.getByText("L")).toBeInTheDocument();
      expect(screen.getByText("M")).toBeInTheDocument();
      expect(screen.getByText("H")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have proper role='radiogroup'", () => {
      render(<ReasoningEffortSelector {...defaultProps} />);
      expect(screen.getByRole("radiogroup")).toBeInTheDocument();
    });

    it("should have aria-label for the group", () => {
      render(<ReasoningEffortSelector {...defaultProps} />);
      expect(screen.getByRole("radiogroup")).toHaveAttribute(
        "aria-label",
        "Reasoning effort level",
      );
    });

    it("should mark selected option with aria-checked", () => {
      render(<ReasoningEffortSelector {...defaultProps} value="high" />);
      const highButton = screen.getByRole("button", { name: /high/i });
      expect(highButton).toHaveAttribute("aria-pressed", "true");
    });

    it("should support keyboard navigation", () => {
      const onChange = vi.fn();
      render(<ReasoningEffortSelector {...defaultProps} onChange={onChange} />);

      const mediumButton = screen.getByRole("button", { name: /medium/i });
      mediumButton.focus();

      // Arrow right should move to high
      fireEvent.keyDown(mediumButton, { key: "ArrowRight" });
      expect(onChange).toHaveBeenCalledWith("high");
    });
  });

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(
        <ReasoningEffortSelector {...defaultProps} className="custom-class" />,
      );
      expect(screen.getByTestId("reasoning-effort-selector")).toHaveClass(
        "custom-class",
      );
    });
  });

  describe("effort level descriptions", () => {
    it("should show effort description when showDescription is true", () => {
      render(
        <ReasoningEffortSelector
          {...defaultProps}
          showDescription={true}
          value="high"
        />,
      );
      expect(screen.getByTestId("effort-description")).toBeInTheDocument();
      expect(
        screen.getByText(/comprehensive|thorough|deep/i),
      ).toBeInTheDocument();
    });
  });
});

// Type tests
describe("ReasoningEffortLevel type", () => {
  it("should accept valid effort levels", () => {
    const levels: ReasoningEffortLevel[] = ["low", "medium", "high"];
    expect(levels).toHaveLength(3);
  });
});
