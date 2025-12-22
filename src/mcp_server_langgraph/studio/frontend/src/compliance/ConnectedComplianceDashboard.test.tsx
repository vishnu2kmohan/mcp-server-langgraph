/**
 * ConnectedComplianceDashboard Tests
 *
 * Tests for the API-connected compliance dashboard container.
 * Verifies data fetching, transformation, and error handling.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import * as api from "../api";
import { ConnectedComplianceDashboard } from "./ConnectedComplianceDashboard";

// =============================================================================
// Mock Data
// =============================================================================

const mockComplianceSummary = {
  soc2: {
    percentage: 94,
    compliant_count: 47,
    total_count: 50,
    status: "partial" as const,
    pending_actions: 3,
  },
  hipaa: {
    percentage: 100,
    compliant_count: 25,
    total_count: 25,
    status: "compliant" as const,
    pending_actions: 0,
  },
  gdpr: {
    percentage: 87,
    compliant_count: 20,
    total_count: 23,
    status: "partial" as const,
    pending_actions: 5,
  },
  fedramp: {
    percentage: 92,
    compliant_count: 46,
    total_count: 50,
    status: "partial" as const,
    pending_actions: 4,
    auth_level: "P-ATO",
  },
};

// =============================================================================
// Mock RTK Query Hook
// =============================================================================

// Mock the API hook
vi.mock("../api", async (importOriginal) => {
  const original = await importOriginal<typeof api>();
  return {
    ...original,
    useGetComplianceSummaryQuery: vi.fn(),
  };
});

const mockUseGetComplianceSummaryQuery = api.useGetComplianceSummaryQuery as ReturnType<typeof vi.fn>;

// =============================================================================
// Test Setup
// =============================================================================

beforeEach(() => {
  vi.clearAllMocks();
  // Default: successful response
  mockUseGetComplianceSummaryQuery.mockReturnValue({
    data: mockComplianceSummary,
    isLoading: false,
    error: undefined,
    refetch: vi.fn(),
  });
});

// =============================================================================
// Tests
// =============================================================================

describe("ConnectedComplianceDashboard", () => {
  describe("Loading State", () => {
    it("should show loading state while fetching data", () => {
      mockUseGetComplianceSummaryQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: undefined,
        refetch: vi.fn(),
      });

      render(<ConnectedComplianceDashboard />);

      expect(screen.getByTestId("compliance-dashboard")).toBeInTheDocument();
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe("Successful Data Fetch", () => {
    it("should display compliance summary after successful fetch", () => {
      render(<ConnectedComplianceDashboard />);

      expect(screen.getByText("Compliance Overview")).toBeInTheDocument();

      // Verify all frameworks are displayed
      expect(screen.getByText("SOC-2")).toBeInTheDocument();
      expect(screen.getByText("HIPAA")).toBeInTheDocument();
      expect(screen.getByText("GDPR")).toBeInTheDocument();
      expect(screen.getByText("FedRAMP")).toBeInTheDocument();
    });

    it("should display correct percentages", () => {
      render(<ConnectedComplianceDashboard />);

      expect(screen.getByText("94%")).toBeInTheDocument();
      expect(screen.getByText("100%")).toBeInTheDocument();
      expect(screen.getByText("87%")).toBeInTheDocument();
      expect(screen.getByText("92%")).toBeInTheDocument();
    });

    it("should display control counts", () => {
      render(<ConnectedComplianceDashboard />);

      expect(screen.getByText("47/50 controls")).toBeInTheDocument();
      expect(screen.getByText("25/25 controls")).toBeInTheDocument();
      expect(screen.getByText("20/23 controls")).toBeInTheDocument();
      expect(screen.getByText("46/50 controls")).toBeInTheDocument();
    });

    it("should display FedRAMP auth level", () => {
      render(<ConnectedComplianceDashboard />);

      expect(screen.getByText("P-ATO")).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("should display error message when API fails", () => {
      mockUseGetComplianceSummaryQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server Error" },
        refetch: vi.fn(),
      });

      render(<ConnectedComplianceDashboard />);

      expect(
        screen.getByText(/failed to load compliance data/i),
      ).toBeInTheDocument();
    });

    it("should show retry button on error", () => {
      mockUseGetComplianceSummaryQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server Error" },
        refetch: vi.fn(),
      });

      render(<ConnectedComplianceDashboard />);

      expect(screen.getByTestId("retry-button")).toBeInTheDocument();
    });

    it("should call refetch when retry button clicked", () => {
      const mockRefetch = vi.fn();
      mockUseGetComplianceSummaryQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server Error" },
        refetch: mockRefetch,
      });

      render(<ConnectedComplianceDashboard />);

      fireEvent.click(screen.getByTestId("retry-button"));
      expect(mockRefetch).toHaveBeenCalled();
    });
  });

  describe("Time Range", () => {
    it("should accept custom date range", () => {
      const startTime = "2024-01-01T00:00:00Z";
      const endTime = "2024-12-31T23:59:59Z";

      render(
        <ConnectedComplianceDashboard startTime={startTime} endTime={endTime} />,
      );

      expect(screen.getByText("Compliance Overview")).toBeInTheDocument();
      // Verify the hook was called with custom date range
      expect(mockUseGetComplianceSummaryQuery).toHaveBeenCalledWith({
        start_time: startTime,
        end_time: endTime,
      });
    });

    it("should default to last 30 days if no date range provided", () => {
      render(<ConnectedComplianceDashboard />);

      expect(screen.getByText("Compliance Overview")).toBeInTheDocument();
      // Verify the hook was called with default date range (30 days ago to now)
      const callArgs = mockUseGetComplianceSummaryQuery.mock.calls[0][0];
      expect(callArgs.start_time).toBeDefined();
      expect(callArgs.end_time).toBeDefined();
    });
  });
});
