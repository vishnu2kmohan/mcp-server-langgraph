/**
 * BatchApprovalPanel Component Tests
 *
 * TDD tests for batch approval functionality.
 *
 * Features:
 * - Display multiple pending approval requests
 * - Select/deselect individual requests
 * - Select all / deselect all
 * - Batch approve selected requests
 * - Batch reject selected requests
 * - Common reason input
 *
 * Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// =============================================================================
// Mock Data
// =============================================================================

const mockApprovals = [
  {
    request_id: "req-001",
    session_id: "session-001",
    task_id: "task-001",
    agent_name: "Research Assistant",
    confidence: 0.65,
    threshold: 0.7,
    proposed_action: "Send analysis report",
    trigger_reason: "low_confidence",
    context: { tokens_used: 1000 },
    requested_at: "2024-01-15T10:36:00Z",
  },
  {
    request_id: "req-002",
    session_id: "session-001",
    task_id: "task-002",
    agent_name: "Data Analyst",
    confidence: 0.55,
    threshold: 0.7,
    proposed_action: "Update database records",
    trigger_reason: "destructive_action",
    context: { tokens_used: 500 },
    requested_at: "2024-01-15T10:37:00Z",
  },
  {
    request_id: "req-003",
    session_id: "session-002",
    task_id: "task-003",
    agent_name: "API Agent",
    confidence: 0.68,
    threshold: 0.7,
    proposed_action: "Call external API",
    trigger_reason: "external_api",
    context: { tokens_used: 200 },
    requested_at: "2024-01-15T10:38:00Z",
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("BatchApprovalPanel", () => {
  let BatchApprovalPanel: React.ComponentType<{
    approvals: typeof mockApprovals;
    onBatchApprove: (ids: string[], reason?: string) => Promise<void>;
    onBatchReject: (ids: string[], reason?: string) => Promise<void>;
    currentUser?: string;
    isApproving?: boolean;
    isRejecting?: boolean;
  }>;

  beforeEach(async () => {
    const module = await import("./BatchApprovalPanel");
    BatchApprovalPanel = module.BatchApprovalPanel;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Component Export", () => {
    it("should export BatchApprovalPanel component", async () => {
      const module = await import("./BatchApprovalPanel");
      expect(module.BatchApprovalPanel).toBeDefined();
    });
  });

  describe("Rendering", () => {
    it("should display all pending approvals", () => {
      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      expect(screen.getByText("Research Assistant")).toBeInTheDocument();
      expect(screen.getByText("Data Analyst")).toBeInTheDocument();
      expect(screen.getByText("API Agent")).toBeInTheDocument();
    });

    it("should display checkboxes for each approval", () => {
      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      const checkboxes = screen.getAllByRole("checkbox");
      // One for each approval + one for "select all"
      expect(checkboxes.length).toBe(mockApprovals.length + 1);
    });

    it("should display select all checkbox", () => {
      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      expect(
        screen.getByRole("checkbox", { name: /select all/i })
      ).toBeInTheDocument();
    });

    it("should display batch approve and reject buttons", () => {
      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      expect(
        screen.getByRole("button", { name: /approve selected/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /reject selected/i })
      ).toBeInTheDocument();
    });

    it("should display confidence for each approval", () => {
      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      expect(screen.getByText("65%")).toBeInTheDocument();
      expect(screen.getByText("55%")).toBeInTheDocument();
      expect(screen.getByText("68%")).toBeInTheDocument();
    });

    it("should show empty state when no approvals pending", () => {
      render(
        <BatchApprovalPanel
          approvals={[]}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      expect(screen.getByText(/no pending approvals/i)).toBeInTheDocument();
    });
  });

  describe("Selection", () => {
    it("should select individual approval on checkbox click", async () => {
      const user = userEvent.setup();

      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      const checkboxes = screen.getAllByRole("checkbox");
      const firstApprovalCheckbox = checkboxes[1]; // Skip "select all"

      await user.click(firstApprovalCheckbox);

      expect(firstApprovalCheckbox).toBeChecked();
    });

    it("should select all when select all checkbox is clicked", async () => {
      const user = userEvent.setup();

      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      const selectAllCheckbox = screen.getByRole("checkbox", {
        name: /select all/i,
      });

      await user.click(selectAllCheckbox);

      const allCheckboxes = screen.getAllByRole("checkbox");
      allCheckboxes.forEach((checkbox) => {
        expect(checkbox).toBeChecked();
      });
    });

    it("should deselect all when select all is unchecked", async () => {
      const user = userEvent.setup();

      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      const selectAllCheckbox = screen.getByRole("checkbox", {
        name: /select all/i,
      });

      // Select all first
      await user.click(selectAllCheckbox);
      // Then deselect all
      await user.click(selectAllCheckbox);

      const allCheckboxes = screen.getAllByRole("checkbox");
      allCheckboxes.forEach((checkbox) => {
        expect(checkbox).not.toBeChecked();
      });
    });

    it("should show selection count", async () => {
      const user = userEvent.setup();

      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      const checkboxes = screen.getAllByRole("checkbox");
      await user.click(checkboxes[1]); // First approval
      await user.click(checkboxes[2]); // Second approval

      expect(screen.getByText(/2 selected/i)).toBeInTheDocument();
    });
  });

  describe("Batch Actions", () => {
    it("should disable batch buttons when nothing is selected", () => {
      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      const approveButton = screen.getByRole("button", {
        name: /approve selected/i,
      });
      const rejectButton = screen.getByRole("button", {
        name: /reject selected/i,
      });

      expect(approveButton).toBeDisabled();
      expect(rejectButton).toBeDisabled();
    });

    it("should enable batch buttons when items are selected", async () => {
      const user = userEvent.setup();

      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      const checkboxes = screen.getAllByRole("checkbox");
      await user.click(checkboxes[1]); // Select first approval

      const approveButton = screen.getByRole("button", {
        name: /approve selected/i,
      });
      const rejectButton = screen.getByRole("button", {
        name: /reject selected/i,
      });

      expect(approveButton).not.toBeDisabled();
      expect(rejectButton).not.toBeDisabled();
    });

    it("should call onBatchApprove with selected IDs when approve clicked", async () => {
      const user = userEvent.setup();
      const onBatchApprove = vi.fn().mockResolvedValue(undefined);

      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={onBatchApprove}
          onBatchReject={vi.fn()}
        />
      );

      const checkboxes = screen.getAllByRole("checkbox");
      await user.click(checkboxes[1]); // req-001
      await user.click(checkboxes[3]); // req-003

      const approveButton = screen.getByRole("button", {
        name: /approve selected/i,
      });
      await user.click(approveButton);

      expect(onBatchApprove).toHaveBeenCalledWith(
        expect.arrayContaining(["req-001", "req-003"]),
        undefined
      );
    });

    it("should call onBatchReject with selected IDs when reject clicked", async () => {
      const user = userEvent.setup();
      const onBatchReject = vi.fn().mockResolvedValue(undefined);

      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={onBatchReject}
        />
      );

      const checkboxes = screen.getAllByRole("checkbox");
      await user.click(checkboxes[2]); // req-002

      const rejectButton = screen.getByRole("button", {
        name: /reject selected/i,
      });
      await user.click(rejectButton);

      expect(onBatchReject).toHaveBeenCalledWith(["req-002"], undefined);
    });
  });

  describe("Common Reason", () => {
    it("should display common reason input", () => {
      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      expect(screen.getByPlaceholderText(/reason/i)).toBeInTheDocument();
    });

    it("should pass reason to batch approve", async () => {
      const user = userEvent.setup();
      const onBatchApprove = vi.fn().mockResolvedValue(undefined);

      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={onBatchApprove}
          onBatchReject={vi.fn()}
        />
      );

      // Select an approval
      const checkboxes = screen.getAllByRole("checkbox");
      await user.click(checkboxes[1]);

      // Enter reason
      const reasonInput = screen.getByPlaceholderText(/reason/i);
      await user.type(reasonInput, "Batch verified by admin");

      // Click approve
      const approveButton = screen.getByRole("button", {
        name: /approve selected/i,
      });
      await user.click(approveButton);

      expect(onBatchApprove).toHaveBeenCalledWith(
        expect.any(Array),
        "Batch verified by admin"
      );
    });
  });

  describe("Loading States", () => {
    it("should show loading spinner during approval", () => {
      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
          isApproving={true}
        />
      );

      expect(screen.getByTestId("batch-approve-loading")).toBeInTheDocument();
    });

    it("should show loading spinner during rejection", () => {
      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
          isRejecting={true}
        />
      );

      expect(screen.getByTestId("batch-reject-loading")).toBeInTheDocument();
    });

    it("should disable all interactions during loading", () => {
      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
          isApproving={true}
        />
      );

      const checkboxes = screen.getAllByRole("checkbox");
      checkboxes.forEach((checkbox) => {
        expect(checkbox).toBeDisabled();
      });
    });
  });

  describe("Accessibility", () => {
    it("should have accessible labels for checkboxes", () => {
      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      // Each approval checkbox should have an accessible name
      mockApprovals.forEach((approval) => {
        expect(
          screen.getByRole("checkbox", {
            name: new RegExp(approval.agent_name, "i"),
          })
        ).toBeInTheDocument();
      });
    });

    it("should support keyboard navigation", async () => {
      const user = userEvent.setup();

      render(
        <BatchApprovalPanel
          approvals={mockApprovals}
          onBatchApprove={vi.fn()}
          onBatchReject={vi.fn()}
        />
      );

      const selectAllCheckbox = screen.getByRole("checkbox", {
        name: /select all/i,
      });

      selectAllCheckbox.focus();
      expect(selectAllCheckbox).toHaveFocus();

      await user.keyboard(" "); // Space to toggle
      expect(selectAllCheckbox).toBeChecked();
    });
  });
});
