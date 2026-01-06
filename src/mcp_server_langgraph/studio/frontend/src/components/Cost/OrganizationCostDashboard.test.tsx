/**
 * OrganizationCostDashboard Tests
 *
 * TDD tests for the organizational cost dashboard component.
 * Tests cover:
 * - View mode switching (organization, project, team)
 * - Data display for each view
 * - Click interactions for drill-down
 * - Loading and error states
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { OrganizationCostDashboard } from "./OrganizationCostDashboard";

// Mock RTK Query hooks
vi.mock("../../api", () => ({
  useGetCostByOrganizationQuery: vi.fn(),
  useGetCostByProjectQuery: vi.fn(),
  useGetCostByTeamQuery: vi.fn(),
}));

import * as apiModule from "../../api";

// Mock data uses camelCase (ADR-0091 Phase 6) - matches RTK Query transformResponse output
const mockOrgCosts = [
  {
    organizationId: "organization:acme",
    totalCost: 500.0,
    totalTokens: 100000,
    requestCount: 250,
  },
  {
    organizationId: "organization:globex",
    totalCost: 300.0,
    totalTokens: 60000,
    requestCount: 150,
  },
];

const mockProjectCosts = [
  {
    projectId: "project:alpha",
    organizationId: "organization:acme",
    totalCost: 250.0,
    totalTokens: 50000,
    requestCount: 125,
  },
  {
    projectId: "project:beta",
    organizationId: "organization:acme",
    totalCost: 250.0,
    totalTokens: 50000,
    requestCount: 125,
  },
];

const mockTeamCosts = [
  {
    teamId: "team:engineering",
    organizationId: "organization:acme",
    projectId: "project:alpha",
    totalCost: 150.0,
    totalTokens: 30000,
    requestCount: 75,
  },
  {
    teamId: "team:data",
    organizationId: "organization:acme",
    projectId: "project:alpha",
    totalCost: 100.0,
    totalTokens: 20000,
    requestCount: 50,
  },
];

const mockedUseGetCostByOrganizationQuery = vi.mocked(
  apiModule.useGetCostByOrganizationQuery,
);
const mockedUseGetCostByProjectQuery = vi.mocked(
  apiModule.useGetCostByProjectQuery,
);
const mockedUseGetCostByTeamQuery = vi.mocked(apiModule.useGetCostByTeamQuery);

// Create a minimal store for testing
const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

const renderWithProviders = (component: React.ReactElement) => {
  const store = createTestStore();
  return render(<Provider store={store}>{component}</Provider>);
};

describe("OrganizationCostDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mocks to default successful responses
    mockedUseGetCostByOrganizationQuery.mockReturnValue({
      data: mockOrgCosts,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof apiModule.useGetCostByOrganizationQuery>);

    mockedUseGetCostByProjectQuery.mockReturnValue({
      data: mockProjectCosts,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof apiModule.useGetCostByProjectQuery>);

    mockedUseGetCostByTeamQuery.mockReturnValue({
      data: mockTeamCosts,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof apiModule.useGetCostByTeamQuery>);
  });

  afterEach(() => {
    cleanup();
  });

  describe("Organization View", () => {
    it("should display organization view by default", () => {
      renderWithProviders(<OrganizationCostDashboard />);
      expect(screen.getByText("Cost by Organization")).toBeInTheDocument();
    });

    it("should display organization cost data", () => {
      renderWithProviders(<OrganizationCostDashboard />);
      expect(screen.getByText("acme")).toBeInTheDocument();
      expect(screen.getByText("globex")).toBeInTheDocument();
      expect(screen.getByText("$500.00")).toBeInTheDocument();
      expect(screen.getByText("$300.00")).toBeInTheDocument();
    });

    it("should display summary cards with totals", () => {
      renderWithProviders(<OrganizationCostDashboard />);
      expect(screen.getByText("Total Organizations")).toBeInTheDocument();
      expect(screen.getByText("Total Cost")).toBeInTheDocument();
      expect(screen.getByText("Total Requests")).toBeInTheDocument();
      expect(screen.getByText("2")).toBeInTheDocument(); // 2 organizations
      expect(screen.getByText("$800.00")).toBeInTheDocument(); // Total cost
      expect(screen.getByText("400")).toBeInTheDocument(); // Total requests
    });

    it("should display percentage of total for each organization", () => {
      renderWithProviders(<OrganizationCostDashboard />);
      expect(screen.getByText("62.5%")).toBeInTheDocument(); // acme
      expect(screen.getByText("37.5%")).toBeInTheDocument(); // globex
    });
  });

  describe("Project View", () => {
    it("should switch to project view when clicking Projects tab", () => {
      renderWithProviders(<OrganizationCostDashboard />);
      fireEvent.click(screen.getByRole("button", { name: /Projects/ }));
      expect(screen.getByText("Cost by Project")).toBeInTheDocument();
    });

    it("should display project cost data", () => {
      renderWithProviders(<OrganizationCostDashboard />);
      fireEvent.click(screen.getByRole("button", { name: /Projects/ }));
      expect(screen.getByText("alpha")).toBeInTheDocument();
      expect(screen.getByText("beta")).toBeInTheDocument();
    });
  });

  describe("Team View", () => {
    it("should switch to team view when clicking Teams tab", () => {
      renderWithProviders(<OrganizationCostDashboard />);
      fireEvent.click(screen.getByRole("button", { name: /Teams/ }));
      expect(screen.getByText("Cost by Team")).toBeInTheDocument();
    });

    it("should display team cost data", () => {
      renderWithProviders(<OrganizationCostDashboard />);
      fireEvent.click(screen.getByRole("button", { name: /Teams/ }));
      expect(screen.getByText("engineering")).toBeInTheDocument();
      expect(screen.getByText("data")).toBeInTheDocument();
    });
  });

  describe("Drill-down Navigation", () => {
    it("should switch to project view when clicking an organization row", () => {
      renderWithProviders(<OrganizationCostDashboard />);
      fireEvent.click(screen.getByText("acme"));
      expect(screen.getByText("Cost by Project")).toBeInTheDocument();
    });

    it("should switch to team view when clicking a project row", () => {
      renderWithProviders(<OrganizationCostDashboard />);
      fireEvent.click(screen.getByRole("button", { name: /Projects/ }));
      fireEvent.click(screen.getByText("alpha"));
      expect(screen.getByText("Cost by Team")).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should display loading skeletons when data is loading", () => {
      mockedUseGetCostByOrganizationQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof apiModule.useGetCostByOrganizationQuery>);

      renderWithProviders(<OrganizationCostDashboard />);
      // Check for skeleton animation class
      const skeletons = document.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe("Error State", () => {
    it("should display error message when API fails", () => {
      mockedUseGetCostByOrganizationQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: { message: "Failed to load" },
        refetch: vi.fn(),
      } as ReturnType<typeof apiModule.useGetCostByOrganizationQuery>);

      renderWithProviders(<OrganizationCostDashboard />);
      expect(
        screen.getByText("Failed to load organizational cost data"),
      ).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should display empty state when no organizations exist", () => {
      mockedUseGetCostByOrganizationQuery.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof apiModule.useGetCostByOrganizationQuery>);

      renderWithProviders(<OrganizationCostDashboard />);
      expect(
        screen.getByText("No organizational cost data available"),
      ).toBeInTheDocument();
    });
  });
});
