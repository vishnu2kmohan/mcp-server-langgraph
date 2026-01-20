/**
 * InteractiveSVGArtifact Component
 *
 * Enhanced SVG renderer with interactive controls:
 * - Zoom in/out with buttons and mouse wheel
 * - Fullscreen view
 * - Pan/drag support
 * - Copy SVG source
 * - Download as SVG or PNG
 */

import { useState, useMemo, useCallback } from "react";
import { Copy, Check } from "lucide-react";
import type { SVGConfig } from "../../types/artifacts";

import { Button } from "@/components/UI";

export interface InteractiveSVGArtifactProps {
  data: string;
  title?: string;
  config?: SVGConfig;
  className?: string;
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
    const attrs = Array.from(el.attributes);
    attrs.forEach((attr) => {
      if (attr.name.toLowerCase().startsWith("on")) {
        el.removeAttribute(attr.name);
      }
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

export function InteractiveSVGArtifact({
  data,
  title,
  className = "",
}: InteractiveSVGArtifactProps) {
  const [zoom, setZoom] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Parse and sanitize SVG
  const { sanitizedSvg, error, rawSvg } = useMemo(() => {
    if (!data || data.trim() === "") {
      return { sanitizedSvg: null, error: "No SVG data provided", rawSvg: "" };
    }

    try {
      const svgContent = extractSvgContent(data);
      const sanitized = sanitizeSvg(svgContent);
      return { sanitizedSvg: sanitized, error: null, rawSvg: svgContent };
    } catch (err) {
      return {
        sanitizedSvg: null,
        error: err instanceof Error ? err.message : "Invalid SVG",
        rawSvg: "",
      };
    }
  }, [data]);

  // Zoom handlers
  const handleZoomIn = useCallback(() => {
    setZoom((prev) => Math.min(prev * 1.25, 4));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((prev) => Math.max(prev * 0.8, 0.25));
  }, []);

  const handleResetZoom = useCallback(() => {
    setZoom(1);
    setPosition({ x: 0, y: 0 });
  }, []);

  // Copy SVG source
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(data);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }, [data]);

  // Toggle fullscreen
  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev);
  }, []);

  // Download as SVG
  const handleDownloadSVG = useCallback(() => {
    if (!rawSvg) return;

    const blob = new Blob([rawSvg], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.download = "image.svg";
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }, [rawSvg]);

  // Download as PNG
  const handleDownloadPNG = useCallback(() => {
    if (!sanitizedSvg) return;

    const svgElement = document.createElement("div");
    svgElement.innerHTML = sanitizedSvg;
    const svgNode = svgElement.querySelector("svg");
    if (!svgNode) return;

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const svgData = new XMLSerializer().serializeToString(svgNode);
    const svgBlob = new Blob([svgData], {
      type: "image/svg+xml;charset=utf-8",
    });
    const url = URL.createObjectURL(svgBlob);

    const img = new Image();
    img.onload = () => {
      canvas.width = img.width * 2;
      canvas.height = img.height * 2;
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      const pngUrl = canvas.toDataURL("image/png");
      const link = document.createElement("a");
      link.download = "image.png";
      link.href = pngUrl;
      link.click();

      URL.revokeObjectURL(url);
    };
    img.src = url;
  }, [sanitizedSvg]);

  // Mouse wheel zoom
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        if (e.deltaY < 0) {
          handleZoomIn();
        } else {
          handleZoomOut();
        }
      }
    },
    [handleZoomIn, handleZoomOut],
  );

  // Pan handlers
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button === 0) {
        setIsDragging(true);
        setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
      }
    },
    [position],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (isDragging) {
        setPosition({
          x: e.clientX - dragStart.x,
          y: e.clientY - dragStart.y,
        });
      }
    },
    [isDragging, dragStart],
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Touch state for pinch-to-zoom
  const [touchState, setTouchState] = useState<{
    initialDistance: number;
    initialZoom: number;
  } | null>(null);

  // Calculate distance between two touch points
  const getTouchDistance = useCallback((touches: React.TouchList) => {
    const touch0 = touches[0];
    const touch1 = touches[1];
    if (touches.length < 2 || !touch0 || !touch1) return 0;
    const dx = touch1.clientX - touch0.clientX;
    const dy = touch1.clientY - touch0.clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }, []);

  // Touch handlers for pan and pinch-to-zoom
  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (e.touches.length === 2) {
        // Two fingers - start pinch
        const distance = getTouchDistance(e.touches);
        setTouchState({
          initialDistance: distance,
          initialZoom: zoom,
        });
      } else if (e.touches.length === 1) {
        // Single finger - start pan
        const touch0 = e.touches[0];
        if (!touch0) return;
        setIsDragging(true);
        setDragStart({
          x: touch0.clientX - position.x,
          y: touch0.clientY - position.y,
        });
      }
    },
    [getTouchDistance, zoom, position],
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
      } else if (e.touches.length === 1 && isDragging) {
        // Pan
        const touch0 = e.touches[0];
        if (!touch0) return;
        setPosition({
          x: touch0.clientX - dragStart.x,
          y: touch0.clientY - dragStart.y,
        });
      }
    },
    [touchState, getTouchDistance, isDragging, dragStart],
  );

  const handleTouchEnd = useCallback(() => {
    setTouchState(null);
    setIsDragging(false);
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

  // Error state
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

  const containerClasses = isFullscreen
    ? "fixed inset-0 z-modal bg-neutral-2"
    : `bg-neutral-1 rounded-lg overflow-hidden ${className}`;

  return (
    <div
      data-testid="svg-container"
      className={containerClasses}
      onKeyDown={handleKeyDown}
      tabIndex={0}
    >
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2 p-2 bg-neutral-2 border-b border-neutral-5">
        {/* Title */}
        {title && (
          <span className="text-sm font-medium text-neutral-11 flex-1">
            {title}
          </span>
        )}

        {/* Zoom controls */}
        <div className="flex items-center gap-1">
          <Button
            variant="secondary"
            className="p-1.5 rounded hover:bg-neutral-3 text-neutral-11"
            type="button"
            onClick={handleZoomOut}
            aria-label="Zoom out"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
              <line x1="8" y1="11" x2="14" y2="11" />
            </svg>
          </Button>
          <span className="text-xs text-neutral-10 w-12 text-center">
            {Math.round(zoom * 100)}%
          </span>
          <Button
            variant="secondary"
            className="p-1.5 rounded hover:bg-neutral-3 text-neutral-11"
            type="button"
            onClick={handleZoomIn}
            aria-label="Zoom in"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
              <line x1="11" y1="8" x2="11" y2="14" />
              <line x1="8" y1="11" x2="14" y2="11" />
            </svg>
          </Button>
          <Button
            variant="secondary"
            className="p-1.5 rounded hover:bg-neutral-3 text-neutral-11"
            type="button"
            onClick={handleResetZoom}
            aria-label="Reset zoom"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
              <path d="M3 3v5h5" />
            </svg>
          </Button>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1">
          <Button
            variant="secondary"
            className="p-1.5 rounded hover:bg-neutral-3 text-neutral-11"
            type="button"
            onClick={handleCopy}
            aria-label="Copy SVG"
          >
            {copied ? (
              <Check size={16} className="text-success-9" />
            ) : (
              <Copy size={16} />
            )}
          </Button>
          <Button
            variant="secondary"
            className="p-1.5 rounded hover:bg-neutral-3 text-neutral-11"
            type="button"
            onClick={handleDownloadSVG}
            aria-label="Download SVG"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
          </Button>
          <Button
            variant="secondary"
            className="p-1.5 rounded hover:bg-neutral-3 text-neutral-11"
            type="button"
            onClick={handleDownloadPNG}
            aria-label="Download PNG"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
          </Button>
          <Button
            variant="secondary"
            className="p-1.5 rounded hover:bg-neutral-3 text-neutral-11"
            type="button"
            onClick={handleToggleFullscreen}
            aria-label="Toggle fullscreen"
          >
            {isFullscreen ? (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="4 14 10 14 10 20" />
                <polyline points="20 10 14 10 14 4" />
                <line x1="14" y1="10" x2="21" y2="3" />
                <line x1="3" y1="21" x2="10" y2="14" />
              </svg>
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="15 3 21 3 21 9" />
                <polyline points="9 21 3 21 3 15" />
                <line x1="21" y1="3" x2="14" y2="10" />
                <line x1="3" y1="21" x2="10" y2="14" />
              </svg>
            )}
          </Button>
        </div>
      </div>
      {/* SVG viewport */}
      <div
        data-testid="svg-viewport"
        className={`${isFullscreen ? "h-[calc(100vh-48px)]" : "h-64"} overflow-hidden cursor-grab active:cursor-grabbing`}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        style={{
          transform: `scale(${zoom}) translate(${position.x / zoom}px, ${position.y / zoom}px)`,
          transformOrigin: "center center",
          transition: isDragging ? "none" : "transform 0.1s ease-out",
        }}
      >
        <div
          className="w-full h-full flex items-center justify-center p-4"
          dangerouslySetInnerHTML={{ __html: sanitizedSvg || "" }}
        />
      </div>
    </div>
  );
}

export default InteractiveSVGArtifact;
