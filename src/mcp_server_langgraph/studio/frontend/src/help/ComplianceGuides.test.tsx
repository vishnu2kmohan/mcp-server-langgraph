/**
 * ComplianceGuides Tests - Phase 6
 *
 * Tests for compliance runbooks and guides in the help module.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ComplianceGuides, type Guide } from "./ComplianceGuides";

// =============================================================================
// Test Data
// =============================================================================

const mockGuides: Guide[] = [
  {
    id: "soc2-access-review",
    title: "SOC-2 Access Review Process",
    framework: "soc2",
    summary: "Quarterly review of user access permissions",
    steps: [
      {
        title: "Export user list",
        description: "Download current user access report",
      },
      {
        title: "Review permissions",
        description: "Check each user's access level",
      },
      { title: "Document findings", description: "Record any discrepancies" },
    ],
    lastUpdated: "2024-01-15",
  },
  {
    id: "hipaa-incident-response",
    title: "HIPAA Incident Response",
    framework: "hipaa",
    summary: "Steps to handle potential PHI breaches",
    steps: [
      { title: "Identify breach", description: "Determine scope of incident" },
      { title: "Contain breach", description: "Prevent further exposure" },
      {
        title: "Notify stakeholders",
        description: "Follow notification requirements",
      },
    ],
    lastUpdated: "2024-01-10",
  },
  {
    id: "gdpr-data-request",
    title: "GDPR Data Subject Request",
    framework: "gdpr",
    summary: "Handle data access or deletion requests",
    steps: [
      { title: "Verify identity", description: "Confirm requester identity" },
      { title: "Locate data", description: "Find all personal data" },
      {
        title: "Fulfill request",
        description: "Export or delete as requested",
      },
    ],
    lastUpdated: "2024-01-08",
  },
  {
    id: "fedramp-audit-prep",
    title: "FedRAMP Audit Preparation",
    framework: "fedramp",
    summary: "Prepare for FedRAMP authorization audit",
    steps: [
      {
        title: "Gather documentation",
        description: "Collect all required documents",
      },
      {
        title: "Review controls",
        description: "Verify control implementation",
      },
    ],
    lastUpdated: "2024-01-05",
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("ComplianceGuides", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render guides container", () => {
      render(<ComplianceGuides guides={mockGuides} />);
      expect(screen.getByTestId("compliance-guides")).toBeInTheDocument();
    });

    it("should display all guides", () => {
      render(<ComplianceGuides guides={mockGuides} />);
      expect(
        screen.getByText("SOC-2 Access Review Process"),
      ).toBeInTheDocument();
      expect(screen.getByText("HIPAA Incident Response")).toBeInTheDocument();
      expect(screen.getByText("GDPR Data Subject Request")).toBeInTheDocument();
    });

    it("should show guide summaries", () => {
      render(<ComplianceGuides guides={mockGuides} />);
      expect(
        screen.getByText("Quarterly review of user access permissions"),
      ).toBeInTheDocument();
    });

    it("should display framework badges", () => {
      render(<ComplianceGuides guides={mockGuides} />);
      expect(screen.getByTestId("framework-badge-soc2")).toBeInTheDocument();
      expect(screen.getByTestId("framework-badge-hipaa")).toBeInTheDocument();
      expect(screen.getByTestId("framework-badge-gdpr")).toBeInTheDocument();
      expect(screen.getByTestId("framework-badge-fedramp")).toBeInTheDocument();
    });
  });

  describe("Filtering", () => {
    it("should filter by framework", () => {
      render(<ComplianceGuides guides={mockGuides} />);
      const filter = screen.getByTestId("framework-filter");
      fireEvent.change(filter, { target: { value: "hipaa" } });

      expect(screen.getByText("HIPAA Incident Response")).toBeInTheDocument();
      expect(
        screen.queryByText("SOC-2 Access Review Process"),
      ).not.toBeInTheDocument();
    });

    it("should show all guides when filter is 'all'", () => {
      render(<ComplianceGuides guides={mockGuides} />);
      const filter = screen.getByTestId("framework-filter");
      fireEvent.change(filter, { target: { value: "all" } });

      expect(
        screen.getByText("SOC-2 Access Review Process"),
      ).toBeInTheDocument();
      expect(screen.getByText("HIPAA Incident Response")).toBeInTheDocument();
      expect(screen.getByText("GDPR Data Subject Request")).toBeInTheDocument();
    });

    it("should filter by search text", () => {
      render(<ComplianceGuides guides={mockGuides} />);
      const search = screen.getByTestId("guide-search");
      fireEvent.change(search, { target: { value: "incident" } });

      expect(screen.getByText("HIPAA Incident Response")).toBeInTheDocument();
      expect(
        screen.queryByText("SOC-2 Access Review Process"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Expansion", () => {
    it("should expand guide on click", () => {
      render(<ComplianceGuides guides={mockGuides} />);
      const guideItem = screen.getByTestId("guide-soc2-access-review");
      fireEvent.click(guideItem);

      expect(screen.getByTestId("guide-steps")).toBeInTheDocument();
    });

    it("should show steps when expanded", () => {
      render(<ComplianceGuides guides={mockGuides} />);
      const guideItem = screen.getByTestId("guide-soc2-access-review");
      fireEvent.click(guideItem);

      expect(screen.getByText("Export user list")).toBeInTheDocument();
      expect(screen.getByText("Review permissions")).toBeInTheDocument();
      expect(screen.getByText("Document findings")).toBeInTheDocument();
    });

    it("should collapse guide on second click", () => {
      render(<ComplianceGuides guides={mockGuides} />);
      const guideItem = screen.getByTestId("guide-soc2-access-review");
      fireEvent.click(guideItem);
      fireEvent.click(guideItem);

      expect(screen.queryByTestId("guide-steps")).not.toBeInTheDocument();
    });
  });

  describe("Step Progress", () => {
    it("should allow marking steps complete", () => {
      render(<ComplianceGuides guides={mockGuides} enableProgress />);
      const guideItem = screen.getByTestId("guide-soc2-access-review");
      fireEvent.click(guideItem);

      const stepCheckbox = screen.getAllByRole("checkbox")[0];
      fireEvent.click(stepCheckbox);

      expect(stepCheckbox).toBeChecked();
    });

    it("should show progress indicator", () => {
      render(<ComplianceGuides guides={mockGuides} enableProgress />);
      const guideItem = screen.getByTestId("guide-soc2-access-review");
      fireEvent.click(guideItem);

      // Mark first step complete
      const stepCheckbox = screen.getAllByRole("checkbox")[0];
      fireEvent.click(stepCheckbox);

      // Progress is shown in multiple places, verify at least one exists
      const progressIndicators = screen.getAllByText(/1 of 3 steps/i);
      expect(progressIndicators.length).toBeGreaterThan(0);
    });

    it("should call onProgressChange when step toggled", () => {
      const onProgressChange = vi.fn();
      render(
        <ComplianceGuides
          guides={mockGuides}
          enableProgress
          onProgressChange={onProgressChange}
        />,
      );

      const guideItem = screen.getByTestId("guide-soc2-access-review");
      fireEvent.click(guideItem);

      const stepCheckbox = screen.getAllByRole("checkbox")[0];
      fireEvent.click(stepCheckbox);

      expect(onProgressChange).toHaveBeenCalledWith(
        "soc2-access-review",
        0,
        true,
      );
    });
  });

  describe("Actions", () => {
    it("should show print button when expanded", () => {
      render(<ComplianceGuides guides={mockGuides} />);
      const guideItem = screen.getByTestId("guide-soc2-access-review");
      fireEvent.click(guideItem);

      expect(screen.getByTestId("print-guide")).toBeInTheDocument();
    });

    it("should call onPrint when print clicked", () => {
      const onPrint = vi.fn();
      render(<ComplianceGuides guides={mockGuides} onPrint={onPrint} />);
      const guideItem = screen.getByTestId("guide-soc2-access-review");
      fireEvent.click(guideItem);

      fireEvent.click(screen.getByTestId("print-guide"));

      expect(onPrint).toHaveBeenCalledWith(mockGuides[0]);
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no guides", () => {
      render(<ComplianceGuides guides={[]} />);
      expect(screen.getByText(/no compliance guides/i)).toBeInTheDocument();
    });

    it("should show empty state when no matches", () => {
      render(<ComplianceGuides guides={mockGuides} />);
      const search = screen.getByTestId("guide-search");
      fireEvent.change(search, { target: { value: "nonexistent" } });

      expect(screen.getByText(/no guides found/i)).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible search input", () => {
      render(<ComplianceGuides guides={mockGuides} />);
      expect(screen.getByRole("searchbox")).toBeInTheDocument();
    });

    it("should use expandable section pattern", () => {
      render(<ComplianceGuides guides={mockGuides} />);
      const guideItem = screen.getByTestId("guide-soc2-access-review");
      expect(guideItem).toHaveAttribute("aria-expanded", "false");

      fireEvent.click(guideItem);
      expect(guideItem).toHaveAttribute("aria-expanded", "true");
    });
  });
});
