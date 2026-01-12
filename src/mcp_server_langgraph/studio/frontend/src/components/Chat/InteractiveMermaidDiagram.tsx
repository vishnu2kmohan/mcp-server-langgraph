/**
 * InteractiveMermaidDiagram Component
 *
 * Enhanced mermaid diagram renderer with interactive controls:
 * - Zoom in/out with buttons and mouse wheel
 * - Fullscreen view
 * - Pan/drag support
 * - Copy source code
 * - Download as PNG
 */

import { useState, useEffect, useRef, useId, useCallback } from "react";
import mermaid from "mermaid";
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Maximize2,
  Minimize2,
  Copy,
  Check,
  AlertCircle,
  Download,
} from "lucide-react";

import { Button } from "@/components/UI";

// Track whether mermaid has been initialized (for lazy loading support)
let mermaidInitialized = false;

/**
 * Initialize mermaid on first use (supports lazy loading)
 */
function ensureMermaidInitialized() {
  if (!mermaidInitialized) {
    // Initialize mermaid with dark theme support
    // suppressErrorRendering prevents Mermaid from rendering its own error SVG at the bottom of the page
    mermaid.initialize({
      startOnLoad: false,
      theme: "dark",
      securityLevel: "loose",
      suppressErrorRendering: true,
    });
    mermaidInitialized = true;
  }
}

export interface InteractiveMermaidDiagramProps {
  /** The mermaid diagram code */
  code: string;
  /** Optional className for the container */
  className?: string;
}

export function InteractiveMermaidDiagram({
  code,
  className = "",
}: InteractiveMermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const uniqueId = useId();
  const [error, setError] = useState<string | null>(null);
  const [svg, setSvg] = useState<string>("");
  const [zoom, setZoom] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Render the mermaid diagram
  useEffect(() => {
    const renderDiagram = async () => {
      if (!containerRef.current) return;

      // Defense-in-depth: Skip render if code is clearly incomplete
      // This prevents error flashing if upstream streaming detection fails
      const trimmedCode = code?.trim() ?? "";
      if (!trimmedCode || trimmedCode.length < 10) {
        // Code too short to be valid mermaid - likely still streaming
        return;
      }

      // Ensure mermaid is initialized (supports lazy loading)
      ensureMermaidInitialized();

      try {
        const id = `mermaid-${uniqueId.replace(/:/g, "-")}`;
        const { svg: renderedSvg } = await mermaid.render(id, code);
        setSvg(renderedSvg);
        setError(null);
      } catch (err) {
        // Code that reaches this point has passed the length check (>= 10 chars)
        // so it should show errors for debugging/user feedback
        console.error("Mermaid rendering error:", err);
        setError(
          err instanceof Error ? err.message : "Failed to render diagram",
        );
      }
    };

    renderDiagram();
  }, [code, uniqueId]);

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

  // Copy source code
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }, [code]);

  // Toggle fullscreen
  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev);
  }, []);

  // Download as PNG
  const handleDownload = useCallback(() => {
    if (!svg) return;

    // Create a canvas to convert SVG to PNG
    const svgElement = document.createElement("div");
    svgElement.innerHTML = svg;
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
      ctx.fillStyle = "#1f2937"; // dark background
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      const pngUrl = canvas.toDataURL("image/png");
      const link = document.createElement("a");
      link.download = "diagram.png";
      link.href = pngUrl;
      link.click();

      URL.revokeObjectURL(url);
    };
    img.src = url;
  }, [svg]);

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
        // Left mouse button
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
      <div className="my-2 p-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg">
        <div className="flex items-center gap-2 text-error-600 dark:text-error-400 mb-2">
          <AlertCircle size={16} />
          <span className="font-medium">Diagram Error</span>
        </div>
        <pre className="text-xs text-error-500 overflow-x-auto">{error}</pre>
        <details className="mt-2">
          <summary className="text-xs text-neutral-500 dark:text-neutral-400 cursor-pointer">
            View source
          </summary>
          <pre className="mt-1 text-xs bg-neutral-100 dark:bg-neutral-800 p-2 rounded overflow-x-auto">
            {code}
          </pre>
        </details>
      </div>
    );
  }

  const containerClasses = isFullscreen
    ? "fixed inset-0 z-50 bg-neutral-900"
    : `my-2 bg-neutral-50 dark:bg-neutral-800 rounded-lg overflow-hidden ${className}`;

  return (
    <div
      data-testid="mermaid-container"
      ref={containerRef}
      className={containerClasses}
      onKeyDown={handleKeyDown}
      tabIndex={0}
    >
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2 p-2 bg-neutral-100 dark:bg-neutral-700 border-b border-neutral-200 dark:border-neutral-700 dark:border-neutral-600">
        {/* Zoom controls */}
        <div className="flex items-center gap-1">
          <Button
            variant="secondary"
            className="p-1.5 rounded hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300"
            type="button"
            onClick={handleZoomOut}
            aria-label="Zoom out"
          >
            <ZoomOut size={16} />
          </Button>
          <span className="text-xs text-neutral-500 dark:text-neutral-400 w-12 text-center">
            {Math.round(zoom * 100)}%
          </span>
          <Button
            variant="secondary"
            className="p-1.5 rounded hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300"
            type="button"
            onClick={handleZoomIn}
            aria-label="Zoom in"
          >
            <ZoomIn size={16} />
          </Button>
          <Button
            variant="secondary"
            className="p-1.5 rounded hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300"
            type="button"
            onClick={handleResetZoom}
            aria-label="Reset zoom"
          >
            <RotateCcw size={16} />
          </Button>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1">
          <Button
            variant="secondary"
            className="p-1.5 rounded hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300"
            type="button"
            onClick={handleCopy}
            aria-label="Copy source"
          >
            {copied ? (
              <Check size={16} className="text-success-500" />
            ) : (
              <Copy size={16} />
            )}
          </Button>
          <Button
            variant="secondary"
            className="p-1.5 rounded hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300"
            type="button"
            onClick={handleDownload}
            aria-label="Download as PNG"
          >
            <Download size={16} />
          </Button>
          <Button
            variant="secondary"
            className="p-1.5 rounded hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300"
            type="button"
            onClick={handleToggleFullscreen}
            aria-label="Toggle fullscreen"
          >
            {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </Button>
        </div>
      </div>
      {/* Diagram viewport */}
      <div
        data-testid="mermaid-viewport"
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
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      </div>
    </div>
  );
}

export default InteractiveMermaidDiagram;
