/**
 * BackgroundAgentPanel Tests
 *
 * Phase 4: AI-Native Features
 * Tests for background agent status panel.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  BackgroundAgentPanel,
  type BackgroundAgent,
} from "./BackgroundAgentPanel";

describe("BackgroundAgentPanel", () => {
  const mockAgents: BackgroundAgent[] = [
    {
      id: "agent-1",
      name: "Code Analyzer",
      task: "Analyzing code complexity",
      status: "running",
      progress: 45,
      startedAt: Date.now() - 30000,
    },
    {
      id: "agent-2",
      name: "Test Generator",
      task: "Generating unit tests",
      status: "queued",
      progress: 0,
      startedAt: Date.now(),
    },
    {
      id: "agent-3",
      name: "Refactor Assistant",
      task: "Identifying refactoring opportunities",
      status: "completed",
      progress: 100,
      startedAt: Date.now() - 60000,
    },
    {
      id: "agent-4",
      name: "Linter",
      task: "Checking code style",
      status: "failed",
      progress: 75,
      startedAt: Date.now() - 45000,
      error: "Connection timeout",
    },
  ];

  const mockOnCancel = vi.fn();
  const mockOnRetry = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("renders the panel container", () => {
      render(
        <BackgroundAgentPanel
          agents={mockAgents}
          onCancel={mockOnCancel}
          onRetry={mockOnRetry}
        />,
      );

      expect(screen.getByTestId("background-agent-panel")).toBeInTheDocument();
    });

    it("renders panel header", () => {
      render(
        <BackgroundAgentPanel
          agents={mockAgents}
          onCancel={mockOnCancel}
          onRetry={mockOnRetry}
        />,
      );

      expect(screen.getByText(/background agents/i)).toBeInTheDocument();
    });

    it("shows agent count", () => {
      render(
        <BackgroundAgentPanel
          agents={mockAgents}
          onCancel={mockOnCancel}
          onRetry={mockOnRetry}
        />,
      );

      expect(screen.getByText("4")).toBeInTheDocument();
    });

    it("renders all agents", () => {
      render(
        <BackgroundAgentPanel
          agents={mockAgents}
          onCancel={mockOnCancel}
          onRetry={mockOnRetry}
        />,
      );

      expect(screen.getByText("Code Analyzer")).toBeInTheDocument();
      expect(screen.getByText("Test Generator")).toBeInTheDocument();
      expect(screen.getByText("Refactor Assistant")).toBeInTheDocument();
      expect(screen.getByText("Linter")).toBeInTheDocument();
    });

    it("shows empty state when no agents", () => {
      render(
        <BackgroundAgentPanel
          agents={[]}
          onCancel={mockOnCancel}
          onRetry={mockOnRetry}
        />,
      );

      expect(screen.getByText(/no active agents/i)).toBeInTheDocument();
    });
  });

  describe("Agent Status", () => {
    it("shows running status with progress", () => {
      render(
        <BackgroundAgentPanel
          agents={[mockAgents[0]]}
          onCancel={mockOnCancel}
          onRetry={mockOnRetry}
        />,
      );

      expect(screen.getByText(/running/i)).toBeInTheDocument();
      expect(screen.getByText(/45%/)).toBeInTheDocument();
    });

    it("shows queued status", () => {
      render(
        <BackgroundAgentPanel
          agents={[mockAgents[1]]}
          onCancel={mockOnCancel}
          onRetry={mockOnRetry}
        />,
      );

      expect(screen.getByText(/queued/i)).toBeInTheDocument();
    });

    it("shows completed status", () => {
      render(
        <BackgroundAgentPanel
          agents={[mockAgents[2]]}
          onCancel={mockOnCancel}
          onRetry={mockOnRetry}
        />,
      );

      expect(screen.getByText(/completed/i)).toBeInTheDocument();
    });

    it("shows failed status with error message", () => {
      render(
        <BackgroundAgentPanel
          agents={[mockAgents[3]]}
          onCancel={mockOnCancel}
          onRetry={mockOnRetry}
        />,
      );

      expect(screen.getByText(/failed/i)).toBeInTheDocument();
      expect(screen.getByText(/connection timeout/i)).toBeInTheDocument();
    });
  });

  describe("Interactions", () => {
    it("calls onCancel when cancel button is clicked for running agent", () => {
      render(
        <BackgroundAgentPanel
          agents={[mockAgents[0]]}
          onCancel={mockOnCancel}
          onRetry={mockOnRetry}
        />,
      );

      const cancelButton = screen.getByLabelText(/cancel/i);
      fireEvent.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalledWith(mockAgents[0].id);
    });

    it("calls onRetry when retry button is clicked for failed agent", () => {
      render(
        <BackgroundAgentPanel
          agents={[mockAgents[3]]}
          onCancel={mockOnCancel}
          onRetry={mockOnRetry}
        />,
      );

      const retryButton = screen.getByLabelText(/retry/i);
      fireEvent.click(retryButton);

      expect(mockOnRetry).toHaveBeenCalledWith(mockAgents[3].id);
    });

    it("does not show cancel button for completed agent", () => {
      render(
        <BackgroundAgentPanel
          agents={[mockAgents[2]]}
          onCancel={mockOnCancel}
          onRetry={mockOnRetry}
        />,
      );

      expect(screen.queryByLabelText(/cancel/i)).not.toBeInTheDocument();
    });
  });

  describe("Collapsibility", () => {
    it("can be collapsed", () => {
      render(
        <BackgroundAgentPanel
          agents={mockAgents}
          onCancel={mockOnCancel}
          onRetry={mockOnRetry}
          defaultCollapsed={false}
        />,
      );

      const toggleButton = screen.getByLabelText(/collapse/i);
      fireEvent.click(toggleButton);

      // Agent list should be hidden
      expect(screen.queryByText("Code Analyzer")).not.toBeInTheDocument();
    });

    it("can start collapsed", () => {
      render(
        <BackgroundAgentPanel
          agents={mockAgents}
          onCancel={mockOnCancel}
          onRetry={mockOnRetry}
          defaultCollapsed={true}
        />,
      );

      // Agent list should be hidden
      expect(screen.queryByText("Code Analyzer")).not.toBeInTheDocument();
      // Header should still be visible
      expect(screen.getByText(/background agents/i)).toBeInTheDocument();
    });
  });
});
