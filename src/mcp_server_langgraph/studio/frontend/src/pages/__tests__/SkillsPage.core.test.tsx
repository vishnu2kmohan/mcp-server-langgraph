/**
 * SkillsPage Core Tests
 *
 * Tests for header, tabs, browse tab, installed tab, updates tab,
 * loading states, refresh, retry button, and feature flag.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";

import {
  mockListMarketplaceSkillsQuery,
  mockListInstalledSkillsQuery,
  mockCheckSkillUpdatesQuery,
  mockInstallSkillMutation,
  mockUninstallSkillMutation,
  mockApplySkillUpdatesMutation,
  mockListMarketplacesQuery,
  mockAddMarketplaceMutation,
  mockRemoveMarketplaceMutation,
  mockSyncMarketplaceMutation,
  mockUseFeatureFlags,
  createTestStore,
  mockSkills,
  resetAllMocks,
} from "./SkillsPage.fixtures";

vi.mock("../../contexts/FeatureFlagContext", async () => {
  const actual = await vi.importActual("../../contexts/FeatureFlagContext");
  return {
    ...actual,
    useFeatureFlags: () => mockUseFeatureFlags(),
  };
});

vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useListMarketplaceSkillsQuery: () => mockListMarketplaceSkillsQuery(),
    useListInstalledSkillsQuery: () => mockListInstalledSkillsQuery(),
    useCheckSkillUpdatesQuery: () => mockCheckSkillUpdatesQuery(),
    useInstallSkillMutation: () => mockInstallSkillMutation(),
    useUninstallSkillMutation: () => mockUninstallSkillMutation(),
    useApplySkillUpdatesMutation: () => mockApplySkillUpdatesMutation(),
    // Marketplace management hooks
    useListMarketplacesQuery: () => mockListMarketplacesQuery(),
    useAddMarketplaceMutation: () => mockAddMarketplaceMutation(),
    useRemoveMarketplaceMutation: () => mockRemoveMarketplaceMutation(),
    useSyncMarketplaceMutation: () => mockSyncMarketplaceMutation(),
  };
});

import { SkillsPage } from "../SkillsPage";

const renderWithStore = () => {
  const store = createTestStore();
  return {
    store,
    ...render(
      <Provider store={store}>
        <SkillsPage />
      </Provider>,
    ),
  };
};

describe("SkillsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Header", () => {
    it("should display page title", () => {
      renderWithStore();
      expect(screen.getByText("Skills Marketplace")).toBeInTheDocument();
    });

    it("should have refresh button", () => {
      renderWithStore();
      expect(screen.getByText("Refresh")).toBeInTheDocument();
    });
  });

  describe("Tabs", () => {
    it("should have Browse Marketplace tab", () => {
      renderWithStore();
      expect(screen.getByText("Browse Marketplace")).toBeInTheDocument();
    });

    it("should have Installed tab", () => {
      renderWithStore();
      expect(screen.getByText("Installed")).toBeInTheDocument();
    });

    it("should have Updates tab", () => {
      renderWithStore();
      expect(screen.getByText("Updates")).toBeInTheDocument();
    });

    it("should show count badges for tabs", () => {
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: {
          skills: mockSkills,
          total: 2,
          marketplace: "anthropic",
          cached: false,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      mockListInstalledSkillsQuery.mockReturnValue({
        data: { skills: ["web-research"], count: 1 },
        isLoading: false,
        refetch: vi.fn(),
      });
      renderWithStore();
      // Check that count badges are shown
      const browseTab = screen
        .getByText("Browse Marketplace")
        .closest("button");
      expect(browseTab).toHaveTextContent("2");
    });
  });

  describe("Browse Tab", () => {
    it("should display skills when available", () => {
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: {
          skills: mockSkills,
          total: 2,
          marketplace: "anthropic",
          cached: false,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      renderWithStore();
      expect(screen.getByText("web-research")).toBeInTheDocument();
      expect(screen.getByText("code-review")).toBeInTheDocument();
    });

    it("should show skill descriptions", () => {
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: {
          skills: mockSkills,
          total: 2,
          marketplace: "anthropic",
          cached: false,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      renderWithStore();
      expect(
        screen.getByText("Search the web for information"),
      ).toBeInTheDocument();
    });

    it("should show skill versions", () => {
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: {
          skills: mockSkills,
          total: 2,
          marketplace: "anthropic",
          cached: false,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      renderWithStore();
      expect(screen.getByText("v1.0.0")).toBeInTheDocument();
      expect(screen.getByText("v2.1.0")).toBeInTheDocument();
    });

    it("should show empty state when no skills", () => {
      renderWithStore();
      expect(screen.getByText("No skills found")).toBeInTheDocument();
    });

    it("should show error state when API fails", () => {
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: null,
        isLoading: false,
        error: { message: "Connection failed" },
        refetch: vi.fn(),
      });
      renderWithStore();
      expect(screen.getByText("Failed to load skills")).toBeInTheDocument();
    });
  });

  describe("Installed Tab", () => {
    it("should switch to installed tab when clicked", () => {
      mockListInstalledSkillsQuery.mockReturnValue({
        data: { skills: ["web-research"], count: 1 },
        isLoading: false,
        refetch: vi.fn(),
      });
      renderWithStore();
      fireEvent.click(screen.getByText("Installed"));
      expect(screen.getByText("web-research")).toBeInTheDocument();
    });

    it("should show uninstall button for installed skills", () => {
      mockListInstalledSkillsQuery.mockReturnValue({
        data: { skills: ["web-research"], count: 1 },
        isLoading: false,
        refetch: vi.fn(),
      });
      renderWithStore();
      fireEvent.click(screen.getByText("Installed"));
      expect(screen.getByText("Uninstall")).toBeInTheDocument();
    });

    it("should show empty state when no skills installed", () => {
      renderWithStore();
      fireEvent.click(screen.getByText("Installed"));
      expect(screen.getByText("No skills installed")).toBeInTheDocument();
    });
  });

  describe("Updates Tab", () => {
    it("should switch to updates tab when clicked", () => {
      renderWithStore();
      fireEvent.click(screen.getByText("Updates"));
      expect(screen.getByText("All skills are up to date")).toBeInTheDocument();
    });

    it("should show update count when updates available", () => {
      mockCheckSkillUpdatesQuery.mockReturnValue({
        data: [
          {
            skillName: "web-research",
            currentVersion: "1.0.0",
            newVersion: "1.1.0",
            marketplace: "anthropic",
          },
        ],
        isLoading: false,
        refetch: vi.fn(),
      });
      renderWithStore();
      fireEvent.click(screen.getByText("Updates"));
      expect(screen.getByText("1 update(s) available")).toBeInTheDocument();
    });

    it("should show Apply All Updates button when updates available", () => {
      mockCheckSkillUpdatesQuery.mockReturnValue({
        data: [
          {
            skillName: "web-research",
            currentVersion: "1.0.0",
            newVersion: "1.1.0",
            marketplace: "anthropic",
          },
        ],
        isLoading: false,
        refetch: vi.fn(),
      });
      renderWithStore();
      fireEvent.click(screen.getByText("Updates"));
      expect(screen.getByText("Apply All Updates")).toBeInTheDocument();
    });
  });

  describe("Loading States", () => {
    it("should show loading spinner when loading marketplace skills", () => {
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      });
      renderWithStore();
      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("should show loading spinner when loading installed skills", () => {
      mockListInstalledSkillsQuery.mockReturnValue({
        data: null,
        isLoading: true,
        refetch: vi.fn(),
      });
      renderWithStore();
      fireEvent.click(screen.getByText("Installed"));
      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("Refresh", () => {
    it("should call refetch when refresh button clicked on browse tab", () => {
      const refetchFn = vi.fn();
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: { skills: [], total: 0, marketplace: "anthropic", cached: false },
        isLoading: false,
        error: null,
        refetch: refetchFn,
      });
      renderWithStore();
      fireEvent.click(screen.getByText("Refresh"));
      expect(refetchFn).toHaveBeenCalled();
    });

    it("should call refetch when refresh button clicked on installed tab", () => {
      const refetchFn = vi.fn();
      mockListInstalledSkillsQuery.mockReturnValue({
        data: { skills: [], count: 0 },
        isLoading: false,
        refetch: refetchFn,
      });
      renderWithStore();
      fireEvent.click(screen.getByText("Installed"));
      fireEvent.click(screen.getByText("Refresh"));
      expect(refetchFn).toHaveBeenCalled();
    });
  });

  describe("Retry Button", () => {
    it("should show retry button when there is an error", () => {
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: null,
        isLoading: false,
        error: { status: 500, message: "Server error" },
        refetch: vi.fn(),
      });
      renderWithStore();
      expect(screen.getByText("Retry")).toBeInTheDocument();
    });

    it("should call refetch when retry button is clicked", () => {
      const refetchFn = vi.fn();
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: null,
        isLoading: false,
        error: { status: 500, message: "Server error" },
        refetch: refetchFn,
      });
      renderWithStore();
      fireEvent.click(screen.getByText("Retry"));
      expect(refetchFn).toHaveBeenCalled();
    });
  });

  describe("Feature Flag", () => {
    it("should show disabled state when marketplace feature flag is disabled", () => {
      mockUseFeatureFlags.mockReturnValue({
        flags: { skills_marketplace: false },
        isLoading: false,
        isError: false,
        isEnabled: () => false,
      });
      renderWithStore();
      expect(
        screen.getByText("Skills Marketplace Disabled"),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/currently disabled for your organization/),
      ).toBeInTheDocument();
    });

    it("should show marketplace when feature flag is enabled", () => {
      mockUseFeatureFlags.mockReturnValue({
        flags: { skills_marketplace: true },
        isLoading: false,
        isError: false,
        isEnabled: (flag: string) => flag === "skills_marketplace",
      });
      renderWithStore();
      expect(screen.getByText("Skills Marketplace")).toBeInTheDocument();
      expect(
        screen.queryByText("Skills Marketplace Disabled"),
      ).not.toBeInTheDocument();
    });

    it("should not show disabled state while feature flags are loading", () => {
      mockUseFeatureFlags.mockReturnValue({
        flags: {},
        isLoading: true,
        isError: false,
        isEnabled: () => false,
      });
      renderWithStore();
      // Should still show the marketplace UI (not the disabled state)
      expect(screen.getByText("Skills Marketplace")).toBeInTheDocument();
      expect(
        screen.queryByText("Skills Marketplace Disabled"),
      ).not.toBeInTheDocument();
    });
  });
});
