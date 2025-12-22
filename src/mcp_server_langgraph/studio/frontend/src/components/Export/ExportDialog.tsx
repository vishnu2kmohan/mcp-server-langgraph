/**
 * ExportDialog Component
 *
 * Dialog for exporting conversation messages.
 * Features:
 * - Format selection (Markdown, JSON)
 * - Export options (timestamps, token counts)
 * - Live preview
 * - Copy to clipboard
 * - Download file
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 */

import { useState, useMemo, useEffect, useRef } from "react";
import { X, Download, Copy, FileText, FileJson, Check } from "lucide-react";
import { useExport, Message, ExportFormat } from "../../hooks/useExport";

// ==============================================================================
// Types
// ==============================================================================

export interface ExportDialogProps {
  /** Whether dialog is open */
  isOpen: boolean;
  /** Close handler */
  onClose: () => void;
  /** Messages to export */
  messages: Message[];
  /** Additional CSS classes */
  className?: string;
}

// ==============================================================================
// Format Button Component
// ==============================================================================

interface FormatButtonProps {
  format: ExportFormat;
  selected: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}

function FormatButton({
  format,
  selected,
  onClick,
  icon,
  label,
}: FormatButtonProps) {
  return (
    <button
      type="button"
      data-testid={`format-${format}`}
      role="radio"
      aria-checked={selected}
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg border-2 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 ${
        selected
          ? "border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
          : "border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500"
      }`}
    >
      {icon}
      <span className="font-medium">{label}</span>
    </button>
  );
}

// ==============================================================================
// Option Toggle Component
// ==============================================================================

interface OptionToggleProps {
  id: string;
  testId: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
}

function OptionToggle({
  id,
  testId,
  checked,
  onChange,
  label,
}: OptionToggleProps) {
  return (
    <label className="flex items-center gap-3 cursor-pointer">
      <button
        type="button"
        id={id}
        data-testid={testId}
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 ${
          checked ? "bg-blue-600" : "bg-gray-200 dark:bg-gray-600"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
            checked ? "translate-x-4" : "translate-x-0"
          }`}
        />
      </button>
      <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>
    </label>
  );
}

// ==============================================================================
// Main Component
// ==============================================================================

export function ExportDialog({
  isOpen,
  onClose,
  messages,
  className = "",
}: ExportDialogProps) {
  const [format, setFormat] = useState<ExportFormat>("markdown");
  const [includeTimestamps, setIncludeTimestamps] = useState(false);
  const [includeTokenCounts, setIncludeTokenCounts] = useState(false);
  const [actionState, setActionState] = useState<
    "copied" | "downloaded" | null
  >(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  const { exportToMarkdown, exportToJson, copyToClipboard, downloadFile } =
    useExport();

  // Generate preview
  const preview = useMemo(() => {
    const options = { includeTimestamps, includeTokenCounts };
    if (format === "markdown") {
      return exportToMarkdown(messages, options);
    } else {
      return exportToJson(messages, { ...options, includeMetadata: true });
    }
  }, [
    format,
    messages,
    includeTimestamps,
    includeTokenCounts,
    exportToMarkdown,
    exportToJson,
  ]);

  // Handle keyboard events
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      // Focus the dialog
      dialogRef.current?.focus();
    }

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  // Reset action state after showing feedback
  useEffect(() => {
    if (actionState) {
      const timer = setTimeout(() => setActionState(null), 2000);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [actionState]);

  // Handle copy
  const handleCopy = async () => {
    await copyToClipboard(messages, format, {
      includeTimestamps,
      includeTokenCounts,
    });
    setActionState("copied");
  };

  // Handle download
  const handleDownload = () => {
    downloadFile(messages, format, { includeTimestamps, includeTokenCounts });
    setActionState("downloaded");
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" />

      {/* Dialog */}
      <div
        ref={dialogRef}
        data-testid="export-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-dialog-title"
        tabIndex={-1}
        className={`relative w-full max-w-2xl bg-white dark:bg-gray-800 rounded-xl shadow-2xl overflow-hidden ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2
            id="export-dialog-title"
            className="text-lg font-semibold text-gray-900 dark:text-gray-100"
          >
            Export Conversation
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-6">
          {/* Format Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Format
            </label>
            <div
              className="flex gap-3"
              role="radiogroup"
              aria-label="Export format"
            >
              <FormatButton
                format="markdown"
                selected={format === "markdown"}
                onClick={() => setFormat("markdown")}
                icon={<FileText size={18} />}
                label="Markdown"
              />
              <FormatButton
                format="json"
                selected={format === "json"}
                onClick={() => setFormat("json")}
                icon={<FileJson size={18} />}
                label="JSON"
              />
            </div>
          </div>

          {/* Options */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Options
            </label>
            <div className="space-y-3">
              <OptionToggle
                id="option-timestamps"
                testId="option-timestamps"
                checked={includeTimestamps}
                onChange={setIncludeTimestamps}
                label="Include timestamps"
              />
              <OptionToggle
                id="option-tokens"
                testId="option-tokens"
                checked={includeTokenCounts}
                onChange={setIncludeTokenCounts}
                label="Include token counts"
              />
            </div>
          </div>

          {/* Preview */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Preview
            </label>
            <pre
              data-testid="export-preview"
              className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg text-sm text-gray-700 dark:text-gray-300 overflow-auto max-h-48 font-mono"
            >
              {preview.slice(0, 500)}
              {preview.length > 500 && "..."}
            </pre>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Cancel
          </button>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {actionState === "copied" ? (
                <>
                  <Check size={16} className="text-green-500" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy size={16} />
                  Copy
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleDownload}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              {actionState === "downloaded" ? (
                <>
                  <Check size={16} />
                  Downloaded!
                </>
              ) : (
                <>
                  <Download size={16} />
                  Download
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ExportDialog;
