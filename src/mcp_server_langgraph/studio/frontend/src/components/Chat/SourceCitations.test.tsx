/**
 * SourceCitations Component Tests
 *
 * TDD tests for the reusable SourceCitations component.
 * Tests rendering, accessibility, and edge cases.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { SourceCitations } from "./SourceCitations";
import type { SourceCitation } from "../../types/session";

// =============================================================================
// Test Data
// =============================================================================

const mockSources: SourceCitation[] = [
  {
    title: "Python Documentation",
    url: "https://docs.python.org/3/tutorial",
    snippet: "The Python Tutorial — Python 3.13 documentation",
  },
  {
    title: "Real Python",
    url: "https://realpython.com/python-basics/",
    snippet: "Python Basics – Real Python tutorials for beginners",
  },
  {
    title: "Stack Overflow",
    url: "https://stackoverflow.com/questions/tagged/python",
    snippet: "Python questions on Stack Overflow",
  },
];

const sourcesWithRelevance: SourceCitation[] = [
  {
    title: "High Relevance",
    url: "https://high.com",
    relevance_score: 0.95,
  },
  {
    title: "Low Relevance",
    url: "https://low.com",
    relevance_score: 0.3,
  },
  {
    title: "No Score",
    url: "https://noscore.com",
  },
];

// =============================================================================
// Rendering Tests
// =============================================================================

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SourceCitations", () => {
  describe("rendering", () => {
    it("should render sources section with correct count", () => {
      render(<SourceCitations sources={mockSources} />);

      const section = screen.getByTestId("sources-section");
      expect(section).toBeInTheDocument();
      expect(screen.getByText("Sources (3)")).toBeInTheDocument();
    });

    it("should render each source as a link", () => {
      render(<SourceCitations sources={mockSources} />);

      const links = screen.getAllByRole("link");
      expect(links).toHaveLength(3);

      expect(links[0]).toHaveAttribute(
        "href",
        "https://docs.python.org/3/tutorial",
      );
      expect(links[1]).toHaveAttribute(
        "href",
        "https://realpython.com/python-basics/",
      );
      expect(links[2]).toHaveAttribute(
        "href",
        "https://stackoverflow.com/questions/tagged/python",
      );
    });

    it("should display source titles", () => {
      render(<SourceCitations sources={mockSources} />);

      expect(screen.getByText("Python Documentation")).toBeInTheDocument();
      expect(screen.getByText("Real Python")).toBeInTheDocument();
      expect(screen.getByText("Stack Overflow")).toBeInTheDocument();
    });

    it("should open links in new tab with security attributes", () => {
      render(<SourceCitations sources={mockSources} />);

      const links = screen.getAllByRole("link");
      links.forEach((link) => {
        expect(link).toHaveAttribute("target", "_blank");
        expect(link).toHaveAttribute("rel", "noopener noreferrer");
      });
    });

    it("should return null for empty sources array", () => {
      const { container } = render(<SourceCitations sources={[]} />);
      expect(container.firstChild).toBeNull();
    });

    it("should return null for undefined sources", () => {
      const { container } = render(
        <SourceCitations sources={undefined as unknown as SourceCitation[]} />,
      );
      expect(container.firstChild).toBeNull();
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("accessibility", () => {
    it("should have navigation landmark with aria-label", () => {
      render(<SourceCitations sources={mockSources} />);

      const nav = screen.getByRole("navigation");
      expect(nav).toHaveAttribute("aria-label", "Source citations");
    });

    it("should have accessible labels for each source link", () => {
      render(<SourceCitations sources={mockSources} />);

      const links = screen.getAllByRole("link");
      expect(links[0]).toHaveAttribute(
        "aria-label",
        "Source: Python Documentation (opens in new tab)",
      );
      expect(links[1]).toHaveAttribute(
        "aria-label",
        "Source: Real Python (opens in new tab)",
      );
    });

    it("should hide decorative external link icon from screen readers", () => {
      render(<SourceCitations sources={mockSources} />);

      // External link icons should have aria-hidden
      const section = screen.getByTestId("sources-section");
      const icons = section.querySelectorAll('[aria-hidden="true"]');
      expect(icons.length).toBeGreaterThan(0);
    });
  });

  // ===========================================================================
  // Edge Cases
  // ===========================================================================

  describe("edge cases", () => {
    it("should display domain when title is empty", () => {
      const sourcesNoTitle: SourceCitation[] = [
        {
          title: "",
          url: "https://docs.python.org/3/tutorial/index.html",
        },
      ];

      render(<SourceCitations sources={sourcesNoTitle} />);

      expect(screen.getByText("docs.python.org")).toBeInTheDocument();
    });

    it("should handle malformed URLs gracefully", () => {
      const sourcesWithBadUrl: SourceCitation[] = [
        {
          title: "Good Title",
          url: "not-a-valid-url",
        },
      ];

      render(<SourceCitations sources={sourcesWithBadUrl} />);

      // Should display the title, not crash
      expect(screen.getByText("Good Title")).toBeInTheDocument();
    });

    it("should truncate long titles", () => {
      const longTitleSource: SourceCitation[] = [
        {
          title:
            "A Very Long Title That Should Be Truncated in the Display Because It Exceeds the Maximum Width Allowed",
          url: "https://example.com/long",
        },
      ];

      render(<SourceCitations sources={longTitleSource} />);

      // The title should be in document but truncated via CSS
      const link = screen.getByRole("link");
      const titleSpan = within(link).getByText(/A Very Long Title/);
      expect(titleSpan).toHaveClass("truncate");
    });

    it("should show snippet as tooltip title", () => {
      render(<SourceCitations sources={mockSources} />);

      const links = screen.getAllByRole("link");
      expect(links[0]).toHaveAttribute(
        "title",
        "The Python Tutorial — Python 3.13 documentation",
      );
    });

    it("should use source title as tooltip when no snippet", () => {
      const sourceNoSnippet: SourceCitation[] = [
        {
          title: "Python Docs",
          url: "https://python.org",
        },
      ];

      render(<SourceCitations sources={sourceNoSnippet} />);

      const link = screen.getByRole("link");
      expect(link).toHaveAttribute("title", "Python Docs");
    });
  });

  // ===========================================================================
  // maxVisible Prop Tests
  // ===========================================================================

  describe("maxVisible prop", () => {
    it("should limit displayed sources to maxVisible", () => {
      const manySources: SourceCitation[] = Array.from(
        { length: 10 },
        (_, i) => ({
          title: `Source ${i + 1}`,
          url: `https://example${i + 1}.com`,
        }),
      );

      render(<SourceCitations sources={manySources} maxVisible={5} />);

      const links = screen.getAllByRole("link");
      expect(links).toHaveLength(5);
    });

    it("should show overflow indicator when sources exceed maxVisible", () => {
      const manySources: SourceCitation[] = Array.from(
        { length: 7 },
        (_, i) => ({
          title: `Source ${i + 1}`,
          url: `https://example${i + 1}.com`,
        }),
      );

      render(<SourceCitations sources={manySources} maxVisible={5} />);

      expect(screen.getByText("+2 more")).toBeInTheDocument();
    });

    it("should not show overflow indicator when sources equal maxVisible", () => {
      const sources: SourceCitation[] = Array.from({ length: 5 }, (_, i) => ({
        title: `Source ${i + 1}`,
        url: `https://example${i + 1}.com`,
      }));

      render(<SourceCitations sources={sources} maxVisible={5} />);

      expect(screen.queryByText(/more/)).not.toBeInTheDocument();
    });

    it("should use default maxVisible of 5", () => {
      const manySources: SourceCitation[] = Array.from(
        { length: 8 },
        (_, i) => ({
          title: `Source ${i + 1}`,
          url: `https://example${i + 1}.com`,
        }),
      );

      render(<SourceCitations sources={manySources} />);

      const links = screen.getAllByRole("link");
      expect(links).toHaveLength(5);
      expect(screen.getByText("+3 more")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Relevance Score Tests
  // ===========================================================================

  describe("relevance score", () => {
    it("should handle sources with relevance_score", () => {
      render(<SourceCitations sources={sourcesWithRelevance} />);

      expect(screen.getByText("High Relevance")).toBeInTheDocument();
      expect(screen.getByText("Low Relevance")).toBeInTheDocument();
      expect(screen.getByText("No Score")).toBeInTheDocument();
    });

    it("should preserve source order (sorted externally)", () => {
      render(<SourceCitations sources={sourcesWithRelevance} />);

      const links = screen.getAllByRole("link");
      expect(links[0]).toHaveTextContent("High Relevance");
      expect(links[1]).toHaveTextContent("Low Relevance");
      expect(links[2]).toHaveTextContent("No Score");
    });
  });

  // ===========================================================================
  // Custom className Tests
  // ===========================================================================

  describe("className prop", () => {
    it("should apply custom className", () => {
      render(
        <SourceCitations sources={mockSources} className="custom-class" />,
      );

      const section = screen.getByTestId("sources-section");
      expect(section).toHaveClass("custom-class");
    });
  });

  // ===========================================================================
  // KB Source Icon Differentiation Tests
  // ===========================================================================

  describe("KB source icon differentiation", () => {
    const mixedSources: SourceCitation[] = [
      { title: "Web Source", url: "https://example.com" },
      { title: "KB Source", url: "/kb/docs/api.md" },
    ];

    it("should show different icon for KB sources", () => {
      render(<SourceCitations sources={mixedSources} />);

      // KB sources should have a book icon (data-testid="kb-icon")
      expect(screen.getByTestId("kb-icon")).toBeInTheDocument();
      // Web sources should have external link icon (data-testid="web-icon")
      expect(screen.getByTestId("web-icon")).toBeInTheDocument();
    });

    it("should identify KB sources by /kb/ URL prefix", () => {
      const kbSources: SourceCitation[] = [
        { title: "API Guide", url: "/kb/docs/api.md" },
        { title: "Config Ref", url: "kb://config.md" },
      ];

      render(<SourceCitations sources={kbSources} />);

      const kbIcons = screen.getAllByTestId("kb-icon");
      expect(kbIcons).toHaveLength(2);
    });

    it("should use external link icon for web sources", () => {
      render(<SourceCitations sources={mockSources} />);

      const webIcons = screen.getAllByTestId("web-icon");
      expect(webIcons).toHaveLength(3);
    });
  });

  // ===========================================================================
  // Source Grouping Tests
  // ===========================================================================

  describe("source grouping", () => {
    const groupedSources: SourceCitation[] = [
      { title: "Web 1", url: "https://a.com" },
      { title: "KB 1", url: "/kb/a.md" },
      { title: "Web 2", url: "https://b.com" },
      { title: "KB 2", url: "/kb/b.md" },
    ];

    it("should group sources by type when groupByType is enabled", () => {
      render(<SourceCitations sources={groupedSources} groupByType />);

      // Should have two groups
      expect(screen.getByTestId("web-sources-group")).toBeInTheDocument();
      expect(screen.getByTestId("kb-sources-group")).toBeInTheDocument();
    });

    it("should show group headers when groupByType is enabled", () => {
      render(<SourceCitations sources={groupedSources} groupByType />);

      expect(screen.getByText("Web (2)")).toBeInTheDocument();
      expect(screen.getByText("Knowledge Base (2)")).toBeInTheDocument();
    });

    it("should not group sources by default", () => {
      render(<SourceCitations sources={groupedSources} />);

      // Should not have group testids when not grouped
      expect(screen.queryByTestId("web-sources-group")).not.toBeInTheDocument();
      expect(screen.queryByTestId("kb-sources-group")).not.toBeInTheDocument();
    });

    it("should hide empty groups", () => {
      const webOnlySources: SourceCitation[] = [
        { title: "Web 1", url: "https://a.com" },
        { title: "Web 2", url: "https://b.com" },
      ];

      render(<SourceCitations sources={webOnlySources} groupByType />);

      expect(screen.getByTestId("web-sources-group")).toBeInTheDocument();
      expect(screen.queryByTestId("kb-sources-group")).not.toBeInTheDocument();
    });
  });
});
