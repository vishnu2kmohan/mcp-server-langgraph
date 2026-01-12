/**
 * CodePanel Component
 *
 * Side panel for displaying generated Python code with copy functionality.
 */

import { X, Copy } from "lucide-react";

import { Button } from "@/components/UI";

export interface CodePanelProps {
  code: string;
  isOpen: boolean;
  onClose: () => void;
  onCopy: () => void;
  isDarkMode: boolean;
}

export function CodePanel({
  code,
  isOpen,
  onClose,
  onCopy,
  isDarkMode,
}: CodePanelProps) {
  if (!isOpen) {
    return null;
  }

  const isEmpty = !code || code.trim() === "";

  return (
    <div
      data-testid="code-panel"
      className={`w-96 border-l flex flex-col ${
        isDarkMode
          ? "bg-neutral-800 border-neutral-700"
          : "bg-white border-neutral-200 dark:border-neutral-700"
      }`}
    >
      <div
        className={`p-4 border-b flex items-center justify-between ${
          isDarkMode
            ? "border-neutral-700"
            : "border-neutral-200 dark:border-neutral-700"
        }`}
      >
        <h2
          className={`text-lg font-semibold ${
            isDarkMode ? "text-white" : "text-neutral-900"
          }`}
        >
          Generated Code
        </h2>
        <div className="flex gap-2">
          <Button
            className="p-2 rounded-lg"
            onClick={onCopy}
            title="Copy to clipboard"
            aria-label="Copy code"
          >
            <Copy size={18} />
          </Button>
          <Button
            className="p-2 rounded-lg"
            onClick={onClose}
            title="Close panel"
            aria-label="Close"
          >
            <X size={18} />
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4">
        {isEmpty ? (
          <div
            className={`text-center py-8 ${
              isDarkMode
                ? "text-neutral-400 dark:text-neutral-400"
                : "text-neutral-500 dark:text-neutral-400"
            }`}
          >
            <p>No code generated yet.</p>
            <p className="text-sm mt-2">
              Add nodes to your workflow and click "Export Code" to generate
              Python code.
            </p>
          </div>
        ) : (
          <pre
            className={`text-sm font-mono whitespace-pre-wrap ${
              isDarkMode ? "text-neutral-300" : "text-neutral-800"
            }`}
          >
            {code}
          </pre>
        )}
      </div>
    </div>
  );
}
