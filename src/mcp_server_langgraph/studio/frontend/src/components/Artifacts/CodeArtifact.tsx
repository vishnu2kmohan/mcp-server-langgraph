/**
 * CodeArtifact Component
 *
 * Displays code with syntax highlighting, line numbers, and copy functionality.
 * Uses react-syntax-highlighter with Prism for rich code coloring.
 */

import { useState, useCallback, useMemo } from "react";
import { Copy, Check, Download } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import {
  oneDark,
  oneLight,
} from "react-syntax-highlighter/dist/esm/styles/prism";
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
   * Get file extension from language
   */
  const getFileExtension = useCallback((lang: string): string => {
    const extensionMap: Record<string, string> = {
      javascript: "js",
      typescript: "ts",
      python: "py",
      java: "java",
      cpp: "cpp",
      c: "c",
      csharp: "cs",
      go: "go",
      rust: "rs",
      ruby: "rb",
      php: "php",
      swift: "swift",
      kotlin: "kt",
      scala: "scala",
      html: "html",
      css: "css",
      scss: "scss",
      less: "less",
      json: "json",
      yaml: "yaml",
      xml: "xml",
      markdown: "md",
      sql: "sql",
      shell: "sh",
      bash: "sh",
      powershell: "ps1",
    };
    return extensionMap[lang.toLowerCase()] || "txt";
  }, []);

  /**
   * Download code as file
   */
  const handleDownload = useCallback(() => {
    const extension = getFileExtension(language);
    const filename = title || `code.${extension}`;
    const finalFilename = filename.includes(".")
      ? filename
      : `${filename}.${extension}`;

    const blob = new Blob([data], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = finalFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [data, title, language, getFileExtension]);

  /**
   * Map language names to Prism-supported language identifiers
   */
  const getPrismLanguage = useCallback((lang: string): string => {
    const languageMap: Record<string, string> = {
      js: "javascript",
      ts: "typescript",
      py: "python",
      rb: "ruby",
      sh: "bash",
      yml: "yaml",
      md: "markdown",
      cs: "csharp",
      kt: "kotlin",
      rs: "rust",
    };
    return languageMap[lang.toLowerCase()] || lang.toLowerCase();
  }, []);

  /**
   * Get the syntax theme based on the theme prop
   */
  const syntaxTheme = useMemo(
    () => (theme === "dark" ? oneDark : oneLight),
    [theme],
  );

  /**
   * Prism language for syntax highlighting
   */
  const prismLanguage = useMemo(
    () => getPrismLanguage(language),
    [language, getPrismLanguage],
  );

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
        <div className="flex items-center gap-1">
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
          <button
            onClick={handleDownload}
            className={`p-1.5 rounded transition-colors ${
              theme === "dark"
                ? "hover:bg-gray-700 text-gray-300"
                : "hover:bg-gray-200 text-gray-700"
            }`}
            aria-label="Download code"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Code Content with Syntax Highlighting */}
      <div className="overflow-auto" style={containerStyle}>
        <SyntaxHighlighter
          language={prismLanguage}
          style={syntaxTheme}
          showLineNumbers={showLineNumbers}
          wrapLines={wrapLines}
          wrapLongLines={wrapLines}
          customStyle={{
            margin: 0,
            borderRadius: 0,
            fontSize: "0.875rem",
            background: "transparent",
          }}
          lineNumberStyle={{
            minWidth: "2.5em",
            paddingRight: "1em",
            textAlign: "right",
            userSelect: "none",
            opacity: 0.5,
          }}
        >
          {data}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
