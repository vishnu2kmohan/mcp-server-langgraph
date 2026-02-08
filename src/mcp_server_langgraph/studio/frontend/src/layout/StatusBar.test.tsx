/**
 * StatusBar Tests
 *
 * TDD tests for the extracted StatusBar component.
 * Tests status display, keyboard shortcuts, and feature flag toggle.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);
import { StatusBar } from "./StatusBar";

import { TestProvider } from "@/test-utils";

// Mock the FeatureFlagToggle component
vi.mock("./FeatureFlagToggle", () => ({
  FeatureFlagToggle: ({ isDev }: { isDev: boolean }) => (
    <div data-testid="feature-flag-toggle" data-is-dev={isDev}>
      Feature Flag Toggle
    </div>
  ),
}));

describe("StatusBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.getByTestId("status-bar")).toBeInTheDocument();
    });

    it("should display Idle status by default (context-aware)", () => {
      // StatusBar now derives status from context instead of static "Ready"
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.getByText("Idle")).toBeInTheDocument();
    });

    it("should render FeatureFlagToggle", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.getByTestId("feature-flag-toggle")).toBeInTheDocument();
    });
  });

  describe("keyboard shortcuts", () => {
    it("should display command palette shortcut", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.getByText("⌘K Command Palette")).toBeInTheDocument();
    });

    it("should display toggle canvas shortcut", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.getByText("⌘/ Toggle Canvas")).toBeInTheDocument();
    });
  });

  describe("custom status", () => {
    it("should display custom status when provided", () => {
      render(
        <TestProvider>
          <StatusBar status="Loading..." />
        </TestProvider>,
      );

      expect(screen.getByText("Loading...")).toBeInTheDocument();
      expect(screen.queryByText("Ready")).not.toBeInTheDocument();
    });
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

  describe("styling", () => {
    it("should apply custom className", () => {
      render(
        <TestProvider>
          <StatusBar className="custom-class" />
        </TestProvider>,
      );

      expect(screen.getByTestId("status-bar")).toHaveClass("custom-class");
    });

    it("should have proper dark mode classes", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      const statusBar = screen.getByTestId("status-bar");
      // Uses semantic neutral classes that adapt to dark mode via CSS variables
      expect(statusBar).toHaveClass("bg-neutral-2", "border-neutral-5");
    });
  });

  describe("error state", () => {
    it("should show error indicator when connectionStatus is error", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="error" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-error-9");
    });

    it("should display error message when provided", () => {
      render(
        <TestProvider>
          <StatusBar errorMessage="Connection failed" />
        </TestProvider>,
      );

      expect(screen.getByTestId("error-message")).toBeInTheDocument();
      expect(screen.getByText("Connection failed")).toBeInTheDocument();
    });

    it("should have error styling on error message", () => {
      render(
        <TestProvider>
          <StatusBar errorMessage="Something went wrong" />
        </TestProvider>,
      );

      const errorElement = screen.getByTestId("error-message");
      // Radix step 11 for text per design system
      expect(errorElement).toHaveClass("text-error-11");
    });

    it("should not display error message when not provided", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.queryByTestId("error-message")).not.toBeInTheDocument();
    });

    it("should show both connection error indicator and error message", () => {
      render(
        <TestProvider>
          <StatusBar
            connectionStatus="error"
            errorMessage="Server unreachable"
          />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toHaveClass("bg-error-9");
      expect(screen.getByText("Server unreachable")).toBeInTheDocument();
    });
  });

  describe("agent task queue toggle", () => {
    it("should display agent queue button when agentCount is provided", () => {
      render(
        <TestProvider>
          <StatusBar agentCount={3} onAgentQueueToggle={() => {}} />
        </TestProvider>,
      );

      const button = screen.getByTestId("agent-queue-toggle");
      expect(button).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("should not display agent queue button when agentCount is 0", () => {
      render(
        <TestProvider>
          <StatusBar agentCount={0} onAgentQueueToggle={() => {}} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("agent-queue-toggle"),
      ).not.toBeInTheDocument();
    });

    it("should not display agent queue button when agentCount is undefined", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("agent-queue-toggle"),
      ).not.toBeInTheDocument();
    });

    it("should call onAgentQueueToggle when button is clicked", async () => {
      const handleToggle = vi.fn();
      render(
        <TestProvider>
          <StatusBar agentCount={2} onAgentQueueToggle={handleToggle} />
        </TestProvider>,
      );

      const button = screen.getByTestId("agent-queue-toggle");
      await button.click();

      expect(handleToggle).toHaveBeenCalledTimes(1);
    });

    it("should show active state when agentQueueOpen is true", () => {
      render(
        <TestProvider>
          <StatusBar
            agentCount={1}
            onAgentQueueToggle={() => {}}
            agentQueueOpen={true}
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("agent-queue-toggle");
      expect(button).toHaveClass("bg-primary-3");
    });

    it("should have accessible label for agent queue button", () => {
      render(
        <TestProvider>
          <StatusBar agentCount={5} onAgentQueueToggle={() => {}} />
        </TestProvider>,
      );

      const button = screen.getByTestId("agent-queue-toggle");
      expect(button).toHaveAttribute(
        "aria-label",
        "Toggle agent task queue (5 agents)",
      );
    });
  });

  describe("pending approvals indicator", () => {
    it("should display pending approvals button when pendingApprovals > 0", () => {
      render(
        <TestProvider>
          <StatusBar pendingApprovals={3} onPendingApprovalsClick={() => {}} />
        </TestProvider>,
      );

      const button = screen.getByTestId("pending-approvals-indicator");
      expect(button).toBeInTheDocument();
      expect(screen.getByText("3 pending")).toBeInTheDocument();
    });

    it("should not display pending approvals when pendingApprovals is 0", () => {
      render(
        <TestProvider>
          <StatusBar pendingApprovals={0} onPendingApprovalsClick={() => {}} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("pending-approvals-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should not display pending approvals when pendingApprovals is undefined", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("pending-approvals-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should call onPendingApprovalsClick when button is clicked", async () => {
      const handleClick = vi.fn();
      render(
        <TestProvider>
          <StatusBar
            pendingApprovals={2}
            onPendingApprovalsClick={handleClick}
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("pending-approvals-indicator");
      await button.click();

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("should have amber styling for pending approvals indicator", () => {
      render(
        <TestProvider>
          <StatusBar pendingApprovals={1} onPendingApprovalsClick={() => {}} />
        </TestProvider>,
      );

      const button = screen.getByTestId("pending-approvals-indicator");
      expect(button).toHaveClass("bg-warning-3");
    });

    it("should show active state when approvalsPanelOpen is true", () => {
      render(
        <TestProvider>
          <StatusBar
            pendingApprovals={1}
            onPendingApprovalsClick={() => {}}
            approvalsPanelOpen={true}
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("pending-approvals-indicator");
      expect(button).toHaveClass("bg-warning-6");
    });

    it("should have accessible aria-label for pending approvals button", () => {
      render(
        <TestProvider>
          <StatusBar pendingApprovals={5} onPendingApprovalsClick={() => {}} />
        </TestProvider>,
      );

      const button = screen.getByTestId("pending-approvals-indicator");
      expect(button).toHaveAttribute(
        "aria-label",
        "View 5 pending agent approvals",
      );
    });

    it("should display singular text for 1 pending approval", () => {
      render(
        <TestProvider>
          <StatusBar pendingApprovals={1} onPendingApprovalsClick={() => {}} />
        </TestProvider>,
      );

      expect(screen.getByText("1 pending")).toBeInTheDocument();
    });
  });

  describe("DevTools toggle", () => {
    it("should display DevTools toggle button when onDevToolsToggle is provided", () => {
      render(
        <TestProvider>
          <StatusBar onDevToolsToggle={() => {}} />
        </TestProvider>,
      );

      const button = screen.getByTestId("devtools-toggle");
      expect(button).toBeInTheDocument();
    });

    it("should not display DevTools toggle when onDevToolsToggle is not provided", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.queryByTestId("devtools-toggle")).not.toBeInTheDocument();
    });

    it("should call onDevToolsToggle when button is clicked", async () => {
      const handleToggle = vi.fn();
      render(
        <TestProvider>
          <StatusBar onDevToolsToggle={handleToggle} />
        </TestProvider>,
      );

      const button = screen.getByTestId("devtools-toggle");
      await button.click();

      expect(handleToggle).toHaveBeenCalledTimes(1);
    });

    it("should show active state when DevTools is open", () => {
      render(
        <TestProvider>
          <StatusBar onDevToolsToggle={() => {}} devToolsCollapsed={false} />
        </TestProvider>,
      );

      const button = screen.getByTestId("devtools-toggle");
      expect(button).toHaveClass("bg-primary-3");
    });

    it("should not show active state when DevTools is collapsed", () => {
      render(
        <TestProvider>
          <StatusBar onDevToolsToggle={() => {}} devToolsCollapsed={true} />
        </TestProvider>,
      );

      const button = screen.getByTestId("devtools-toggle");
      expect(button).not.toHaveClass("bg-primary-3");
    });

    it("should have accessible aria-label for collapsed state", () => {
      render(
        <TestProvider>
          <StatusBar onDevToolsToggle={() => {}} devToolsCollapsed={true} />
        </TestProvider>,
      );

      const button = screen.getByTestId("devtools-toggle");
      expect(button).toHaveAttribute("aria-label", "Open DevTools");
    });

    it("should have accessible aria-label for open state", () => {
      render(
        <TestProvider>
          <StatusBar onDevToolsToggle={() => {}} devToolsCollapsed={false} />
        </TestProvider>,
      );

      const button = screen.getByTestId("devtools-toggle");
      expect(button).toHaveAttribute("aria-label", "Close DevTools");
    });

    it("should have aria-pressed attribute", () => {
      render(
        <TestProvider>
          <StatusBar onDevToolsToggle={() => {}} devToolsCollapsed={false} />
        </TestProvider>,
      );

      const button = screen.getByTestId("devtools-toggle");
      expect(button).toHaveAttribute("aria-pressed", "true");
    });

    it("should display problem count badge when problemCount > 0", () => {
      render(
        <TestProvider>
          <StatusBar onDevToolsToggle={() => {}} problemCount={5} />
        </TestProvider>,
      );

      const badge = screen.getByTestId("devtools-problem-count");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent("5");
    });

    it("should not display problem count badge when problemCount is 0", () => {
      render(
        <TestProvider>
          <StatusBar onDevToolsToggle={() => {}} problemCount={0} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("devtools-problem-count"),
      ).not.toBeInTheDocument();
    });

    it("should not display problem count badge when problemCount is undefined", () => {
      render(
        <TestProvider>
          <StatusBar onDevToolsToggle={() => {}} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("devtools-problem-count"),
      ).not.toBeInTheDocument();
    });

    it("should display 99+ when problem count exceeds 99", () => {
      render(
        <TestProvider>
          <StatusBar onDevToolsToggle={() => {}} problemCount={150} />
        </TestProvider>,
      );

      const badge = screen.getByTestId("devtools-problem-count");
      expect(badge).toHaveTextContent("99+");
    });

    it("should display DevTools keyboard shortcut", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.getByText("⌘⇧I DevTools")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have role status", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("should have aria-live for status updates", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      const statusBar = screen.getByTestId("status-bar");
      expect(statusBar).toHaveAttribute("aria-live", "polite");
    });

    it("should have no accessibility violations", async () => {
      const { container } = render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  // =============================================================================
  // Reconnection Status (WebSocket reconnection visibility)
  // =============================================================================
  describe("reconnection status", () => {
    it("should show reconnecting indicator when status is connecting and reconnectAttempts > 0", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="connecting" reconnectAttempts={3} />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("reconnecting-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveTextContent("Reconnecting (3)...");
    });

    it("should not show reconnecting indicator when reconnectAttempts is 0", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="connecting" reconnectAttempts={0} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("reconnecting-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should not show reconnecting indicator when status is not connecting", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="connected" reconnectAttempts={3} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("reconnecting-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should have pulsing animation on reconnecting indicator", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="connecting" reconnectAttempts={2} />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("reconnecting-indicator");
      expect(indicator).toHaveClass("animate-pulse");
    });

    it("should have accessible aria-label for reconnecting status", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="connecting" reconnectAttempts={5} />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("reconnecting-indicator");
      expect(indicator).toHaveAttribute(
        "aria-label",
        "Reconnecting, attempt 5",
      );
    });
  });

  // =============================================================================
  // Knowledge Base Status Indicator (Dynamic Context Integration)
  // ADR: Show KB/Semantic context status in StatusBar
  // =============================================================================
  describe("knowledge base status indicator", () => {
    it("should display KB status indicator when kbStatus is provided", () => {
      render(
        <TestProvider>
          <StatusBar kbStatus="ready" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("kb-status-indicator");
      expect(indicator).toBeInTheDocument();
    });

    it("should not display KB status indicator when kbStatus is undefined", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("kb-status-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should show green indicator when kbStatus is ready", () => {
      render(
        <TestProvider>
          <StatusBar kbStatus="ready" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("kb-status-indicator");
      expect(indicator).toHaveClass("bg-success-9");
    });

    it("should show yellow indicator when kbStatus is misconfigured", () => {
      render(
        <TestProvider>
          <StatusBar kbStatus="misconfigured" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("kb-status-indicator");
      expect(indicator).toHaveClass("bg-warning-9");
    });

    it("should show gray indicator when kbStatus is unavailable", () => {
      render(
        <TestProvider>
          <StatusBar kbStatus="unavailable" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("kb-status-indicator");
      expect(indicator).toHaveClass("bg-neutral-4");
    });

    it("should display KB label text with status", () => {
      render(
        <TestProvider>
          <StatusBar kbStatus="ready" />
        </TestProvider>,
      );

      expect(screen.getByText("KB")).toBeInTheDocument();
    });

    it("should show tooltip with kbStatusMessage when provided", () => {
      render(
        <TestProvider>
          <StatusBar
            kbStatus="misconfigured"
            kbStatusMessage="Missing QDRANT_URL configuration"
          />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("kb-status-indicator");
      expect(indicator.closest("[title]")).toHaveAttribute(
        "title",
        expect.stringContaining("Missing QDRANT_URL"),
      );
    });

    it("should show context stats when kbContextStats is provided", () => {
      render(
        <TestProvider>
          <StatusBar
            kbStatus="ready"
            kbContextStats={{
              refsCount: 3,
              tokensUsed: 1500,
              tokenBudget: 2000,
            }}
          />
        </TestProvider>,
      );

      // Should display refs count
      expect(screen.getByText(/3 refs/i)).toBeInTheDocument();
      // Should display token usage
      expect(screen.getByText(/1,500/)).toBeInTheDocument();
    });

    it("should not show context stats when kbContextStats is undefined", () => {
      render(
        <TestProvider>
          <StatusBar kbStatus="ready" />
        </TestProvider>,
      );

      expect(screen.queryByTestId("kb-context-stats")).not.toBeInTheDocument();
    });

    it("should have accessible aria-label for KB indicator", () => {
      render(
        <TestProvider>
          <StatusBar kbStatus="ready" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("kb-status-indicator");
      const container = indicator.closest("[role='status']");
      expect(container).toHaveAttribute(
        "aria-label",
        expect.stringContaining("Knowledge"),
      );
    });

    it("should show token budget usage percentage", () => {
      render(
        <TestProvider>
          <StatusBar
            kbStatus="ready"
            kbContextStats={{
              refsCount: 2,
              tokensUsed: 1500,
              tokenBudget: 2000,
            }}
          />
        </TestProvider>,
      );

      // Should show percentage or fraction
      const statsElement = screen.getByTestId("kb-context-stats");
      expect(statsElement).toHaveAttribute(
        "title",
        expect.stringContaining("75%"),
      );
    });
  });

  // =============================================================================
  // Tooltips (TDD RED - Tests should FAIL initially)
  // =============================================================================
  describe("tooltips", () => {
    /**
     * These tests verify that StatusBar elements have tooltips for better UX.
     * TDD RED Phase: These tests should FAIL until we add title attributes.
     */

    it("should have tooltip on connection indicator", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="connected" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toHaveAttribute(
        "title",
        expect.stringContaining("connected"),
      );
    });

    it("should have tooltip on model indicator", () => {
      render(
        <TestProvider>
          <StatusBar modelName="claude-3-opus" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("model-indicator");
      expect(indicator).toHaveAttribute(
        "title",
        expect.stringContaining("Model"),
      );
    });

    it("should have tooltip on token count indicator", () => {
      render(
        <TestProvider>
          <StatusBar tokenCount={1500} />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("token-count");
      expect(indicator).toHaveAttribute(
        "title",
        expect.stringContaining("token"),
      );
    });

    // User indicator has been removed (redundant with top-bar)
    // This test is intentionally removed as userName prop is deprecated

    it("should have tooltip on agent queue toggle", () => {
      render(
        <TestProvider>
          <StatusBar agentCount={3} onAgentQueueToggle={() => {}} />
        </TestProvider>,
      );

      const toggle = screen.getByRole("button", { name: /agent/i });
      expect(toggle).toHaveAttribute("title", expect.stringContaining("agent"));
    });

    it("should have tooltip on DevTools toggle", () => {
      render(
        <TestProvider>
          <StatusBar onDevToolsToggle={() => {}} />
        </TestProvider>,
      );

      const toggle = screen.getByRole("button", { name: /devtools/i });
      expect(toggle).toHaveAttribute(
        "title",
        expect.stringContaining("DevTools"),
      );
    });

    it("should have tooltip on pending approvals indicator", () => {
      render(
        <TestProvider>
          <StatusBar pendingApprovals={2} onPendingApprovalsClick={() => {}} />
        </TestProvider>,
      );

      const indicator = screen.getByRole("button", { name: /approval/i });
      expect(indicator).toHaveAttribute(
        "title",
        expect.stringContaining("approval"),
      );
    });
  });
});
