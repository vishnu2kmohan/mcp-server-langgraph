/**
 * SVGArtifact Component
 *
 * Renders SVG content inline with sanitization for security.
 * Supports raw SVG markup, base64 data URLs, and URL-encoded data URLs.
 *
 * Features:
 * - Security sanitization (removes scripts, event handlers)
 * - Copy to clipboard
 * - Download as SVG file
 */

import { useMemo, useState, useCallback } from "react";
import { Copy, Check } from "lucide-react";
import { ArtifactExporter } from "./ArtifactExporter";
import type { ExportFormat } from "./ArtifactExporter";
import { CodePreviewToggle, type ViewMode } from "./CodePreviewToggle";
import type { SVGConfig } from "../../types/artifacts";

import { Button } from "@/components/UI";

export interface SVGArtifactProps {
  data: string;
  title?: string;
  config?: SVGConfig;
}

/**
 * Sanitize SVG content to remove potentially dangerous elements and attributes
 */
function sanitizeSvg(svgContent: string): string {
  // Create a DOM parser to parse the SVG
  const parser = new DOMParser();
  const doc = parser.parseFromString(svgContent, "image/svg+xml");

  // Check for parsing errors
  const parserError = doc.querySelector("parsererror");
  if (parserError) {
    throw new Error("Invalid SVG content");
  }

  const svg = doc.querySelector("svg");
  if (!svg) {
    throw new Error("No SVG element found");
  }

  // Remove dangerous elements
  const dangerousElements = [
    "script",
    "foreignObject",
    "iframe",
    "object",
    "embed",
  ];
  dangerousElements.forEach((tag) => {
    const elements = svg.querySelectorAll(tag);
    elements.forEach((el) => el.remove());
  });

  // Remove event handlers from all elements
  const allElements = svg.querySelectorAll("*");
  allElements.forEach((el) => {
    // Get all attributes
    const attrs = Array.from(el.attributes);
    attrs.forEach((attr) => {
      // Remove event handlers (on*)
      if (attr.name.toLowerCase().startsWith("on")) {
        el.removeAttribute(attr.name);
      }
      // Remove javascript: URLs
      if (attr.value.toLowerCase().includes("javascript:")) {
        el.removeAttribute(attr.name);
      }
    });
  });

  // Also sanitize the SVG element itself
  const svgAttrs = Array.from(svg.attributes);
  svgAttrs.forEach((attr) => {
    if (attr.name.toLowerCase().startsWith("on")) {
      svg.removeAttribute(attr.name);
    }
  });

  return svg.outerHTML;
}

/**
 * Extract SVG content from data URL or raw SVG
 */
function extractSvgContent(data: string): string {
  // Handle base64 data URL
  if (data.startsWith("data:image/svg+xml;base64,")) {
    const base64 = data.replace("data:image/svg+xml;base64,", "");
    return atob(base64);
  }

  // Handle URL-encoded data URL
  if (data.startsWith("data:image/svg+xml,")) {
    const encoded = data.replace("data:image/svg+xml,", "");
    return decodeURIComponent(encoded);
  }

  // Raw SVG content
  return data;
}

export function SVGArtifact({ data, title, config }: SVGArtifactProps) {
  const [copied, setCopied] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("preview");

  const { sanitizedSvg, error } = useMemo(() => {
    if (!data || data.trim() === "") {
      return { sanitizedSvg: null, error: "No SVG data provided" };
    }

    try {
      const svgContent = extractSvgContent(data);
      const sanitized = sanitizeSvg(svgContent);
      return { sanitizedSvg: sanitized, error: null };
    } catch (err) {
      return {
        sanitizedSvg: null,
        error: err instanceof Error ? err.message : "Invalid SVG",
      };
    }
  }, [data]);

  // Copy SVG to clipboard
  const handleCopy = useCallback(async () => {
    if (!sanitizedSvg) return;
    try {
      await navigator.clipboard.writeText(sanitizedSvg);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy SVG:", err);
    }
  }, [sanitizedSvg]);

  // Handle export from ArtifactExporter
  const handleExport = useCallback(
    (format: ExportFormat, blob: Blob | string) => {
      // Download the blob
      if (blob instanceof Blob) {
        const extension =
          format === "pdf" ? "pdf" : format === "png" ? "png" : "svg";
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${title?.replace(/\s+/g, "_") || "diagram"}.${extension}`;
        a.click();
        URL.revokeObjectURL(url);
      }
    },
    [title],
  );

  const containerStyle: React.CSSProperties = {
    width: config?.width
      ? typeof config.width === "number"
        ? `${config.width}px`
        : config.width
      : undefined,
    height: config?.height
      ? typeof config.height === "number"
        ? `${config.height}px`
        : config.height
      : undefined,
  };

  if (error) {
    return (
      <div
        className="p-4 bg-error-1 dark:bg-error-a3 border border-error-4 dark:border-error-11 rounded-lg"
        role="alert"
      >
        <p className="text-sm text-error-10 dark:text-error-7">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-neutral-1 rounded-lg overflow-hidden border border-neutral-5">
      {/* Header with title and actions */}
      <div className="px-4 py-2 border-b border-neutral-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h4 className="text-sm font-medium text-neutral-11">
            {title || "SVG"}
          </h4>
          <CodePreviewToggle
            mode={viewMode}
            onModeChange={setViewMode}
            previewSupported={!error}
          />
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="secondary"
            className="p-1.5 text-neutral-10 hover:text-neutral-11 rounded hover:bg-neutral-2"
            onClick={handleCopy}
            aria-label="Copy SVG"
          >
            {copied ? (
              <Check size={16} className="text-success-9" />
            ) : (
              <Copy size={16} />
            )}
          </Button>
          <ArtifactExporter
            artifactType="svg"
            data={sanitizedSvg || ""}
            onExport={handleExport}
            filename={(title || "diagram").replace(/\s+/g, "_")}
          />
        </div>
      </div>
      {/* SVG Content - Preview Mode */}
      {viewMode === "preview" && (
        <div
          data-testid="svg-container"
          className="p-4 flex items-center justify-center"
          style={containerStyle}
          dangerouslySetInnerHTML={{ __html: sanitizedSvg || "" }}
        />
      )}
      {/* SVG Source Code - Code Mode */}
      {viewMode === "code" && (
        <div data-testid="svg-source-code" className="p-4">
          <pre className="bg-neutral-2 text-neutral-9 p-4 rounded-lg overflow-x-auto text-sm font-mono">
            <code>{data}</code>
          </pre>
        </div>
      )}
    </div>
  );
}
