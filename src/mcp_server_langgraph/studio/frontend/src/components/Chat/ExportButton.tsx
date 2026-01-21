/**
 * ExportButton Component
 *
 * Button to export a chat session in various formats (Markdown, JSON, HTML).
 * Uses the session export API endpoint via RTK Query.
 *
 * Features:
 * - Dropdown menu for format selection
 * - Include metadata toggle
 * - Automatic file download
 * - Loading state while exporting
 */

import { useState, useCallback } from "react";
import {
  Download,
  ChevronDown,
  FileText,
  FileJson,
  FileCode,
} from "lucide-react";
import { toast } from "sonner";
import { useExportSessionMutation } from "../../api";
import { TOAST_ID_EXPORT } from "../../constants/toastIds";
import type { ExportFormat } from "../../types/api";

import { Button, Checkbox } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface ExportButtonProps {
  /** Session ID to export */
  sessionId: string;
  /** Session title for filename */
  sessionTitle?: string;
  /** Whether to show a compact version */
  compact?: boolean;
  /** Custom class name */
  className?: string;
}

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Trigger file download from Blob
 */
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// =============================================================================
// Component
// =============================================================================

export function ExportButton({
  sessionId,
  sessionTitle,
  compact = false,
  className,
}: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [includeMetadata, setIncludeMetadata] = useState(false);
  const [exportSession, { isLoading }] = useExportSessionMutation();

  const handleExport = useCallback(
    async (format: ExportFormat) => {
      try {
        const result = await exportSession({
          sessionId,
          request: {
            format,
            include_metadata: includeMetadata,
          },
        }).unwrap();

        // Generate filename
        const safeTitle = sessionTitle
          ? sessionTitle
              .replace(/[^a-zA-Z0-9-_ ]/g, "")
              .trim()
              .slice(0, 50) || "session"
          : "session";
        const timestamp = new Date()
          .toISOString()
          .slice(0, 10)
          .replace(/-/g, "");
        const extension = format === "markdown" ? "md" : format;
        const filename = `${safeTitle}_${timestamp}.${extension}`;

        // Download the file
        downloadBlob(result, filename);

        toast.success(`Session exported as ${format.toUpperCase()}`, { id: TOAST_ID_EXPORT });
        setIsOpen(false);
      } catch {
        toast.error("Failed to export session", { id: TOAST_ID_EXPORT });
      }
    },
    [exportSession, sessionId, sessionTitle, includeMetadata],
  );

  const formatOptions: {
    format: ExportFormat;
    icon: typeof FileText;
    label: string;
  }[] = [
    { format: "markdown", icon: FileText, label: "Markdown (.md)" },
    { format: "json", icon: FileJson, label: "JSON (.json)" },
    { format: "html", icon: FileCode, label: "HTML (.html)" },
  ];

  return (
    <div className="relative">
      <Button
        variant="primary"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 text-sm",
          "text-neutral-11",
          "hover:bg-neutral-2 rounded",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          className,
        )}
        aria-label="Export session"
        aria-expanded={isOpen}
        aria-haspopup="true">
        <Download size={16} className={isLoading ? "animate-pulse" : ""} />
        {!compact && <span>Export</span>}
        <ChevronDown
          size={14}
          className={cn("transition-transform", isOpen && "rotate-180")}
        />
      </Button>
      {/* Dropdown Menu */}
      {isOpen && (
        <>
          {/* Backdrop to close dropdown */}
          <div
            className="fixed inset-0 z-dropdown"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />

          {/* Menu */}
          <div
            className={cn(
              "absolute right-0 top-full mt-1 z-dropdown",
              "w-56 rounded-md shadow-lg",
              "bg-neutral-1",
              "border border-neutral-5",
              "py-1",
            )}
            role="menu"
            aria-orientation="vertical"
          >
            {/* Format Options */}
            {formatOptions.map(({ format, icon: Icon, label }) => (
              <Button
                variant="primary"
                key={format}
                onClick={() => handleExport(format)}
                disabled={isLoading}
                className={cn(
                  "w-full flex items-center gap-3 px-4 py-2 text-sm text-left",
                  "text-neutral-11",
                  "hover:bg-neutral-2",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                )}
                role="menuitem">
                <Icon size={16} />
                <span>{label}</span>
              </Button>
            ))}

            {/* Divider */}
            <div className="my-1 border-t border-neutral-5" />

            {/* Include Metadata Toggle */}
            <div
              className={cn(
                "px-4 py-2",
                "hover:bg-neutral-2",
              )}
            >
              <Checkbox
                checked={includeMetadata}
                onChange={setIncludeMetadata}
                label="Include metadata"
                size="sm"
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default ExportButton;
