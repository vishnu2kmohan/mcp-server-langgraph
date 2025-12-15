/**
 * LaTeXArtifact Component
 *
 * Renders LaTeX mathematical expressions using KaTeX.
 * Features:
 * - Inline and display mode rendering
 * - Copy to clipboard
 * - Error handling for invalid LaTeX
 * - Accessible markup
 */

import { useState, useCallback, useMemo } from "react";
import { Copy, Check, AlertTriangle } from "lucide-react";
import katex from "katex";

/**
 * LaTeXArtifact props
 */
export interface LaTeXArtifactProps {
  /** LaTeX content to render */
  content: string;
  /** Display mode (block) vs inline mode */
  displayMode?: boolean;
  /** Optional title */
  title?: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * LaTeXArtifact component for rendering mathematical expressions
 */
export function LaTeXArtifact({
  content,
  displayMode = false,
  title,
  className = "",
}: LaTeXArtifactProps) {
  const [copied, setCopied] = useState(false);

  // Render LaTeX with error handling
  const { html, error } = useMemo(() => {
    try {
      const rendered = katex.renderToString(content, {
        displayMode,
        throwOnError: true,
        errorColor: "#ef4444",
        strict: false,
        trust: false,
      });
      return { html: rendered, error: null };
    } catch (err) {
      return {
        html: null,
        error: err instanceof Error ? err.message : "Failed to render LaTeX",
      };
    }
  }, [content, displayMode]);

  // Copy to clipboard
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }, [content]);

  return (
    <div
      className={`rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden ${className}`}
    >
      {/* Header with title and actions */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
        {title ? (
          <span
            data-testid="latex-title"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            {title}
          </span>
        ) : (
          <span className="text-sm text-gray-500 dark:text-gray-400">
            LaTeX
          </span>
        )}

        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
          aria-label={copied ? "Copied" : "Copy LaTeX"}
        >
          {copied ? (
            <>
              <Check size={14} className="text-green-500" />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <Copy size={14} />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* LaTeX content */}
      <div className="p-4">
        {error ? (
          <div className="flex flex-col gap-3">
            {/* Error message */}
            <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
              <AlertTriangle size={16} className="text-red-500" />
              <span className="text-sm text-red-700 dark:text-red-400">
                Error: {error}
              </span>
            </div>

            {/* Show raw LaTeX */}
            <pre className="p-3 bg-gray-50 dark:bg-gray-900 rounded text-sm text-gray-700 dark:text-gray-300 font-mono overflow-x-auto">
              {content}
            </pre>
          </div>
        ) : (
          <div
            data-testid="latex-artifact"
            role="img"
            aria-label={`LaTeX math: ${content}`}
            className={`${displayMode ? "text-center" : ""} overflow-x-auto`}
            dangerouslySetInnerHTML={{ __html: html || "" }}
          />
        )}
      </div>
    </div>
  );
}
