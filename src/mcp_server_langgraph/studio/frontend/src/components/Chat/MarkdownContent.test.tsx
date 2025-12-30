/**
 * MarkdownContent Component Test Suite
 *
 * TDD tests for markdown rendering with custom components.
 * Extracted from ChatMessages.tsx for reusability.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { MarkdownContent } from "./MarkdownContent";

// Mock heavy dependencies to speed up tests
vi.mock("./InteractiveMermaidDiagram", () => ({
  default: ({ code }: { code: string }) => (
    <div data-testid="mermaid-diagram">{code}</div>
  ),
}));

vi.mock("./CodeBlock", () => ({
  default: ({
    children,
    language,
  }: {
    children: string;
    language?: string;
  }) => (
    <pre data-testid="code-block" data-language={language}>
      {children}
    </pre>
  ),
}));

vi.mock("../Artifacts/SandpackExecutor", () => ({
  default: ({ code, language }: { code: string; language: string }) => (
    <div data-testid="sandpack-executor" data-language={language}>
      {code}
    </div>
  ),
}));

describe("MarkdownContent", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("basic markdown rendering", () => {
    it("should render plain text", () => {
      render(<MarkdownContent content="Hello, world!" />);
      expect(screen.getByText("Hello, world!")).toBeInTheDocument();
    });

    it("should render paragraphs", () => {
      render(<MarkdownContent content="First paragraph" />);
      expect(screen.getByText("First paragraph")).toBeInTheDocument();
    });

    it("should render headings", () => {
      render(<MarkdownContent content="# Heading 1" />);
      expect(
        screen.getByRole("heading", { level: 1, name: "Heading 1" }),
      ).toBeInTheDocument();
    });

    it("should render unordered lists", () => {
      const { container } = render(<MarkdownContent content="- Item 1" />);
      expect(container.querySelector("ul")).toBeInTheDocument();
    });

    it("should render ordered lists", () => {
      const { container } = render(<MarkdownContent content="1. First" />);
      expect(container.querySelector("ol")).toBeInTheDocument();
    });

    it("should render blockquotes", () => {
      render(<MarkdownContent content="> This is a quote" />);
      const blockquote = screen
        .getByText("This is a quote")
        .closest("blockquote");
      expect(blockquote).toBeInTheDocument();
    });

    it("should render horizontal rules", () => {
      const { container } = render(<MarkdownContent content="---" />);
      expect(container.querySelector("hr")).toBeInTheDocument();
    });
  });

  describe("links", () => {
    it("should render links with target=_blank", () => {
      render(<MarkdownContent content="[Click here](https://example.com)" />);
      const link = screen.getByRole("link", { name: "Click here" });
      expect(link).toHaveAttribute("href", "https://example.com");
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
    });
  });

  describe("inline code", () => {
    it("should render inline code with styling", () => {
      render(<MarkdownContent content="Use `const` for constants" />);
      const code = screen.getByText("const");
      expect(code.tagName).toBe("CODE");
    });
  });

  describe("code blocks", () => {
    it("should render code blocks with syntax highlighting", async () => {
      // Multi-line code triggers CodeBlock rendering
      const code = "```javascript\nconst x = 1;\nconst y = 2;\n```";
      render(<MarkdownContent content={code} />);

      await waitFor(() => {
        const codeBlock = screen.getByTestId("code-block");
        expect(codeBlock).toBeInTheDocument();
        expect(codeBlock).toHaveAttribute("data-language", "javascript");
      });
    });

    it("should render multi-line code blocks", async () => {
      const code = "```python\ndef hello():\n    print('Hello')\n```";
      render(<MarkdownContent content={code} />);

      await waitFor(() => {
        const codeBlock = screen.getByTestId("code-block");
        expect(codeBlock).toHaveAttribute("data-language", "python");
      });
    });
  });

  describe("tables (GFM)", () => {
    it("should render markdown tables", () => {
      const tableMarkdown = `
| Column 1 | Column 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |
`;
      render(<MarkdownContent content={tableMarkdown} />);

      expect(screen.getByText("Column 1")).toBeInTheDocument();
      expect(screen.getByText("Cell 1")).toBeInTheDocument();
    });
  });

  describe("interactive artifacts", () => {
    it("should render mermaid diagrams when enabled", async () => {
      const mermaidCode = "```mermaid\ngraph TD\nA-->B\n```";
      render(
        <MarkdownContent content={mermaidCode} enableInteractiveArtifacts />,
      );

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-diagram")).toBeInTheDocument();
      });
    });

    it("should not render mermaid diagrams when disabled", async () => {
      const mermaidCode = "```mermaid\ngraph TD\nA-->B\n```";
      render(
        <MarkdownContent
          content={mermaidCode}
          enableInteractiveArtifacts={false}
        />,
      );

      await waitFor(() => {
        // Should render as a code block instead
        const codeBlock = screen.getByTestId("code-block");
        expect(codeBlock).toBeInTheDocument();
      });
    });

    it("should render JSX with Sandpack when enabled", async () => {
      // Multi-line JSX to trigger Sandpack rendering
      const jsxCode =
        "```jsx\nconst App = () => {\n  return <div>Hello</div>;\n};\n```";
      render(<MarkdownContent content={jsxCode} enableInteractiveArtifacts />);

      await waitFor(() => {
        const sandpack = screen.getByTestId("sandpack-executor");
        expect(sandpack).toBeInTheDocument();
        expect(sandpack).toHaveAttribute("data-language", "jsx");
      });
    });

    it("should render TSX with Sandpack when enabled", async () => {
      // Multi-line TSX to trigger Sandpack rendering
      const tsxCode =
        "```tsx\nconst App: React.FC = () => {\n  return <div>Hello</div>;\n};\n```";
      render(<MarkdownContent content={tsxCode} enableInteractiveArtifacts />);

      await waitFor(() => {
        const sandpack = screen.getByTestId("sandpack-executor");
        expect(sandpack).toBeInTheDocument();
        expect(sandpack).toHaveAttribute("data-language", "tsx");
      });
    });
  });

  describe("math rendering (KaTeX)", () => {
    it("should render inline math", () => {
      render(<MarkdownContent content="The formula is $E = mc^2$" />);
      // KaTeX renders the math, we just verify no error
      expect(screen.getByText(/The formula is/)).toBeInTheDocument();
    });
  });

  describe("enableInteractiveArtifacts prop", () => {
    it("should default to true", async () => {
      const mermaidCode = "```mermaid\ngraph TD\nA-->B\n```";
      render(<MarkdownContent content={mermaidCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-diagram")).toBeInTheDocument();
      });
    });

    it("should disable all interactive artifacts when false", async () => {
      // Multi-line JSX so it renders as CodeBlock when interactive is disabled
      const jsxCode =
        "```jsx\nconst App = () => {\n  return <div>Hello</div>;\n};\n```";
      render(
        <MarkdownContent
          content={jsxCode}
          enableInteractiveArtifacts={false}
        />,
      );

      await waitFor(() => {
        // Should render as regular code block, not Sandpack
        expect(
          screen.queryByTestId("sandpack-executor"),
        ).not.toBeInTheDocument();
        expect(screen.getByTestId("code-block")).toBeInTheDocument();
      });
    });
  });

  describe("streaming behavior", () => {
    it("should show placeholder for mermaid during streaming with incomplete code", async () => {
      // Incomplete mermaid - no closing ```
      const incompleteMermaid = "```mermaid\ngraph TD\n  A --";
      render(
        <MarkdownContent
          content={incompleteMermaid}
          isStreaming={true}
          enableInteractiveArtifacts
        />,
      );

      await waitFor(() => {
        // Should show streaming placeholder, not the mermaid diagram
        expect(
          screen.getByTestId("streaming-artifact-placeholder"),
        ).toBeInTheDocument();
        expect(screen.queryByTestId("mermaid-diagram")).not.toBeInTheDocument();
      });
    });

    it("should render mermaid diagram when streaming is false", async () => {
      const completeMermaid = "```mermaid\ngraph TD\n  A --> B\n```";
      render(
        <MarkdownContent
          content={completeMermaid}
          isStreaming={false}
          enableInteractiveArtifacts
        />,
      );

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-diagram")).toBeInTheDocument();
        expect(
          screen.queryByTestId("streaming-artifact-placeholder"),
        ).not.toBeInTheDocument();
      });
    });

    it("should show placeholder for mermaid during streaming even if code block looks complete", async () => {
      // Even with closing ```, show placeholder during streaming
      // Mermaid internal syntax (like dates in gantt charts) can be malformed during streaming
      // so we rely entirely on isStreaming flag rather than content heuristics
      const completeMermaid = "```mermaid\ngraph TD\n  A --> B\n```";
      render(
        <MarkdownContent
          content={completeMermaid}
          isStreaming={true}
          enableInteractiveArtifacts
        />,
      );

      await waitFor(() => {
        // Should show placeholder even though code block looks complete
        // because Mermaid syntax errors can't be detected by content heuristics
        expect(
          screen.getByTestId("streaming-artifact-placeholder"),
        ).toBeInTheDocument();
      });
    });

    it("should show placeholder for chart during streaming", async () => {
      // Chart artifacts always show placeholder during streaming
      // to avoid JSON parse errors from incomplete content
      const chartContent = '```chart\n{"type": "bar", "data": [1, 2, 3]}\n```';
      render(
        <MarkdownContent
          content={chartContent}
          isStreaming={true}
          enableInteractiveArtifacts
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByTestId("streaming-artifact-placeholder"),
        ).toBeInTheDocument();
      });
    });

    it("should show placeholder for SVG during streaming", async () => {
      // SVG artifacts always show placeholder during streaming
      // to avoid DOMParser errors from incomplete content
      const svgContent =
        '```svg\n<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/></svg>\n```';
      render(
        <MarkdownContent
          content={svgContent}
          isStreaming={true}
          enableInteractiveArtifacts
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByTestId("streaming-artifact-placeholder"),
        ).toBeInTheDocument();
      });
    });

    it("should transition from placeholder to rendered artifact when streaming completes", async () => {
      const incompleteMermaid = "```mermaid\ngraph TD\n  A --";
      const { rerender } = render(
        <MarkdownContent
          content={incompleteMermaid}
          isStreaming={true}
          enableInteractiveArtifacts
        />,
      );

      // Initially shows placeholder
      await waitFor(() => {
        expect(
          screen.getByTestId("streaming-artifact-placeholder"),
        ).toBeInTheDocument();
      });

      // Rerender with complete content and streaming=false
      const completeMermaid = "```mermaid\ngraph TD\n  A --> B\n```";
      rerender(
        <MarkdownContent
          content={completeMermaid}
          isStreaming={false}
          enableInteractiveArtifacts
        />,
      );

      // Now should show the diagram
      await waitFor(() => {
        expect(screen.getByTestId("mermaid-diagram")).toBeInTheDocument();
        expect(
          screen.queryByTestId("streaming-artifact-placeholder"),
        ).not.toBeInTheDocument();
      });
    });

    it("should not affect non-parse-prone artifacts like audio during streaming", async () => {
      // Audio URLs don't need parsing, should render immediately
      const audioCode = "```audio\nhttps://example.com/audio.mp3\n```";
      render(
        <MarkdownContent
          content={audioCode}
          isStreaming={true}
          enableInteractiveArtifacts
        />,
      );

      // Audio should render without placeholder (it's not parse-prone)
      await waitFor(() => {
        expect(
          screen.queryByTestId("streaming-artifact-placeholder"),
        ).not.toBeInTheDocument();
      });
    });

    it("should handle multiple code blocks where only one is incomplete", async () => {
      // First block is complete (multi-line so it renders as CodeBlock), second is incomplete
      const mixedContent =
        "```javascript\nconst x = 1;\nconst y = 2;\n```\n\nSome text\n\n```mermaid\ngraph TD";
      render(
        <MarkdownContent
          content={mixedContent}
          isStreaming={true}
          enableInteractiveArtifacts
        />,
      );

      await waitFor(() => {
        // First code block should render normally (it's complete with multi-line content)
        expect(screen.getByTestId("code-block")).toBeInTheDocument();
        // Second (mermaid) should show placeholder since it's incomplete
        expect(
          screen.getByTestId("streaming-artifact-placeholder"),
        ).toBeInTheDocument();
      });
    });

    it("should default isStreaming to false", async () => {
      const completeMermaid = "```mermaid\ngraph TD\n  A --> B\n```";
      render(
        <MarkdownContent
          content={completeMermaid}
          enableInteractiveArtifacts
        />,
      );

      await waitFor(() => {
        // Should render diagram since isStreaming defaults to false
        expect(screen.getByTestId("mermaid-diagram")).toBeInTheDocument();
      });
    });
  });
});
