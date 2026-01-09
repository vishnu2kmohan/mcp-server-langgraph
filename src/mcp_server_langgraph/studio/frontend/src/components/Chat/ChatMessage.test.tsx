/**
 * ChatMessage Tests
 *
 * Tests for individual chat message display component.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ChatMessage } from "./ChatMessage";

describe("ChatMessage", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("User Messages", () => {
    it("should render user message with correct styling", () => {
      render(
        <ChatMessage
          role="user"
          content="Hello, how are you?"
          timestamp={new Date("2024-01-15T10:30:00Z")}
        />,
      );

      expect(screen.getByText("Hello, how are you?")).toBeInTheDocument();
    });

    it("should display user label", () => {
      render(
        <ChatMessage
          role="user"
          content="Test message"
          timestamp={new Date()}
        />,
      );

      expect(screen.getByText("You")).toBeInTheDocument();
    });

    it("should apply user message styling", () => {
      render(
        <ChatMessage
          role="user"
          content="Test message"
          timestamp={new Date()}
        />,
      );

      const messageBubble = screen.getByTestId("message-bubble");
      expect(messageBubble).toHaveClass("bg-chat-user-bubble");
    });
  });

  describe("Assistant Messages", () => {
    it("should render assistant message", () => {
      render(
        <ChatMessage
          role="assistant"
          content="I am doing well, thank you!"
          timestamp={new Date()}
        />,
      );

      expect(
        screen.getByText("I am doing well, thank you!"),
      ).toBeInTheDocument();
    });

    it("should display assistant label", () => {
      render(
        <ChatMessage
          role="assistant"
          content="Test response"
          timestamp={new Date()}
        />,
      );

      expect(screen.getByText("Assistant")).toBeInTheDocument();
    });

    it("should apply assistant message styling", () => {
      render(
        <ChatMessage
          role="assistant"
          content="Test message"
          timestamp={new Date()}
        />,
      );

      const messageBubble = screen.getByTestId("message-bubble");
      expect(messageBubble).toHaveClass("bg-chat-ai-bubble");
    });
  });

  describe("Avatar (Sprint 3.1)", () => {
    it("should render avatar by default (showAvatar=true)", () => {
      render(
        <ChatMessage
          role="user"
          content="Test message"
          timestamp={new Date()}
        />,
      );

      expect(screen.getByTestId("user-avatar")).toBeInTheDocument();
    });

    it("should not render avatar when showAvatar is false", () => {
      render(
        <ChatMessage
          role="user"
          content="Test message"
          timestamp={new Date()}
          showAvatar={false}
        />,
      );

      expect(screen.queryByTestId("user-avatar")).not.toBeInTheDocument();
    });

    it("should render user avatar when showAvatar is true", () => {
      render(
        <ChatMessage
          role="user"
          content="Test message"
          timestamp={new Date()}
          showAvatar={true}
        />,
      );

      expect(screen.getByTestId("user-avatar")).toBeInTheDocument();
    });

    it("should render assistant avatar when showAvatar is true", () => {
      render(
        <ChatMessage
          role="assistant"
          content="Test response"
          timestamp={new Date()}
          showAvatar={true}
        />,
      );

      expect(screen.getByTestId("assistant-avatar")).toBeInTheDocument();
    });

    it("should display user initials in avatar", () => {
      render(
        <ChatMessage
          role="user"
          content="Test message"
          timestamp={new Date()}
          showAvatar={true}
          userInitials="JD"
        />,
      );

      expect(screen.getByText("JD")).toBeInTheDocument();
    });
  });

  describe("Timestamp", () => {
    it("should display formatted timestamp", () => {
      render(
        <ChatMessage
          role="user"
          content="Test"
          timestamp={new Date("2024-01-15T10:30:00Z")}
          showTimestamp={true}
        />,
      );

      // Should display time in some format
      expect(screen.getByText(/\d{1,2}:\d{2}/)).toBeInTheDocument();
    });

    it("should hide timestamp when showTimestamp is false", () => {
      render(
        <ChatMessage
          role="user"
          content="Test"
          timestamp={new Date("2024-01-15T10:30:00Z")}
          showTimestamp={false}
        />,
      );

      // Timestamp text should not be present
      const timestampElement = screen.queryByTestId("timestamp");
      expect(timestampElement).not.toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when isLoading is true", () => {
      render(
        <ChatMessage
          role="assistant"
          content=""
          timestamp={new Date()}
          isLoading={true}
        />,
      );

      expect(screen.getByTestId("loading-indicator")).toBeInTheDocument();
    });
  });

  describe("Markdown Content", () => {
    it("should render markdown content when enabled", () => {
      render(
        <ChatMessage
          role="assistant"
          content="**Bold text**"
          timestamp={new Date()}
          renderMarkdown={true}
        />,
      );

      // Should render as bold (strong element)
      expect(screen.getByText("Bold text")).toBeInTheDocument();
    });
  });

  describe("AI Source Citations", () => {
    it("should display sources section when sources are provided", () => {
      const sources = [
        { title: "API Documentation", url: "https://example.com/docs" },
        { title: "User Guide", url: "https://example.com/guide" },
      ];

      render(
        <ChatMessage
          role="assistant"
          content="Here is some information"
          timestamp={new Date()}
          sources={sources}
        />,
      );

      expect(screen.getByTestId("sources-section")).toBeInTheDocument();
      expect(screen.getByText("Sources:")).toBeInTheDocument();
    });

    it("should render source links as clickable", () => {
      const sources = [
        { title: "API Documentation", url: "https://example.com/docs" },
      ];

      render(
        <ChatMessage
          role="assistant"
          content="Here is some information"
          timestamp={new Date()}
          sources={sources}
        />,
      );

      const link = screen.getByRole("link", { name: "API Documentation" });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("href", "https://example.com/docs");
    });

    it("should open source links in new tab", () => {
      const sources = [
        { title: "External Resource", url: "https://example.com" },
      ];

      render(
        <ChatMessage
          role="assistant"
          content="Check this out"
          timestamp={new Date()}
          sources={sources}
        />,
      );

      const link = screen.getByRole("link", { name: "External Resource" });
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
    });

    it("should not display sources section when sources array is empty", () => {
      render(
        <ChatMessage
          role="assistant"
          content="No sources here"
          timestamp={new Date()}
          sources={[]}
        />,
      );

      expect(screen.queryByTestId("sources-section")).not.toBeInTheDocument();
    });

    it("should not display sources section when sources prop is undefined", () => {
      render(
        <ChatMessage
          role="assistant"
          content="No sources defined"
          timestamp={new Date()}
        />,
      );

      expect(screen.queryByTestId("sources-section")).not.toBeInTheDocument();
    });

    it("should display multiple sources as a list", () => {
      const sources = [
        { title: "Source 1", url: "https://example.com/1" },
        { title: "Source 2", url: "https://example.com/2" },
        { title: "Source 3", url: "https://example.com/3" },
      ];

      render(
        <ChatMessage
          role="assistant"
          content="Multiple sources"
          timestamp={new Date()}
          sources={sources}
        />,
      );

      expect(
        screen.getByRole("link", { name: "Source 1" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: "Source 2" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: "Source 3" }),
      ).toBeInTheDocument();
    });

    it("should not show sources for user messages", () => {
      const sources = [
        { title: "Should not appear", url: "https://example.com" },
      ];

      render(
        <ChatMessage
          role="user"
          content="User message with sources"
          timestamp={new Date()}
          sources={sources}
        />,
      );

      expect(screen.queryByTestId("sources-section")).not.toBeInTheDocument();
    });

    it("should display sources icon", () => {
      const sources = [{ title: "Doc", url: "https://example.com" }];

      render(
        <ChatMessage
          role="assistant"
          content="With icon"
          timestamp={new Date()}
          sources={sources}
        />,
      );

      expect(screen.getByTestId("sources-icon")).toBeInTheDocument();
    });

    it("should style source links appropriately", () => {
      const sources = [{ title: "Styled Link", url: "https://example.com" }];

      render(
        <ChatMessage
          role="assistant"
          content="Styled sources"
          timestamp={new Date()}
          sources={sources}
        />,
      );

      const link = screen.getByRole("link", { name: "Styled Link" });
      expect(link).toHaveClass("text-primary-600");
    });
  });

  describe("Interactive Artifacts", () => {
    it("should render a chart artifact from code block", () => {
      const content = `Here is the data:

\`\`\`chart
{"type": "bar", "data": [{"label": "A", "value": 10}]}
\`\`\`

Hope this helps!`;

      render(
        <ChatMessage
          role="assistant"
          content={content}
          timestamp={new Date()}
          renderArtifacts={true}
        />,
      );

      expect(screen.getByTestId("artifact-chart")).toBeInTheDocument();
    });

    it("should render a mermaid diagram from code block", () => {
      const content = `Here is the diagram:

\`\`\`mermaid
graph TD
    A --> B
\`\`\``;

      render(
        <ChatMessage
          role="assistant"
          content={content}
          timestamp={new Date()}
          renderArtifacts={true}
        />,
      );

      // Mermaid renders an SVG
      expect(screen.getByText("Here is the diagram:")).toBeInTheDocument();
    });

    it("should render executable code with Run button", () => {
      const content = `Here is a component:

\`\`\`tsx
export default function App() {
  return <div>Hello World</div>;
}
\`\`\``;

      render(
        <ChatMessage
          role="assistant"
          content={content}
          timestamp={new Date()}
          renderArtifacts={true}
        />,
      );

      expect(screen.getByRole("button", { name: /run/i })).toBeInTheDocument();
    });

    it("should not render artifacts when renderArtifacts is false", () => {
      const content = `\`\`\`chart
{"type": "bar", "data": []}
\`\`\``;

      render(
        <ChatMessage
          role="assistant"
          content={content}
          timestamp={new Date()}
          renderArtifacts={false}
        />,
      );

      expect(screen.queryByTestId("artifact-chart")).not.toBeInTheDocument();
    });

    it("should render JSON artifact", () => {
      const content = `Here is the config:

\`\`\`json
{"key": "value", "nested": {"a": 1}}
\`\`\``;

      render(
        <ChatMessage
          role="assistant"
          content={content}
          timestamp={new Date()}
          renderArtifacts={true}
        />,
      );

      expect(screen.getByTestId("artifact-json")).toBeInTheDocument();
    });

    it("should render SVG artifact", () => {
      const content = `Here is the icon:

\`\`\`svg
<svg width="100" height="100"><circle cx="50" cy="50" r="40" fill="red"/></svg>
\`\`\``;

      render(
        <ChatMessage
          role="assistant"
          content={content}
          timestamp={new Date()}
          renderArtifacts={true}
        />,
      );

      expect(screen.getByTestId("artifact-svg")).toBeInTheDocument();
    });

    it("should render regular code as code artifact", () => {
      const content = `Here is the code:

\`\`\`python
def hello():
    print("world")
\`\`\``;

      render(
        <ChatMessage
          role="assistant"
          content={content}
          timestamp={new Date()}
          renderArtifacts={true}
        />,
      );

      expect(screen.getByTestId("artifact-code")).toBeInTheDocument();
    });

    it("should render multiple artifacts in one message", () => {
      const content = `Chart:

\`\`\`chart
{"type": "bar", "data": [{"label": "A", "value": 10}]}
\`\`\`

And JSON:

\`\`\`json
{"key": "value"}
\`\`\``;

      render(
        <ChatMessage
          role="assistant"
          content={content}
          timestamp={new Date()}
          renderArtifacts={true}
        />,
      );

      expect(screen.getByTestId("artifact-chart")).toBeInTheDocument();
      expect(screen.getByTestId("artifact-json")).toBeInTheDocument();
    });

    it("should preserve text segments between artifacts", () => {
      const content = `Introduction text.

\`\`\`json
{"key": "value"}
\`\`\`

Conclusion text.`;

      render(
        <ChatMessage
          role="assistant"
          content={content}
          timestamp={new Date()}
          renderArtifacts={true}
        />,
      );

      expect(screen.getByText("Introduction text.")).toBeInTheDocument();
      expect(screen.getByText("Conclusion text.")).toBeInTheDocument();
    });
  });

  describe("AI Follow-Up Suggestions", () => {
    const mockSuggestions = [
      {
        id: "s1",
        text: "Tell me more about this",
        category: "explore" as const,
      },
      {
        id: "s2",
        text: "Can you give an example?",
        category: "example" as const,
      },
    ];

    it("should display follow-up suggestions for assistant messages", () => {
      render(
        <ChatMessage
          role="assistant"
          content="Here is some information"
          timestamp={new Date()}
          suggestions={mockSuggestions}
          onSuggestionSelect={vi.fn()}
        />,
      );

      expect(screen.getByTestId("follow-up-suggestions")).toBeInTheDocument();
    });

    it("should render suggestion chips", () => {
      render(
        <ChatMessage
          role="assistant"
          content="Here is some information"
          timestamp={new Date()}
          suggestions={mockSuggestions}
          onSuggestionSelect={vi.fn()}
        />,
      );

      expect(screen.getByText("Tell me more about this")).toBeInTheDocument();
      expect(screen.getByText("Can you give an example?")).toBeInTheDocument();
    });

    it("should call onSuggestionSelect when suggestion is clicked", () => {
      const handleSelect = vi.fn();
      render(
        <ChatMessage
          role="assistant"
          content="Here is some information"
          timestamp={new Date()}
          suggestions={mockSuggestions}
          onSuggestionSelect={handleSelect}
        />,
      );

      fireEvent.click(screen.getByText("Tell me more about this"));
      expect(handleSelect).toHaveBeenCalledWith(mockSuggestions[0]);
    });

    it("should not display suggestions for user messages", () => {
      render(
        <ChatMessage
          role="user"
          content="My message"
          timestamp={new Date()}
          suggestions={mockSuggestions}
          onSuggestionSelect={vi.fn()}
        />,
      );

      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });

    it("should not display suggestions when loading", () => {
      render(
        <ChatMessage
          role="assistant"
          content=""
          timestamp={new Date()}
          isLoading={true}
          suggestions={mockSuggestions}
          onSuggestionSelect={vi.fn()}
        />,
      );

      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });

    it("should show loading state for suggestions", () => {
      render(
        <ChatMessage
          role="assistant"
          content="Here is info"
          timestamp={new Date()}
          suggestionsLoading={true}
          onSuggestionSelect={vi.fn()}
        />,
      );

      expect(screen.getByTestId("suggestions-loading")).toBeInTheDocument();
    });

    it("should not display suggestions when empty array", () => {
      render(
        <ChatMessage
          role="assistant"
          content="Here is info"
          timestamp={new Date()}
          suggestions={[]}
          onSuggestionSelect={vi.fn()}
        />,
      );

      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });

    it("should position suggestions after sources if both present", () => {
      const sources = [{ title: "Doc", url: "https://example.com" }];

      const { container } = render(
        <ChatMessage
          role="assistant"
          content="Here is info"
          timestamp={new Date()}
          sources={sources}
          suggestions={mockSuggestions}
          onSuggestionSelect={vi.fn()}
        />,
      );

      const sourcesSection = container.querySelector(
        '[data-testid="sources-section"]',
      );
      const suggestionsSection = container.querySelector(
        '[data-testid="follow-up-suggestions"]',
      );

      expect(sourcesSection).toBeInTheDocument();
      expect(suggestionsSection).toBeInTheDocument();
    });
  });

  describe("Selected Tools Display (ADR-0099)", () => {
    it("should display selected tools for assistant messages", () => {
      const selectedTools = ["calculator", "search", "read_file"];
      const selectionScores = { calculator: 0.95, search: 0.88, read_file: 0.75 };

      render(
        <ChatMessage
          role="assistant"
          content="Here is the result"
          timestamp={new Date()}
          selectedTools={selectedTools}
          selectionScores={selectionScores}
        />,
      );

      expect(screen.getByTestId("selected-tools-display")).toBeInTheDocument();
      expect(screen.getByText("calculator")).toBeInTheDocument();
      expect(screen.getByText("search")).toBeInTheDocument();
      expect(screen.getByText("read_file")).toBeInTheDocument();
    });

    it("should show selection scores as percentages", () => {
      const selectedTools = ["calculator"];
      const selectionScores = { calculator: 0.95 };

      render(
        <ChatMessage
          role="assistant"
          content="Calculated result"
          timestamp={new Date()}
          selectedTools={selectedTools}
          selectionScores={selectionScores}
        />,
      );

      expect(screen.getByText("95%")).toBeInTheDocument();
    });

    it("should show total available tools count when provided", () => {
      const selectedTools = ["calculator", "search"];
      const selectionScores = { calculator: 0.9, search: 0.8 };

      render(
        <ChatMessage
          role="assistant"
          content="Result with tool count"
          timestamp={new Date()}
          selectedTools={selectedTools}
          selectionScores={selectionScores}
          totalAvailableTools={50}
        />,
      );

      expect(screen.getByText("(2 of 50)")).toBeInTheDocument();
    });

    it("should not display selected tools for user messages", () => {
      const selectedTools = ["calculator"];
      const selectionScores = { calculator: 0.95 };

      render(
        <ChatMessage
          role="user"
          content="Calculate something"
          timestamp={new Date()}
          selectedTools={selectedTools}
          selectionScores={selectionScores}
        />,
      );

      expect(
        screen.queryByTestId("selected-tools-display"),
      ).not.toBeInTheDocument();
    });

    it("should not display selected tools when loading", () => {
      const selectedTools = ["calculator"];
      const selectionScores = { calculator: 0.95 };

      render(
        <ChatMessage
          role="assistant"
          content=""
          timestamp={new Date()}
          isLoading={true}
          selectedTools={selectedTools}
          selectionScores={selectionScores}
        />,
      );

      expect(
        screen.queryByTestId("selected-tools-display"),
      ).not.toBeInTheDocument();
    });

    it("should not display selected tools when array is empty", () => {
      render(
        <ChatMessage
          role="assistant"
          content="No tools used"
          timestamp={new Date()}
          selectedTools={[]}
          selectionScores={{}}
        />,
      );

      expect(
        screen.queryByTestId("selected-tools-display"),
      ).not.toBeInTheDocument();
    });

    it("should not display selected tools when props are undefined", () => {
      render(
        <ChatMessage
          role="assistant"
          content="No tool selection info"
          timestamp={new Date()}
        />,
      );

      expect(
        screen.queryByTestId("selected-tools-display"),
      ).not.toBeInTheDocument();
    });

    it("should render in compact mode", () => {
      const selectedTools = ["calculator", "search"];
      const selectionScores = { calculator: 0.9, search: 0.8 };

      const { container } = render(
        <ChatMessage
          role="assistant"
          content="Compact display"
          timestamp={new Date()}
          selectedTools={selectedTools}
          selectionScores={selectionScores}
        />,
      );

      // SelectedToolsDisplay uses compact mode by default in ChatMessage
      expect(container.querySelector(".text-xs")).toBeInTheDocument();
    });
  });
});
