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
    ? "fixed inset-0 z-50 bg-white dark:bg-gray-900 overflow-auto"
    : `rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden ${className}`;

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
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
        {title ? (
          <span
            data-testid="latex-title"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            {title}
          </span>
        ) : (
          <span className="text-sm text-gray-500 dark:text-gray-400">
            LaTeX
          </span>
        )}

        <div className="flex items-center gap-2">
          {/* Zoom controls */}
          <div className="flex items-center gap-1">
            <button
              onClick={handleZoomOut}
              className="p-1 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
              aria-label="Zoom out"
            >
              <ZoomOut size={14} />
            </button>
            <span className="text-xs text-gray-500 dark:text-gray-400 w-10 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={handleZoomIn}
              className="p-1 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
              aria-label="Zoom in"
            >
              <ZoomIn size={14} />
            </button>
            <button
              onClick={handleResetZoom}
              className="p-1 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
              aria-label="Reset zoom"
            >
              <RotateCcw size={14} />
            </button>
          </div>

          {/* Fullscreen toggle */}
          <button
            onClick={handleToggleFullscreen}
            className="p-1 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
            aria-label="Toggle fullscreen"
          >
            {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>

          {/* Copy button */}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
            aria-label={copied ? "Copied" : "Copy LaTeX"}
          >
            {copied ? (
              <>
                <Check size={14} className="text-green-500" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy size={14} />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* LaTeX content */}
      <div
        className={`p-4 ${isFullscreen ? "min-h-[calc(100vh-60px)] flex items-center justify-center" : ""}`}
      >
        {error ? (
          <div className="flex flex-col gap-3">
            {/* Error message */}
            <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
              <AlertTriangle size={16} className="text-red-500" />
              <span className="text-sm text-red-700 dark:text-red-400">
                Error: {error}
              </span>
            </div>

            {/* Show raw LaTeX */}
            <pre className="p-3 bg-gray-50 dark:bg-gray-900 rounded text-sm text-gray-700 dark:text-gray-300 font-mono overflow-x-auto">
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
