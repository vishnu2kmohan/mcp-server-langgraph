/**
 * VegaLiteArtifact Component
 *
 * Renders Vega-Lite specifications using vega-embed.
 * Enables interactive Altair charts in the chat/canvas.
 *
 * Features:
 * - Renders Vega-Lite JSON specs
 * - Dark/light theme support
 * - Responsive sizing
 * - Export functionality
 * - Error handling with retry
 * - Accessibility support
 */

import { useEffect, useRef, useState, useCallback } from "react";
import embed, {
  Result as VegaEmbedResult,
  VisualizationSpec,
} from "vega-embed";
import { BarChart3, RefreshCw, Download, AlertCircle } from "lucide-react";
import type { VegaLiteSpec, VegaLiteConfig } from "../../types/artifacts";

import { Button } from "@/components/UI";

export interface VegaLiteArtifactProps {
  /** Vega-Lite specification (object or JSON string) */
  spec: VegaLiteSpec | string;
  /** Chart title (overrides spec.description) */
  title?: string;
  /** Theme for chart rendering */
  theme?: "light" | "dark";
  /** Width in pixels (default: responsive) */
  width?: number;
  /** Height in pixels (default: 300) */
  height?: number;
  /** Additional configuration */
  config?: VegaLiteConfig;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Parse spec from string or object
 */
function parseSpec(spec: VegaLiteSpec | string): VegaLiteSpec | null {
  if (typeof spec === "string") {
    try {
      return JSON.parse(spec) as VegaLiteSpec;
    } catch {
      return null;
    }
  }
  return spec;
}

/**
 * Extract title from Vega-Lite spec
 */
function extractTitle(spec: VegaLiteSpec): string {
  // Check for explicit title
  if (spec.title) {
    if (typeof spec.title === "string") {
      return spec.title;
    }
    if (typeof spec.title === "object" && spec.title.text) {
      return spec.title.text;
    }
  }
  // Fall back to description
  if (spec.description) {
    return spec.description;
  }
  return "Vega-Lite Chart";
}

/**
 * Check if a spec looks like a valid Vega-Lite spec
 */
function isValidVegaLiteSpec(spec: VegaLiteSpec): boolean {
  // Must have either mark, layer, or concat
  return !!(
    spec.mark ||
    spec.layer ||
    spec.hconcat ||
    spec.vconcat ||
    spec.concat ||
    spec.repeat ||
    spec.facet
  );
}

export function VegaLiteArtifact({
  spec,
  title,
  theme = "light",
  width,
  height = 300,
  config,
  className = "",
}: VegaLiteArtifactProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const embedResultRef = useRef<VegaEmbedResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [parsedSpec, setParsedSpec] = useState<VegaLiteSpec | null>(null);

  // Parse the spec on mount or when it changes
  useEffect(() => {
    const parsed = parseSpec(spec);
    if (!parsed) {
      setError("Failed to parse Vega-Lite specification: Invalid JSON");
      setIsLoading(false);
      return;
    }
    if (!isValidVegaLiteSpec(parsed)) {
      setError(
        "Invalid Vega-Lite specification: Missing mark, layer, or composition",
      );
      setIsLoading(false);
      return;
    }
    setParsedSpec(parsed);
    setError(null);
  }, [spec]);

  // Embed the chart when we have a valid spec
  const embedChart = useCallback(async () => {
    if (!containerRef.current || !parsedSpec) return;

    setIsLoading(true);
    setError(null);

    try {
      // Clean up previous embed
      if (embedResultRef.current) {
        embedResultRef.current.finalize();
        embedResultRef.current = null;
      }

      // Clear container
      containerRef.current.innerHTML = "";

      // Build embed options
      const embedOptions = {
        // Theme configuration
        theme: theme === "dark" ? ("dark" as const) : undefined,
        // Renderer (SVG by default for better quality)
        renderer: (config?.renderer || "svg") as "svg" | "canvas",
        // Actions menu
        actions:
          config?.actions !== undefined
            ? config.actions
            : { export: true, source: false, compiled: false },
        // Tooltip
        tooltip: config?.enableTooltip !== false,
        // Width and height are set in the spec, not in options
        ...(width ? { width } : {}),
        ...(height ? { height } : {}),
      };

      // Merge spec with width/height if not responsive
      const specWithSize = {
        ...parsedSpec,
        ...(width ? { width } : { width: "container" }),
        ...(height ? { height } : {}),
      } as VisualizationSpec;

      // Embed the chart
      const result = await embed(
        containerRef.current,
        specWithSize,
        embedOptions,
      );
      embedResultRef.current = result;
      setIsLoading(false);
    } catch (err) {
      console.error("Vega-Lite embed error:", err);
      setError(
        `Failed to render chart: ${err instanceof Error ? err.message : "Unknown error"}`,
      );
      setIsLoading(false);
    }
  }, [parsedSpec, theme, width, height, config]);

  // Embed chart when spec or dependencies change
  useEffect(() => {
    if (parsedSpec) {
      embedChart();
    }

    // Cleanup on unmount
    return () => {
      if (embedResultRef.current) {
        embedResultRef.current.finalize();
        embedResultRef.current = null;
      }
    };
  }, [parsedSpec, embedChart]);

  // Handle retry
  const handleRetry = useCallback(() => {
    setError(null);
    setParsedSpec(null);
    // Re-parse and re-embed
    const parsed = parseSpec(spec);
    if (parsed && isValidVegaLiteSpec(parsed)) {
      setParsedSpec(parsed);
    } else {
      setError("Failed to parse Vega-Lite specification");
    }
  }, [spec]);

  // Determine display title (before handleExport which uses it)
  const displayTitle =
    title || (parsedSpec ? extractTitle(parsedSpec) : "Vega-Lite Chart");

  // Handle export
  const handleExport = useCallback(async () => {
    if (!embedResultRef.current) return;

    try {
      // Get the SVG or PNG from vega
      const view = embedResultRef.current.view;
      const url = await view.toImageURL("png", 2); // 2x scale for quality

      // Download
      const a = document.createElement("a");
      a.href = url;
      a.download = `${displayTitle.replace(/\s+/g, "_")}.png`;
      a.click();
    } catch (err) {
      console.error("Export error:", err);
    }
  }, [displayTitle]);

  return (
    <div
      data-testid="vega-lite-artifact"
      className={`bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden w-full ${
        theme === "dark" ? "dark" : ""
      } ${className}`}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3
            size={16}
            className="text-neutral-500 dark:text-neutral-400"
          />
          <h3 className="font-medium text-neutral-900 dark:text-neutral-100">
            {displayTitle}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {/* Export button */}
          {!error && !isLoading && (
            <Button
              variant="secondary"
              className="p-1.5 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded"
              onClick={handleExport}
              aria-label="Export chart"
              title="Export as PNG"
            >
              <Download size={16} />
            </Button>
          )}
          {/* Retry button (shown on error) */}
          {error && (
            <Button
              variant="secondary"
              className="p-1.5 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded"
              onClick={handleRetry}
              aria-label="Retry"
              title="Retry rendering"
            >
              <RefreshCw size={16} />
            </Button>
          )}
        </div>
      </div>
      {/* Chart Container */}
      <div className="relative" style={{ minHeight: height }}>
        {/* Loading state */}
        {isLoading && (
          <div
            data-testid="vega-loading"
            className="absolute inset-0 flex items-center justify-center bg-neutral-50 dark:bg-neutral-900/50"
          >
            <div className="flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
              <div className="animate-spin rounded-full h-5 w-5 border-2 border-neutral-300 border-t-primary-500" />
              <span>Loading chart...</span>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div
            data-testid="vega-error"
            className="absolute inset-0 flex flex-col items-center justify-center bg-error-50 dark:bg-error-900/20 p-4"
          >
            <AlertCircle
              size={24}
              className="text-error-500 dark:text-error-400 mb-2"
            />
            <p className="text-error-700 dark:text-error-300 text-sm text-center">
              {error}
            </p>
            <Button
              variant="danger"
              className="mt-3 px-3 py-1.5 text-sm bg-error-100 dark:bg-error-900/50 text-error-700 dark:text-error-300 rounded hover:bg-error-200 dark:hover:bg-error-900/70"
              onClick={handleRetry}
            >
              Retry
            </Button>
          </div>
        )}

        {/* Vega chart container */}
        <div
          ref={containerRef}
          data-testid="vega-chart-container"
          role="img"
          aria-label={`Vega-Lite chart: ${displayTitle}`}
          className="w-full p-4"
          style={{ minHeight: error ? 0 : height }}
        />
      </div>
    </div>
  );
}

export default VegaLiteArtifact;
