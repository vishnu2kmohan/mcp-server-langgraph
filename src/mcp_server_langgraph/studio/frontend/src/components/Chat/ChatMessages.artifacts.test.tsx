/**
 * ChatMessages Artifacts Tests
 *
 * Tests for code blocks, diagrams, charts, and citation rendering.
 * Split from ChatMessages.test.tsx for memory optimization.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { ChatMessages } from "./ChatMessages";

describe("ChatMessages Artifacts", () => {
  // Cleanup after each test to prevent DOM leakage and state pollution
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("Source Citations", () => {
    const messagesWithSources = [
      {
        id: "msg-1",
        role: "user" as const,
        content: "What is LangGraph?",
        timestamp: Date.now() - 60000,
      },
      {
        id: "msg-2",
        role: "assistant" as const,
        content: "LangGraph is a framework for building stateful agents.",
        timestamp: Date.now() - 30000,
        sources: [
          {
            title: "LangGraph Documentation",
            url: "https://langchain-ai.github.io/langgraph",
          },
          {
            title: "LangChain Blog",
            url: "https://blog.langchain.dev/langgraph",
          },
        ],
      },
    ];

    it("should display sources section when assistant message has sources", () => {
      render(<ChatMessages messages={messagesWithSources} />);
      expect(screen.getByText("Sources:")).toBeInTheDocument();
    });

    it("should render source links", () => {
      render(<ChatMessages messages={messagesWithSources} />);
      expect(screen.getByText("LangGraph Documentation")).toBeInTheDocument();
      expect(screen.getByText("LangChain Blog")).toBeInTheDocument();
    });

    it("should have correct href on source links", () => {
      render(<ChatMessages messages={messagesWithSources} />);
      const docLink = screen.getByText("LangGraph Documentation");
      expect(docLink).toHaveAttribute(
        "href",
        "https://langchain-ai.github.io/langgraph",
      );
    });

    it("should open links in new tab", () => {
      render(<ChatMessages messages={messagesWithSources} />);
      const docLink = screen.getByText("LangGraph Documentation");
      expect(docLink).toHaveAttribute("target", "_blank");
      expect(docLink).toHaveAttribute("rel", "noopener noreferrer");
    });

    it("should not show sources for user messages", () => {
      const userWithSources = [
        {
          id: "msg-1",
          role: "user" as const,
          content: "Hello",
          timestamp: Date.now(),
          sources: [{ title: "Test", url: "https://test.com" }],
        },
      ];
      render(<ChatMessages messages={userWithSources} />);
      expect(screen.queryByText("Sources:")).not.toBeInTheDocument();
    });

    it("should not show sources section when sources array is empty", () => {
      const noSources = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content: "Response without sources",
          timestamp: Date.now(),
          sources: [],
        },
      ];
      render(<ChatMessages messages={noSources} />);
      expect(screen.queryByText("Sources:")).not.toBeInTheDocument();
    });
  });

  describe("Mermaid Diagram Rendering", () => {
    it("should render mermaid code blocks as diagrams", async () => {
      const mermaidMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content:
            "Here's a diagram:\n\n```mermaid\ngraph TD\n    A[Start] --> B[End]\n```",
          timestamp: Date.now(),
        },
      ];
      render(<ChatMessages messages={mermaidMessage} />);
      // Should render the mermaid diagram container, not just code
      const diagramContainer = document.querySelector(
        ".bg-gray-50, .dark\\:bg-gray-800",
      );
      expect(diagramContainer).toBeInTheDocument();
    });

    it("should not render regular code blocks as mermaid diagrams", async () => {
      const jsCodeMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content: "```javascript\nconst x = 1;\nconst y = 2;\n```",
          timestamp: Date.now(),
        },
      ];
      render(<ChatMessages messages={jsCodeMessage} />);
      // Should show the code block with language label
      expect(
        await screen.findByText("javascript", {}, { timeout: 5000 }),
      ).toBeInTheDocument();
      const codeContainer = document.querySelector("pre");
      expect(codeContainer?.textContent).toContain("const");
      expect(codeContainer?.textContent).toContain("x");
    });
  });

  describe("Chart Rendering", () => {
    it("should render chart code blocks as interactive charts", () => {
      const chartMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content:
            '```chart\n{"type": "bar", "title": "Sales", "data": [{"name": "Jan", "value": 100}]}\n```',
          timestamp: Date.now(),
        },
      ];
      render(<ChatMessages messages={chartMessage} />);
      expect(screen.getByText("Sales")).toBeInTheDocument();
    });
  });

  describe("Interactive Artifacts Feature Flag", () => {
    it("should render mermaid diagrams when enableInteractiveArtifacts is true", () => {
      const mermaidMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content:
            "Here's a diagram:\n\n```mermaid\ngraph TD\n    A[Start] --> B[End]\n```",
          timestamp: Date.now(),
        },
      ];
      render(
        <ChatMessages messages={mermaidMessage} enableInteractiveArtifacts />,
      );
      const diagramContainer = document.querySelector(
        ".bg-gray-50, .dark\\:bg-gray-800",
      );
      expect(diagramContainer).toBeInTheDocument();
    });

    it("should render chart blocks as interactive charts when enableInteractiveArtifacts is true", () => {
      const chartMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content:
            '```chart\n{"type": "bar", "title": "Test Chart", "data": [{"name": "A", "value": 10}]}\n```',
          timestamp: Date.now(),
        },
      ];
      render(
        <ChatMessages messages={chartMessage} enableInteractiveArtifacts />,
      );
      expect(screen.getByText("Test Chart")).toBeInTheDocument();
    });

    it("should render mermaid as plain code when enableInteractiveArtifacts is false", async () => {
      const mermaidMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content:
            "Here's a diagram:\n\n```mermaid\ngraph TD\n    A[Start] --> B[End]\n```",
          timestamp: Date.now(),
        },
      ];
      render(
        <ChatMessages
          messages={mermaidMessage}
          enableInteractiveArtifacts={false}
        />,
      );
      expect(await screen.findByText("mermaid")).toBeInTheDocument();
    });

    it("should render chart as plain code when enableInteractiveArtifacts is false", async () => {
      const chartMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content:
            '```chart\n{\n  "type": "bar",\n  "title": "Test Chart",\n  "data": []\n}\n```',
          timestamp: Date.now(),
        },
      ];
      render(
        <ChatMessages
          messages={chartMessage}
          enableInteractiveArtifacts={false}
        />,
      );
      expect(await screen.findByText("chart")).toBeInTheDocument();
    });

    it("should default to enabled for interactive artifacts", () => {
      const chartMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content:
            '```chart\n{"type": "bar", "title": "Default Enabled", "data": [{"name": "A", "value": 5}]}\n```',
          timestamp: Date.now(),
        },
      ];
      render(<ChatMessages messages={chartMessage} />);
      expect(screen.getByText("Default Enabled")).toBeInTheDocument();
    });
  });

  describe("Enhanced Code Block Features", () => {
    const codeMessage = [
      {
        id: "msg-1",
        role: "assistant" as const,
        content:
          "```python\ndef hello():\n    print('Hello, World!')\n    return True\n```",
        timestamp: Date.now(),
      },
    ];

    it("should render code block with language label", async () => {
      render(<ChatMessages messages={codeMessage} />);
      expect(await screen.findByText("python")).toBeInTheDocument();
    });

    it("should have copy button", async () => {
      render(<ChatMessages messages={codeMessage} />);
      expect(await screen.findByTitle("Copy code")).toBeInTheDocument();
    });

    it("should have word wrap toggle button", async () => {
      render(<ChatMessages messages={codeMessage} />);
      expect(await screen.findByTitle("Toggle word wrap")).toBeInTheDocument();
    });

    it("should have download button", async () => {
      render(<ChatMessages messages={codeMessage} />);
      expect(await screen.findByTitle("Download file")).toBeInTheDocument();
    });

    it("should show line numbers", async () => {
      render(<ChatMessages messages={codeMessage} />);
      await screen.findByText("python");
      const codeBlock = document.querySelector("pre");
      expect(codeBlock).toBeInTheDocument();
    });
  });
});
