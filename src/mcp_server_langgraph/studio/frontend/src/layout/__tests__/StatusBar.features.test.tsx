/**
 * StatusBar Features Tests
 *
 * Tests for agent task queue toggle, pending approvals indicator, DevTools toggle,
 * accessibility, reconnection status, knowledge base status indicator, and tooltips.
 *
 * Split from StatusBar.test.tsx for memory optimization.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

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
