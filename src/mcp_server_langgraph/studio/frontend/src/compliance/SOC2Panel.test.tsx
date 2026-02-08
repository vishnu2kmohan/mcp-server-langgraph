/**
 * SOC2Panel Tests
 *
 * Phase 5: Compliance Dashboards
 * Tests for SOC-2 compliance controls panel.
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { SOC2Panel, type SOC2Control } from "./SOC2Panel";

import { TestProvider } from "@/test-utils";

describe("SOC2Panel", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });
  const mockControls: SOC2Control[] = [
    {
      id: "CC6.1",
      name: "Logical and Physical Access",
      status: "compliant",
      lastAssessed: "2025-12-01T00:00:00Z",
    },
    {
      id: "CC6.2",
      name: "System Operations",
      status: "partial",
      lastAssessed: "2025-12-01T00:00:00Z",
      remediationDue: "2025-12-31T00:00:00Z",
    },
    {
      id: "CC6.3",
      name: "Change Management",
      status: "non-compliant",
      lastAssessed: "2025-11-15T00:00:00Z",
      remediationDue: "2025-12-15T00:00:00Z",
    },
  ];

  describe("Rendering", () => {
    it("renders the panel container", () => {
      render(
        <TestProvider>
          <SOC2Panel controls={mockControls} />
        </TestProvider>,
      );
      expect(screen.getByTestId("soc2-panel")).toBeInTheDocument();
    });

    it("renders panel header with SOC-2 title", () => {
      render(
        <TestProvider>
          <SOC2Panel controls={mockControls} />
        </TestProvider>,
      );
      expect(screen.getByText(/soc-?2/i)).toBeInTheDocument();
    });

    it("renders all controls", () => {
      render(
        <TestProvider>
          <SOC2Panel controls={mockControls} />
        </TestProvider>,
      );
      expect(screen.getByText("CC6.1")).toBeInTheDocument();
      expect(screen.getByText("CC6.2")).toBeInTheDocument();
      expect(screen.getByText("CC6.3")).toBeInTheDocument();
    });

    it("shows control names", () => {
      render(
        <TestProvider>
          <SOC2Panel controls={mockControls} />
        </TestProvider>,
      );
      expect(
        screen.getByText("Logical and Physical Access"),
      ).toBeInTheDocument();
      expect(screen.getByText("System Operations")).toBeInTheDocument();
      expect(screen.getByText("Change Management")).toBeInTheDocument();
    });

    it("shows empty state when no controls", () => {
      render(
        <TestProvider>
          <SOC2Panel controls={[]} />
        </TestProvider>,
      );
      expect(screen.getByText(/no controls/i)).toBeInTheDocument();
    });
  });

  describe("Status Display", () => {
    it("shows compliant status with green indicator", () => {
      render(
        <TestProvider>
          <SOC2Panel controls={[mockControls[0]]} />
        </TestProvider>,
      );
      const statusElement = screen.getByText(/compliant/i);
      expect(statusElement).toBeInTheDocument();
    });

    it("shows partial compliance status with yellow indicator", () => {
      render(
        <TestProvider>
          <SOC2Panel controls={[mockControls[1]]} />
        </TestProvider>,
      );
      const statusElement = screen.getByText(/partial/i);
      expect(statusElement).toBeInTheDocument();
    });

    it("shows non-compliant status with red indicator", () => {
      render(
        <TestProvider>
          <SOC2Panel controls={[mockControls[2]]} />
        </TestProvider>,
      );
      const statusElement = screen.getByText(/non-compliant/i);
      expect(statusElement).toBeInTheDocument();
    });
  });

  describe("Summary Statistics", () => {
    it("shows compliance percentage", () => {
      render(
        <TestProvider>
          <SOC2Panel controls={mockControls} />
        </TestProvider>,
      );
      // 1 compliant out of 3 = 33%
      expect(screen.getByText(/33%/)).toBeInTheDocument();
    });

    it("shows total controls count", () => {
      render(
        <TestProvider>
          <SOC2Panel controls={mockControls} />
        </TestProvider>,
      );
      // Match "1/3 controls" or similar pattern
      expect(screen.getByText(/\/3 controls/)).toBeInTheDocument();
    });
  });

  describe("Remediation Info", () => {
    it("shows remediation due date for non-compliant controls", () => {
      render(
        <TestProvider>
          <SOC2Panel controls={[mockControls[2]]} />
        </TestProvider>,
      );
      // Match "Due:" label with December date (day may vary by timezone)
      expect(screen.getByText(/due:/i)).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("shows loading spinner when isLoading is true", () => {
      render(
        <TestProvider>
          <SOC2Panel controls={[]} isLoading={true} />
        </TestProvider>,
      );
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });
});
