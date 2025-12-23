/**
 * CodeBlock Component Tests
 *
 * TDD tests for the enhanced code block with syntax highlighting.
 * Features:
 * - Syntax highlighting via Prism
 * - Copy to clipboard
 * - Word wrap toggle
 * - Download as file
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import { CodeBlock } from "./CodeBlock";

// Mock clipboard API
const mockWriteText = vi.fn();
Object.assign(navigator, {
  clipboard: {
    writeText: mockWriteText,
  },
});

// Mock URL API
const mockCreateObjectURL = vi.fn(() => "blob:test-url");
const mockRevokeObjectURL = vi.fn();
URL.createObjectURL = mockCreateObjectURL;
URL.revokeObjectURL = mockRevokeObjectURL;

describe("CodeBlock", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockWriteText.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Basic Rendering", () => {
    it("should render code content", () => {
      render(<CodeBlock>const x = 1;</CodeBlock>);

      expect(screen.getByText("const x = 1;")).toBeInTheDocument();
    });

    it("should render with language label when provided", () => {
      render(<CodeBlock language="javascript">const x = 1;</CodeBlock>);

      expect(screen.getByText("javascript")).toBeInTheDocument();
    });

    it("should not render language label when not provided", () => {
      render(<CodeBlock>const x = 1;</CodeBlock>);

      // No language label should be present
      expect(screen.queryByText("javascript")).not.toBeInTheDocument();
    });

    it("should render with proper accessibility attributes", () => {
      render(<CodeBlock language="python">print("hello")</CodeBlock>);

      expect(screen.getByRole("toolbar")).toHaveAttribute(
        "aria-label",
        "Code block actions",
      );
    });
  });

  describe("Copy to Clipboard", () => {
    it("should copy code when copy button is clicked", async () => {
      const code = 'console.log("test");';
      render(<CodeBlock language="javascript">{code}</CodeBlock>);

      const copyButton = screen.getByRole("button", {
        name: "Copy code to clipboard",
      });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(mockWriteText).toHaveBeenCalledWith(code);
      });
    });

    it("should have copy button initially showing copy state", () => {
      render(<CodeBlock language="javascript">const x = 1;</CodeBlock>);

      const copyButton = screen.getByRole("button", {
        name: "Copy code to clipboard",
      });

      expect(copyButton).toBeInTheDocument();
    });

    it("should handle copy button click and call clipboard API", async () => {
      const code = "test code";
      render(<CodeBlock language="javascript">{code}</CodeBlock>);

      const copyButton = screen.getByRole("button", {
        name: "Copy code to clipboard",
      });

      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(mockWriteText).toHaveBeenCalledWith(code);
      });
    });
  });

  describe("Word Wrap Toggle", () => {
    it("should render word wrap button", () => {
      render(<CodeBlock language="javascript">const x = 1;</CodeBlock>);

      expect(
        screen.getByRole("button", { name: "Enable word wrap" }),
      ).toBeInTheDocument();
    });

    it("should toggle word wrap when button is clicked", () => {
      render(<CodeBlock language="javascript">const x = 1;</CodeBlock>);

      const wrapButton = screen.getByRole("button", {
        name: "Enable word wrap",
      });
      expect(wrapButton).toHaveAttribute("aria-pressed", "false");

      fireEvent.click(wrapButton);

      expect(
        screen.getByRole("button", { name: "Disable word wrap" }),
      ).toHaveAttribute("aria-pressed", "true");
    });

    it("should toggle word wrap off when clicked again", () => {
      render(<CodeBlock language="javascript">const x = 1;</CodeBlock>);

      const wrapButton = screen.getByRole("button", {
        name: "Enable word wrap",
      });

      // Click to enable
      fireEvent.click(wrapButton);
      expect(
        screen.getByRole("button", { name: "Disable word wrap" }),
      ).toHaveAttribute("aria-pressed", "true");

      // Click to disable
      fireEvent.click(
        screen.getByRole("button", { name: "Disable word wrap" }),
      );
      expect(
        screen.getByRole("button", { name: "Enable word wrap" }),
      ).toHaveAttribute("aria-pressed", "false");
    });
  });

  describe("Download", () => {
    let originalCreateElement: typeof document.createElement;

    beforeEach(() => {
      originalCreateElement = document.createElement.bind(document);
    });

    afterEach(() => {
      document.createElement = originalCreateElement;
    });

    it("should render download button", () => {
      render(<CodeBlock language="javascript">const x = 1;</CodeBlock>);

      expect(
        screen.getByRole("button", { name: "Download code as file" }),
      ).toBeInTheDocument();
    });

    it("should trigger download with correct extension for javascript", () => {
      const mockClick = vi.fn();
      let capturedDownload = "";

      document.createElement = vi.fn((tagName: string) => {
        if (tagName === "a") {
          const link = originalCreateElement("a");
          Object.defineProperty(link, "click", { value: mockClick });
          const _originalDescriptor = Object.getOwnPropertyDescriptor(
            HTMLAnchorElement.prototype,
            "download",
          );
          Object.defineProperty(link, "download", {
            get: () => capturedDownload,
            set: (value: string) => {
              capturedDownload = value;
            },
          });
          return link;
        }
        return originalCreateElement(tagName);
      });

      render(<CodeBlock language="javascript">const x = 1;</CodeBlock>);

      const downloadButton = screen.getByRole("button", {
        name: "Download code as file",
      });
      fireEvent.click(downloadButton);

      expect(capturedDownload).toBe("code.js");
      expect(mockClick).toHaveBeenCalled();
    });

    it("should trigger download with correct extension for python", () => {
      const mockClick = vi.fn();
      let capturedDownload = "";

      document.createElement = vi.fn((tagName: string) => {
        if (tagName === "a") {
          const link = originalCreateElement("a");
          Object.defineProperty(link, "click", { value: mockClick });
          Object.defineProperty(link, "download", {
            get: () => capturedDownload,
            set: (value: string) => {
              capturedDownload = value;
            },
          });
          return link;
        }
        return originalCreateElement(tagName);
      });

      render(<CodeBlock language="python">print("hello")</CodeBlock>);

      const downloadButton = screen.getByRole("button", {
        name: "Download code as file",
      });
      fireEvent.click(downloadButton);

      expect(capturedDownload).toBe("code.py");
    });

    it("should trigger download with language as extension for unknown language", () => {
      const mockClick = vi.fn();
      let capturedDownload = "";

      document.createElement = vi.fn((tagName: string) => {
        if (tagName === "a") {
          const link = originalCreateElement("a");
          Object.defineProperty(link, "click", { value: mockClick });
          Object.defineProperty(link, "download", {
            get: () => capturedDownload,
            set: (value: string) => {
              capturedDownload = value;
            },
          });
          return link;
        }
        return originalCreateElement(tagName);
      });

      render(<CodeBlock language="unknownlang">some code</CodeBlock>);

      const downloadButton = screen.getByRole("button", {
        name: "Download code as file",
      });
      fireEvent.click(downloadButton);

      expect(capturedDownload).toBe("code.unknownlang");
    });

    it("should trigger download with .txt extension when no language", () => {
      const mockClick = vi.fn();
      let capturedDownload = "";

      document.createElement = vi.fn((tagName: string) => {
        if (tagName === "a") {
          const link = originalCreateElement("a");
          Object.defineProperty(link, "click", { value: mockClick });
          Object.defineProperty(link, "download", {
            get: () => capturedDownload,
            set: (value: string) => {
              capturedDownload = value;
            },
          });
          return link;
        }
        return originalCreateElement(tagName);
      });

      render(<CodeBlock>some plain text</CodeBlock>);

      const downloadButton = screen.getByRole("button", {
        name: "Download code as file",
      });
      fireEvent.click(downloadButton);

      expect(capturedDownload).toBe("code.txt");
    });
  });

  describe("Accessibility", () => {
    it("should have accessible button labels", () => {
      render(<CodeBlock language="javascript">const x = 1;</CodeBlock>);

      expect(
        screen.getByRole("button", { name: "Enable word wrap" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Download code as file" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Copy code to clipboard" }),
      ).toBeInTheDocument();
    });

    it("should have toolbar with correct aria-label", () => {
      render(<CodeBlock language="javascript">const x = 1;</CodeBlock>);

      expect(screen.getByRole("toolbar")).toHaveAttribute(
        "aria-label",
        "Code block actions",
      );
    });
  });
});
