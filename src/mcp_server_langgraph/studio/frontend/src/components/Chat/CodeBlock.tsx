/**
 * CodeBlock Component
 *
 * Enhanced code block with syntax highlighting and interactive controls.
 * Extracted for lazy loading support to reduce initial bundle size.
 *
 * Features:
 * - Syntax highlighting via Prism
 * - Copy to clipboard
 * - Word wrap toggle
 * - Download as file
 */

import { useState, useCallback } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Copy, Check } from "lucide-react";

/**
 * Get file extension for a language
 */
function getFileExtension(language?: string): string {
  const extensions: Record<string, string> = {
    javascript: "js",
    typescript: "ts",
    python: "py",
    ruby: "rb",
    rust: "rs",
    java: "java",
    cpp: "cpp",
    c: "c",
    go: "go",
    swift: "swift",
    kotlin: "kt",
    scala: "scala",
    php: "php",
    html: "html",
    css: "css",
    scss: "scss",
    json: "json",
    yaml: "yaml",
    xml: "xml",
    sql: "sql",
    bash: "sh",
    shell: "sh",
    markdown: "md",
    text: "txt",
  };
  return extensions[language || ""] || language || "txt";
}

export interface CodeBlockProps {
  /** Programming language for syntax highlighting */
  language?: string;
  /** The code content to display */
  children: string;
}

/**
 * Enhanced code block component with syntax highlighting and interactive controls:
 * - Copy to clipboard
 * - Word wrap toggle
 * - Download as file
 */
export function CodeBlock({ language, children }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [wordWrap, setWordWrap] = useState(false);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [children]);

  const handleToggleWordWrap = useCallback(() => {
    setWordWrap((prev) => !prev);
  }, []);

  const handleDownload = useCallback(() => {
    const ext = getFileExtension(language);
    const blob = new Blob([children], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.download = `code.${ext}`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }, [children, language]);

  return (
    <div className="relative group my-2">
      {/* Toolbar */}
      <div
        className="absolute right-2 top-2 z-10 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
        role="toolbar"
        aria-label="Code block actions"
      >
        <button
          onClick={handleToggleWordWrap}
          className={`p-1.5 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 ${
            wordWrap
              ? "bg-blue-600 text-white"
              : "bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white"
          }`}
          title="Toggle word wrap"
          aria-label={wordWrap ? "Disable word wrap" : "Enable word wrap"}
          aria-pressed={wordWrap}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <line x1="3" y1="6" x2="21" y2="6" />
            <path d="M3 12h15a3 3 0 1 1 0 6h-4" />
            <polyline points="16 16 14 18 16 20" />
            <line x1="3" y1="18" x2="10" y2="18" />
          </svg>
        </button>
        <button
          onClick={handleDownload}
          className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
          title="Download file"
          aria-label="Download code as file"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
        </button>
        <button
          onClick={handleCopy}
          className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
          title="Copy code"
          aria-label={
            copied ? "Code copied to clipboard" : "Copy code to clipboard"
          }
        >
          {copied ? (
            <Check size={14} aria-hidden="true" />
          ) : (
            <Copy size={14} aria-hidden="true" />
          )}
        </button>
      </div>
      {language && (
        <div className="absolute left-3 top-2 z-10 text-xs text-gray-400 font-mono">
          {language}
        </div>
      )}
      <SyntaxHighlighter
        style={oneDark}
        language={language || "text"}
        showLineNumbers
        wrapLongLines={wordWrap}
        customStyle={{
          margin: 0,
          borderRadius: "0.5rem",
          paddingTop: "2rem",
        }}
        codeTagProps={{
          className: "text-sm font-mono",
        }}
      >
        {children}
      </SyntaxHighlighter>
    </div>
  );
}

export default CodeBlock;
