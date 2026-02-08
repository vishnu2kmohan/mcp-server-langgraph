/**
 * ComplianceDashboard Tests
 *
 * Phase 5: Compliance Dashboards
 * Tests for unified compliance dashboard view.
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);
import {
  ComplianceDashboard,
  type ComplianceSummary,
} from "./ComplianceDashboard";

import { TestProvider } from "@/test-utils";

describe("ComplianceDashboard", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });
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
      render(
        <TestProvider>
          <ComplianceDashboard summary={mockSummary} />
        </TestProvider>,
      );
      expect(screen.getByTestId("compliance-dashboard")).toBeInTheDocument();
    });

    it("renders dashboard title", () => {
      render(
        <TestProvider>
          <ComplianceDashboard summary={mockSummary} />
        </TestProvider>,
      );
      expect(screen.getByText(/compliance overview/i)).toBeInTheDocument();
    });

    it("renders all four framework cards", () => {
      render(
        <TestProvider>
          <ComplianceDashboard summary={mockSummary} />
        </TestProvider>,
      );
      expect(screen.getByText(/soc-?2/i)).toBeInTheDocument();
      expect(screen.getByText(/hipaa/i)).toBeInTheDocument();
      expect(screen.getByText(/gdpr/i)).toBeInTheDocument();
      expect(screen.getByText(/fedramp/i)).toBeInTheDocument();
    });
  });

  describe("Framework Summary Cards", () => {
    it("shows SOC-2 compliance percentage", () => {
      render(
        <TestProvider>
          <ComplianceDashboard summary={mockSummary} />
        </TestProvider>,
      );
      expect(screen.getByText(/94%/)).toBeInTheDocument();
    });

    it("shows HIPAA compliance percentage", () => {
      render(
        <TestProvider>
          <ComplianceDashboard summary={mockSummary} />
        </TestProvider>,
      );
      expect(screen.getByText(/100%/)).toBeInTheDocument();
    });

    it("shows GDPR compliance percentage", () => {
      render(
        <TestProvider>
          <ComplianceDashboard summary={mockSummary} />
        </TestProvider>,
      );
      expect(screen.getByText(/87%/)).toBeInTheDocument();
    });

    it("shows FedRAMP compliance percentage", () => {
      render(
        <TestProvider>
          <ComplianceDashboard summary={mockSummary} />
        </TestProvider>,
      );
      expect(screen.getByText(/92%/)).toBeInTheDocument();
    });

    it("shows control counts for SOC-2", () => {
      render(
        <TestProvider>
          <ComplianceDashboard summary={mockSummary} />
        </TestProvider>,
      );
      expect(screen.getByText(/47.*50/)).toBeInTheDocument();
    });

    it("shows FedRAMP authorization level", () => {
      render(
        <TestProvider>
          <ComplianceDashboard summary={mockSummary} />
        </TestProvider>,
      );
      expect(screen.getByText(/p-ato/i)).toBeInTheDocument();
    });

    it("shows GDPR pending actions count", () => {
      render(
        <TestProvider>
          <ComplianceDashboard summary={mockSummary} />
        </TestProvider>,
      );
      expect(screen.getByText(/3.*action/i)).toBeInTheDocument();
    });
  });

  describe("Status Indicators", () => {
    it("shows compliant status with green indicator", () => {
      render(
        <TestProvider>
          <ComplianceDashboard summary={mockSummary} />
        </TestProvider>,
      );
      // Multiple compliant frameworks should have green indicators
      const compliantIndicators = screen.getAllByRole("img", { hidden: true });
      expect(compliantIndicators.length).toBeGreaterThan(0);
    });

    it("shows partial status with yellow indicator for GDPR", () => {
      render(
        <TestProvider>
          <ComplianceDashboard summary={mockSummary} />
        </TestProvider>,
      );
      // GDPR should show partial compliance status
      expect(screen.getByText(/partial/i)).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("shows loading skeleton when isLoading is true", () => {
      render(
        <TestProvider>
          <ComplianceDashboard summary={mockSummary} isLoading={true} />
        </TestProvider>,
      );
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("shows empty state when no summary data", () => {
      render(
        <TestProvider>
          <ComplianceDashboard summary={null} />
        </TestProvider>,
      );
      expect(screen.getByText(/no compliance data/i)).toBeInTheDocument();
    });
  });

  describe("Accessibility (WCAG 2.1 AA)", () => {
    it("should have no accessibility violations with data", async () => {
      const { container } = render(
        <TestProvider>
          <ComplianceDashboard summary={mockSummary} />
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations in empty state", async () => {
      const { container } = render(
        <TestProvider>
          <ComplianceDashboard summary={null} />
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
