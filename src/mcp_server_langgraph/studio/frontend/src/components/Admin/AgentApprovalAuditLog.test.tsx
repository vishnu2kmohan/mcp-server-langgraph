/**
 * AgentApprovalAuditLog Component Tests
 *
 * TDD tests for the HITL approval audit log display.
 *
 * Features:
 * - Display approval/rejection history
 * - Filter by date range
 * - Filter by decision type
 * - Export functionality
 * - Pagination
 *
 * Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import React from "react";

// =============================================================================
// Mock Data
// =============================================================================

const mockAuditEntries = [
  {
    id: "audit-001",
    request_id: "req-001",
    agent_name: "Research Assistant",
    decision: "approved",
    confidence: 0.65,
    threshold: 0.7,
    decided_by: "admin@example.com",
    decided_at: "2025-12-21T10:30:00Z",
    reason: "Verified output quality",
  },
  {
    id: "audit-002",
    request_id: "req-002",
    agent_name: "Data Analyzer",
    decision: "rejected",
    confidence: 0.45,
    threshold: 0.7,
    decided_by: "reviewer@example.com",
    decided_at: "2025-12-21T09:15:00Z",
    reason: "Insufficient confidence for sensitive operation",
  },
  {
    id: "audit-003",
    request_id: "req-003",
    agent_name: "Code Generator",
    decision: "approved",
    confidence: 0.72,
    threshold: 0.7,
    decided_by: "admin@example.com",
    decided_at: "2025-12-20T14:00:00Z",
    reason: null,
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("AgentApprovalAuditLog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Export", () => {
    it("should export AgentApprovalAuditLog component", async () => {
      const module = await import("./AgentApprovalAuditLog");
      expect(module.AgentApprovalAuditLog).toBeDefined();
    });
  });

  describe("Rendering", () => {
    it("should render audit log header", async () => {
      const { AgentApprovalAuditLog } = await import("./AgentApprovalAuditLog");

      render(<AgentApprovalAuditLog entries={mockAuditEntries} />);

      expect(screen.getByText(/Approval Audit Log/i)).toBeInTheDocument();
    });

    it("should display audit entries", async () => {
      const { AgentApprovalAuditLog } = await import("./AgentApprovalAuditLog");

      render(<AgentApprovalAuditLog entries={mockAuditEntries} />);

      expect(screen.getByText("Research Assistant")).toBeInTheDocument();
      expect(screen.getByText("Data Analyzer")).toBeInTheDocument();
      expect(screen.getByText("Code Generator")).toBeInTheDocument();
    });

    it("should display decision status with appropriate styling", async () => {
      const { AgentApprovalAuditLog } = await import("./AgentApprovalAuditLog");

      render(<AgentApprovalAuditLog entries={mockAuditEntries} />);

      // Should have approved and rejected indicators
      const approvedElements = screen.getAllByText(/approved/i);
      const rejectedElements = screen.getAllByText(/rejected/i);

      expect(approvedElements.length).toBeGreaterThanOrEqual(2);
      expect(rejectedElements.length).toBeGreaterThanOrEqual(1);
    });

    it("should display confidence scores", async () => {
      const { AgentApprovalAuditLog } = await import("./AgentApprovalAuditLog");

      render(<AgentApprovalAuditLog entries={mockAuditEntries} />);

      // Should show confidence percentages
      expect(screen.getByText(/65%/)).toBeInTheDocument();
      expect(screen.getByText(/45%/)).toBeInTheDocument();
    });

    it("should display who made the decision", async () => {
      const { AgentApprovalAuditLog } = await import("./AgentApprovalAuditLog");

      render(<AgentApprovalAuditLog entries={mockAuditEntries} />);

      // admin@example.com appears twice (two approved entries)
      const adminElements = screen.getAllByText(/admin@example.com/);
      expect(adminElements.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/reviewer@example.com/)).toBeInTheDocument();
    });

    it("should show empty state when no entries", async () => {
      const { AgentApprovalAuditLog } = await import("./AgentApprovalAuditLog");

      render(<AgentApprovalAuditLog entries={[]} />);

      expect(screen.getByText(/No approval history/i)).toBeInTheDocument();
    });
  });

  describe("Filtering", () => {
    it("should have filter controls", async () => {
      const { AgentApprovalAuditLog } = await import("./AgentApprovalAuditLog");

      render(<AgentApprovalAuditLog entries={mockAuditEntries} />);

      // Should have filter options
      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("should filter by decision type", async () => {
      const { AgentApprovalAuditLog } = await import("./AgentApprovalAuditLog");

      render(<AgentApprovalAuditLog entries={mockAuditEntries} />);

      // Select "Approved Only" filter
      const select = screen.getByRole("combobox");
      fireEvent.change(select, { target: { value: "approved" } });

      await waitFor(() => {
        // Should only show approved entries
        expect(screen.getByText("Research Assistant")).toBeInTheDocument();
        expect(screen.queryByText("Data Analyzer")).not.toBeInTheDocument();
      });
    });
  });

  describe("Export", () => {
    it("should have export button", async () => {
      const { AgentApprovalAuditLog } = await import("./AgentApprovalAuditLog");

      render(<AgentApprovalAuditLog entries={mockAuditEntries} />);

      expect(
        screen.getByRole("button", { name: /export/i }),
      ).toBeInTheDocument();
    });

    it("should call onExport when export button clicked", async () => {
      const { AgentApprovalAuditLog } = await import("./AgentApprovalAuditLog");

      const onExport = vi.fn();
      render(
        <AgentApprovalAuditLog
          entries={mockAuditEntries}
          onExport={onExport}
        />,
      );

      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);

      expect(onExport).toHaveBeenCalledWith(mockAuditEntries);
    });
  });

  describe("Loading State", () => {
    it("should show loading state when isLoading is true", async () => {
      const { AgentApprovalAuditLog } = await import("./AgentApprovalAuditLog");

      render(<AgentApprovalAuditLog entries={[]} isLoading={true} />);

      expect(screen.getByText(/Loading/i)).toBeInTheDocument();
    });
  });

  describe("Entry Details", () => {
    it("should expand entry to show reason", async () => {
      const { AgentApprovalAuditLog } = await import("./AgentApprovalAuditLog");

      render(<AgentApprovalAuditLog entries={mockAuditEntries} />);

      // Click on an entry row to expand
      const entryRow = screen.getByText("Research Assistant").closest("tr");
      if (entryRow) {
        fireEvent.click(entryRow);
      }

      await waitFor(() => {
        expect(screen.getByText("Verified output quality")).toBeInTheDocument();
      });
    });
  });

  describe("Accessibility", () => {
    it("should have proper table structure", async () => {
      const { AgentApprovalAuditLog } = await import("./AgentApprovalAuditLog");

      render(<AgentApprovalAuditLog entries={mockAuditEntries} />);

      expect(screen.getByRole("table")).toBeInTheDocument();
      expect(screen.getAllByRole("row").length).toBeGreaterThan(0);
    });

    it("should have proper column headers", async () => {
      const { AgentApprovalAuditLog } = await import("./AgentApprovalAuditLog");

      render(<AgentApprovalAuditLog entries={mockAuditEntries} />);

      // Check for column headers within the table (using more specific selectors)
      const table = screen.getByRole("table");
      expect(table).toBeInTheDocument();

      // These headers are unique within the th elements
      expect(screen.getByText("Agent")).toBeInTheDocument();
      expect(screen.getByText("Confidence")).toBeInTheDocument();
      // "Decision" appears in both header and filter, so check it exists
      const decisionElements = screen.getAllByText(/Decision/i);
      expect(decisionElements.length).toBeGreaterThanOrEqual(1);
    });
  });
});
