/**
 * ProjectDetailPage Feature Flags Tests
 *
 * Tests for feature flag integration controlling tab visibility.
 * Split from ProjectDetailPage.test.tsx for memory optimization.
 *
 * @see ProjectDetailPage.setup.ts for shared mocks and utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor, cleanup } from "@testing-library/react";

// Import shared setup
import {
  resetAllMocks,
  setupDefaultMocks,
  renderWithRouter,
} from "./ProjectDetailPage.setup";

// =============================================================================
// MOCKS - Must be defined before component imports
// =============================================================================

vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useGetFeatureFlagsQuery: vi.fn(),
    useGetProjectQuery: vi.fn(),
    useGetProjectObservabilityQuery: vi.fn(),
    useGetProjectLogsQuery: vi.fn(),
    useGetProjectAlertsQuery: vi.fn(),
    useGetProjectCostSummaryQuery: vi.fn(),
    useGetProjectCostByModelQuery: vi.fn(),
    useAddProjectMemberMutation: vi.fn(),
    useRemoveProjectMemberMutation: vi.fn(),
    useAddProjectConnectionMutation: vi.fn(),
  };
});

// Import mocked hooks
import {
  useGetFeatureFlagsQuery,
  useGetProjectQuery,
  useGetProjectObservabilityQuery,
  useGetProjectLogsQuery,
  useGetProjectAlertsQuery,
  useGetProjectCostSummaryQuery,
  useGetProjectCostByModelQuery,
  useAddProjectMemberMutation,
  useRemoveProjectMemberMutation,
  useAddProjectConnectionMutation,
} from "../../api";

// Cast for type safety
const mockUseGetFeatureFlagsQuery = useGetFeatureFlagsQuery as ReturnType<
  typeof vi.fn
>;
const mockUseGetProjectQuery = useGetProjectQuery as ReturnType<typeof vi.fn>;
const mockUseGetProjectObservabilityQuery =
  useGetProjectObservabilityQuery as ReturnType<typeof vi.fn>;
const mockUseGetProjectLogsQuery = useGetProjectLogsQuery as ReturnType<
  typeof vi.fn
>;
const mockUseGetProjectAlertsQuery = useGetProjectAlertsQuery as ReturnType<
  typeof vi.fn
>;
const mockUseGetProjectCostSummaryQuery =
  useGetProjectCostSummaryQuery as ReturnType<typeof vi.fn>;
const mockUseGetProjectCostByModelQuery =
  useGetProjectCostByModelQuery as ReturnType<typeof vi.fn>;
const mockUseAddProjectMemberMutation =
  useAddProjectMemberMutation as ReturnType<typeof vi.fn>;
const mockUseRemoveProjectMemberMutation =
  useRemoveProjectMemberMutation as ReturnType<typeof vi.fn>;
const mockUseAddProjectConnectionMutation =
  useAddProjectConnectionMutation as ReturnType<typeof vi.fn>;

// =============================================================================
// TEST LIFECYCLE
// =============================================================================

describe("ProjectDetailPage - Feature Flags", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAllMocks();
    setupDefaultMocks({
      useGetFeatureFlagsQuery: mockUseGetFeatureFlagsQuery,
      useGetProjectQuery: mockUseGetProjectQuery,
      useGetProjectObservabilityQuery: mockUseGetProjectObservabilityQuery,
      useGetProjectLogsQuery: mockUseGetProjectLogsQuery,
      useGetProjectAlertsQuery: mockUseGetProjectAlertsQuery,
      useGetProjectCostSummaryQuery: mockUseGetProjectCostSummaryQuery,
      useGetProjectCostByModelQuery: mockUseGetProjectCostByModelQuery,
      useAddProjectMemberMutation: mockUseAddProjectMemberMutation,
      useRemoveProjectMemberMutation: mockUseRemoveProjectMemberMutation,
      useAddProjectConnectionMutation: mockUseAddProjectConnectionMutation,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // ALL FEATURES ENABLED
  // ===========================================================================

  describe("All Features Enabled", () => {
    it("should show all tabs when all features are enabled", async () => {
      renderWithRouter(
        "project-123",
        {
          workflows: true,
          observability: true,
          cost_dashboard: true,
        },
        mockUseGetFeatureFlagsQuery,
      );

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // All tabs should be visible
      expect(
        screen.getByRole("button", { name: /Sessions/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Workflows/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Connections/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Observability/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Cost/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Members/i }),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // WORKFLOWS FEATURE DISABLED
  // ===========================================================================

  describe("Workflows Feature Disabled", () => {
    it("should hide Workflows tab when workflows is false", async () => {
      renderWithRouter(
        "project-123",
        {
          workflows: false,
          observability: true,
          cost_dashboard: true,
        },
        mockUseGetFeatureFlagsQuery,
      );

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Sessions tab should still be visible
      expect(
        screen.getByRole("button", { name: /Sessions/i }),
      ).toBeInTheDocument();

      // Workflows tab should be hidden
      expect(
        screen.queryByRole("button", { name: /Workflows/i }),
      ).not.toBeInTheDocument();

      // Other tabs should still be visible
      expect(
        screen.getByRole("button", { name: /Connections/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Observability/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Cost/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Members/i }),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // OBSERVABILITY FEATURE DISABLED
  // ===========================================================================

  describe("Observability Feature Disabled", () => {
    it("should hide Observability tab when observability is false", async () => {
      renderWithRouter(
        "project-123",
        {
          workflows: true,
          observability: false,
          cost_dashboard: true,
        },
        mockUseGetFeatureFlagsQuery,
      );

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Sessions tab should still be visible
      expect(
        screen.getByRole("button", { name: /Sessions/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Workflows/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Connections/i }),
      ).toBeInTheDocument();

      // Observability tab should be hidden
      expect(
        screen.queryByRole("button", { name: /Observability/i }),
      ).not.toBeInTheDocument();

      // Other tabs should still be visible
      expect(screen.getByRole("button", { name: /Cost/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Members/i }),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // COST DASHBOARD DISABLED
  // ===========================================================================

  describe("Cost Dashboard Disabled", () => {
    it("should hide Cost tab when cost_dashboard is false", async () => {
      renderWithRouter(
        "project-123",
        {
          workflows: true,
          observability: true,
          cost_dashboard: false,
        },
        mockUseGetFeatureFlagsQuery,
      );

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Sessions tab should still be visible
      expect(
        screen.getByRole("button", { name: /Sessions/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Workflows/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Connections/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Observability/i }),
      ).toBeInTheDocument();

      // Cost tab should be hidden
      expect(
        screen.queryByRole("button", { name: /Cost/i }),
      ).not.toBeInTheDocument();

      // Members tab should still be visible
      expect(
        screen.getByRole("button", { name: /Members/i }),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // MULTIPLE FEATURES DISABLED
  // ===========================================================================

  describe("Multiple Features Disabled", () => {
    it("should hide multiple tabs when multiple features are disabled", async () => {
      renderWithRouter(
        "project-123",
        {
          workflows: false,
          observability: false,
          cost_dashboard: false,
        },
        mockUseGetFeatureFlagsQuery,
      );

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Essential tabs should always be visible
      expect(
        screen.getByRole("button", { name: /Sessions/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Connections/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Members/i }),
      ).toBeInTheDocument();

      // Feature-gated tabs should be hidden
      expect(
        screen.queryByRole("button", { name: /Workflows/i }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /Observability/i }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /Cost/i }),
      ).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // DEFAULT BEHAVIOR
  // ===========================================================================

  describe("Default Behavior", () => {
    it("should show all tabs by default (all features enabled)", async () => {
      // No feature flags passed - should default to all enabled
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // All tabs should be visible
      expect(
        screen.getByRole("button", { name: /Sessions/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Workflows/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Connections/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Observability/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Cost/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Members/i }),
      ).toBeInTheDocument();
    });
  });
});
