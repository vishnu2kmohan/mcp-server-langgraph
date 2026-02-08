/**
 * FedRAMPPanel Tests
 *
 * Phase 5: Compliance Dashboards
 * Tests for FedRAMP compliance panel.
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { FedRAMPPanel, type FedRAMPControl } from "./FedRAMPPanel";

import { TestProvider } from "@/test-utils";

describe("FedRAMPPanel", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });
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
        <TestProvider>
          <FedRAMPPanel controls={mockControls} authStatus={mockAuthStatus} />
        </TestProvider>,
      );
      expect(screen.getByTestId("fedramp-panel")).toBeInTheDocument();
    });

    it("renders panel header with FedRAMP title", () => {
      render(
        <TestProvider>
          <FedRAMPPanel controls={mockControls} authStatus={mockAuthStatus} />
        </TestProvider>,
      );
      expect(screen.getByText(/fedramp/i)).toBeInTheDocument();
    });

    it("renders all controls", () => {
      render(
        <TestProvider>
          <FedRAMPPanel controls={mockControls} authStatus={mockAuthStatus} />
        </TestProvider>,
      );
      expect(screen.getByText("Access Control Policy")).toBeInTheDocument();
      expect(screen.getByText("Audit Policy")).toBeInTheDocument();
      expect(screen.getByText("System Protection Policy")).toBeInTheDocument();
    });

    it("shows empty state when no controls", () => {
      render(
        <TestProvider>
          <FedRAMPPanel controls={[]} authStatus={mockAuthStatus} />
        </TestProvider>,
      );
      expect(screen.getByText(/no controls/i)).toBeInTheDocument();
    });
  });

  describe("Authorization Status", () => {
    it("shows P-ATO authorization level", () => {
      render(
        <TestProvider>
          <FedRAMPPanel controls={mockControls} authStatus={mockAuthStatus} />
        </TestProvider>,
      );
      expect(screen.getByText(/p-ato/i)).toBeInTheDocument();
    });

    it("shows ATO authorization level", () => {
      render(
        <TestProvider>
          <FedRAMPPanel
            controls={mockControls}
            authStatus={{ ...mockAuthStatus, level: "ATO" }}
          />
        </TestProvider>,
      );
      expect(screen.getByText(/^ato$/i)).toBeInTheDocument();
    });

    it("shows authorization expiry date", () => {
      render(
        <TestProvider>
          <FedRAMPPanel controls={mockControls} authStatus={mockAuthStatus} />
        </TestProvider>,
      );
      expect(screen.getByText(/2028/)).toBeInTheDocument();
    });
  });

  describe("Impact Level Display", () => {
    it("shows high impact level", () => {
      render(
        <TestProvider>
          <FedRAMPPanel
            controls={[mockControls[0]]}
            authStatus={mockAuthStatus}
          />
        </TestProvider>,
      );
      expect(screen.getByText(/high/i)).toBeInTheDocument();
    });

    it("shows moderate impact level", () => {
      render(
        <TestProvider>
          <FedRAMPPanel
            controls={[mockControls[2]]}
            authStatus={mockAuthStatus}
          />
        </TestProvider>,
      );
      expect(screen.getByText(/moderate/i)).toBeInTheDocument();
    });
  });

  describe("POA&M Tracking", () => {
    it("shows POA&M ID when available", () => {
      render(
        <TestProvider>
          <FedRAMPPanel
            controls={[mockControls[2]]}
            authStatus={mockAuthStatus}
          />
        </TestProvider>,
      );
      expect(screen.getByText(/poam-123/i)).toBeInTheDocument();
    });
  });

  describe("Summary Statistics", () => {
    it("shows compliance percentage", () => {
      render(
        <TestProvider>
          <FedRAMPPanel controls={mockControls} authStatus={mockAuthStatus} />
        </TestProvider>,
      );
      // 2 compliant out of 3 = 67%
      expect(screen.getByText(/67%/)).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("shows loading spinner when isLoading is true", () => {
      render(
        <TestProvider>
          <FedRAMPPanel
            controls={[]}
            authStatus={mockAuthStatus}
            isLoading={true}
          />
        </TestProvider>,
      );
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });
});
