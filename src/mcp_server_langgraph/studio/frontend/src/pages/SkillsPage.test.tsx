/**
 * SkillsPage Tests
 *
 * TDD tests for the skills marketplace page.
 * Uses RTK Query for API state.
 * Tests cover:
 * - Tab navigation (Browse, Installed, Updates)
 * - Skills display and cards
 * - Search and filter functionality
 * - Install/Uninstall actions
 * - Loading and error states
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  cleanup,
  waitFor,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { SkillsPage } from "./SkillsPage";
import { api } from "../api";

// Mock RTK Query hooks
const mockListMarketplaceSkillsQuery = vi.fn(() => ({
  data: { skills: [], total: 0, marketplace: "anthropic", cached: false },
  isLoading: false,
  error: null,
  refetch: vi.fn(),
}));

const mockListInstalledSkillsQuery = vi.fn(() => ({
  data: { skills: [], count: 0 },
  isLoading: false,
  refetch: vi.fn(),
}));

const mockCheckSkillUpdatesQuery = vi.fn(() => ({
  data: [],
  isLoading: false,
  refetch: vi.fn(),
}));

const mockInstallSkillMutation = vi.fn(() => [vi.fn(), { isLoading: false }]);
const mockUninstallSkillMutation = vi.fn(() => [vi.fn(), { isLoading: false }]);
const mockApplySkillUpdatesMutation = vi.fn(() => [
  vi.fn(),
  { isLoading: false },
]);

// Mock useFeatureFlags hook
const mockUseFeatureFlags = vi.fn(() => ({
  flags: { enable_skills_marketplace: true },
  isLoading: false,
  isError: false,
  isEnabled: (flag: string) => flag === "enable_skills_marketplace",
}));

vi.mock("../contexts/FeatureFlagContext", async () => {
  const actual = await vi.importActual("../contexts/FeatureFlagContext");
  return {
    ...actual,
    useFeatureFlags: () => mockUseFeatureFlags(),
  };
});

vi.mock("../api", async () => {
  const actual = await vi.importActual("../api");
  return {
    ...actual,
    useListMarketplaceSkillsQuery: () => mockListMarketplaceSkillsQuery(),
    useListInstalledSkillsQuery: () => mockListInstalledSkillsQuery(),
    useCheckSkillUpdatesQuery: () => mockCheckSkillUpdatesQuery(),
    useInstallSkillMutation: () => mockInstallSkillMutation(),
    useUninstallSkillMutation: () => mockUninstallSkillMutation(),
    useApplySkillUpdatesMutation: () => mockApplySkillUpdatesMutation(),
  };
});

// Helper to create a test store
const createTestStore = () => {
  return configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });
};

// Helper to render with store
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

// Mock skill data
const mockSkills = [
  {
    name: "web-research",
    description: "Search the web for information",
    version: "1.0.0",
    author: "Anthropic",
    tags: ["research", "web"],
  },
  {
    name: "code-review",
    description: "Review and analyze code",
    version: "2.1.0",
    author: "Community",
    tags: ["development", "code"],
  },
];

describe("SkillsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mocks to default state
    mockListMarketplaceSkillsQuery.mockReturnValue({
      data: { skills: [], total: 0, marketplace: "anthropic", cached: false },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
    mockListInstalledSkillsQuery.mockReturnValue({
      data: { skills: [], count: 0 },
      isLoading: false,
      refetch: vi.fn(),
    });
    mockCheckSkillUpdatesQuery.mockReturnValue({
      data: [],
      isLoading: false,
      refetch: vi.fn(),
    });
    mockInstallSkillMutation.mockReturnValue([vi.fn(), { isLoading: false }]);
    mockUninstallSkillMutation.mockReturnValue([vi.fn(), { isLoading: false }]);
    mockApplySkillUpdatesMutation.mockReturnValue([
      vi.fn(),
      { isLoading: false },
    ]);
    // Reset feature flag mock to enabled state
    mockUseFeatureFlags.mockReturnValue({
      flags: { enable_skills_marketplace: true },
      isLoading: false,
      isError: false,
      isEnabled: (flag: string) => flag === "enable_skills_marketplace",
    });
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

  describe("Search", () => {
    it("should have search input on browse tab", () => {
      renderWithStore();
      expect(
        screen.getByPlaceholderText("Search skills..."),
      ).toBeInTheDocument();
    });

    it("should filter skills by search query", () => {
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
      const searchInput = screen.getByPlaceholderText("Search skills...");
      fireEvent.change(searchInput, { target: { value: "web" } });
      expect(screen.getByText("web-research")).toBeInTheDocument();
      expect(screen.queryByText("code-review")).not.toBeInTheDocument();
    });
  });

  describe("Tag Filtering", () => {
    it("should display tag filter buttons", () => {
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
      // Tags appear both in filter area and on cards, so use getAllByText
      const researchTags = screen.getAllByText("research");
      const webTags = screen.getAllByText("web");
      // At least one should be present (filter button)
      expect(researchTags.length).toBeGreaterThan(0);
      expect(webTags.length).toBeGreaterThan(0);
    });

    it("should toggle tag selection on click", () => {
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
      // Get the first research tag which should be the filter button
      const researchTags = screen.getAllByText("research");
      // Filter button is the one inside a button element in the filter area
      const filterButton = researchTags.find((el) => el.tagName === "BUTTON");
      expect(filterButton).toBeDefined();
      if (filterButton) {
        fireEvent.click(filterButton);
        // Tag should now be selected (has different styling)
        expect(filterButton).toHaveClass("bg-accent-primary");
      }
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

  describe("Install/Uninstall Actions", () => {
    it("should show Install button for non-installed skills", () => {
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
        data: { skills: [], count: 0 },
        isLoading: false,
        refetch: vi.fn(),
      });
      renderWithStore();
      const installButtons = screen.getAllByText("Install");
      expect(installButtons.length).toBe(2);
    });

    it("should show Installed badge for installed skills", () => {
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
      // web-research should show as Installed
      const installedBadges = screen.getAllByText("Installed");
      expect(installedBadges.length).toBeGreaterThan(0);
    });

    it("should call install mutation when Install button clicked", async () => {
      const installFn = vi
        .fn()
        .mockReturnValue({ unwrap: vi.fn().mockResolvedValue({}) });
      mockInstallSkillMutation.mockReturnValue([
        installFn,
        { isLoading: false },
      ]);
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: {
          skills: [mockSkills[0]],
          total: 1,
          marketplace: "anthropic",
          cached: false,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      mockListInstalledSkillsQuery.mockReturnValue({
        data: { skills: [], count: 0 },
        isLoading: false,
        refetch: vi.fn(),
      });
      renderWithStore();
      const installButton = screen.getByText("Install");
      fireEvent.click(installButton);
      await waitFor(() => {
        expect(installFn).toHaveBeenCalledWith({ skillName: "web-research" });
      });
    });

    it("should call uninstall mutation when Uninstall button clicked", async () => {
      const uninstallFn = vi
        .fn()
        .mockReturnValue({ unwrap: vi.fn().mockResolvedValue({}) });
      mockUninstallSkillMutation.mockReturnValue([
        uninstallFn,
        { isLoading: false },
      ]);
      mockListInstalledSkillsQuery.mockReturnValue({
        data: { skills: ["web-research"], count: 1 },
        isLoading: false,
        refetch: vi.fn(),
      });
      renderWithStore();
      fireEvent.click(screen.getByText("Installed"));
      const uninstallButton = screen.getByText("Uninstall");
      fireEvent.click(uninstallButton);
      await waitFor(() => {
        expect(uninstallFn).toHaveBeenCalledWith("web-research");
      });
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

  describe("Skill Tags Display", () => {
    it("should display skill tags on cards", () => {
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
      // Tags should appear on cards (may appear multiple times due to filter and cards)
      const researchTags = screen.getAllByText("research");
      expect(researchTags.length).toBeGreaterThan(0);
    });
  });

  describe("Feature Flag", () => {
    it("should show disabled state when marketplace feature flag is disabled", () => {
      mockUseFeatureFlags.mockReturnValue({
        flags: { enable_skills_marketplace: false },
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
        flags: { enable_skills_marketplace: true },
        isLoading: false,
        isError: false,
        isEnabled: (flag: string) => flag === "enable_skills_marketplace",
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
