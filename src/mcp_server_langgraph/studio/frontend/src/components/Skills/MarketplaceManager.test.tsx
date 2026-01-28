/**
 * MarketplaceManager Component Tests
 *
 * TDD test suite for the marketplace management component.
 * Tests marketplace list rendering, add/remove/sync operations.
 *
 * Following STYLE.md conventions:
 * - Focus-visible rings for keyboard navigation
 * - Button variants: secondary for Cancel, danger for Delete, primary for Confirm
 * - Accessible dialogs with proper ARIA attributes
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MarketplaceManager } from "./MarketplaceManager";
import type { MarketplaceInfo } from "../../types/skills";

// Mock marketplace data
const mockMarketplaces: MarketplaceInfo[] = [
  {
    name: "anthropic",
    uri: "https://github.com/anthropics/skills-marketplace",
    type: "github",
    trusted: true,
    autoSync: true,
    requiresApproval: false,
  },
  {
    name: "community",
    uri: "https://github.com/community/skills",
    type: "github",
    trusted: false,
    autoSync: false,
    requiresApproval: true,
  },
];

describe("MarketplaceManager", () => {
  const defaultProps = {
    marketplaces: mockMarketplaces,
    onAdd: vi.fn(),
    onRemove: vi.fn(),
    onSync: vi.fn(),
    isLoading: false,
    isSyncing: false,
    syncingMarketplace: null as string | null,
    error: null as string | null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("Rendering", () => {
    it("renders marketplace manager container", () => {
      render(<MarketplaceManager {...defaultProps} />);
      expect(screen.getByTestId("marketplace-manager")).toBeInTheDocument();
    });

    it("renders header with title", () => {
      render(<MarketplaceManager {...defaultProps} />);
      expect(
        screen.getByRole("heading", { name: /marketplaces/i }),
      ).toBeInTheDocument();
    });

    it("renders add marketplace button", () => {
      render(<MarketplaceManager {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /add marketplace/i }),
      ).toBeInTheDocument();
    });

    it("renders marketplace list", () => {
      render(<MarketplaceManager {...defaultProps} />);
      expect(screen.getByTestId("marketplace-list")).toBeInTheDocument();
    });

    it("renders all marketplaces", () => {
      render(<MarketplaceManager {...defaultProps} />);
      expect(screen.getByTestId("marketplace-anthropic")).toBeInTheDocument();
      expect(screen.getByTestId("marketplace-community")).toBeInTheDocument();
    });

    it("displays marketplace names", () => {
      render(<MarketplaceManager {...defaultProps} />);
      expect(screen.getByText("anthropic")).toBeInTheDocument();
      expect(screen.getByText("community")).toBeInTheDocument();
    });

    it("displays marketplace URIs", () => {
      render(<MarketplaceManager {...defaultProps} />);
      expect(
        screen.getByText("https://github.com/anthropics/skills-marketplace"),
      ).toBeInTheDocument();
    });

    it("shows trusted badge for trusted marketplaces", () => {
      render(<MarketplaceManager {...defaultProps} />);
      const anthropicRow = screen.getByTestId("marketplace-anthropic");
      expect(within(anthropicRow).getByText(/trusted/i)).toBeInTheDocument();
    });

    it("shows auto-sync badge for auto-sync marketplaces", () => {
      render(<MarketplaceManager {...defaultProps} />);
      const anthropicRow = screen.getByTestId("marketplace-anthropic");
      expect(within(anthropicRow).getByText(/auto-sync/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Action Buttons Tests
  // ===========================================================================

  describe("Action Buttons", () => {
    it("renders sync button for each marketplace", () => {
      render(<MarketplaceManager {...defaultProps} />);
      const syncButtons = screen.getAllByRole("button", { name: /sync/i });
      expect(syncButtons.length).toBe(2);
    });

    it("does not show remove button for default anthropic marketplace", () => {
      render(<MarketplaceManager {...defaultProps} />);
      const anthropicRow = screen.getByTestId("marketplace-anthropic");
      expect(
        within(anthropicRow).queryByRole("button", { name: /remove/i }),
      ).not.toBeInTheDocument();
    });

    it("shows remove button for non-default marketplaces", () => {
      render(<MarketplaceManager {...defaultProps} />);
      const communityRow = screen.getByTestId("marketplace-community");
      expect(
        within(communityRow).getByRole("button", { name: /remove/i }),
      ).toBeInTheDocument();
    });

    it("calls onAdd when Add Marketplace button clicked", async () => {
      const user = userEvent.setup();
      render(<MarketplaceManager {...defaultProps} />);

      await user.click(
        screen.getByRole("button", { name: /add marketplace/i }),
      );
      expect(defaultProps.onAdd).toHaveBeenCalledTimes(1);
    });

    it("calls onRemove with marketplace name when Remove clicked", async () => {
      const user = userEvent.setup();
      render(<MarketplaceManager {...defaultProps} />);

      const communityRow = screen.getByTestId("marketplace-community");
      await user.click(
        within(communityRow).getByRole("button", { name: /remove/i }),
      );
      expect(defaultProps.onRemove).toHaveBeenCalledWith("community");
    });

    it("calls onSync with marketplace name when Sync clicked", async () => {
      const user = userEvent.setup();
      render(<MarketplaceManager {...defaultProps} />);

      const communityRow = screen.getByTestId("marketplace-community");
      await user.click(
        within(communityRow).getByRole("button", { name: /sync/i }),
      );
      expect(defaultProps.onSync).toHaveBeenCalledWith("community");
    });
  });

  // ===========================================================================
  // Loading States Tests
  // ===========================================================================

  describe("Loading States", () => {
    it("shows loading spinner when isLoading", () => {
      render(<MarketplaceManager {...defaultProps} isLoading={true} />);
      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("hides marketplace list when loading", () => {
      render(<MarketplaceManager {...defaultProps} isLoading={true} />);
      expect(screen.queryByTestId("marketplace-list")).not.toBeInTheDocument();
    });

    it("disables sync button for syncing marketplace", () => {
      render(
        <MarketplaceManager
          {...defaultProps}
          isSyncing={true}
          syncingMarketplace="community"
        />,
      );
      const communityRow = screen.getByTestId("marketplace-community");
      expect(
        within(communityRow).getByRole("button", { name: /syncing/i }),
      ).toBeDisabled();
    });

    it("shows syncing spinner on syncing marketplace", () => {
      render(
        <MarketplaceManager
          {...defaultProps}
          isSyncing={true}
          syncingMarketplace="community"
        />,
      );
      const communityRow = screen.getByTestId("marketplace-community");
      // The spinner is inside the syncing button
      const syncingButton = within(communityRow).getByRole("button", {
        name: /syncing/i,
      });
      expect(syncingButton.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("does not disable other sync buttons while one is syncing", () => {
      render(
        <MarketplaceManager
          {...defaultProps}
          isSyncing={true}
          syncingMarketplace="community"
        />,
      );
      const anthropicRow = screen.getByTestId("marketplace-anthropic");
      expect(
        within(anthropicRow).getByRole("button", { name: /sync/i }),
      ).not.toBeDisabled();
    });
  });

  // ===========================================================================
  // Error State Tests
  // ===========================================================================

  describe("Error States", () => {
    it("shows error message when error prop provided", () => {
      render(
        <MarketplaceManager
          {...defaultProps}
          error="Failed to load marketplaces"
        />,
      );
      expect(
        screen.getByText(/failed to load marketplaces/i),
      ).toBeInTheDocument();
    });

    it("shows error with alert role for accessibility", () => {
      render(
        <MarketplaceManager
          {...defaultProps}
          error="Failed to load marketplaces"
        />,
      );
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Empty State Tests
  // ===========================================================================

  describe("Empty State", () => {
    it("shows empty state when no marketplaces", () => {
      render(<MarketplaceManager {...defaultProps} marketplaces={[]} />);
      expect(
        screen.getByText(/no marketplaces registered/i),
      ).toBeInTheDocument();
    });

    it("shows add marketplace prompt in empty state", () => {
      render(<MarketplaceManager {...defaultProps} marketplaces={[]} />);
      expect(
        screen.getByRole("button", { name: /add marketplace/i }),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("Accessibility", () => {
    it("has accessible button labels", () => {
      render(<MarketplaceManager {...defaultProps} />);

      // Add button should have descriptive label
      expect(
        screen.getByRole("button", { name: /add marketplace/i }),
      ).toBeInTheDocument();

      // Sync buttons should be accessible
      const syncButtons = screen.getAllByRole("button", { name: /sync/i });
      expect(syncButtons.length).toBeGreaterThan(0);
    });

    it("uses semantic list for marketplaces", () => {
      render(<MarketplaceManager {...defaultProps} />);
      expect(screen.getByRole("list")).toBeInTheDocument();
    });

    it("each marketplace is a listitem", () => {
      render(<MarketplaceManager {...defaultProps} />);
      const items = screen.getAllByRole("listitem");
      expect(items.length).toBe(2);
    });

    it("has proper heading hierarchy", () => {
      render(<MarketplaceManager {...defaultProps} />);
      const heading = screen.getByRole("heading", { name: /marketplaces/i });
      expect(heading.tagName).toBe("H2");
    });
  });

  // ===========================================================================
  // Keyboard Navigation Tests
  // ===========================================================================

  describe("Keyboard Navigation", () => {
    it("buttons are focusable", async () => {
      const user = userEvent.setup();
      render(<MarketplaceManager {...defaultProps} />);

      // Tab navigation should focus buttons
      await user.tab();

      // Eventually should be able to focus a button
      expect(document.activeElement?.tagName).toBe("BUTTON");
    });

    it("Enter key activates focused button", async () => {
      const user = userEvent.setup();
      render(<MarketplaceManager {...defaultProps} />);

      const addButton = screen.getByRole("button", {
        name: /add marketplace/i,
      });
      addButton.focus();
      await user.keyboard("{Enter}");

      expect(defaultProps.onAdd).toHaveBeenCalled();
    });
  });
});
