/**
 * HTMLArtifact Component
 *
 * Safely renders HTML content in a sandboxed iframe.
 * Supports Bokeh visualization output and generic HTML from code execution.
 *
 * Security:
 * - Uses sandboxed iframe to isolate content
 * - Restricts access to parent page
 * - Only enables scripts for trusted content (Bokeh)
 */

import { useMemo, useRef, useEffect, useState } from "react";
import { Code, Maximize2, AlertCircle, BarChart3 } from "lucide-react";
import { detectBokehHTML } from "../../utils/artifactParser";

import { Button } from "@/components/UI";

export interface HTMLArtifactProps {
  /** HTML content to render */
  data: string;
  /** Display title */
  title?: string;
  /** Height in pixels */
  height?: number;
  /** Theme for container styling */
  theme?: "light" | "dark";
  /** Additional CSS classes */
  className?: string;
  /** Explicitly allow scripts (overrides auto-detection) */
  allowScripts?: boolean;
}

/**
 * Build sandbox attribute based on content type
 */
function getSandboxAttribute(shouldAllowScripts: boolean): string {
  // Base sandbox restrictions
  const permissions: string[] = [];

  if (shouldAllowScripts) {
    // Scripts enabled for Bokeh or explicitly allowed
    permissions.push("allow-scripts");
  }

  // Note: We intentionally do NOT include allow-same-origin
  // This prevents the iframe from accessing parent page data
  return permissions.join(" ");
}

/**
 * Wrap HTML content with proper document structure
 */
function wrapHTMLContent(html: string, theme: "light" | "dark"): string {
  // Check if already has html/body tags
  const hasHTMLTag = /<html[\s>]/i.test(html);
  const hasBodyTag = /<body[\s>]/i.test(html);

  if (hasHTMLTag && hasBodyTag) {
    // Already a complete document
    return html;
  }

  // Wrap in a minimal document with theme-aware styling
  const bgColor = theme === "dark" ? "#1f2937" : "#ffffff";
  const textColor = theme === "dark" ? "#e5e7eb" : "#1f2937";

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      margin: 0;
      padding: 16px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background-color: ${bgColor};
      color: ${textColor};
    }
    table {
      border-collapse: collapse;
      width: 100%;
    }
    th, td {
      border: 1px solid ${theme === "dark" ? "#374151" : "#e5e7eb"};
      padding: 8px;
      text-align: left;
    }
    th {
      background-color: ${theme === "dark" ? "#374151" : "#f3f4f6"};
    }
  </style>
</head>
<body>
${html}
</body>
</html>
  `.trim();
}

export function HTMLArtifact({
  data,
  title,
  height = 400,
  theme = "light",
  className = "",
  allowScripts,
}: HTMLArtifactProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Detect if this is Bokeh HTML
  const isBokeh = useMemo(() => detectBokehHTML(data), [data]);

  // Get sandbox permissions - allow scripts if Bokeh detected OR explicitly allowed
  const sandboxAttr = useMemo(
    () => getSandboxAttribute(isBokeh || allowScripts === true),
    [isBokeh, allowScripts],
  );

  // Wrap content if needed
  const wrappedContent = useMemo(
    () => wrapHTMLContent(data, theme),
    [data, theme],
  );

  // Create blob URL for iframe src
  const blobUrl = useMemo(() => {
    try {
      const blob = new Blob([wrappedContent], { type: "text/html" });
      return URL.createObjectURL(blob);
    } catch {
      setError("Failed to create HTML content");
      return null;
    }
  }, [wrappedContent]);

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [blobUrl]);

  // Determine display title
  const displayTitle = title || (isBokeh ? "Bokeh Chart" : "HTML");

  // Icon based on content type
  const Icon = isBokeh ? BarChart3 : Code;

  return (
    <div
      data-testid="html-artifact"
      className={`bg-neutral-1 border border-neutral-5 rounded-lg overflow-hidden ${
        theme === "dark" ? "dark" : ""
      } ${className}`}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-neutral-5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={16} className="text-neutral-10" />
          <h3 className="font-medium text-neutral-12">
            {displayTitle}
          </h3>
          {isBokeh && (
            <span className="px-2 py-0.5 text-xs bg-primary-3 bg-primary-4 text-primary-10 dark:text-primary-7 rounded">
              Bokeh
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            className="p-1.5 text-neutral-11 hover:bg-neutral-2 rounded"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-label="Expand"
            title="Expand view"
          >
            <Maximize2 size={16} />
          </Button>
        </div>
      </div>
      {/* Content */}
      <div
        className="relative"
        style={{ height: isExpanded ? "80vh" : height }}
      >
        {error ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-error-1 dark:bg-error-a3 p-4">
            <AlertCircle
              size={24}
              className="text-error-9 dark:text-error-7 mb-2"
            />
            <p className="text-error-11 dark:text-error-9 text-sm text-center">
              {error}
            </p>
          </div>
        ) : blobUrl ? (
          <iframe
            ref={iframeRef}
            data-testid="html-iframe"
            src={blobUrl}
            sandbox={sandboxAttr}
            title={displayTitle}
            className="w-full h-full border-0"
            style={{ height: isExpanded ? "80vh" : height }}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-neutral-10">
            Loading...
          </div>
        )}
      </div>
    </div>
  );
}

export default HTMLArtifact;
