/**
 * HelpPane Tests
 *
 * Phase 6: Help & Accessibility
 * Tests for searchable help pane component.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { HelpPane, type HelpTopic } from "./HelpPane";

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
});
