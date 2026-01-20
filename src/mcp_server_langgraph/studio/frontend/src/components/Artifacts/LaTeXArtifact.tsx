/**
 * LaTeXArtifact Component
 *
 * Renders LaTeX mathematical expressions using KaTeX.
 * Features:
 * - Inline and display mode rendering
 * - Copy to clipboard
 * - Error handling for invalid LaTeX
 * - Accessible markup
 * - Zoom controls for complex equations
 * - Fullscreen view
 */

import { useState, useCallback, useMemo } from "react";
import {
  Copy,
  Check,
  AlertTriangle,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Maximize2,
  Minimize2,
} from "lucide-react";
import katex from "katex";

import { Button } from "@/components/UI";

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
  const [zoom, setZoom] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);

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

  // Zoom handlers
  const handleZoomIn = useCallback(() => {
    setZoom((prev) => Math.min(prev * 1.25, 4));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((prev) => Math.max(prev * 0.8, 0.25));
  }, []);

  const handleResetZoom = useCallback(() => {
    setZoom(1);
  }, []);

  // Fullscreen toggle
  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev);
  }, []);

  // Touch state for pinch-to-zoom
  const [touchState, setTouchState] = useState<{
    initialDistance: number;
    initialZoom: number;
  } | null>(null);

  // Calculate distance between two touch points
  const getTouchDistance = useCallback((touches: React.TouchList) => {
    if (touches.length < 2) return 0;
    const touch0 = touches[0];
    const touch1 = touches[1];
    if (!touch0 || !touch1) return 0;
    const dx = touch1.clientX - touch0.clientX;
    const dy = touch1.clientY - touch0.clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }, []);

  // Touch handlers for pinch-to-zoom
  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (e.touches.length === 2) {
        // Two fingers - start pinch
        const distance = getTouchDistance(e.touches);
        setTouchState({
          initialDistance: distance,
          initialZoom: zoom,
        });
      }
    },
    [getTouchDistance, zoom],
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (e.touches.length === 2 && touchState) {
        // Pinch-to-zoom
        e.preventDefault();
        const currentDistance = getTouchDistance(e.touches);
        const scale = currentDistance / touchState.initialDistance;
        const newZoom = Math.min(
          4,
          Math.max(0.25, touchState.initialZoom * scale),
        );
        setZoom(newZoom);
      }
    },
    [touchState, getTouchDistance],
  );

  const handleTouchEnd = useCallback(() => {
    setTouchState(null);
  }, []);

  // Keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case "+":
        case "=":
          e.preventDefault();
          handleZoomIn();
          break;
        case "-":
        case "_":
          e.preventDefault();
          handleZoomOut();
          break;
        case "0":
          e.preventDefault();
          handleResetZoom();
          break;
        case "Escape":
          if (isFullscreen) {
            e.preventDefault();
            setIsFullscreen(false);
          }
          break;
      }
    },
    [handleZoomIn, handleZoomOut, handleResetZoom, isFullscreen],
  );

  const containerClasses = isFullscreen
    ? "fixed inset-0 z-modal bg-neutral-1 overflow-auto"
    : `rounded-lg border border-neutral-5 bg-neutral-1 overflow-hidden ${className}`;

  return (
    <div
      data-testid="latex-container"
      className={containerClasses}
      onKeyDown={handleKeyDown}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      tabIndex={0}
    >
      {/* Header with title and actions */}
      <div className="flex items-center justify-between px-4 py-2 bg-neutral-1 border-b border-neutral-5">
        {title ? (
          <span
            data-testid="latex-title"
            className="text-sm font-medium text-neutral-11"
          >
            {title}
          </span>
        ) : (
          <span className="text-sm text-neutral-10">
            LaTeX
          </span>
        )}

        <div className="flex items-center gap-2">
          {/* Zoom controls */}
          <div className="flex items-center gap-1">
            <Button size="icon"
              variant="secondary"
              className="p-1 text-neutral-11 hover:bg-neutral-3 rounded"
              onClick={handleZoomOut}
              aria-label="Zoom out"
            >
              <ZoomOut size={14} />
            </Button>
            <span className="text-xs text-neutral-10 w-10 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <Button size="icon"
              variant="secondary"
              className="p-1 text-neutral-11 hover:bg-neutral-3 rounded"
              onClick={handleZoomIn}
              aria-label="Zoom in"
            >
              <ZoomIn size={14} />
            </Button>
            <Button size="icon"
              variant="secondary"
              className="p-1 text-neutral-11 hover:bg-neutral-3 rounded"
              onClick={handleResetZoom}
              aria-label="Reset zoom"
            >
              <RotateCcw size={14} />
            </Button>
          </div>

          {/* Fullscreen toggle */}
          <Button
            variant="secondary"
            className="p-1 text-neutral-11 hover:bg-neutral-3 rounded"
            onClick={handleToggleFullscreen}
            aria-label="Toggle fullscreen"
          >
            {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </Button>

          {/* Copy button */}
          <Button
            variant="secondary"
            size="sm"
            className="flex px-2 py-1 text-xs text-neutral-11 hover:bg-neutral-3 rounded"
            onClick={handleCopy}
            aria-label={copied ? "Copied" : "Copy LaTeX"}
          >
            {copied ? (
              <>
                <Check size={14} className="text-success-9" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy size={14} />
                <span>Copy</span>
              </>
            )}
          </Button>
        </div>
      </div>
      {/* LaTeX content */}
      <div
        className={`p-4 ${isFullscreen ? "min-h-[calc(100vh-60px)] flex items-center justify-center" : ""}`}
      >
        {error ? (
          <div className="flex flex-col gap-3">
            {/* Error message */}
            <div className="flex items-center gap-2 p-3 bg-error-1 dark:bg-error-a3 rounded border border-error-4 dark:border-error-11">
              <AlertTriangle size={16} className="text-error-9" />
              <span className="text-sm text-error-11 dark:text-error-7">
                Error: {error}
              </span>
            </div>

            {/* Show raw LaTeX */}
            <pre className="p-3 bg-neutral-1 rounded text-sm text-neutral-11 font-mono overflow-x-auto">
              {content}
            </pre>
          </div>
        ) : (
          <div
            data-testid="latex-artifact"
            role="img"
            aria-label={`LaTeX math: ${content}`}
            className={`${displayMode ? "text-center" : ""} overflow-x-auto transition-transform`}
            style={{
              transform: `scale(${zoom})`,
              transformOrigin: "center center",
            }}
            dangerouslySetInnerHTML={{ __html: html || "" }}
          />
        )}
      </div>
    </div>
  );
}
