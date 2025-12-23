/**
 * HIPAAPanel Tests
 *
 * Phase 5: Compliance Dashboards
 * Tests for HIPAA compliance panel.
 */
import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { HIPAAPanel, type HIPAAControl } from "./HIPAAPanel";

describe("HIPAAPanel", () => {
  afterEach(() => {
    cleanup();
  });
  const mockControls: HIPAAControl[] = [
    {
      id: "164.308(a)(1)",
      name: "Security Management Process",
      category: "administrative",
      status: "compliant",
      lastAssessed: "2025-12-01T00:00:00Z",
    },
    {
      id: "164.310(a)(1)",
      name: "Facility Access Controls",
      category: "physical",
      status: "compliant",
      lastAssessed: "2025-12-01T00:00:00Z",
    },
    {
      id: "164.312(a)(1)",
      name: "Access Control",
      category: "technical",
      status: "partial",
      lastAssessed: "2025-11-20T00:00:00Z",
      phiAccessCount: 42,
    },
  ];

  describe("Rendering", () => {
    it("renders the panel container", () => {
      render(<HIPAAPanel controls={mockControls} />);
      expect(screen.getByTestId("hipaa-panel")).toBeInTheDocument();
    });

    it("renders panel header with HIPAA title", () => {
      render(<HIPAAPanel controls={mockControls} />);
      expect(screen.getByText(/hipaa/i)).toBeInTheDocument();
    });

    it("renders all controls", () => {
      render(<HIPAAPanel controls={mockControls} />);
      expect(
        screen.getByText("Security Management Process"),
      ).toBeInTheDocument();
      expect(screen.getByText("Facility Access Controls")).toBeInTheDocument();
      expect(screen.getByText("Access Control")).toBeInTheDocument();
    });

    it("shows empty state when no controls", () => {
      render(<HIPAAPanel controls={[]} />);
      expect(screen.getByText(/no controls/i)).toBeInTheDocument();
    });
  });

  describe("Category Display", () => {
    it("shows administrative category label", () => {
      render(<HIPAAPanel controls={[mockControls[0]]} />);
      expect(screen.getByText(/administrative/i)).toBeInTheDocument();
    });

    it("shows physical category label", () => {
      render(<HIPAAPanel controls={[mockControls[1]]} />);
      expect(screen.getByText(/physical/i)).toBeInTheDocument();
    });

    it("shows technical category label", () => {
      render(<HIPAAPanel controls={[mockControls[2]]} />);
      expect(screen.getByText(/technical/i)).toBeInTheDocument();
    });
  });

  describe("PHI Access Tracking", () => {
    it("shows PHI access count when available", () => {
      render(<HIPAAPanel controls={[mockControls[2]]} />);
      expect(screen.getByText(/42/)).toBeInTheDocument();
    });

    it("shows PHI access indicator", () => {
      render(<HIPAAPanel controls={[mockControls[2]]} />);
      expect(screen.getByText(/phi access/i)).toBeInTheDocument();
    });
  });

  describe("Summary Statistics", () => {
    it("shows compliance percentage", () => {
      render(<HIPAAPanel controls={mockControls} />);
      // 2 compliant out of 3 = 67%
      expect(screen.getByText(/67%/)).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("shows loading spinner when isLoading is true", () => {
      render(<HIPAAPanel controls={[]} isLoading={true} />);
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });
});
