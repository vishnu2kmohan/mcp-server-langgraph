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

import { Button } from "@/components/UI";

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
      className={`border border-neutral-5 rounded-lg overflow-hidden ${theme === "dark" ? "dark" : ""} ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-neutral-1 border-b border-neutral-5">
        <span className="text-sm font-medium text-neutral-11">
          {title || "Mermaid Diagram"}
        </span>
        <div className="flex items-center gap-1">
          <Button
            variant="secondary"
            className="p-1.5 text-neutral-10 hover:text-neutral-11 rounded hover:bg-neutral-2"
            onClick={handleCopy}
            title="Copy code"
          >
            {isCopied ? (
              <Check size={16} className="text-success-9" />
            ) : (
              <Copy size={16} />
            )}
          </Button>
          <Button size="icon"
            variant="secondary"
            className="p-1.5 text-neutral-10 hover:text-neutral-11 rounded hover:bg-neutral-2"
            onClick={handleOpenInLive}
            title="Open in Mermaid Live"
          >
            <ExternalLink size={16} />
          </Button>
          <ArtifactExporter
            artifactType="mermaid"
            data={code}
            onExport={handleExport}
            filename={(title || "diagram").replace(/\s+/g, "_")}
          />
          {expandable && (
            <Button
              variant="secondary"
              className="p-1.5 text-neutral-10 hover:text-neutral-11 rounded hover:bg-neutral-2"
              onClick={handleToggleExpand}
              title={isExpanded ? "Collapse" : "Expand"}
            >
              {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </Button>
          )}
        </div>
      </div>
      {/* Code Content */}
      <div
        className={`bg-neutral-2 text-neutral-9 p-4 overflow-auto ${isExpanded ? "max-h-[600px]" : "max-h-[300px]"}`}
      >
        <pre className="text-sm font-mono whitespace-pre-wrap">
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
}

export default MermaidArtifact;
