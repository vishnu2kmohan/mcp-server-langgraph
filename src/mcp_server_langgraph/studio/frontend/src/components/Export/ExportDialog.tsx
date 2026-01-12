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

import { Button, Toggle } from "@/components/UI";

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
    <Button
      className="flex px-4 py-2 rounded-lg border-2 focus:ring-primary-500"
      type="button"
      data-testid={`format-${format}`}
      role="radio"
      aria-checked={selected}
      onClick={onClick}
    >
      {icon}
      <span className="font-medium">{label}</span>
    </Button>
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
    <Toggle
      id={id}
      data-testid={testId}
      checked={checked}
      onChange={onChange}
      label={label}
      size="sm"
    />
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
        className={`relative w-full max-w-2xl bg-white dark:bg-neutral-800 rounded-xl shadow-2xl overflow-hidden ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
          <h2
            id="export-dialog-title"
            className="text-lg font-semibold text-neutral-900 dark:text-neutral-100"
          >
            Export Conversation
          </h2>
          <Button
            variant="secondary"
            className="p-1 text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300 dark:hover:text-neutral-200 rounded-lg hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 focus:ring-primary-500"
            type="button"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={20} />
          </Button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-6">
          {/* Format Selection */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
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
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
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
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
              Preview
            </label>
            <pre
              data-testid="export-preview"
              className="p-4 bg-neutral-50 dark:bg-neutral-900 rounded-lg text-sm text-neutral-700 dark:text-neutral-300 overflow-auto max-h-48 font-mono"
            >
              {preview.slice(0, 500)}
              {preview.length > 500 && "..."}
            </pre>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50">
          <Button
            variant="secondary"
            className="px-4 py-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded-lg focus:ring-primary-500"
            type="button"
            onClick={onClose}
          >
            Cancel
          </Button>

          <div className="flex gap-3">
            <Button
              variant="secondary"
              className="px-4 py-2 text-sm text-neutral-700 dark:text-neutral-300 bg-white dark:bg-neutral-700 border border-neutral-300 dark:border-neutral-600 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-600 focus:ring-primary-500"
              type="button"
              onClick={handleCopy}
            >
              {actionState === "copied" ? (
                <>
                  <Check size={16} className="text-success-500" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy size={16} />
                  Copy
                </>
              )}
            </Button>

            <Button
              variant="primary"
              className="px-4 py-2 text-sm text-white bg-primary-600 rounded-lg hover:bg-primary-700 focus:ring-primary-500 focus:ring-offset-2"
              type="button"
              onClick={handleDownload}
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
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ExportDialog;
