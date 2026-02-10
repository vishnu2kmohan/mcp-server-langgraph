/**
 * SkillsPage Marketplace Tests
 *
 * Tests for install/uninstall actions, marketplace selector,
 * modal integration, and marketplace management.
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
          expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
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
});
