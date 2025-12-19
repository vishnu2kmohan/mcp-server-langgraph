/**
 * FedRAMPPanel Tests
 *
 * Phase 5: Compliance Dashboards
 * Tests for FedRAMP compliance panel.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FedRAMPPanel, type FedRAMPControl } from "./FedRAMPPanel";

describe("FedRAMPPanel", () => {
  const mockControls: FedRAMPControl[] = [
    {
      id: "AC-1",
      name: "Access Control Policy",
      family: "Access Control",
      impact: "high",
      status: "compliant",
      lastAssessed: "2025-12-01T00:00:00Z",
    },
    {
      id: "AU-1",
      name: "Audit Policy",
      family: "Audit and Accountability",
      impact: "high",
      status: "compliant",
      lastAssessed: "2025-12-01T00:00:00Z",
    },
    {
      id: "SC-1",
      name: "System Protection Policy",
      family: "System and Communications Protection",
      impact: "moderate",
      status: "partial",
      lastAssessed: "2025-11-20T00:00:00Z",
      poamId: "POAM-123",
    },
  ];

  const mockAuthStatus = {
    level: "P-ATO" as const,
    grantedDate: "2025-01-15T00:00:00Z",
    expiresDate: "2028-01-15T00:00:00Z",
  };

  describe("Rendering", () => {
    it("renders the panel container", () => {
      render(
        <FedRAMPPanel controls={mockControls} authStatus={mockAuthStatus} />,
      );
      expect(screen.getByTestId("fedramp-panel")).toBeInTheDocument();
    });

    it("renders panel header with FedRAMP title", () => {
      render(
        <FedRAMPPanel controls={mockControls} authStatus={mockAuthStatus} />,
      );
      expect(screen.getByText(/fedramp/i)).toBeInTheDocument();
    });

    it("renders all controls", () => {
      render(
        <FedRAMPPanel controls={mockControls} authStatus={mockAuthStatus} />,
      );
      expect(screen.getByText("Access Control Policy")).toBeInTheDocument();
      expect(screen.getByText("Audit Policy")).toBeInTheDocument();
      expect(screen.getByText("System Protection Policy")).toBeInTheDocument();
    });

    it("shows empty state when no controls", () => {
      render(<FedRAMPPanel controls={[]} authStatus={mockAuthStatus} />);
      expect(screen.getByText(/no controls/i)).toBeInTheDocument();
    });
  });

  describe("Authorization Status", () => {
    it("shows P-ATO authorization level", () => {
      render(
        <FedRAMPPanel controls={mockControls} authStatus={mockAuthStatus} />,
      );
      expect(screen.getByText(/p-ato/i)).toBeInTheDocument();
    });

    it("shows ATO authorization level", () => {
      render(
        <FedRAMPPanel
          controls={mockControls}
          authStatus={{ ...mockAuthStatus, level: "ATO" }}
        />,
      );
      expect(screen.getByText(/^ato$/i)).toBeInTheDocument();
    });

    it("shows authorization expiry date", () => {
      render(
        <FedRAMPPanel controls={mockControls} authStatus={mockAuthStatus} />,
      );
      expect(screen.getByText(/2028/)).toBeInTheDocument();
    });
  });

  describe("Impact Level Display", () => {
    it("shows high impact level", () => {
      render(
        <FedRAMPPanel
          controls={[mockControls[0]]}
          authStatus={mockAuthStatus}
        />,
      );
      expect(screen.getByText(/high/i)).toBeInTheDocument();
    });

    it("shows moderate impact level", () => {
      render(
        <FedRAMPPanel
          controls={[mockControls[2]]}
          authStatus={mockAuthStatus}
        />,
      );
      expect(screen.getByText(/moderate/i)).toBeInTheDocument();
    });
  });

  describe("POA&M Tracking", () => {
    it("shows POA&M ID when available", () => {
      render(
        <FedRAMPPanel
          controls={[mockControls[2]]}
          authStatus={mockAuthStatus}
        />,
      );
      expect(screen.getByText(/poam-123/i)).toBeInTheDocument();
    });
  });

  describe("Summary Statistics", () => {
    it("shows compliance percentage", () => {
      render(
        <FedRAMPPanel controls={mockControls} authStatus={mockAuthStatus} />,
      );
      // 2 compliant out of 3 = 67%
      expect(screen.getByText(/67%/)).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("shows loading spinner when isLoading is true", () => {
      render(
        <FedRAMPPanel
          controls={[]}
          authStatus={mockAuthStatus}
          isLoading={true}
        />,
      );
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });
});
