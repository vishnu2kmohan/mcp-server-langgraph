/**
 * GDPRPanel Tests
 *
 * Phase 5: Compliance Dashboards
 * Tests for GDPR compliance panel.
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { GDPRPanel, type GDPRControl } from "./GDPRPanel";

import { TestProvider } from "@/test-utils";

describe("GDPRPanel", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });
  const mockControls: GDPRControl[] = [
    {
      id: "Art5",
      name: "Principles of Processing",
      article: "Article 5",
      status: "compliant",
      lastAssessed: "2025-12-01T00:00:00Z",
    },
    {
      id: "Art6",
      name: "Lawfulness of Processing",
      article: "Article 6",
      status: "compliant",
      lastAssessed: "2025-12-01T00:00:00Z",
    },
    {
      id: "Art17",
      name: "Right to Erasure",
      article: "Article 17",
      status: "partial",
      lastAssessed: "2025-11-20T00:00:00Z",
      pendingRequests: 3,
    },
  ];

  describe("Rendering", () => {
    it("renders the panel container", () => {
      render(
        <TestProvider>
          <GDPRPanel controls={mockControls} />
        </TestProvider>,
      );
      expect(screen.getByTestId("gdpr-panel")).toBeInTheDocument();
    });

    it("renders panel header with GDPR title", () => {
      render(
        <TestProvider>
          <GDPRPanel controls={mockControls} />
        </TestProvider>,
      );
      expect(screen.getByText(/gdpr/i)).toBeInTheDocument();
    });

    it("renders all controls", () => {
      render(
        <TestProvider>
          <GDPRPanel controls={mockControls} />
        </TestProvider>,
      );
      expect(screen.getByText("Principles of Processing")).toBeInTheDocument();
      expect(screen.getByText("Lawfulness of Processing")).toBeInTheDocument();
      expect(screen.getByText("Right to Erasure")).toBeInTheDocument();
    });

    it("shows empty state when no controls", () => {
      render(
        <TestProvider>
          <GDPRPanel controls={[]} />
        </TestProvider>,
      );
      expect(screen.getByText(/no controls/i)).toBeInTheDocument();
    });
  });

  describe("Article Display", () => {
    it("shows article reference", () => {
      render(
        <TestProvider>
          <GDPRPanel controls={[mockControls[0]]} />
        </TestProvider>,
      );
      expect(screen.getByText(/article 5/i)).toBeInTheDocument();
    });
  });

  describe("Data Subject Requests", () => {
    it("shows pending requests count when available", () => {
      render(
        <TestProvider>
          <GDPRPanel controls={[mockControls[2]]} />
        </TestProvider>,
      );
      expect(screen.getByText(/3/)).toBeInTheDocument();
    });

    it("shows pending requests label", () => {
      render(
        <TestProvider>
          <GDPRPanel controls={[mockControls[2]]} />
        </TestProvider>,
      );
      expect(screen.getByText(/pending request/i)).toBeInTheDocument();
    });
  });

  describe("Summary Statistics", () => {
    it("shows compliance percentage", () => {
      render(
        <TestProvider>
          <GDPRPanel controls={mockControls} />
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
          <GDPRPanel controls={[]} isLoading={true} />
        </TestProvider>,
      );
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });
});
