/**
 * ChatSuggestions Component Tests
 *
 * Tests for the suggested prompts component that shows contextual
 * suggestions to help users start conversations.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ChatSuggestions } from "./ChatSuggestions";

import { TestProvider } from "@/test-utils";

describe("ChatSuggestions", () => {
  const mockSuggestions = [
    {
      id: "1",
      text: "What can you help me with?",
      category: "general",
      icon: "help",
    },
    {
      id: "2",
      text: "Write a Python function",
      category: "coding",
      icon: "code",
    },
    {
      id: "3",
      text: "Explain quantum computing",
      category: "learning",
      icon: "book",
    },
    { id: "4", text: "Review my code", category: "coding", icon: "search" },
  ];

  const mockOnSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render suggestions when provided", () => {
      render(
        <TestProvider>
          <ChatSuggestions
            suggestions={mockSuggestions}
            onSelect={mockOnSelect}
          />
        </TestProvider>,
      );

      expect(
        screen.getByText("What can you help me with?"),
      ).toBeInTheDocument();
      expect(screen.getByText("Write a Python function")).toBeInTheDocument();
      expect(screen.getByText("Explain quantum computing")).toBeInTheDocument();
    });

    it("should render nothing when suggestions array is empty", () => {
      const { container } = render(
        <TestProvider>
          <ChatSuggestions suggestions={[]} onSelect={mockOnSelect} />
        </TestProvider>,
      );

      expect(container.firstChild).toBeNull();
    });

    it("should apply custom className when provided", () => {
      render(
        <TestProvider>
          <ChatSuggestions
            suggestions={mockSuggestions}
            onSelect={mockOnSelect}
            className="custom-class"
          />
        </TestProvider>,
      );

      const container = screen.getByRole("list");
      expect(container.className).toContain("custom-class");
    });
  });

  describe("Interaction", () => {
    it("should call onSelect with suggestion text when clicked", () => {
      render(
        <TestProvider>
          <ChatSuggestions
            suggestions={mockSuggestions}
            onSelect={mockOnSelect}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Write a Python function"));

      expect(mockOnSelect).toHaveBeenCalledTimes(1);
      expect(mockOnSelect).toHaveBeenCalledWith("Write a Python function");
    });

    it("should handle keyboard navigation with Enter key", () => {
      render(
        <TestProvider>
          <ChatSuggestions
            suggestions={mockSuggestions}
            onSelect={mockOnSelect}
          />
        </TestProvider>,
      );

      const suggestion = screen.getByText("Explain quantum computing");
      fireEvent.keyDown(suggestion, { key: "Enter" });

      expect(mockOnSelect).toHaveBeenCalledWith("Explain quantum computing");
    });
  });

  describe("Loading State", () => {
    it("should show loading skeleton when isLoading is true", () => {
      render(
        <TestProvider>
          <ChatSuggestions
            suggestions={[]}
            onSelect={mockOnSelect}
            isLoading={true}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestions-loading")).toBeInTheDocument();
    });

    it("should not show loading skeleton when isLoading is false", () => {
      render(
        <TestProvider>
          <ChatSuggestions
            suggestions={mockSuggestions}
            onSelect={mockOnSelect}
            isLoading={false}
          />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("suggestions-loading"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Visibility Control", () => {
    it("should be visible by default", () => {
      render(
        <TestProvider>
          <ChatSuggestions
            suggestions={mockSuggestions}
            onSelect={mockOnSelect}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("list")).toBeVisible();
    });

    it("should hide when show prop is false", () => {
      const { container } = render(
        <TestProvider>
          <ChatSuggestions
            suggestions={mockSuggestions}
            onSelect={mockOnSelect}
            show={false}
          />
        </TestProvider>,
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe("Title", () => {
    it("should show default title when suggestions exist", () => {
      render(
        <TestProvider>
          <ChatSuggestions
            suggestions={mockSuggestions}
            onSelect={mockOnSelect}
          />
        </TestProvider>,
      );

      expect(screen.getByText("Try asking")).toBeInTheDocument();
    });

    it("should show custom title when provided", () => {
      render(
        <TestProvider>
          <ChatSuggestions
            suggestions={mockSuggestions}
            onSelect={mockOnSelect}
            title="Start with"
          />
        </TestProvider>,
      );

      expect(screen.getByText("Start with")).toBeInTheDocument();
    });
  });

  describe("Max Suggestions", () => {
    it("should limit displayed suggestions when maxItems is provided", () => {
      render(
        <TestProvider>
          <ChatSuggestions
            suggestions={mockSuggestions}
            onSelect={mockOnSelect}
            maxItems={2}
          />
        </TestProvider>,
      );

      const buttons = screen.getAllByRole("button");
      expect(buttons).toHaveLength(2);
    });

    it("should show all suggestions when maxItems is not provided", () => {
      render(
        <TestProvider>
          <ChatSuggestions
            suggestions={mockSuggestions}
            onSelect={mockOnSelect}
          />
        </TestProvider>,
      );

      const buttons = screen.getAllByRole("button");
      expect(buttons).toHaveLength(4);
    });
  });

  describe("Compact Mode", () => {
    it("should apply compact styling when compact prop is true", () => {
      render(
        <TestProvider>
          <ChatSuggestions
            suggestions={mockSuggestions}
            onSelect={mockOnSelect}
            compact={true}
          />
        </TestProvider>,
      );

      const container = screen.getByRole("list");
      expect(container.className).toContain("gap-2");
    });

    it("should apply normal styling when compact prop is false", () => {
      render(
        <TestProvider>
          <ChatSuggestions
            suggestions={mockSuggestions}
            onSelect={mockOnSelect}
            compact={false}
          />
        </TestProvider>,
      );

      const container = screen.getByRole("list");
      expect(container.className).toContain("gap-3");
    });
  });
});
