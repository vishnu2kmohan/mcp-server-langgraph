/**
 * CodeArtifact Component
 *
 * Displays code with syntax highlighting, line numbers, and copy functionality.
 */

import { useState, useCallback } from "react";
import { Copy, Check } from "lucide-react";
import type { CodeArtifact as CodeArtifactType } from "../../types/artifacts";

export interface CodeArtifactProps {
  artifact: CodeArtifactType;
}

export function CodeArtifact({ artifact }: CodeArtifactProps) {
  const [copied, setCopied] = useState(false);

  const { data, config, title } = artifact;
  const {
    language,
    showLineNumbers = true,
    theme = "light",
    maxHeight,
    wrapLines = false,
  } = config;

  /**
   * Copy code to clipboard
   */
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(data);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error("Failed to copy code:", error);
    }
  }, [data]);

  /**
   * Split code into lines for line number display
   */
  const lines = data.split("\n");

  const containerStyle = maxHeight
    ? { maxHeight: `${maxHeight}px` }
    : undefined;

  const themeClasses =
    theme === "dark"
      ? "bg-gray-900 text-gray-100 border-gray-700"
      : "bg-gray-50 text-gray-900 border-gray-200";

  return (
    <div
      className={`rounded-lg border ${themeClasses} overflow-hidden`}
      data-theme={theme}
      role="region"
      aria-label="Code block"
    >
      {/* Header */}
      <div
        className={`flex items-center justify-between px-4 py-2 border-b ${
          theme === "dark"
            ? "border-gray-700 bg-gray-800"
            : "border-gray-200 bg-gray-100"
        }`}
      >
        <div className="flex items-center gap-3">
          {title && <span className="font-medium">{title}</span>}
          <span
            className={`text-xs font-mono px-2 py-1 rounded ${
              theme === "dark"
                ? "bg-gray-700 text-gray-300"
                : "bg-gray-200 text-gray-700"
            }`}
          >
            {language}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className={`flex items-center gap-2 px-3 py-1 text-sm rounded transition-colors ${
            theme === "dark"
              ? "hover:bg-gray-700 text-gray-300"
              : "hover:bg-gray-200 text-gray-700"
          }`}
          aria-label="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-4 h-4 text-green-500" />
              <span className="text-green-500">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code Content */}
      <div className="overflow-auto" style={containerStyle}>
        <div className="relative">
          {showLineNumbers ? (
            <table className="w-full border-collapse">
              <tbody>
                {lines.map((line, index) => (
                  <tr key={index} className="hover:bg-opacity-50">
                    <td
                      className={`select-none text-right px-4 py-1 font-mono text-xs ${
                        theme === "dark"
                          ? "text-gray-500 border-r border-gray-700"
                          : "text-gray-400 border-r border-gray-300"
                      }`}
                      style={{ width: "1%", whiteSpace: "nowrap" }}
                    >
                      {index + 1}
                    </td>
                    <td
                      className={`px-4 py-1 font-mono text-sm ${
                        wrapLines ? "whitespace-pre-wrap" : "whitespace-pre"
                      }`}
                    >
                      {line || "\n"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <pre
              className={`p-4 font-mono text-sm ${
                wrapLines ? "whitespace-pre-wrap" : "whitespace-pre"
              }`}
            >
              {data}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
