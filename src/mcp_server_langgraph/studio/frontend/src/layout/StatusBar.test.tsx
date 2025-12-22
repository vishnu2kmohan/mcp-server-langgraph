/**
 * StatusBar Tests
 *
 * TDD tests for the extracted StatusBar component.
 * Tests status display, keyboard shortcuts, and feature flag toggle.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
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

  describe("rendering", () => {
    it("should render with data-testid", () => {
      render(<StatusBar />);

      expect(screen.getByTestId("status-bar")).toBeInTheDocument();
    });

    it("should display Ready status", () => {
      render(<StatusBar />);

      expect(screen.getByText("Ready")).toBeInTheDocument();
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
      expect(indicator).toHaveClass("bg-green-500");
    });

    it("should show disconnected indicator when disconnected", () => {
      render(<StatusBar connectionStatus="disconnected" />);

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-red-500");
    });

    it("should show connecting indicator when connecting", () => {
      render(<StatusBar connectionStatus="connecting" />);

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-yellow-500");
    });

    it("should hide connection indicator when status is undefined", () => {
      render(<StatusBar />);

      expect(screen.queryByTestId("connection-indicator")).not.toBeInTheDocument();
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
  });

  describe("user indicator", () => {
    it("should display user name when provided", () => {
      render(<StatusBar userName="alice" />);

      expect(screen.getByTestId("user-indicator")).toBeInTheDocument();
      expect(screen.getByText("alice")).toBeInTheDocument();
    });

    it("should not display user indicator when not provided", () => {
      render(<StatusBar />);

      expect(screen.queryByTestId("user-indicator")).not.toBeInTheDocument();
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
      expect(statusBar).toHaveClass("dark:bg-gray-900");
    });
  });

  describe("error state", () => {
    it("should show error indicator when connectionStatus is error", () => {
      render(<StatusBar connectionStatus="error" />);

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-red-500");
    });

    it("should display error message when provided", () => {
      render(<StatusBar errorMessage="Connection failed" />);

      expect(screen.getByTestId("error-message")).toBeInTheDocument();
      expect(screen.getByText("Connection failed")).toBeInTheDocument();
    });

    it("should have error styling on error message", () => {
      render(<StatusBar errorMessage="Something went wrong" />);

      const errorElement = screen.getByTestId("error-message");
      expect(errorElement).toHaveClass("text-red-500");
    });

    it("should not display error message when not provided", () => {
      render(<StatusBar />);

      expect(screen.queryByTestId("error-message")).not.toBeInTheDocument();
    });

    it("should show both connection error indicator and error message", () => {
      render(
        <StatusBar connectionStatus="error" errorMessage="Server unreachable" />,
      );

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toHaveClass("bg-red-500");
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

      expect(screen.queryByTestId("agent-queue-toggle")).not.toBeInTheDocument();
    });

    it("should not display agent queue button when agentCount is undefined", () => {
      render(<StatusBar />);

      expect(screen.queryByTestId("agent-queue-toggle")).not.toBeInTheDocument();
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
      expect(button).toHaveAttribute("aria-label", "Toggle agent task queue (5 agents)");
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
        <StatusBar pendingApprovals={2} onPendingApprovalsClick={handleClick} />,
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
      expect(button).toHaveClass("bg-amber-100");
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
      expect(button).toHaveClass("bg-amber-200");
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
});
