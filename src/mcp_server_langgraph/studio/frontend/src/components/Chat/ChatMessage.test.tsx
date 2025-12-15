/**
 * ChatMessage Tests
 *
 * Tests for individual chat message display component.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatMessage } from "./ChatMessage";

describe("ChatMessage", () => {
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
      const { container } = render(
        <ChatMessage
          role="user"
          content="Test message"
          timestamp={new Date()}
        />,
      );

      const messageDiv = container.querySelector('[data-role="user"]');
      expect(messageDiv).toHaveClass("bg-blue-100");
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
      const { container } = render(
        <ChatMessage
          role="assistant"
          content="Test message"
          timestamp={new Date()}
        />,
      );

      const messageDiv = container.querySelector('[data-role="assistant"]');
      expect(messageDiv).toHaveClass("bg-gray-100");
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
      expect(link).toHaveClass("text-blue-600");
    });
  });
});
