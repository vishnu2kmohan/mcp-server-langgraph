/**
 * StatusBar Indicators Tests
 *
 * Tests for connection status, agent status, model indicator, token count,
 * model provider, context-aware status, and user indicator (deprecated).
 *
 * Split from StatusBar.test.tsx for memory optimization.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";

import { TestProvider } from "@/test-utils";
import { mockFeatureFlagToggle } from "./StatusBar.fixtures";
import { StatusBar } from "../StatusBar";

// Apply shared mocks
mockFeatureFlagToggle();

describe("StatusBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("connection status", () => {
    it("should show connected indicator when connected", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="connected" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-success-9");
    });

    it("should show disconnected indicator when disconnected", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="disconnected" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-error-9");
    });

    it("should show connecting indicator when connecting", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="connecting" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-warning-9");
    });

    it("should hide connection indicator when status is undefined", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("connection-indicator"),
      ).not.toBeInTheDocument();
    });
  });

  describe("agent status", () => {
    it("should display agent status when provided", () => {
      render(
        <TestProvider>
          <StatusBar agentStatus="Thinking..." />
        </TestProvider>,
      );

      expect(screen.getByText("Thinking...")).toBeInTheDocument();
    });

    it("should not display agent status section when not provided", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.queryByTestId("agent-status")).not.toBeInTheDocument();
    });
  });

  describe("model indicator", () => {
    it("should display model name when provided", () => {
      render(
        <TestProvider>
          <StatusBar modelName="claude-3-opus" />
        </TestProvider>,
      );

      expect(screen.getByTestId("model-indicator")).toBeInTheDocument();
      expect(screen.getByText("claude-3-opus")).toBeInTheDocument();
    });

    it("should not display model indicator when not provided", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.queryByTestId("model-indicator")).not.toBeInTheDocument();
    });
  });

  describe("token count", () => {
    it("should display token count when provided", () => {
      render(
        <TestProvider>
          <StatusBar tokenCount={1234} />
        </TestProvider>,
      );

      expect(screen.getByTestId("token-count")).toBeInTheDocument();
      expect(screen.getByText("1,234 tokens")).toBeInTheDocument();
    });

    it("should display zero token count", () => {
      render(
        <TestProvider>
          <StatusBar tokenCount={0} />
        </TestProvider>,
      );

      expect(screen.getByTestId("token-count")).toBeInTheDocument();
      expect(screen.getByText("0 tokens")).toBeInTheDocument();
    });

    it("should not display token count when not provided", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.queryByTestId("token-count")).not.toBeInTheDocument();
    });

    it("should display cost when costBreakdown is provided", () => {
      render(
        <TestProvider>
          <StatusBar
            tokenCount={1500}
            costBreakdown={{ estimatedCostUsd: 0.0234 }}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("token-count")).toBeInTheDocument();
      // Costs >= 0.01 are formatted with 2 decimal places
      expect(screen.getByText(/\$0\.02/)).toBeInTheDocument();
    });

    it("should format low costs with 4 decimal places", () => {
      render(
        <TestProvider>
          <StatusBar
            tokenCount={100}
            costBreakdown={{ estimatedCostUsd: 0.0001 }}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/\$0\.0001/)).toBeInTheDocument();
    });

    it("should include token breakdown in title attribute", () => {
      render(
        <TestProvider>
          <StatusBar
            tokenCount={1500}
            tokenBreakdown={{
              promptTokens: 1000,
              completionTokens: 500,
              totalTokens: 1500,
            }}
          />
        </TestProvider>,
      );

      const tokenElement = screen.getByTestId("token-count");
      expect(tokenElement.getAttribute("title")).toContain(
        "Input: 1,000 tokens",
      );
      expect(tokenElement.getAttribute("title")).toContain(
        "Output: 500 tokens",
      );
      expect(tokenElement.getAttribute("title")).toContain(
        "Total: 1,500 tokens",
      );
    });

    it("should include per-model breakdown in title attribute when costBreakdown.byModel is provided", () => {
      render(
        <TestProvider>
          <StatusBar
            tokenCount={2500}
            tokenBreakdown={{
              promptTokens: 1500,
              completionTokens: 1000,
              totalTokens: 2500,
            }}
            costBreakdown={{
              estimatedCostUsd: 0.0345,
              byModel: {
                "claude-3-opus": { tokens: 1500, cost: 0.025 },
                "claude-3-sonnet": { tokens: 1000, cost: 0.0095 },
              },
            }}
          />
        </TestProvider>,
      );

      const tokenElement = screen.getByTestId("token-count");
      const title = tokenElement.getAttribute("title") ?? "";

      // Should include per-model breakdown section
      expect(title).toContain("By model:");
      expect(title).toContain("claude-3-opus");
      expect(title).toContain("1,500 tokens");
      expect(title).toContain("$0.03"); // cost for opus (rounded from 0.025)
      expect(title).toContain("claude-3-sonnet");
      expect(title).toContain("1,000 tokens");
    });

    it("should show estimated cost in title when costBreakdown is provided", () => {
      render(
        <TestProvider>
          <StatusBar
            tokenCount={1000}
            costBreakdown={{
              estimatedCostUsd: 0.0156,
            }}
          />
        </TestProvider>,
      );

      const tokenElement = screen.getByTestId("token-count");
      const title = tokenElement.getAttribute("title") ?? "";

      expect(title).toContain("Estimated cost:");
      expect(title).toContain("$0.02"); // rounded from 0.0156
    });
  });

  describe("model provider", () => {
    it("should apply provider color class for openai", () => {
      render(
        <TestProvider>
          <StatusBar modelName="gpt-4" modelProvider="openai" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("model-indicator");
      // Radix step 11 for text per design system
      expect(indicator).toHaveClass("text-success-11");
    });

    it("should apply provider color class for anthropic", () => {
      render(
        <TestProvider>
          <StatusBar modelName="claude-3" modelProvider="anthropic" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("model-indicator");
      // Radix step 11 for text per design system
      expect(indicator).toHaveClass("text-grafana-11");
    });

    it("should apply provider color class for google", () => {
      render(
        <TestProvider>
          <StatusBar modelName="gemini-2.5" modelProvider="google" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("model-indicator");
      // Radix step 11 for text per design system
      expect(indicator).toHaveClass("text-primary-11");
    });

    it("should include provider in title", () => {
      render(
        <TestProvider>
          <StatusBar modelName="gpt-4" modelProvider="openai" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("model-indicator");
      expect(indicator.getAttribute("title")).toBe("Model: gpt-4 (openai)");
    });
  });

  // =============================================================================
  // Context-Aware Status (NEW - TDD RED Phase)
  // ADR: StatusBar should not show static "Ready" but derive context from activity
  // =============================================================================
  describe("context-aware status", () => {
    it("should NOT display static 'Ready' by default - derive from connection state", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="connected" />
        </TestProvider>,
      );

      // When connected with no activity, show "Connected" not "Ready"
      expect(screen.queryByText("Ready")).not.toBeInTheDocument();
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    it("should show 'Connecting...' when connection status is connecting", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="connecting" />
        </TestProvider>,
      );

      expect(screen.getByText("Connecting...")).toBeInTheDocument();
    });

    it("should show 'Disconnected' when connection status is disconnected", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="disconnected" />
        </TestProvider>,
      );

      expect(screen.getByText("Disconnected")).toBeInTheDocument();
    });

    it("should show 'Connection Error' when connection status is error", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="error" />
        </TestProvider>,
      );

      expect(screen.getByText("Connection Error")).toBeInTheDocument();
    });

    it("should prioritize agentStatus over connection-derived status", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="connected" agentStatus="Analyzing..." />
        </TestProvider>,
      );

      // Agent status should replace connection status text
      expect(screen.queryByText("Connected")).not.toBeInTheDocument();
      expect(screen.getByText("Analyzing...")).toBeInTheDocument();
    });

    it("should show pending approvals count in status when pendingApprovals > 0", () => {
      render(
        <TestProvider>
          <StatusBar
            connectionStatus="connected"
            pendingApprovals={3}
            onPendingApprovalsClick={() => {}}
          />
        </TestProvider>,
      );

      // Context-aware: Show that action is needed
      expect(screen.getByText(/3 approvals needed/i)).toBeInTheDocument();
    });

    it("should show agent count in status when agents are running", () => {
      render(
        <TestProvider>
          <StatusBar
            connectionStatus="connected"
            agentCount={2}
            onAgentQueueToggle={() => {}}
          />
        </TestProvider>,
      );

      // Context-aware: Show running agents info
      expect(screen.getByText(/2 agents running/i)).toBeInTheDocument();
    });

    it("should show combined context when multiple activities are happening", () => {
      render(
        <TestProvider>
          <StatusBar
            connectionStatus="connected"
            agentCount={2}
            pendingApprovals={1}
            onAgentQueueToggle={() => {}}
            onPendingApprovalsClick={() => {}}
          />
        </TestProvider>,
      );

      // Should indicate both agents running and approval needed
      const statusBar = screen.getByTestId("status-bar");
      expect(statusBar.textContent).toMatch(/agent/i);
      expect(statusBar.textContent).toMatch(/approval/i);
    });

    it("should show 'Idle' when connected with no activity (fallback from Ready)", () => {
      // When no specific activity, "Idle" is clearer than "Ready"
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      // Default state without connection info should show Idle
      expect(screen.queryByText("Ready")).not.toBeInTheDocument();
      expect(screen.getByText("Idle")).toBeInTheDocument();
    });
  });

  // =============================================================================
  // User Indicator REMOVED - Redundant with top-bar
  // =============================================================================
  describe("user indicator (DEPRECATED)", () => {
    it("should NOT display user indicator - redundant with top-bar", () => {
      // userName prop is deprecated - user info is in the top-bar
      render(
        <TestProvider>
          <StatusBar userName="alice" />
        </TestProvider>,
      );

      expect(screen.queryByTestId("user-indicator")).not.toBeInTheDocument();
      expect(screen.queryByText("alice")).not.toBeInTheDocument();
    });
  });
});
