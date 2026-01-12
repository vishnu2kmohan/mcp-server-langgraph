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

import { Button } from "@/components/UI";

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
      ? "bg-neutral-900 text-neutral-100 border-neutral-700"
      : "bg-neutral-50 text-neutral-900 border-neutral-200 dark:border-neutral-700";

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
            ? "border-neutral-700 bg-neutral-800"
            : "border-neutral-200 dark:border-neutral-700 bg-neutral-100 dark:bg-neutral-800"
        }`}
      >
        <div className="flex items-center gap-3">
          {title && <span className="font-medium">{title}</span>}
          <span
            className={`text-xs font-mono px-2 py-1 rounded ${
              theme === "dark"
                ? "bg-neutral-700 text-neutral-300"
                : "bg-neutral-200 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-200"
            }`}
          >
            {language}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            className="flex px-3 py-1 text-sm rounded"
            onClick={handleCopy}
            aria-label="Copy code"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-success-500" />
                <span className="text-success-500">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                <span>Copy</span>
              </>
            )}
          </Button>
          <Button
            className="p-1.5 rounded"
            onClick={handleDownload}
            aria-label="Download code"
          >
            <Download className="w-4 h-4" />
          </Button>
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
