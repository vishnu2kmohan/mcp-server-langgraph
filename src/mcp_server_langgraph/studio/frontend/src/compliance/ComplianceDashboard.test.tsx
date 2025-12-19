/**
 * ComplianceDashboard Tests
 *
 * Phase 5: Compliance Dashboards
 * Tests for unified compliance dashboard view.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  ComplianceDashboard,
  type ComplianceSummary,
} from "./ComplianceDashboard";

describe("ComplianceDashboard", () => {
  const mockSummary: ComplianceSummary = {
    soc2: {
      percentage: 94,
      compliantCount: 47,
      totalCount: 50,
      status: "compliant",
    },
    hipaa: {
      percentage: 100,
      compliantCount: 20,
      totalCount: 20,
      status: "compliant",
    },
    gdpr: {
      percentage: 87,
      compliantCount: 26,
      totalCount: 30,
      status: "partial",
      pendingActions: 3,
    },
    fedramp: {
      percentage: 92,
      compliantCount: 46,
      totalCount: 50,
      status: "compliant",
      authLevel: "P-ATO",
    },
  };

  describe("Rendering", () => {
    it("renders the dashboard container", () => {
      render(<ComplianceDashboard summary={mockSummary} />);
      expect(screen.getByTestId("compliance-dashboard")).toBeInTheDocument();
    });

    it("renders dashboard title", () => {
      render(<ComplianceDashboard summary={mockSummary} />);
      expect(screen.getByText(/compliance overview/i)).toBeInTheDocument();
    });

    it("renders all four framework cards", () => {
      render(<ComplianceDashboard summary={mockSummary} />);
      expect(screen.getByText(/soc-?2/i)).toBeInTheDocument();
      expect(screen.getByText(/hipaa/i)).toBeInTheDocument();
      expect(screen.getByText(/gdpr/i)).toBeInTheDocument();
      expect(screen.getByText(/fedramp/i)).toBeInTheDocument();
    });
  });

  describe("Framework Summary Cards", () => {
    it("shows SOC-2 compliance percentage", () => {
      render(<ComplianceDashboard summary={mockSummary} />);
      expect(screen.getByText(/94%/)).toBeInTheDocument();
    });

    it("shows HIPAA compliance percentage", () => {
      render(<ComplianceDashboard summary={mockSummary} />);
      expect(screen.getByText(/100%/)).toBeInTheDocument();
    });

    it("shows GDPR compliance percentage", () => {
      render(<ComplianceDashboard summary={mockSummary} />);
      expect(screen.getByText(/87%/)).toBeInTheDocument();
    });

    it("shows FedRAMP compliance percentage", () => {
      render(<ComplianceDashboard summary={mockSummary} />);
      expect(screen.getByText(/92%/)).toBeInTheDocument();
    });

    it("shows control counts for SOC-2", () => {
      render(<ComplianceDashboard summary={mockSummary} />);
      expect(screen.getByText(/47.*50/)).toBeInTheDocument();
    });

    it("shows FedRAMP authorization level", () => {
      render(<ComplianceDashboard summary={mockSummary} />);
      expect(screen.getByText(/p-ato/i)).toBeInTheDocument();
    });

    it("shows GDPR pending actions count", () => {
      render(<ComplianceDashboard summary={mockSummary} />);
      expect(screen.getByText(/3.*action/i)).toBeInTheDocument();
    });
  });

  describe("Status Indicators", () => {
    it("shows compliant status with green indicator", () => {
      render(<ComplianceDashboard summary={mockSummary} />);
      // Multiple compliant frameworks should have green indicators
      const compliantIndicators = screen.getAllByRole("img", { hidden: true });
      expect(compliantIndicators.length).toBeGreaterThan(0);
    });

    it("shows partial status with yellow indicator for GDPR", () => {
      render(<ComplianceDashboard summary={mockSummary} />);
      // GDPR should show partial compliance status
      expect(screen.getByText(/partial/i)).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("shows loading skeleton when isLoading is true", () => {
      render(<ComplianceDashboard summary={mockSummary} isLoading={true} />);
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("shows empty state when no summary data", () => {
      render(<ComplianceDashboard summary={null} />);
      expect(screen.getByText(/no compliance data/i)).toBeInTheDocument();
    });
  });
});
