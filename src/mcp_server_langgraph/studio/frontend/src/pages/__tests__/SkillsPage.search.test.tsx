/**
 * SkillsPage Search & Navigation Tests
 *
 * Tests for search, tag filtering, skill tags display,
 * pagination, and keyboard navigation.
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
      const { waitFor } = await import("@testing-library/react");
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
      const { waitFor } = await import("@testing-library/react");
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
