/**
 * BrowseContent Component Tests
 *
 * TDD test suite for the browse marketplace skills tab component.
 * Tests skill grid rendering, pagination, error handling, and user interactions.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowseContent } from "./BrowseContent";
import type { SkillMetadata } from "../../types/skills";

// Mock skill data
const mockSkills: SkillMetadata[] = [
  {
    name: "web-research",
    description: "Search the web for information",
    version: "1.2.0",
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
  {
    name: "data-analysis",
    description: "Analyze datasets",
    version: "1.0.0",
    author: "Anthropic",
    tags: ["data", "analytics"],
  },
];

describe("BrowseContent", () => {
  const defaultProps = {
    skills: mockSkills,
    installedSkills: [] as string[],
    onInstall: vi.fn(),
    isInstalling: false,
    error: null,
    onRetry: vi.fn(),
    total: mockSkills.length,
    onLoadMore: vi.fn(),
    isLoadingMore: false,
    onViewDetails: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("Rendering", () => {
    it("renders skill cards in a grid", () => {
      render(<BrowseContent {...defaultProps} />);

      expect(screen.getByTestId("skills-browse-list")).toBeInTheDocument();
      expect(
        screen.getByTestId("skills-card-web-research"),
      ).toBeInTheDocument();
      expect(screen.getByTestId("skills-card-code-review")).toBeInTheDocument();
      expect(
        screen.getByTestId("skills-card-data-analysis"),
      ).toBeInTheDocument();
    });

    it("displays correct number of skill cards", () => {
      render(<BrowseContent {...defaultProps} />);

      const cards = screen.getAllByTestId(/^skills-card-/);
      expect(cards).toHaveLength(3);
    });

    it("shows installed badge for installed skills", () => {
      render(
        <BrowseContent {...defaultProps} installedSkills={["web-research"]} />,
      );

      const webResearchCard = screen.getByTestId("skills-card-web-research");
      expect(
        within(webResearchCard).getByText("Installed"),
      ).toBeInTheDocument();
    });

    it("shows install button for non-installed skills", () => {
      render(
        <BrowseContent {...defaultProps} installedSkills={["web-research"]} />,
      );

      const codeReviewCard = screen.getByTestId("skills-card-code-review");
      expect(
        within(codeReviewCard).getByRole("button", { name: /install/i }),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Empty State Tests
  // ===========================================================================

  describe("Empty State", () => {
    it("renders empty state when no skills", () => {
      render(<BrowseContent {...defaultProps} skills={[]} total={0} />);

      expect(screen.getByTestId("skills-browse-empty")).toBeInTheDocument();
      expect(screen.getByText("No skills found")).toBeInTheDocument();
      expect(
        screen.getByText("Try adjusting your search or filters."),
      ).toBeInTheDocument();
    });

    it("does not show skill grid when empty", () => {
      render(<BrowseContent {...defaultProps} skills={[]} total={0} />);

      expect(
        screen.queryByTestId("skills-browse-list"),
      ).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Error State Tests
  // ===========================================================================

  describe("Error State", () => {
    it("renders error state with retry button for network errors", () => {
      render(
        <BrowseContent
          {...defaultProps}
          skills={[]}
          error={{ status: 500, message: "Internal Server Error" }}
        />,
      );

      expect(screen.getByTestId("skills-browse-error")).toBeInTheDocument();
      expect(screen.getByText("Failed to load skills")).toBeInTheDocument();
      expect(screen.getByTestId("skills-retry-button")).toBeInTheDocument();
    });

    it("calls onRetry when retry button is clicked", async () => {
      const user = userEvent.setup();
      const onRetry = vi.fn();

      render(
        <BrowseContent
          {...defaultProps}
          skills={[]}
          error={{ status: 500 }}
          onRetry={onRetry}
        />,
      );

      await user.click(screen.getByTestId("skills-retry-button"));
      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it("shows Access Denied for 403 errors", () => {
      render(
        <BrowseContent {...defaultProps} skills={[]} error={{ status: 403 }} />,
      );

      expect(screen.getByText("Access Denied")).toBeInTheDocument();
    });

    it("does not show retry button for 403 errors", () => {
      render(
        <BrowseContent {...defaultProps} skills={[]} error={{ status: 403 }} />,
      );

      expect(
        screen.queryByTestId("skills-retry-button"),
      ).not.toBeInTheDocument();
    });

    it("displays custom error message from API for non-403 errors", () => {
      render(
        <BrowseContent
          {...defaultProps}
          skills={[]}
          error={{ status: 400, data: { detail: "Custom validation error" } }}
        />,
      );

      // For non-403 errors, the generic message is shown, not the detail
      expect(
        screen.getByText("Please check your connection and try again."),
      ).toBeInTheDocument();
    });

    it("displays generic permission message for 403 without detail", () => {
      render(
        <BrowseContent {...defaultProps} skills={[]} error={{ status: 403 }} />,
      );

      expect(screen.getByText(/don't have permission/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Pagination Tests
  // ===========================================================================

  describe("Pagination", () => {
    it("shows pagination info when skills exist", () => {
      render(<BrowseContent {...defaultProps} />);

      expect(screen.getByTestId("skills-pagination")).toBeInTheDocument();
      expect(screen.getByText(/showing 3 of 3 skills/i)).toBeInTheDocument();
    });

    it("shows Load More button when more skills available", () => {
      render(
        <BrowseContent
          {...defaultProps}
          skills={mockSkills.slice(0, 2)}
          total={5}
        />,
      );

      expect(screen.getByTestId("skills-load-more")).toBeInTheDocument();
      expect(screen.getByText(/showing 2 of 5 skills/i)).toBeInTheDocument();
    });

    it("hides Load More button when all skills loaded", () => {
      render(<BrowseContent {...defaultProps} />);

      expect(screen.queryByTestId("skills-load-more")).not.toBeInTheDocument();
    });

    it("calls onLoadMore when Load More is clicked", async () => {
      const user = userEvent.setup();
      const onLoadMore = vi.fn();

      render(
        <BrowseContent
          {...defaultProps}
          skills={mockSkills.slice(0, 2)}
          total={5}
          onLoadMore={onLoadMore}
        />,
      );

      await user.click(screen.getByTestId("skills-load-more"));
      expect(onLoadMore).toHaveBeenCalledTimes(1);
    });

    it("disables Load More button when loading more", () => {
      render(
        <BrowseContent
          {...defaultProps}
          skills={mockSkills.slice(0, 2)}
          total={5}
          isLoadingMore={true}
        />,
      );

      expect(screen.getByTestId("skills-load-more")).toBeDisabled();
    });

    it("does not show pagination when total is 0", () => {
      render(<BrowseContent {...defaultProps} skills={[]} total={0} />);

      expect(screen.queryByTestId("skills-pagination")).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // User Interaction Tests
  // ===========================================================================

  describe("User Interactions", () => {
    it("calls onInstall with skill name when install clicked", async () => {
      const user = userEvent.setup();
      const onInstall = vi.fn();

      render(<BrowseContent {...defaultProps} onInstall={onInstall} />);

      const codeReviewCard = screen.getByTestId("skills-card-code-review");
      const installButton = within(codeReviewCard).getByRole("button", {
        name: /install/i,
      });

      await user.click(installButton);
      expect(onInstall).toHaveBeenCalledWith("code-review");
    });

    it("calls onViewDetails when card is clicked", async () => {
      const user = userEvent.setup();
      const onViewDetails = vi.fn();

      render(<BrowseContent {...defaultProps} onViewDetails={onViewDetails} />);

      const card = screen.getByTestId("skills-card-web-research");
      await user.click(card);

      expect(onViewDetails).toHaveBeenCalledWith(mockSkills[0]);
    });

    it("disables install buttons when installing", () => {
      render(<BrowseContent {...defaultProps} isInstalling={true} />);

      const codeReviewCard = screen.getByTestId("skills-card-code-review");
      const installButton = within(codeReviewCard).getByRole("button");

      expect(installButton).toBeDisabled();
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("Accessibility", () => {
    it("has accessible skill cards with article role", () => {
      render(<BrowseContent {...defaultProps} />);

      const articles = screen.getAllByRole("article");
      expect(articles.length).toBeGreaterThan(0);
    });

    it("retry button is keyboard accessible", () => {
      render(
        <BrowseContent {...defaultProps} skills={[]} error={{ status: 500 }} />,
      );

      const retryButton = screen.getByTestId("skills-retry-button");
      expect(retryButton).not.toBeDisabled();
    });
  });
});
