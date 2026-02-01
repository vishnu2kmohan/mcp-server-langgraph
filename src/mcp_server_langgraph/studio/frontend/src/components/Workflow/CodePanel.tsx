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
          ? "bg-neutral-3 border-neutral-7"
          : "bg-neutral-1 border-neutral-5"
      }`}
    >
      <div
        className={`p-4 border-b flex items-center justify-between ${
          isDarkMode ? "border-neutral-7" : "border-neutral-5"
        }`}
      >
        <h2
          className={`text-lg font-semibold ${
            isDarkMode ? "text-neutral-12" : "text-neutral-12"
          }`}
        >
          Generated Code
        </h2>
        <div className="flex gap-2">
          <Button
            size="icon"
            variant="ghost"
            className="p-2 rounded-lg"
            onClick={onCopy}
            title="Copy to clipboard"
            aria-label="Copy code"
          >
            <Copy size={18} />
          </Button>
          <Button
            size="icon"
            variant="ghost"
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
              isDarkMode ? "text-neutral-9" : "text-neutral-10"
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
              isDarkMode ? "text-neutral-9" : "text-neutral-12"
            }`}
          >
            {code}
          </pre>
        )}
      </div>
    </div>
  );
}
