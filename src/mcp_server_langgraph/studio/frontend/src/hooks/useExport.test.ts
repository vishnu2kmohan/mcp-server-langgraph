/**
 * useExport Tests
 *
 * TDD tests for the Export hook.
 * Tests cover:
 * - Export to Markdown format
 * - Export to JSON format
 * - Export options (full, selected, code only)
 * - Include/exclude metadata
 * - Copy to clipboard
 * - Download file
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useExport, Message, ExportFormat, ExportOptions } from "./useExport";

describe("useExport", () => {
  const mockMessages: Message[] = [
    {
      id: "1",
      role: "user",
      content: "Hello, how are you?",
      timestamp: "2024-01-01T10:00:00Z",
    },
    {
      id: "2",
      role: "assistant",
      content:
        "I'm doing well! Here's some code:\n```python\nprint('hello')\n```",
      timestamp: "2024-01-01T10:00:10Z",
      tokenCount: 50,
    },
    {
      id: "3",
      role: "user",
      content: "Thanks!",
      timestamp: "2024-01-01T10:00:20Z",
    },
  ];

  let originalClipboard: Clipboard;
  let originalCreateObjectURL: typeof URL.createObjectURL;
  let originalRevokeObjectURL: typeof URL.revokeObjectURL;

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock clipboard
    originalClipboard = navigator.clipboard;
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
      writable: true,
    });

    // Mock URL methods
    originalCreateObjectURL = URL.createObjectURL;
    originalRevokeObjectURL = URL.revokeObjectURL;
    URL.createObjectURL = vi.fn().mockReturnValue("blob:mock-url");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    Object.defineProperty(navigator, "clipboard", {
      value: originalClipboard,
      writable: true,
    });
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
  });

  // ===========================================================================
  // Markdown Export Tests
  // ===========================================================================

  describe("markdown export", () => {
    it("should export messages to markdown format", () => {
      const { result } = renderHook(() => useExport());

      const markdown = result.current.exportToMarkdown(mockMessages);

      expect(markdown).toContain("# Conversation Export");
      expect(markdown).toContain("**User:**");
      expect(markdown).toContain("Hello, how are you?");
      expect(markdown).toContain("**Assistant:**");
      expect(markdown).toContain("print('hello')");
    });

    it("should include timestamps when option is enabled", () => {
      const { result } = renderHook(() => useExport());

      const markdown = result.current.exportToMarkdown(mockMessages, {
        includeTimestamps: true,
      });

      // Timestamps are formatted via toLocaleString, so check for common patterns
      expect(markdown).toMatch(/\d{1,2}\/\d{1,2}\/\d{4}|\d{4}-\d{2}-\d{2}/);
    });

    it("should exclude timestamps by default", () => {
      const { result } = renderHook(() => useExport());

      const markdown = result.current.exportToMarkdown(mockMessages);

      expect(markdown).not.toContain("2024-01-01T10:00:00Z");
    });

    it("should include token counts when option is enabled", () => {
      const { result } = renderHook(() => useExport());

      const markdown = result.current.exportToMarkdown(mockMessages, {
        includeTokenCounts: true,
      });

      expect(markdown).toContain("50 tokens");
    });
  });

  // ===========================================================================
  // JSON Export Tests
  // ===========================================================================

  describe("json export", () => {
    it("should export messages to JSON format", () => {
      const { result } = renderHook(() => useExport());

      const json = result.current.exportToJson(mockMessages);
      const parsed = JSON.parse(json);

      expect(parsed.messages).toHaveLength(3);
      expect(parsed.messages[0].content).toBe("Hello, how are you?");
    });

    it("should include metadata in JSON export", () => {
      const { result } = renderHook(() => useExport());

      const json = result.current.exportToJson(mockMessages, {
        includeMetadata: true,
      });
      const parsed = JSON.parse(json);

      expect(parsed.exportedAt).toBeDefined();
      expect(parsed.messageCount).toBe(3);
    });

    it("should export only code blocks when option is set", () => {
      const { result } = renderHook(() => useExport());

      const json = result.current.exportToJson(mockMessages, {
        codeOnly: true,
      });
      const parsed = JSON.parse(json);

      expect(parsed.codeBlocks).toBeDefined();
      expect(parsed.codeBlocks).toContain("print('hello')");
    });
  });

  // ===========================================================================
  // Selected Messages Tests
  // ===========================================================================

  describe("selected messages", () => {
    it("should export only selected messages", () => {
      const { result } = renderHook(() => useExport());

      const markdown = result.current.exportToMarkdown(mockMessages, {
        selectedIds: ["1", "3"],
      });

      expect(markdown).toContain("Hello, how are you?");
      expect(markdown).toContain("Thanks!");
      expect(markdown).not.toContain("I'm doing well");
    });
  });

  // ===========================================================================
  // Code Only Export Tests
  // ===========================================================================

  describe("code only export", () => {
    it("should extract only code blocks", () => {
      const { result } = renderHook(() => useExport());

      const code = result.current.extractCodeBlocks(mockMessages);

      expect(code).toContain("print('hello')");
      expect(code).not.toContain("Hello, how are you?");
    });
  });

  // ===========================================================================
  // Copy to Clipboard Tests
  // ===========================================================================

  describe("copy to clipboard", () => {
    it("should copy markdown to clipboard", async () => {
      const { result } = renderHook(() => useExport());

      await act(async () => {
        await result.current.copyToClipboard(mockMessages, "markdown");
      });

      expect(navigator.clipboard.writeText).toHaveBeenCalled();
      expect(result.current.lastAction).toBe("copied");
    });

    it("should copy JSON to clipboard", async () => {
      const { result } = renderHook(() => useExport());

      await act(async () => {
        await result.current.copyToClipboard(mockMessages, "json");
      });

      expect(navigator.clipboard.writeText).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Download File Tests
  // ===========================================================================

  describe("download file", () => {
    it("should trigger download for markdown", () => {
      const { result } = renderHook(() => useExport());
      const appendChildSpy = vi.spyOn(document.body, "appendChild");
      const removeChildSpy = vi.spyOn(document.body, "removeChild");

      act(() => {
        result.current.downloadFile(mockMessages, "markdown");
      });

      expect(URL.createObjectURL).toHaveBeenCalled();
      expect(appendChildSpy).toHaveBeenCalled();
      expect(result.current.lastAction).toBe("downloaded");

      appendChildSpy.mockRestore();
      removeChildSpy.mockRestore();
    });

    it("should generate correct filename", () => {
      const { result } = renderHook(() => useExport());

      const filename = result.current.generateFilename("markdown");

      expect(filename).toMatch(/^conversation-\d{4}-\d{2}-\d{2}\.md$/);
    });

    it("should generate JSON filename", () => {
      const { result } = renderHook(() => useExport());

      const filename = result.current.generateFilename("json");

      expect(filename).toMatch(/^conversation-\d{4}-\d{2}-\d{2}\.json$/);
    });
  });

  // ===========================================================================
  // Export State Tests
  // ===========================================================================

  describe("export state", () => {
    it("should track export in progress", async () => {
      const { result } = renderHook(() => useExport());

      expect(result.current.isExporting).toBe(false);
    });

    it("should track last action", async () => {
      const { result } = renderHook(() => useExport());

      await act(async () => {
        await result.current.copyToClipboard(mockMessages, "markdown");
      });

      expect(result.current.lastAction).toBe("copied");
    });
  });
});
