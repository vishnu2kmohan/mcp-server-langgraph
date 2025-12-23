/**
 * HelpPanel Component Tests
 *
 * TDD tests for the contextual help panel.
 * Provides context-sensitive tips and documentation links.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { HelpPanel, HelpPanelProps, HelpArticle, HelpTip } from "./HelpPanel";

const mockTips: HelpTip[] = [
  {
    id: "tip-1",
    content: "Drag nodes from palette to canvas",
    icon: "drag",
  },
  {
    id: "tip-2",
    content: "Connect nodes to create flow",
    icon: "connect",
  },
  {
    id: "tip-3",
    content: "Press Cmd+S to save",
    icon: "keyboard",
  },
];

const mockArticles: HelpArticle[] = [
  {
    id: "article-1",
    title: "Workflow Basics",
    url: "/docs/workflows",
    description: "Learn how to create and manage workflows",
  },
  {
    id: "article-2",
    title: "Node Types",
    url: "/docs/nodes",
    description: "Explore different node types available",
  },
];

describe("HelpPanel", () => {
  const defaultProps: HelpPanelProps = {
    isOpen: true,
    contextId: "workflow-builder",
    tips: mockTips,
    articles: mockArticles,
    onClose: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Visibility", () => {
    it("should render when isOpen is true", () => {
      render(<HelpPanel {...defaultProps} />);
      expect(screen.getByRole("complementary")).toBeInTheDocument();
    });

    it("should not render when isOpen is false", () => {
      render(<HelpPanel {...defaultProps} isOpen={false} />);
      expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    });
  });

  describe("Header", () => {
    it("should display help title", () => {
      render(<HelpPanel {...defaultProps} />);
      expect(screen.getByText(/help/i)).toBeInTheDocument();
    });

    it("should have close button", () => {
      render(<HelpPanel {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /close/i }),
      ).toBeInTheDocument();
    });

    it("should call onClose when close button clicked", () => {
      render(<HelpPanel {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /close/i }));
      expect(defaultProps.onClose).toHaveBeenCalled();
    });
  });

  describe("Tips Section", () => {
    it("should display tips section heading", () => {
      render(<HelpPanel {...defaultProps} />);
      expect(screen.getByText(/tips/i)).toBeInTheDocument();
    });

    it("should display all tips", () => {
      render(<HelpPanel {...defaultProps} />);
      expect(screen.getByText(/drag nodes from palette/i)).toBeInTheDocument();
      expect(
        screen.getByText(/connect nodes to create flow/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/press cmd\+s to save/i)).toBeInTheDocument();
    });

    it("should handle empty tips gracefully", () => {
      render(<HelpPanel {...defaultProps} tips={[]} />);
      expect(screen.queryByText(/tips/i)).not.toBeInTheDocument();
    });
  });

  describe("Articles Section", () => {
    it("should display articles section heading", () => {
      render(<HelpPanel {...defaultProps} />);
      expect(screen.getByText(/documentation/i)).toBeInTheDocument();
    });

    it("should display all articles", () => {
      render(<HelpPanel {...defaultProps} />);
      expect(screen.getByText("Workflow Basics")).toBeInTheDocument();
      expect(screen.getByText("Node Types")).toBeInTheDocument();
    });

    it("should display article descriptions", () => {
      render(<HelpPanel {...defaultProps} />);
      expect(
        screen.getByText(/learn how to create and manage/i),
      ).toBeInTheDocument();
    });

    it("should render articles as links", () => {
      render(<HelpPanel {...defaultProps} />);
      const workflowLink = screen.getByRole("link", {
        name: /workflow basics/i,
      });
      expect(workflowLink).toHaveAttribute("href", "/docs/workflows");
    });

    it("should handle empty articles gracefully", () => {
      render(<HelpPanel {...defaultProps} articles={[]} />);
      expect(screen.queryByText(/documentation/i)).not.toBeInTheDocument();
    });
  });

  describe("Search", () => {
    it("should display search input", () => {
      render(<HelpPanel {...defaultProps} />);
      expect(screen.getByPlaceholderText(/search help/i)).toBeInTheDocument();
    });

    it("should filter tips by search query", () => {
      render(<HelpPanel {...defaultProps} />);
      const searchInput = screen.getByPlaceholderText(/search help/i);
      fireEvent.change(searchInput, { target: { value: "drag" } });

      expect(screen.getByText(/drag nodes from palette/i)).toBeInTheDocument();
      expect(screen.queryByText(/connect nodes/i)).not.toBeInTheDocument();
    });

    it("should filter articles by search query", () => {
      render(<HelpPanel {...defaultProps} />);
      const searchInput = screen.getByPlaceholderText(/search help/i);
      fireEvent.change(searchInput, { target: { value: "workflow" } });

      expect(screen.getByText("Workflow Basics")).toBeInTheDocument();
      expect(screen.queryByText("Node Types")).not.toBeInTheDocument();
    });

    it("should show no results message when nothing matches", () => {
      render(<HelpPanel {...defaultProps} />);
      const searchInput = screen.getByPlaceholderText(/search help/i);
      fireEvent.change(searchInput, { target: { value: "xyz123" } });

      expect(screen.getByText(/no results found/i)).toBeInTheDocument();
    });
  });

  describe("Context-Specific Content", () => {
    it("should display context-specific title when provided", () => {
      render(
        <HelpPanel {...defaultProps} contextTitle="Workflow Builder Help" />,
      );
      expect(screen.getByText("Workflow Builder Help")).toBeInTheDocument();
    });
  });

  describe("Expandable Tips", () => {
    it("should allow expanding tips with more details", () => {
      const tipsWithDetails: HelpTip[] = [
        {
          id: "tip-1",
          content: "Drag nodes from palette to canvas",
          icon: "drag",
          details:
            "You can drag any node type from the left palette onto the canvas.",
        },
      ];

      render(<HelpPanel {...defaultProps} tips={tipsWithDetails} />);
      const expandButton = screen.getByRole("button", { name: /more/i });
      fireEvent.click(expandButton);

      expect(
        screen.getByText(/you can drag any node type/i),
      ).toBeInTheDocument();
    });
  });

  describe("Keyboard Navigation", () => {
    it("should close on Escape key", () => {
      render(<HelpPanel {...defaultProps} />);
      fireEvent.keyDown(document, { key: "Escape" });
      expect(defaultProps.onClose).toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("should have complementary role", () => {
      render(<HelpPanel {...defaultProps} />);
      expect(screen.getByRole("complementary")).toBeInTheDocument();
    });

    it("should have accessible panel label", () => {
      render(<HelpPanel {...defaultProps} />);
      const panel = screen.getByRole("complementary");
      expect(panel).toHaveAttribute(
        "aria-label",
        expect.stringContaining("help"),
      );
    });

    it("should have searchbox role for search input", () => {
      render(<HelpPanel {...defaultProps} />);
      expect(screen.getByRole("searchbox")).toBeInTheDocument();
    });
  });
});
