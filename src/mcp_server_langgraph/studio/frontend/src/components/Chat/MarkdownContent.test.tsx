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
});
