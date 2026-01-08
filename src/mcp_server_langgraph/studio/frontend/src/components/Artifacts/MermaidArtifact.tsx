/**
 * MermaidArtifact Component
 *
 * Renders Mermaid diagram code with utilities for viewing.
 * Features:
 * - Code display with syntax highlighting appearance
 * - Copy to clipboard
 * - Open in mermaid.live for rendering
 * - Expandable/collapsible view
 * - Theme support
 *
 * Note: This component displays the diagram code. For actual rendering,
 * the diagram can be opened in mermaid.live. Consider adding the mermaid
 * library as a dependency for inline rendering.
 */

import { useState, useCallback } from "react";
import { Copy, ExternalLink, Maximize2, Minimize2, Check } from "lucide-react";
import { ArtifactExporter } from "./ArtifactExporter";
import type { ExportFormat } from "./ArtifactExporter";

export interface MermaidArtifactProps {
  code: string;
  title?: string;
  theme?: "default" | "forest" | "dark" | "neutral";
  expandable?: boolean;
  className?: string;
}

/**
 * Encode diagram for mermaid.live URL
 */
function encodeMermaidUrl(code: string): string {
  const state = {
    code,
    mermaid: { theme: "default" },
    autoSync: true,
    updateDiagram: true,
  };
  const json = JSON.stringify(state);
  const encoded = btoa(json);
  return `https://mermaid.live/edit#pako:${encoded}`;
}

export function MermaidArtifact({
  code,
  title,
  theme = "default",
  expandable = false,
  className = "",
}: MermaidArtifactProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isCopied, setIsCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch {
      // Silently fail
    }
  };

  const handleOpenInLive = () => {
    const url = encodeMermaidUrl(code);
    window.open(url, "_blank");
  };

  const handleToggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  // Handle export from ArtifactExporter
  const handleExport = useCallback(
    (format: ExportFormat, blob: Blob | string) => {
      // Download the blob
      if (blob instanceof Blob) {
        const extension = format === "code" ? "mmd" : format;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${(title || "diagram").replace(/\s+/g, "_")}.${extension}`;
        a.click();
        URL.revokeObjectURL(url);
      }
    },
    [title],
  );

  return (
    <div
      data-testid="mermaid-container"
      className={`border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden ${theme === "dark" ? "dark" : ""} ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {title || "Mermaid Diagram"}
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={handleCopy}
            title="Copy code"
            className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-200 dark:text-gray-400 dark:hover:text-gray-200 rounded hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700"
          >
            {isCopied ? (
              <Check size={16} className="text-success-500" />
            ) : (
              <Copy size={16} />
            )}
          </button>
          <button
            onClick={handleOpenInLive}
            title="Open in Mermaid Live"
            className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-200 dark:text-gray-400 dark:hover:text-gray-200 rounded hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700"
          >
            <ExternalLink size={16} />
          </button>
          <ArtifactExporter
            artifactType="mermaid"
            data={code}
            onExport={handleExport}
            filename={(title || "diagram").replace(/\s+/g, "_")}
          />
          {expandable && (
            <button
              onClick={handleToggleExpand}
              title={isExpanded ? "Collapse" : "Expand"}
              className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-200 dark:text-gray-400 dark:hover:text-gray-200 rounded hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700"
            >
              {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </button>
          )}
        </div>
      </div>

      {/* Code Content */}
      <div
        className={`bg-gray-900 text-gray-100 p-4 overflow-auto ${isExpanded ? "max-h-[600px]" : "max-h-[300px]"}`}
      >
        <pre className="text-sm font-mono whitespace-pre-wrap">
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
}

export default MermaidArtifact;
