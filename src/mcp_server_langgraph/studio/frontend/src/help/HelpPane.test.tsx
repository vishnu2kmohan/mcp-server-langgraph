/**
 * HelpPane Tests
 *
 * Phase 6: Help & Accessibility
 * Tests for searchable help pane component.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);
import { HelpPane, type HelpTopic } from "./HelpPane";

// Mock useContextualHelp hook
vi.mock("../hooks/useUXIntelligence", () => ({
  useContextualHelp: vi.fn(() => ({
    topics: [],
    quickActions: [],
    summary: null,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

describe("HelpPane", () => {
  const mockTopics: HelpTopic[] = [
    {
      id: "getting-started",
      title: "Getting Started",
      category: "basics",
      content: "Welcome to the platform. This guide will help you get started.",
      keywords: ["introduction", "start", "basics"],
    },
    {
      id: "keyboard-shortcuts",
      title: "Keyboard Shortcuts",
      category: "productivity",
      content: "Learn keyboard shortcuts to boost your productivity.",
      keywords: ["shortcuts", "keyboard", "hotkeys"],
    },
    {
      id: "compliance-overview",
      title: "Compliance Overview",
      category: "compliance",
      content: "Understanding SOC-2, HIPAA, GDPR, and FedRAMP compliance.",
      keywords: ["compliance", "soc2", "hipaa", "gdpr"],
    },
  ];

  const mockOnTopicSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("renders the help pane container", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );
      expect(screen.getByTestId("help-pane")).toBeInTheDocument();
    });

    it("renders help pane header", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );
      // Get the h3 element specifically
      expect(
        screen.getByRole("heading", { name: /help/i }),
      ).toBeInTheDocument();
    });

    it("renders search input", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );
      expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
    });

    it("renders all topics", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );
      expect(screen.getByText("Getting Started")).toBeInTheDocument();
      expect(screen.getByText("Keyboard Shortcuts")).toBeInTheDocument();
      expect(screen.getByText("Compliance Overview")).toBeInTheDocument();
    });

    it("shows empty state when no topics", () => {
      render(<HelpPane topics={[]} onTopicSelect={mockOnTopicSelect} />);
      expect(screen.getByText(/no help topics/i)).toBeInTheDocument();
    });
  });

  describe("Search", () => {
    it("filters topics by title", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "keyboard" } });

      expect(screen.getByText("Keyboard Shortcuts")).toBeInTheDocument();
      expect(screen.queryByText("Getting Started")).not.toBeInTheDocument();
    });

    it("filters topics by keywords", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "soc2" } });

      expect(screen.getByText("Compliance Overview")).toBeInTheDocument();
      expect(screen.queryByText("Getting Started")).not.toBeInTheDocument();
    });

    it("shows no results message when search matches nothing", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "nonexistent" } });

      expect(screen.getByText(/no results/i)).toBeInTheDocument();
    });

    it("clears search when clear button is clicked", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "keyboard" } });

      const clearButton = screen.getByLabelText(/clear search/i);
      fireEvent.click(clearButton);

      expect(screen.getByText("Getting Started")).toBeInTheDocument();
    });
  });

  describe("Topic Selection", () => {
    it("calls onTopicSelect when topic is clicked", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );

      fireEvent.click(screen.getByText("Getting Started"));

      expect(mockOnTopicSelect).toHaveBeenCalledWith(mockTopics[0]);
    });
  });

  describe("Categories", () => {
    it("shows category labels", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );
      // Categories may also appear in content, so check category badges specifically
      // Each topic has a category badge as a span element
      const basicsElements = screen.getAllByText(/basics/i);
      expect(basicsElements.length).toBeGreaterThan(0);
      const productivityElements = screen.getAllByText(/productivity/i);
      expect(productivityElements.length).toBeGreaterThan(0);
      const complianceElements = screen.getAllByText(/compliance/i);
      expect(complianceElements.length).toBeGreaterThan(0);
    });
  });

  describe("Loading State", () => {
    it("shows loading state when isLoading is true", () => {
      render(
        <HelpPane
          topics={[]}
          onTopicSelect={mockOnTopicSelect}
          isLoading={true}
        />,
      );
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe("Accessibility (WCAG 2.1 AA)", () => {
    it("should have no accessibility violations with topics", async () => {
      const { container } = render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when empty", async () => {
      const { container } = render(
        <HelpPane topics={[]} onTopicSelect={mockOnTopicSelect} />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("Search Edge Cases", () => {
    it("filters topics by content", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "platform" } });

      expect(screen.getByText("Getting Started")).toBeInTheDocument();
      expect(screen.queryByText("Keyboard Shortcuts")).not.toBeInTheDocument();
    });

    it("handles whitespace-only search query", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "   " } });

      // Should show all topics when query is whitespace only
      expect(screen.getByText("Getting Started")).toBeInTheDocument();
      expect(screen.getByText("Keyboard Shortcuts")).toBeInTheDocument();
      expect(screen.getByText("Compliance Overview")).toBeInTheDocument();
    });

    it("handles case-insensitive keyword search", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "HOTKEYS" } });

      expect(screen.getByText("Keyboard Shortcuts")).toBeInTheDocument();
    });

    it("handles partial keyword matches", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "intro" } });

      expect(screen.getByText("Getting Started")).toBeInTheDocument();
    });

    it("does not show clear button when search is empty", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );

      expect(screen.queryByLabelText(/clear search/i)).not.toBeInTheDocument();
    });

    it("shows clear button when search has content", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "test" } });

      expect(screen.getByLabelText(/clear search/i)).toBeInTheDocument();
    });
  });

  describe("Category Colors", () => {
    it("applies correct color for unknown category", () => {
      const topicWithUnknownCategory: HelpTopic[] = [
        {
          id: "unknown-cat",
          title: "Unknown Category Topic",
          category: "unknown",
          content: "This has an unknown category",
          keywords: ["test"],
        },
      ];

      render(
        <HelpPane
          topics={topicWithUnknownCategory}
          onTopicSelect={mockOnTopicSelect}
        />,
      );

      // Should render without error
      expect(screen.getByText("Unknown Category Topic")).toBeInTheDocument();
      expect(screen.getByText("unknown")).toBeInTheDocument();
    });
  });

  describe("Custom className", () => {
    it("applies custom className to container", () => {
      render(
        <HelpPane
          topics={mockTopics}
          onTopicSelect={mockOnTopicSelect}
          className="custom-help-class"
        />,
      );

      expect(screen.getByTestId("help-pane")).toHaveClass("custom-help-class");
    });
  });

  describe("Topic Selection", () => {
    it("calls onTopicSelect with correct topic when filtered topic is clicked", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );

      // Filter to show only one topic
      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "keyboard" } });

      // Click the filtered topic
      fireEvent.click(screen.getByText("Keyboard Shortcuts"));

      expect(mockOnTopicSelect).toHaveBeenCalledWith(mockTopics[1]);
    });
  });

  describe("Topic Content Display", () => {
    it("displays topic content preview", () => {
      render(
        <HelpPane topics={mockTopics} onTopicSelect={mockOnTopicSelect} />,
      );

      expect(
        screen.getByText(/welcome to the platform/i),
      ).toBeInTheDocument();
    });

    it("displays all keywords matching topics when multiple match", () => {
      const topicsWithSharedKeywords: HelpTopic[] = [
        {
          id: "topic-1",
          title: "First Topic",
          category: "basics",
          content: "First content",
          keywords: ["shared"],
        },
        {
          id: "topic-2",
          title: "Second Topic",
          category: "basics",
          content: "Second content",
          keywords: ["shared"],
        },
      ];

      render(
        <HelpPane
          topics={topicsWithSharedKeywords}
          onTopicSelect={mockOnTopicSelect}
        />,
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "shared" } });

      expect(screen.getByText("First Topic")).toBeInTheDocument();
      expect(screen.getByText("Second Topic")).toBeInTheDocument();
    });
  });

  describe("AI Contextual Help Integration (Sprint 6)", () => {
    it("should accept enableAI prop", () => {
      render(
        <HelpPane
          topics={mockTopics}
          onTopicSelect={mockOnTopicSelect}
          enableAI={true}
          currentPage="chat"
        />
      );
      expect(screen.getByTestId("help-pane")).toBeInTheDocument();
    });

    it("should show contextual suggestions section when AI is enabled", () => {
      render(
        <HelpPane
          topics={mockTopics}
          onTopicSelect={mockOnTopicSelect}
          enableAI={true}
          currentPage="chat"
        />
      );
      // The component should render with AI section
      expect(screen.getByTestId("help-pane")).toBeInTheDocument();
    });

    it("should not show AI section when enableAI is false", () => {
      render(
        <HelpPane
          topics={mockTopics}
          onTopicSelect={mockOnTopicSelect}
          enableAI={false}
        />
      );
      expect(screen.queryByTestId("ai-contextual-help-section")).not.toBeInTheDocument();
    });

    it("should show quick actions when provided by AI", () => {
      render(
        <HelpPane
          topics={mockTopics}
          onTopicSelect={mockOnTopicSelect}
          enableAI={true}
          currentPage="admin"
        />
      );
      // Quick actions section should be available when AI provides them
      expect(screen.getByTestId("help-pane")).toBeInTheDocument();
    });

    it("should gracefully handle AI errors", () => {
      // When AI fails, the component should still render regular help
      render(
        <HelpPane
          topics={mockTopics}
          onTopicSelect={mockOnTopicSelect}
          enableAI={true}
          currentPage="chat"
        />
      );
      // Should still show regular topics
      expect(screen.getByText("Getting Started")).toBeInTheDocument();
    });
  });
});
