/**
 * TokenUsageDisplay Component Tests
 *
 * Tests for the inline token usage display that shows prompt and completion
 * token counts directly below AI responses.
 *
 * TDD RED Phase: Write failing tests first.
 */

import { render, screen, cleanup } from "@testing-library/react";
import { describe, it, expect, afterEach, vi } from "vitest";
import {
  TokenUsageDisplay,
  type TokenUsageDisplayProps,
} from "./TokenUsageDisplay";

import { TestProvider } from "@/test-utils";

describe("TokenUsageDisplay", () => {
  const defaultProps: TokenUsageDisplayProps = {
    promptTokens: 150,
    completionTokens: 250,
  };

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render token counts", () => {
      render(
        <TestProvider>
          <TokenUsageDisplay {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("token-usage-container")).toBeInTheDocument();
      expect(screen.getByText(/150/)).toBeInTheDocument();
      expect(screen.getByText(/250/)).toBeInTheDocument();
    });

    it("should display total tokens", () => {
      render(
        <TestProvider>
          <TokenUsageDisplay {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/400/)).toBeInTheDocument();
    });

    it("should show labels for token types", () => {
      render(
        <TestProvider>
          <TokenUsageDisplay {...defaultProps} showLabels />
        </TestProvider>,
      );

      expect(screen.getByText(/input/i)).toBeInTheDocument();
      expect(screen.getByText(/output/i)).toBeInTheDocument();
    });
  });

  describe("cost estimation", () => {
    it("should show estimated cost when showCost is true", () => {
      render(
        <TestProvider>
          <TokenUsageDisplay
            {...defaultProps}
            showCost
            modelProvider="openai"
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("estimated-cost")).toBeInTheDocument();
      // Should show dollar amount
      expect(screen.getByText(/\$/)).toBeInTheDocument();
    });

    it("should not show cost when showCost is false", () => {
      render(
        <TestProvider>
          <TokenUsageDisplay {...defaultProps} showCost={false} />
        </TestProvider>,
      );

      expect(screen.queryByTestId("estimated-cost")).not.toBeInTheDocument();
    });

    it("should calculate cost for different providers", () => {
      const { rerender } = render(
        <TestProvider>
          <TokenUsageDisplay
            {...defaultProps}
            showCost
            modelProvider="openai"
          />
        </TestProvider>,
      );

      const openAICost = screen.getByTestId("estimated-cost").textContent;

      rerender(
        <TokenUsageDisplay
          {...defaultProps}
          showCost
          modelProvider="anthropic"
        />,
      );

      const anthropicCost = screen.getByTestId("estimated-cost").textContent;

      // Different providers have different rates
      expect(openAICost).not.toBe(anthropicCost);
    });
  });

  describe("zero tokens", () => {
    it("should handle zero prompt tokens", () => {
      render(
        <TestProvider>
          <TokenUsageDisplay promptTokens={0} completionTokens={100} />
        </TestProvider>,
      );

      // Should render the container with token info
      const container = screen.getByTestId("token-usage-container");
      expect(container).toBeInTheDocument();
      expect(container.textContent).toContain("0");
      expect(container.textContent).toContain("100");
    });

    it("should not render when both are zero", () => {
      render(
        <TestProvider>
          <TokenUsageDisplay promptTokens={0} completionTokens={0} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("token-usage-container"),
      ).not.toBeInTheDocument();
    });
  });

  describe("formatting", () => {
    it("should format large numbers with commas", () => {
      render(
        <TestProvider>
          <TokenUsageDisplay promptTokens={1500} completionTokens={2500} />
        </TestProvider>,
      );

      expect(screen.getByText(/1,500/)).toBeInTheDocument();
      expect(screen.getByText(/2,500/)).toBeInTheDocument();
    });
  });

  describe("compact mode", () => {
    it("should render smaller in compact mode", () => {
      render(
        <TestProvider>
          <TokenUsageDisplay {...defaultProps} compact />
        </TestProvider>,
      );

      const container = screen.getByTestId("token-usage-container");
      expect(container).toHaveClass("text-xs");
    });
  });

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(
        <TestProvider>
          <TokenUsageDisplay {...defaultProps} className="custom-class" />
        </TestProvider>,
      );

      const container = screen.getByTestId("token-usage-container");
      expect(container).toHaveClass("custom-class");
    });
  });
});
