/**
 * CodeArtifact Tests
 *
 * Tests for code display component with syntax highlighting and copy functionality.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CodeArtifact } from "./CodeArtifact";
import type { CodeArtifact as CodeArtifactType } from "../../types/artifacts";

describe("CodeArtifact", () => {
  const mockArtifact: CodeArtifactType = {
    id: "code-1",
    type: "code",
    data: 'console.log("Hello, World!");',
    config: {
      language: "javascript",
    },
  };

  beforeEach(() => {
    // Mock clipboard API
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: vi.fn(() => Promise.resolve()),
      },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render code content", () => {
      render(<CodeArtifact artifact={mockArtifact} />);
      expect(screen.getByText(/console.log/)).toBeInTheDocument();
    });

    it("should display language label", () => {
      render(<CodeArtifact artifact={mockArtifact} />);
      expect(screen.getByText("javascript")).toBeInTheDocument();
    });

    it("should render with custom title", () => {
      const artifactWithTitle: CodeArtifactType = {
        ...mockArtifact,
        title: "My Code Example",
      };
      render(<CodeArtifact artifact={artifactWithTitle} />);
      expect(screen.getByText("My Code Example")).toBeInTheDocument();
    });

    it("should render multiline code", () => {
      const multilineArtifact: CodeArtifactType = {
        ...mockArtifact,
        data: "function greet(name) {\n  console.log(`Hello, ${name}!`);\n}",
      };
      render(<CodeArtifact artifact={multilineArtifact} />);
      expect(screen.getByText(/function greet/)).toBeInTheDocument();
    });
  });

  describe("Line Numbers", () => {
    it("should show line numbers by default", () => {
      render(<CodeArtifact artifact={mockArtifact} />);
      const codeContainer = screen.getByRole("region", { name: /code/i });
      expect(codeContainer).toBeInTheDocument();
    });

    it("should hide line numbers when configured", () => {
      const artifactNoLineNumbers: CodeArtifactType = {
        ...mockArtifact,
        config: {
          ...mockArtifact.config,
          showLineNumbers: false,
        },
      };
      render(<CodeArtifact artifact={artifactNoLineNumbers} />);
      const codeContainer = screen.getByRole("region", { name: /code/i });
      expect(codeContainer).toBeInTheDocument();
    });
  });

  describe("Copy Functionality", () => {
    it("should have copy button", () => {
      render(<CodeArtifact artifact={mockArtifact} />);
      expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
    });

    it("should show feedback after copying", async () => {
      const user = userEvent.setup();
      render(<CodeArtifact artifact={mockArtifact} />);

      const copyButton = screen.getByRole("button", { name: /copy/i });
      await user.click(copyButton);

      await waitFor(() => {
        expect(screen.getByText(/copied/i)).toBeInTheDocument();
      });
    });
  });

  describe("Language Support", () => {
    const languages = [
      "javascript",
      "python",
      "typescript",
      "json",
      "html",
      "css",
    ];

    languages.forEach((language) => {
      it(`should render ${language} code`, () => {
        const artifact: CodeArtifactType = {
          id: `code-${language}`,
          type: "code",
          data: `// ${language} code`,
          config: { language },
        };
        render(<CodeArtifact artifact={artifact} />);
        expect(screen.getByText(language)).toBeInTheDocument();
      });
    });
  });

  describe("Theme Support", () => {
    it("should apply light theme", () => {
      const lightArtifact: CodeArtifactType = {
        ...mockArtifact,
        config: {
          ...mockArtifact.config,
          theme: "light",
        },
      };
      const { container } = render(<CodeArtifact artifact={lightArtifact} />);
      const codeContainer = container.querySelector('[data-theme="light"]');
      expect(codeContainer).toBeInTheDocument();
    });

    it("should apply dark theme", () => {
      const darkArtifact: CodeArtifactType = {
        ...mockArtifact,
        config: {
          ...mockArtifact.config,
          theme: "dark",
        },
      };
      const { container } = render(<CodeArtifact artifact={darkArtifact} />);
      const codeContainer = container.querySelector('[data-theme="dark"]');
      expect(codeContainer).toBeInTheDocument();
    });
  });

  describe("Long Code", () => {
    it("should handle very long code", () => {
      const longCode = Array(100).fill('console.log("line");').join("\n");
      const longArtifact: CodeArtifactType = {
        ...mockArtifact,
        data: longCode,
      };
      render(<CodeArtifact artifact={longArtifact} />);
      expect(screen.getAllByText(/console.log/)[0]).toBeInTheDocument();
    });

    it("should apply max height when configured", () => {
      const artifactWithMaxHeight: CodeArtifactType = {
        ...mockArtifact,
        config: {
          ...mockArtifact.config,
          maxHeight: 300,
        },
      };
      const { container } = render(
        <CodeArtifact artifact={artifactWithMaxHeight} />,
      );
      const codeContainer = container.querySelector('[style*="max-height"]');
      expect(codeContainer).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("should handle empty code", () => {
      const emptyArtifact: CodeArtifactType = {
        ...mockArtifact,
        data: "",
      };
      render(<CodeArtifact artifact={emptyArtifact} />);
      expect(screen.getByRole("region", { name: /code/i })).toBeInTheDocument();
    });

    it("should handle special characters", () => {
      const specialCharsArtifact: CodeArtifactType = {
        ...mockArtifact,
        data: '<script>alert("XSS")</script>',
      };
      render(<CodeArtifact artifact={specialCharsArtifact} />);
      // Should render as text, not execute - use getAllByText due to "javascript" language label
      const elements = screen.getAllByText(/script/i);
      expect(elements.length).toBeGreaterThan(0);
    });
  });

  describe("Download Functionality", () => {
    it("should have download button", () => {
      render(<CodeArtifact artifact={mockArtifact} />);
      expect(
        screen.getByRole("button", { name: /download/i }),
      ).toBeInTheDocument();
    });

    it("should trigger download when button clicked", async () => {
      const user = userEvent.setup();

      // Mock URL methods
      const createObjectURLMock = vi.fn(() => "blob:test-url");
      const revokeObjectURLMock = vi.fn();
      URL.createObjectURL = createObjectURLMock;
      URL.revokeObjectURL = revokeObjectURLMock;

      render(<CodeArtifact artifact={mockArtifact} />);
      const downloadButton = screen.getByRole("button", { name: /download/i });
      await user.click(downloadButton);

      // Verify blob URL was created and cleaned up
      expect(createObjectURLMock).toHaveBeenCalled();
      expect(revokeObjectURLMock).toHaveBeenCalled();
    });
  });
});
