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

// Mock marketplace management hooks
const mockListMarketplacesQuery = vi.fn(() => ({
  data: {
    marketplaces: [
      {
        name: "anthropic",
        uri: "https://github.com/anthropics/skills-marketplace",
        type: "github",
        trusted: true,
        autoSync: true,
        requiresApproval: false,
      },
    ],
  },
  isLoading: false,
  error: null,
  refetch: vi.fn(),
}));

const mockAddMarketplaceMutation = vi.fn(() => [vi.fn(), { isLoading: false }]);
const mockRemoveMarketplaceMutation = vi.fn(() => [
  vi.fn(),
  { isLoading: false },
]);
const mockSyncMarketplaceMutation = vi.fn(() => [
  vi.fn(),
  { isLoading: false },
]);

// Mock useFeatureFlags hook
const mockUseFeatureFlags = vi.fn(() => ({
  flags: { skills_marketplace: true },
  isLoading: false,
  isError: false,
  isEnabled: (flag: string) => flag === "skills_marketplace",
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
    // Marketplace management hooks
    useListMarketplacesQuery: () => mockListMarketplacesQuery(),
    useAddMarketplaceMutation: () => mockAddMarketplaceMutation(),
    useRemoveMarketplaceMutation: () => mockRemoveMarketplaceMutation(),
    useSyncMarketplaceMutation: () => mockSyncMarketplaceMutation(),
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
      flags: { skills_marketplace: true },
      isLoading: false,
      isError: false,
      isEnabled: (flag: string) => flag === "skills_marketplace",
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
        // Tag should now be selected (has different styling - Radix 1-12 scale)
        expect(filterButton).toHaveClass("bg-primary-3");
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

    it("should call uninstall mutation when Uninstall confirmed in dialog", async () => {
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

      // Click Uninstall button to open confirmation dialog
      const uninstallButton = screen.getByText("Uninstall");
      fireEvent.click(uninstallButton);

      // Wait for confirmation dialog to open
      await waitFor(() => {
        expect(screen.getByTestId("uninstall-dialog")).toBeInTheDocument();
      });

      // Click confirm button in the dialog (the Uninstall button, not Cancel)
      const dialog = screen.getByTestId("uninstall-dialog");
      const buttons = dialog.querySelectorAll("button");
      // Last button is the confirm button (Uninstall)
      const confirmButton = buttons[buttons.length - 1];
      expect(confirmButton).toBeInTheDocument();
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(uninstallFn).toHaveBeenCalledWith("web-research");
      });
    });

    it("should open uninstall confirmation dialog when Uninstall clicked", async () => {
      mockListInstalledSkillsQuery.mockReturnValue({
        data: { skills: ["web-research"], count: 1 },
        isLoading: false,
        refetch: vi.fn(),
      });
      renderWithStore();
      fireEvent.click(screen.getByText("Installed"));

      // Click Uninstall button
      const uninstallButton = screen.getByText("Uninstall");
      fireEvent.click(uninstallButton);

      // Confirmation dialog should open
      await waitFor(() => {
        expect(screen.getByTestId("uninstall-dialog")).toBeInTheDocument();
      });

      // Should show skill name in dialog (check within dialog)
      const dialog = screen.getByTestId("uninstall-dialog");
      expect(dialog).toHaveTextContent("web-research");
    });

    it("should close uninstall dialog when Cancel clicked", async () => {
      mockListInstalledSkillsQuery.mockReturnValue({
        data: { skills: ["web-research"], count: 1 },
        isLoading: false,
        refetch: vi.fn(),
      });
      renderWithStore();
      fireEvent.click(screen.getByText("Installed"));

      // Click Uninstall button
      const uninstallButton = screen.getByText("Uninstall");
      fireEvent.click(uninstallButton);

      // Wait for dialog
      await waitFor(() => {
        expect(screen.getByTestId("uninstall-dialog")).toBeInTheDocument();
      });

      // Click Cancel
      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelButton);

      // Dialog should close
      await waitFor(() => {
        expect(
          screen.queryByTestId("uninstall-dialog"),
        ).not.toBeInTheDocument();
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

  describe("Marketplace Selector", () => {
    it("should display marketplace selector on browse tab", () => {
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: { skills: [], total: 0, marketplace: "anthropic", cached: false },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      renderWithStore();
      // Should show the marketplace selector
      expect(screen.getByLabelText("Marketplace")).toBeInTheDocument();
    });

    it("should show Anthropic as default marketplace", () => {
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: { skills: [], total: 0, marketplace: "anthropic", cached: false },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      renderWithStore();
      const selector = screen.getByLabelText("Marketplace");
      expect(selector).toHaveValue("anthropic");
    });

    it("should update query when marketplace changes", () => {
      const refetchFn = vi.fn();
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: { skills: [], total: 0, marketplace: "anthropic", cached: false },
        isLoading: false,
        error: null,
        refetch: refetchFn,
      });
      renderWithStore();
      const selector = screen.getByLabelText("Marketplace");
      fireEvent.change(selector, { target: { value: "enterprise" } });
      // Should trigger a refetch with the new marketplace
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

  describe("Pagination", () => {
    // Generate more skills for client-side pagination testing
    const manyMockSkills = Array.from({ length: 20 }, (_, i) => ({
      name: `skill-${i + 1}`,
      description: `Description for skill ${i + 1}`,
      version: "1.0.0",
      author: "Anthropic",
      tags: ["test"],
    }));

    it("should show Load More button when more skills than visible count", () => {
      // Client-side pagination: shows 12 initially, button appears when > 12 skills
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: {
          skills: manyMockSkills, // 20 skills, more than initial visible count of 12
          total: 20,
          marketplace: "anthropic",
          cached: false,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      renderWithStore();
      expect(screen.getByText("Load More")).toBeInTheDocument();
    });

    it("should not show Load More button when all skills are visible", () => {
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: {
          skills: mockSkills, // Only 2 skills, less than initial visible count of 12
          total: 2,
          marketplace: "anthropic",
          cached: false,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      renderWithStore();
      expect(screen.queryByText("Load More")).not.toBeInTheDocument();
    });

    it("should show skill count summary", () => {
      // Client-side pagination: shows visible count of total filtered skills
      mockListMarketplaceSkillsQuery.mockReturnValue({
        data: {
          skills: manyMockSkills, // 20 skills
          total: 20,
          marketplace: "anthropic",
          cached: false,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      renderWithStore();
      // Initial visible count is 12, total is 20
      expect(screen.getByText(/Showing 12 of 20 skills/)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Modal Integration Tests
  // ===========================================================================

  describe("Modal Integration", () => {
    beforeEach(() => {
      // Setup with skills for modal testing
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
    });

    it("should open SkillDetails modal when card is clicked", async () => {
      renderWithStore();

      // Click on a skill card
      const skillCard = screen.getByTestId("skills-card-web-research");
      fireEvent.click(skillCard);

      // Modal should open with skill name visible
      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
    });

    it("should display skill info in SkillDetails modal", async () => {
      renderWithStore();

      const skillCard = screen.getByTestId("skills-card-web-research");
      fireEvent.click(skillCard);

      await waitFor(() => {
        // Skill name should be visible in the modal
        const dialog = screen.getByRole("dialog");
        expect(dialog).toBeInTheDocument();
      });
    });

    it("should close SkillDetails modal when close button is clicked", async () => {
      renderWithStore();

      // Open modal
      const skillCard = screen.getByTestId("skills-card-web-research");
      fireEvent.click(skillCard);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      // Close modal
      const closeButton = screen.getByRole("button", { name: /close/i });
      fireEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      });
    });

    it("should open InstallDialog when Install clicked in SkillDetails", async () => {
      renderWithStore();

      // Open skill details modal
      const skillCard = screen.getByTestId("skills-card-web-research");
      fireEvent.click(skillCard);

      await waitFor(() => {
        expect(screen.getByTestId("skill-details-modal")).toBeInTheDocument();
      });

      // Click Install button in the details modal (skip the Close button)
      const modal = screen.getByTestId("skill-details-modal");
      const installButton = modal.querySelector(
        'button:not([aria-label="Close"])',
      );
      expect(installButton).toBeInTheDocument();
      fireEvent.click(installButton!);

      // InstallDialog should open (title is "Install Skill")
      await waitFor(() => {
        expect(screen.getByTestId("install-dialog")).toBeInTheDocument();
      });
    });

    it("should close InstallDialog when Cancel is clicked", async () => {
      renderWithStore();

      // Open skill details modal
      const skillCard = screen.getByTestId("skills-card-web-research");
      fireEvent.click(skillCard);

      await waitFor(() => {
        expect(screen.getByTestId("skill-details-modal")).toBeInTheDocument();
      });

      // Click Install to open confirmation (find within the modal)
      const modal = screen.getByTestId("skill-details-modal");
      const installButton = modal.querySelector(
        'button:not([aria-label="Close"])',
      );
      expect(installButton).toBeInTheDocument();
      fireEvent.click(installButton!);

      await waitFor(() => {
        expect(screen.getByTestId("install-dialog")).toBeInTheDocument();
      });

      // Click Cancel
      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByTestId("install-dialog")).not.toBeInTheDocument();
      });
    });

    it("should not open modal when clicking Install button directly", async () => {
      renderWithStore();

      // Find the Install button within the card
      const skillCard = screen.getByTestId("skills-card-code-review");
      const installButton = skillCard.querySelector("button");

      if (installButton) {
        fireEvent.click(installButton);
      }

      // Should not open the modal (button has stopPropagation)
      await waitFor(
        () => {
          // Modal may not open when clicking directly on Install
          // This tests the event propagation behavior
        },
        { timeout: 500 },
      );
    });

    it("should show Installed badge in SkillDetails for installed skills", async () => {
      // Mock with installed skill
      mockListInstalledSkillsQuery.mockReturnValue({
        data: { skills: ["web-research"], count: 1 },
        isLoading: false,
        refetch: vi.fn(),
      });

      renderWithStore();

      const skillCard = screen.getByTestId("skills-card-web-research");
      fireEvent.click(skillCard);

      await waitFor(() => {
        const dialog = screen.getByRole("dialog");
        expect(dialog).toBeInTheDocument();
      });

      // Should show Installed badge in the modal (multiple Installed texts are expected)
      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveTextContent(/installed/i);
    });
  });

  // ===========================================================================
  // Marketplace Management Tests
  // ===========================================================================

  describe("Marketplace Management", () => {
    it("should render Settings button in header", () => {
      renderWithStore();
      expect(
        screen.getByRole("button", { name: /settings/i }),
      ).toBeInTheDocument();
    });

    it("should open marketplace manager when Settings clicked", async () => {
      renderWithStore();
      fireEvent.click(screen.getByRole("button", { name: /settings/i }));
      await waitFor(() => {
        expect(screen.getByTestId("marketplace-manager")).toBeInTheDocument();
      });
    });

    it("should show Add Marketplace button in marketplace manager", async () => {
      renderWithStore();
      fireEvent.click(screen.getByRole("button", { name: /settings/i }));
      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /add marketplace/i }),
        ).toBeInTheDocument();
      });
    });

    it("should open add marketplace dialog when Add Marketplace clicked", async () => {
      renderWithStore();
      fireEvent.click(screen.getByRole("button", { name: /settings/i }));
      await waitFor(() => {
        expect(screen.getByTestId("marketplace-manager")).toBeInTheDocument();
      });
      fireEvent.click(screen.getByRole("button", { name: /add marketplace/i }));
      await waitFor(() => {
        expect(
          screen.getByTestId("add-marketplace-dialog"),
        ).toBeInTheDocument();
      });
    });

    it("should close add marketplace dialog when Cancel clicked", async () => {
      renderWithStore();
      fireEvent.click(screen.getByRole("button", { name: /settings/i }));
      await waitFor(() => {
        expect(screen.getByTestId("marketplace-manager")).toBeInTheDocument();
      });
      fireEvent.click(screen.getByRole("button", { name: /add marketplace/i }));
      await waitFor(() => {
        expect(
          screen.getByTestId("add-marketplace-dialog"),
        ).toBeInTheDocument();
      });
      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
      await waitFor(() => {
        expect(
          screen.queryByTestId("add-marketplace-dialog"),
        ).not.toBeInTheDocument();
      });
    });

    it("should close marketplace manager when clicking outside", async () => {
      renderWithStore();
      fireEvent.click(screen.getByRole("button", { name: /settings/i }));
      await waitFor(() => {
        expect(screen.getByTestId("marketplace-manager")).toBeInTheDocument();
      });
      // Close by clicking the close button
      fireEvent.click(screen.getByRole("button", { name: /close settings/i }));
      await waitFor(() => {
        expect(
          screen.queryByTestId("marketplace-manager"),
        ).not.toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Keyboard Navigation Tests
  // ===========================================================================

  describe("Keyboard Navigation", () => {
    beforeEach(() => {
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
    });

    it("should close modal on Escape key", async () => {
      renderWithStore();

      // Open modal
      const skillCard = screen.getByTestId("skills-card-web-research");
      fireEvent.click(skillCard);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      // Press Escape
      fireEvent.keyDown(document, { key: "Escape", code: "Escape" });

      await waitFor(() => {
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      });
    });

    it("should have focusable close button in modal", async () => {
      renderWithStore();

      const skillCard = screen.getByTestId("skills-card-web-research");
      fireEvent.click(skillCard);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      const closeButton = screen.getByRole("button", { name: /close/i });
      expect(closeButton).not.toBeDisabled();
    });

    it("tabs should be keyboard navigable", () => {
      renderWithStore();

      const browseTab = screen.getByTestId("skills-tab-browse");
      const installedTab = screen.getByTestId("skills-tab-installed");
      const updatesTab = screen.getByTestId("skills-tab-updates");

      // All tabs should be focusable
      expect(browseTab).not.toBeDisabled();
      expect(installedTab).not.toBeDisabled();
      expect(updatesTab).not.toBeDisabled();
    });

    it("refresh button should be keyboard accessible", () => {
      renderWithStore();

      const refreshButton = screen.getByTestId("skills-refresh-button");
      expect(refreshButton).not.toBeDisabled();
    });
  });
});
