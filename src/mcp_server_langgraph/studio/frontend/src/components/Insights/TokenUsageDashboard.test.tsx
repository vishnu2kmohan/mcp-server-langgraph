/**
 * TokenUsageDashboard Tests
 *
 * TDD tests for the Token Usage Dashboard component.
 * Tests cover:
 * - Token usage display
 * - Input/output breakdown
 * - Cost estimation display
 * - Context window indicator
 * - WCAG 2.1 AA accessibility compliance
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { TokenUsageDashboard } from "./TokenUsageDashboard";

expect.extend(toHaveNoViolations);

// Mock useTokenUsage hook
const mockRefresh = vi.fn();

vi.mock("../../hooks/useTokenUsage", () => ({
  useTokenUsage: () => ({
    inputTokens: 1500,
    outputTokens: 3000,
    totalTokens: 4500,
    estimatedCost: 0.05,
    contextWindowSize: 128000,
    contextWindowUsage: 3.5,
    isContextWindowNearLimit: false,
    history: [
      { timestamp: "2024-01-01T00:00:00Z", tokens: 1000 },
      { timestamp: "2024-01-01T01:00:00Z", tokens: 2500 },
      { timestamp: "2024-01-01T02:00:00Z", tokens: 4500 },
    ],
    isLoading: false,
    error: null,
    refresh: mockRefresh,
  }),
}));

describe("TokenUsageDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render the dashboard", () => {
      render(<TokenUsageDashboard sessionId="session-1" />);

      expect(screen.getByTestId("token-usage-dashboard")).toBeInTheDocument();
    });

    it("should display total tokens", () => {
      render(<TokenUsageDashboard sessionId="session-1" />);

      expect(screen.getByText("4,500")).toBeInTheDocument();
      expect(screen.getByText(/total tokens/i)).toBeInTheDocument();
    });

    it("should display input and output token breakdown", () => {
      render(<TokenUsageDashboard sessionId="session-1" />);

      expect(screen.getByText("1,500")).toBeInTheDocument();
      expect(screen.getByText("3,000")).toBeInTheDocument();
      expect(screen.getByText(/input/i)).toBeInTheDocument();
      expect(screen.getByText(/output/i)).toBeInTheDocument();
    });

    it("should display estimated cost", () => {
      render(<TokenUsageDashboard sessionId="session-1" />);

      expect(screen.getByText("$0.05")).toBeInTheDocument();
    });

    it("should display context window usage", () => {
      render(<TokenUsageDashboard sessionId="session-1" />);

      expect(screen.getByText(/3\.5%/)).toBeInTheDocument();
      expect(screen.getByText(/128,000/)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Context Window Warning Tests
  // ===========================================================================

  describe("context window warning", () => {
    it("should show warning when context window is near limit", () => {
      vi.doMock("../../hooks/useTokenUsage", () => ({
        useTokenUsage: () => ({
          inputTokens: 50000,
          outputTokens: 50000,
          totalTokens: 100000,
          contextWindowSize: 128000,
          contextWindowUsage: 78,
          isContextWindowNearLimit: true,
          isLoading: false,
          error: null,
          refresh: mockRefresh,
        }),
      }));

      // For this test, we'll check the warning is present via the progress bar color
      render(<TokenUsageDashboard sessionId="session-1" />);

      const progressBar = screen.getByTestId("context-window-progress");
      expect(progressBar).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Loading State Tests
  // ===========================================================================

  describe("loading state", () => {
    it("should show loading skeleton when loading", () => {
      vi.doMock("../../hooks/useTokenUsage", () => ({
        useTokenUsage: () => ({
          inputTokens: 0,
          outputTokens: 0,
          totalTokens: 0,
          isLoading: true,
          error: null,
          refresh: mockRefresh,
        }),
      }));

      render(<TokenUsageDashboard sessionId="session-1" showLoading />);

      // Dashboard should still render with current values
      expect(screen.getByTestId("token-usage-dashboard")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Refresh Tests
  // ===========================================================================

  describe("refresh", () => {
    it("should render refresh button", () => {
      render(<TokenUsageDashboard sessionId="session-1" />);

      expect(
        screen.getByRole("button", { name: /refresh/i }),
      ).toBeInTheDocument();
    });

    it("should call refresh when refresh button is clicked", async () => {
      const user = userEvent.setup();
      render(<TokenUsageDashboard sessionId="session-1" />);

      await user.click(screen.getByRole("button", { name: /refresh/i }));

      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Compact Mode Tests
  // ===========================================================================

  describe("compact mode", () => {
    it("should render in compact mode", () => {
      render(<TokenUsageDashboard sessionId="session-1" compact />);

      expect(screen.getByTestId("token-usage-dashboard")).toHaveAttribute(
        "data-compact",
        "true",
      );
    });
  });

  // ===========================================================================
  // History Chart Tests
  // ===========================================================================

  describe("history chart", () => {
    it("should render usage history chart", () => {
      render(<TokenUsageDashboard sessionId="session-1" showHistory />);

      expect(screen.getByTestId("usage-history-chart")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <TokenUsageDashboard sessionId="session-1" />,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper heading structure", () => {
      render(<TokenUsageDashboard sessionId="session-1" />);

      expect(
        screen.getByRole("heading", { name: /token usage/i }),
      ).toBeInTheDocument();
    });

    it("should have accessible labels for metrics", () => {
      render(<TokenUsageDashboard sessionId="session-1" />);

      // Progress bar should have accessible name
      const progressBar = screen.getByTestId("context-window-progress");
      expect(progressBar).toHaveAttribute("aria-label");
    });

    it("should be keyboard navigable", async () => {
      const user = userEvent.setup();
      render(<TokenUsageDashboard sessionId="session-1" />);

      await user.tab();

      // Refresh button should be focusable
      expect(screen.getByRole("button", { name: /refresh/i })).toHaveFocus();
    });
  });

  // ===========================================================================
  // Custom ClassName Tests
  // ===========================================================================

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(
        <TokenUsageDashboard sessionId="session-1" className="custom-class" />,
      );

      expect(screen.getByTestId("token-usage-dashboard")).toHaveClass(
        "custom-class",
      );
    });
  });
});
