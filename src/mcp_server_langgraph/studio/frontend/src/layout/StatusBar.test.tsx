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
      render(<StatusBar />);

      expect(screen.getByTestId("status-bar")).toBeInTheDocument();
    });

    it("should display Idle status by default (context-aware)", () => {
      // StatusBar now derives status from context instead of static "Ready"
      render(<StatusBar />);

      expect(screen.getByText("Idle")).toBeInTheDocument();
    });

    it("should render FeatureFlagToggle", () => {
      render(<StatusBar />);

      expect(screen.getByTestId("feature-flag-toggle")).toBeInTheDocument();
    });
  });

  describe("keyboard shortcuts", () => {
    it("should display command palette shortcut", () => {
      render(<StatusBar />);

      expect(screen.getByText("⌘K Command Palette")).toBeInTheDocument();
    });

    it("should display toggle canvas shortcut", () => {
      render(<StatusBar />);

      expect(screen.getByText("⌘/ Toggle Canvas")).toBeInTheDocument();
    });
  });

  describe("custom status", () => {
    it("should display custom status when provided", () => {
      render(<StatusBar status="Loading..." />);

      expect(screen.getByText("Loading...")).toBeInTheDocument();
      expect(screen.queryByText("Ready")).not.toBeInTheDocument();
    });
  });

  describe("connection status", () => {
    it("should show connected indicator when connected", () => {
      render(<StatusBar connectionStatus="connected" />);

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-success-500");
    });

    it("should show disconnected indicator when disconnected", () => {
      render(<StatusBar connectionStatus="disconnected" />);

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-error-500");
    });

    it("should show connecting indicator when connecting", () => {
      render(<StatusBar connectionStatus="connecting" />);

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-warning-500");
    });

    it("should hide connection indicator when status is undefined", () => {
      render(<StatusBar />);

      expect(
        screen.queryByTestId("connection-indicator"),
      ).not.toBeInTheDocument();
    });
  });

  describe("agent status", () => {
    it("should display agent status when provided", () => {
      render(<StatusBar agentStatus="Thinking..." />);

      expect(screen.getByText("Thinking...")).toBeInTheDocument();
    });

    it("should not display agent status section when not provided", () => {
      render(<StatusBar />);

      expect(screen.queryByTestId("agent-status")).not.toBeInTheDocument();
    });
  });

  describe("model indicator", () => {
    it("should display model name when provided", () => {
      render(<StatusBar modelName="claude-3-opus" />);

      expect(screen.getByTestId("model-indicator")).toBeInTheDocument();
      expect(screen.getByText("claude-3-opus")).toBeInTheDocument();
    });

    it("should not display model indicator when not provided", () => {
      render(<StatusBar />);

      expect(screen.queryByTestId("model-indicator")).not.toBeInTheDocument();
    });
  });

  describe("token count", () => {
    it("should display token count when provided", () => {
      render(<StatusBar tokenCount={1234} />);

      expect(screen.getByTestId("token-count")).toBeInTheDocument();
      expect(screen.getByText("1,234 tokens")).toBeInTheDocument();
    });

    it("should display zero token count", () => {
      render(<StatusBar tokenCount={0} />);

      expect(screen.getByTestId("token-count")).toBeInTheDocument();
      expect(screen.getByText("0 tokens")).toBeInTheDocument();
    });

    it("should not display token count when not provided", () => {
      render(<StatusBar />);

      expect(screen.queryByTestId("token-count")).not.toBeInTheDocument();
    });

    it("should display cost when costBreakdown is provided", () => {
      render(
        <StatusBar
          tokenCount={1500}
          costBreakdown={{ estimatedCostUsd: 0.0234 }}
        />,
      );

      expect(screen.getByTestId("token-count")).toBeInTheDocument();
      // Costs >= 0.01 are formatted with 2 decimal places
      expect(screen.getByText(/\$0\.02/)).toBeInTheDocument();
    });

    it("should format low costs with 4 decimal places", () => {
      render(
        <StatusBar
          tokenCount={100}
          costBreakdown={{ estimatedCostUsd: 0.0001 }}
        />,
      );

      expect(screen.getByText(/\$0\.0001/)).toBeInTheDocument();
    });

    it("should include token breakdown in title attribute", () => {
      render(
        <StatusBar
          tokenCount={1500}
          tokenBreakdown={{
            promptTokens: 1000,
            completionTokens: 500,
            totalTokens: 1500,
          }}
        />,
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
        />,
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
        <StatusBar
          tokenCount={1000}
          costBreakdown={{
            estimatedCostUsd: 0.0156,
          }}
        />,
      );

      const tokenElement = screen.getByTestId("token-count");
      const title = tokenElement.getAttribute("title") ?? "";

      expect(title).toContain("Estimated cost:");
      expect(title).toContain("$0.02"); // rounded from 0.0156
    });
  });

  describe("model provider", () => {
    it("should apply provider color class for openai", () => {
      render(<StatusBar modelName="gpt-4" modelProvider="openai" />);

      const indicator = screen.getByTestId("model-indicator");
      expect(indicator).toHaveClass("text-success-600");
    });

    it("should apply provider color class for anthropic", () => {
      render(<StatusBar modelName="claude-3" modelProvider="anthropic" />);

      const indicator = screen.getByTestId("model-indicator");
      expect(indicator).toHaveClass("text-grafana-600");
    });

    it("should apply provider color class for google", () => {
      render(<StatusBar modelName="gemini-2.5" modelProvider="google" />);

      const indicator = screen.getByTestId("model-indicator");
      expect(indicator).toHaveClass("text-primary-600");
    });

    it("should include provider in title", () => {
      render(<StatusBar modelName="gpt-4" modelProvider="openai" />);

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
      render(<StatusBar connectionStatus="connected" />);

      // When connected with no activity, show "Connected" not "Ready"
      expect(screen.queryByText("Ready")).not.toBeInTheDocument();
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    it("should show 'Connecting...' when connection status is connecting", () => {
      render(<StatusBar connectionStatus="connecting" />);

      expect(screen.getByText("Connecting...")).toBeInTheDocument();
    });

    it("should show 'Disconnected' when connection status is disconnected", () => {
      render(<StatusBar connectionStatus="disconnected" />);

      expect(screen.getByText("Disconnected")).toBeInTheDocument();
    });

    it("should show 'Connection Error' when connection status is error", () => {
      render(<StatusBar connectionStatus="error" />);

      expect(screen.getByText("Connection Error")).toBeInTheDocument();
    });

    it("should prioritize agentStatus over connection-derived status", () => {
      render(
        <StatusBar connectionStatus="connected" agentStatus="Analyzing..." />,
      );

      // Agent status should replace connection status text
      expect(screen.queryByText("Connected")).not.toBeInTheDocument();
      expect(screen.getByText("Analyzing...")).toBeInTheDocument();
    });

    it("should show pending approvals count in status when pendingApprovals > 0", () => {
      render(
        <StatusBar
          connectionStatus="connected"
          pendingApprovals={3}
          onPendingApprovalsClick={() => {}}
        />,
      );

      // Context-aware: Show that action is needed
      expect(screen.getByText(/3 approvals needed/i)).toBeInTheDocument();
    });

    it("should show agent count in status when agents are running", () => {
      render(
        <StatusBar
          connectionStatus="connected"
          agentCount={2}
          onAgentQueueToggle={() => {}}
        />,
      );

      // Context-aware: Show running agents info
      expect(screen.getByText(/2 agents running/i)).toBeInTheDocument();
    });

    it("should show combined context when multiple activities are happening", () => {
      render(
        <StatusBar
          connectionStatus="connected"
          agentCount={2}
          pendingApprovals={1}
          onAgentQueueToggle={() => {}}
          onPendingApprovalsClick={() => {}}
        />,
      );

      // Should indicate both agents running and approval needed
      const statusBar = screen.getByTestId("status-bar");
      expect(statusBar.textContent).toMatch(/agent/i);
      expect(statusBar.textContent).toMatch(/approval/i);
    });

    it("should show 'Idle' when connected with no activity (fallback from Ready)", () => {
      // When no specific activity, "Idle" is clearer than "Ready"
      render(<StatusBar />);

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
      render(<StatusBar userName="alice" />);

      expect(screen.queryByTestId("user-indicator")).not.toBeInTheDocument();
      expect(screen.queryByText("alice")).not.toBeInTheDocument();
    });
  });

  describe("styling", () => {
    it("should apply custom className", () => {
      render(<StatusBar className="custom-class" />);

      expect(screen.getByTestId("status-bar")).toHaveClass("custom-class");
    });

    it("should have proper dark mode classes", () => {
      render(<StatusBar />);

      const statusBar = screen.getByTestId("status-bar");
      expect(statusBar).toHaveClass("dark:bg-gray-800");
    });
  });

  describe("error state", () => {
    it("should show error indicator when connectionStatus is error", () => {
      render(<StatusBar connectionStatus="error" />);

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-error-500");
    });

    it("should display error message when provided", () => {
      render(<StatusBar errorMessage="Connection failed" />);

      expect(screen.getByTestId("error-message")).toBeInTheDocument();
      expect(screen.getByText("Connection failed")).toBeInTheDocument();
    });

    it("should have error styling on error message", () => {
      render(<StatusBar errorMessage="Something went wrong" />);

      const errorElement = screen.getByTestId("error-message");
      expect(errorElement).toHaveClass("text-error-500");
    });

    it("should not display error message when not provided", () => {
      render(<StatusBar />);

      expect(screen.queryByTestId("error-message")).not.toBeInTheDocument();
    });

    it("should show both connection error indicator and error message", () => {
      render(
        <StatusBar
          connectionStatus="error"
          errorMessage="Server unreachable"
        />,
      );

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toHaveClass("bg-error-500");
      expect(screen.getByText("Server unreachable")).toBeInTheDocument();
    });
  });

  describe("agent task queue toggle", () => {
    it("should display agent queue button when agentCount is provided", () => {
      render(<StatusBar agentCount={3} onAgentQueueToggle={() => {}} />);

      const button = screen.getByTestId("agent-queue-toggle");
      expect(button).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("should not display agent queue button when agentCount is 0", () => {
      render(<StatusBar agentCount={0} onAgentQueueToggle={() => {}} />);

      expect(
        screen.queryByTestId("agent-queue-toggle"),
      ).not.toBeInTheDocument();
    });

    it("should not display agent queue button when agentCount is undefined", () => {
      render(<StatusBar />);

      expect(
        screen.queryByTestId("agent-queue-toggle"),
      ).not.toBeInTheDocument();
    });

    it("should call onAgentQueueToggle when button is clicked", async () => {
      const handleToggle = vi.fn();
      render(<StatusBar agentCount={2} onAgentQueueToggle={handleToggle} />);

      const button = screen.getByTestId("agent-queue-toggle");
      await button.click();

      expect(handleToggle).toHaveBeenCalledTimes(1);
    });

    it("should show active state when agentQueueOpen is true", () => {
      render(
        <StatusBar
          agentCount={1}
          onAgentQueueToggle={() => {}}
          agentQueueOpen={true}
        />,
      );

      const button = screen.getByTestId("agent-queue-toggle");
      expect(button).toHaveClass("bg-primary-100");
    });

    it("should have accessible label for agent queue button", () => {
      render(<StatusBar agentCount={5} onAgentQueueToggle={() => {}} />);

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
        <StatusBar pendingApprovals={3} onPendingApprovalsClick={() => {}} />,
      );

      const button = screen.getByTestId("pending-approvals-indicator");
      expect(button).toBeInTheDocument();
      expect(screen.getByText("3 pending")).toBeInTheDocument();
    });

    it("should not display pending approvals when pendingApprovals is 0", () => {
      render(
        <StatusBar pendingApprovals={0} onPendingApprovalsClick={() => {}} />,
      );

      expect(
        screen.queryByTestId("pending-approvals-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should not display pending approvals when pendingApprovals is undefined", () => {
      render(<StatusBar />);

      expect(
        screen.queryByTestId("pending-approvals-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should call onPendingApprovalsClick when button is clicked", async () => {
      const handleClick = vi.fn();
      render(
        <StatusBar
          pendingApprovals={2}
          onPendingApprovalsClick={handleClick}
        />,
      );

      const button = screen.getByTestId("pending-approvals-indicator");
      await button.click();

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("should have amber styling for pending approvals indicator", () => {
      render(
        <StatusBar pendingApprovals={1} onPendingApprovalsClick={() => {}} />,
      );

      const button = screen.getByTestId("pending-approvals-indicator");
      expect(button).toHaveClass("bg-warning-100");
    });

    it("should show active state when approvalsPanelOpen is true", () => {
      render(
        <StatusBar
          pendingApprovals={1}
          onPendingApprovalsClick={() => {}}
          approvalsPanelOpen={true}
        />,
      );

      const button = screen.getByTestId("pending-approvals-indicator");
      expect(button).toHaveClass("bg-warning-200");
    });

    it("should have accessible aria-label for pending approvals button", () => {
      render(
        <StatusBar pendingApprovals={5} onPendingApprovalsClick={() => {}} />,
      );

      const button = screen.getByTestId("pending-approvals-indicator");
      expect(button).toHaveAttribute(
        "aria-label",
        "View 5 pending agent approvals",
      );
    });

    it("should display singular text for 1 pending approval", () => {
      render(
        <StatusBar pendingApprovals={1} onPendingApprovalsClick={() => {}} />,
      );

      expect(screen.getByText("1 pending")).toBeInTheDocument();
    });
  });

  describe("DevTools toggle", () => {
    it("should display DevTools toggle button when onDevToolsToggle is provided", () => {
      render(<StatusBar onDevToolsToggle={() => {}} />);

      const button = screen.getByTestId("devtools-toggle");
      expect(button).toBeInTheDocument();
    });

    it("should not display DevTools toggle when onDevToolsToggle is not provided", () => {
      render(<StatusBar />);

      expect(screen.queryByTestId("devtools-toggle")).not.toBeInTheDocument();
    });

    it("should call onDevToolsToggle when button is clicked", async () => {
      const handleToggle = vi.fn();
      render(<StatusBar onDevToolsToggle={handleToggle} />);

      const button = screen.getByTestId("devtools-toggle");
      await button.click();

      expect(handleToggle).toHaveBeenCalledTimes(1);
    });

    it("should show active state when DevTools is open", () => {
      render(
        <StatusBar onDevToolsToggle={() => {}} devToolsCollapsed={false} />,
      );

      const button = screen.getByTestId("devtools-toggle");
      expect(button).toHaveClass("bg-primary-100");
    });

    it("should not show active state when DevTools is collapsed", () => {
      render(
        <StatusBar onDevToolsToggle={() => {}} devToolsCollapsed={true} />,
      );

      const button = screen.getByTestId("devtools-toggle");
      expect(button).not.toHaveClass("bg-primary-100");
    });

    it("should have accessible aria-label for collapsed state", () => {
      render(
        <StatusBar onDevToolsToggle={() => {}} devToolsCollapsed={true} />,
      );

      const button = screen.getByTestId("devtools-toggle");
      expect(button).toHaveAttribute("aria-label", "Open DevTools");
    });

    it("should have accessible aria-label for open state", () => {
      render(
        <StatusBar onDevToolsToggle={() => {}} devToolsCollapsed={false} />,
      );

      const button = screen.getByTestId("devtools-toggle");
      expect(button).toHaveAttribute("aria-label", "Close DevTools");
    });

    it("should have aria-pressed attribute", () => {
      render(
        <StatusBar onDevToolsToggle={() => {}} devToolsCollapsed={false} />,
      );

      const button = screen.getByTestId("devtools-toggle");
      expect(button).toHaveAttribute("aria-pressed", "true");
    });

    it("should display problem count badge when problemCount > 0", () => {
      render(<StatusBar onDevToolsToggle={() => {}} problemCount={5} />);

      const badge = screen.getByTestId("devtools-problem-count");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent("5");
    });

    it("should not display problem count badge when problemCount is 0", () => {
      render(<StatusBar onDevToolsToggle={() => {}} problemCount={0} />);

      expect(
        screen.queryByTestId("devtools-problem-count"),
      ).not.toBeInTheDocument();
    });

    it("should not display problem count badge when problemCount is undefined", () => {
      render(<StatusBar onDevToolsToggle={() => {}} />);

      expect(
        screen.queryByTestId("devtools-problem-count"),
      ).not.toBeInTheDocument();
    });

    it("should display 99+ when problem count exceeds 99", () => {
      render(<StatusBar onDevToolsToggle={() => {}} problemCount={150} />);

      const badge = screen.getByTestId("devtools-problem-count");
      expect(badge).toHaveTextContent("99+");
    });

    it("should display DevTools keyboard shortcut", () => {
      render(<StatusBar />);

      expect(screen.getByText("⌘⇧I DevTools")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have role status", () => {
      render(<StatusBar />);

      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("should have aria-live for status updates", () => {
      render(<StatusBar />);

      const statusBar = screen.getByTestId("status-bar");
      expect(statusBar).toHaveAttribute("aria-live", "polite");
    });

    it("should have no accessibility violations", async () => {
      const { container } = render(<StatusBar />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  // =============================================================================
  // Reconnection Status (WebSocket reconnection visibility)
  // =============================================================================
  describe("reconnection status", () => {
    it("should show reconnecting indicator when status is connecting and reconnectAttempts > 0", () => {
      render(<StatusBar connectionStatus="connecting" reconnectAttempts={3} />);

      const indicator = screen.getByTestId("reconnecting-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveTextContent("Reconnecting (3)...");
    });

    it("should not show reconnecting indicator when reconnectAttempts is 0", () => {
      render(<StatusBar connectionStatus="connecting" reconnectAttempts={0} />);

      expect(
        screen.queryByTestId("reconnecting-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should not show reconnecting indicator when status is not connecting", () => {
      render(<StatusBar connectionStatus="connected" reconnectAttempts={3} />);

      expect(
        screen.queryByTestId("reconnecting-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should have pulsing animation on reconnecting indicator", () => {
      render(<StatusBar connectionStatus="connecting" reconnectAttempts={2} />);

      const indicator = screen.getByTestId("reconnecting-indicator");
      expect(indicator).toHaveClass("animate-pulse");
    });

    it("should have accessible aria-label for reconnecting status", () => {
      render(<StatusBar connectionStatus="connecting" reconnectAttempts={5} />);

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
      render(<StatusBar kbStatus="ready" />);

      const indicator = screen.getByTestId("kb-status-indicator");
      expect(indicator).toBeInTheDocument();
    });

    it("should not display KB status indicator when kbStatus is undefined", () => {
      render(<StatusBar />);

      expect(
        screen.queryByTestId("kb-status-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should show green indicator when kbStatus is ready", () => {
      render(<StatusBar kbStatus="ready" />);

      const indicator = screen.getByTestId("kb-status-indicator");
      expect(indicator).toHaveClass("bg-success-500");
    });

    it("should show yellow indicator when kbStatus is misconfigured", () => {
      render(<StatusBar kbStatus="misconfigured" />);

      const indicator = screen.getByTestId("kb-status-indicator");
      expect(indicator).toHaveClass("bg-warning-500");
    });

    it("should show gray indicator when kbStatus is unavailable", () => {
      render(<StatusBar kbStatus="unavailable" />);

      const indicator = screen.getByTestId("kb-status-indicator");
      expect(indicator).toHaveClass("bg-gray-400");
    });

    it("should display KB label text with status", () => {
      render(<StatusBar kbStatus="ready" />);

      expect(screen.getByText("KB")).toBeInTheDocument();
    });

    it("should show tooltip with kbStatusMessage when provided", () => {
      render(
        <StatusBar
          kbStatus="misconfigured"
          kbStatusMessage="Missing QDRANT_URL configuration"
        />,
      );

      const indicator = screen.getByTestId("kb-status-indicator");
      expect(indicator.closest("[title]")).toHaveAttribute(
        "title",
        expect.stringContaining("Missing QDRANT_URL"),
      );
    });

    it("should show context stats when kbContextStats is provided", () => {
      render(
        <StatusBar
          kbStatus="ready"
          kbContextStats={{ refsCount: 3, tokensUsed: 1500, tokenBudget: 2000 }}
        />,
      );

      // Should display refs count
      expect(screen.getByText(/3 refs/i)).toBeInTheDocument();
      // Should display token usage
      expect(screen.getByText(/1,500/)).toBeInTheDocument();
    });

    it("should not show context stats when kbContextStats is undefined", () => {
      render(<StatusBar kbStatus="ready" />);

      expect(screen.queryByTestId("kb-context-stats")).not.toBeInTheDocument();
    });

    it("should have accessible aria-label for KB indicator", () => {
      render(<StatusBar kbStatus="ready" />);

      const indicator = screen.getByTestId("kb-status-indicator");
      const container = indicator.closest("[role='status']");
      expect(container).toHaveAttribute(
        "aria-label",
        expect.stringContaining("Knowledge"),
      );
    });

    it("should show token budget usage percentage", () => {
      render(
        <StatusBar
          kbStatus="ready"
          kbContextStats={{ refsCount: 2, tokensUsed: 1500, tokenBudget: 2000 }}
        />,
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
      render(<StatusBar connectionStatus="connected" />);

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toHaveAttribute(
        "title",
        expect.stringContaining("connected"),
      );
    });

    it("should have tooltip on model indicator", () => {
      render(<StatusBar modelName="claude-3-opus" />);

      const indicator = screen.getByTestId("model-indicator");
      expect(indicator).toHaveAttribute(
        "title",
        expect.stringContaining("Model"),
      );
    });

    it("should have tooltip on token count indicator", () => {
      render(<StatusBar tokenCount={1500} />);

      const indicator = screen.getByTestId("token-count");
      expect(indicator).toHaveAttribute(
        "title",
        expect.stringContaining("token"),
      );
    });

    // User indicator has been removed (redundant with top-bar)
    // This test is intentionally removed as userName prop is deprecated

    it("should have tooltip on agent queue toggle", () => {
      render(<StatusBar agentCount={3} onAgentQueueToggle={() => {}} />);

      const toggle = screen.getByRole("button", { name: /agent/i });
      expect(toggle).toHaveAttribute("title", expect.stringContaining("agent"));
    });

    it("should have tooltip on DevTools toggle", () => {
      render(<StatusBar onDevToolsToggle={() => {}} />);

      const toggle = screen.getByRole("button", { name: /devtools/i });
      expect(toggle).toHaveAttribute(
        "title",
        expect.stringContaining("DevTools"),
      );
    });

    it("should have tooltip on pending approvals indicator", () => {
      render(
        <StatusBar pendingApprovals={2} onPendingApprovalsClick={() => {}} />,
      );

      const indicator = screen.getByRole("button", { name: /approval/i });
      expect(indicator).toHaveAttribute(
        "title",
        expect.stringContaining("approval"),
      );
    });
  });
});
