/**
 * useExport Hook
 *
 * Hook to export conversation messages.
 * Features:
 * - Export to Markdown format
 * - Export to JSON format
 * - Filter by selected messages
 * - Extract code blocks only
 * - Include/exclude metadata
 * - Copy to clipboard
 * - Download as file
 *
 * Standard feature in all chat tools.
 */

import { useState, useCallback } from "react";

// ==============================================================================
// Types
// ==============================================================================

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
  tokenCount?: number;
}

export type ExportFormat = "markdown" | "json";

export interface ExportOptions {
  includeTimestamps?: boolean;
  includeTokenCounts?: boolean;
  includeMetadata?: boolean;
  selectedIds?: string[];
  codeOnly?: boolean;
}

export interface ExportState {
  isExporting: boolean;
  lastAction: "copied" | "downloaded" | null;
  exportToMarkdown: (messages: Message[], options?: ExportOptions) => string;
  exportToJson: (messages: Message[], options?: ExportOptions) => string;
  extractCodeBlocks: (messages: Message[]) => string;
  copyToClipboard: (
    messages: Message[],
    format: ExportFormat,
    options?: ExportOptions,
  ) => Promise<void>;
  downloadFile: (
    messages: Message[],
    format: ExportFormat,
    options?: ExportOptions,
  ) => void;
  generateFilename: (format: ExportFormat) => string;
}

// ==============================================================================
// Helper Functions
// ==============================================================================

function filterMessages(
  messages: Message[],
  selectedIds?: string[],
): Message[] {
  if (!selectedIds || selectedIds.length === 0) {
    return messages;
  }
  return messages.filter((m) => selectedIds.includes(m.id));
}

function extractCodeBlocksFromContent(content: string): string[] {
  const codeBlockRegex = /```[\w]*\n([\s\S]*?)```/g;
  const blocks: string[] = [];
  let match;
  while ((match = codeBlockRegex.exec(content)) !== null) {
    blocks.push(match[1].trim());
  }
  return blocks;
}

function formatRole(role: string): string {
  return role.charAt(0).toUpperCase() + role.slice(1);
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString();
}

// ==============================================================================
// Hook
// ==============================================================================

export function useExport(): ExportState {
  const [isExporting, setIsExporting] = useState(false);
  const [lastAction, setLastAction] = useState<"copied" | "downloaded" | null>(
    null,
  );

  // Export to Markdown
  const exportToMarkdown = useCallback(
    (messages: Message[], options: ExportOptions = {}): string => {
      const filtered = filterMessages(messages, options.selectedIds);
      const lines: string[] = ["# Conversation Export", ""];

      filtered.forEach((msg) => {
        lines.push(`**${formatRole(msg.role)}:**`);

        if (options.includeTimestamps && msg.timestamp) {
          lines.push(`*${formatTimestamp(msg.timestamp)}*`);
        }

        lines.push("");
        lines.push(msg.content);
        lines.push("");

        if (options.includeTokenCounts && msg.tokenCount) {
          lines.push(`*${msg.tokenCount} tokens*`);
          lines.push("");
        }

        lines.push("---");
        lines.push("");
      });

      return lines.join("\n");
    },
    [],
  );

  // Export to JSON
  const exportToJson = useCallback(
    (messages: Message[], options: ExportOptions = {}): string => {
      const filtered = filterMessages(messages, options.selectedIds);

      if (options.codeOnly) {
        const allCodeBlocks: string[] = [];
        filtered.forEach((msg) => {
          const blocks = extractCodeBlocksFromContent(msg.content);
          allCodeBlocks.push(...blocks);
        });

        return JSON.stringify(
          {
            codeBlocks: allCodeBlocks,
            exportedAt: new Date().toISOString(),
          },
          null,
          2,
        );
      }

      const exportData: Record<string, unknown> = {
        messages: filtered.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          ...(options.includeTimestamps &&
            m.timestamp && { timestamp: m.timestamp }),
          ...(options.includeTokenCounts &&
            m.tokenCount && { tokenCount: m.tokenCount }),
        })),
      };

      if (options.includeMetadata) {
        exportData.exportedAt = new Date().toISOString();
        exportData.messageCount = filtered.length;
      }

      return JSON.stringify(exportData, null, 2);
    },
    [],
  );

  // Extract code blocks only
  const extractCodeBlocks = useCallback((messages: Message[]): string => {
    const allCodeBlocks: string[] = [];
    messages.forEach((msg) => {
      const blocks = extractCodeBlocksFromContent(msg.content);
      allCodeBlocks.push(...blocks);
    });
    return allCodeBlocks.join("\n\n");
  }, []);

  // Generate filename
  const generateFilename = useCallback((format: ExportFormat): string => {
    const date = new Date().toISOString().split("T")[0];
    const extension = format === "markdown" ? "md" : format;
    return `conversation-${date}.${extension}`;
  }, []);

  // Copy to clipboard
  const copyToClipboard = useCallback(
    async (
      messages: Message[],
      format: ExportFormat,
      options: ExportOptions = {},
    ): Promise<void> => {
      setIsExporting(true);

      try {
        let content: string;
        if (format === "markdown") {
          content = exportToMarkdown(messages, options);
        } else {
          content = exportToJson(messages, options);
        }

        await navigator.clipboard.writeText(content);
        setLastAction("copied");
      } finally {
        setIsExporting(false);
      }
    },
    [exportToMarkdown, exportToJson],
  );

  // Download file
  const downloadFile = useCallback(
    (
      messages: Message[],
      format: ExportFormat,
      options: ExportOptions = {},
    ): void => {
      setIsExporting(true);

      try {
        let content: string;
        let mimeType: string;

        if (format === "markdown") {
          content = exportToMarkdown(messages, options);
          mimeType = "text/markdown";
        } else {
          content = exportToJson(messages, options);
          mimeType = "application/json";
        }

        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");
        link.href = url;
        link.download = generateFilename(format);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        URL.revokeObjectURL(url);
        setLastAction("downloaded");
      } finally {
        setIsExporting(false);
      }
    },
    [exportToMarkdown, exportToJson, generateFilename],
  );

  return {
    isExporting,
    lastAction,
    exportToMarkdown,
    exportToJson,
    extractCodeBlocks,
    copyToClipboard,
    downloadFile,
    generateFilename,
  };
}

export default useExport;
