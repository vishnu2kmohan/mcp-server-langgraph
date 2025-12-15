/**
 * CodePanel Component
 *
 * Side panel for displaying generated Python code with copy functionality.
 */

import { X, Copy } from "lucide-react";

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
        isDarkMode ? "bg-gray-800 border-gray-700" : "bg-white border-gray-200"
      }`}
    >
      <div
        className={`p-4 border-b flex items-center justify-between ${
          isDarkMode ? "border-gray-700" : "border-gray-200"
        }`}
      >
        <h2
          className={`text-lg font-semibold ${
            isDarkMode ? "text-white" : "text-gray-900"
          }`}
        >
          Generated Code
        </h2>
        <div className="flex gap-2">
          <button
            onClick={onCopy}
            className={`p-2 rounded-lg transition-colors ${
              isDarkMode
                ? "hover:bg-gray-700 text-gray-300"
                : "hover:bg-gray-100 text-gray-600"
            }`}
            title="Copy to clipboard"
            aria-label="Copy code"
          >
            <Copy size={18} />
          </button>
          <button
            onClick={onClose}
            className={`p-2 rounded-lg transition-colors ${
              isDarkMode
                ? "hover:bg-gray-700 text-gray-300"
                : "hover:bg-gray-100 text-gray-600"
            }`}
            title="Close panel"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {isEmpty ? (
          <div
            className={`text-center py-8 ${
              isDarkMode ? "text-gray-400" : "text-gray-500"
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
              isDarkMode ? "text-gray-300" : "text-gray-800"
            }`}
          >
            {code}
          </pre>
        )}
      </div>
    </div>
  );
}
