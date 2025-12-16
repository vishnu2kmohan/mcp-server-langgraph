/**
 * ChatMessages Component
 *
 * Displays the message list with streaming response support.
 * Handles empty state, message rendering, and auto-scroll.
 *
 * Features:
 * - Rich markdown rendering with react-markdown
 * - GitHub Flavored Markdown (tables, strikethrough, task lists)
 * - Native emoji support
 * - Syntax highlighting for code blocks
 * - Source citations for AI responses
 *
 * Extracted from ChatPage for improved modularity.
 */

import { useRef, useEffect, useMemo, useId } from "react";
import {
  MessageSquare,
  RefreshCw,
  ExternalLink,
  Copy,
  Check,
  AlertCircle,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { ConfidenceIndicator } from "./ConfidenceIndicator";
// Rich media artifact components for artifact rendering support
import { InteractiveSVGArtifact } from "../Artifacts/InteractiveSVGArtifact";
import { AudioArtifact } from "../Artifacts/AudioArtifact";
import { VideoArtifact } from "../Artifacts/VideoArtifact";
import { ExecutableArtifact } from "../Artifacts/ExecutableArtifact";
import {
  HallucinationIndicator,
  type HallucinationReport,
} from "./HallucinationIndicator";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { useState, useCallback } from "react";
import mermaid from "mermaid";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import "katex/dist/katex.min.css";

// Initialize mermaid with dark theme support
mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  securityLevel: "loose",
  fontFamily: "ui-monospace, monospace",
});

export interface Source {
  title: string;
  url: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  sources?: Source[];
  /** AI confidence score (0-1) for assistant messages */
  confidence?: number;
  /** Whether this message has been flagged for hallucination */
  isReported?: boolean;
}

export interface ThinkingTrace {
  rawOutput?: string;
  steps?: Array<{ name: string; status: string; duration?: number }>;
  tokens?: { input: number; output: number };
}

export interface ChatMessagesProps {
  messages: Message[];
  isStreaming?: boolean;
  streamingContent?: string;
  isSending?: boolean;
  thinkingTrace?: ThinkingTrace;
  /** Callback when user reports a hallucination */
  onReportHallucination?: (report: HallucinationReport) => void;
}

// Chart color palette
const CHART_COLORS = [
  "#3b82f6", // blue
  "#10b981", // green
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // purple
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#84cc16", // lime
];

/**
 * Interactive Mermaid diagram renderer with controls
 * Renders flowcharts, sequence diagrams, Gantt charts, etc.
 * Features: zoom, pan, fullscreen, copy source, download as PNG
 */
function MermaidDiagram({ code }: { code: string }) {
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

  useEffect(() => {
    const renderDiagram = async () => {
      if (!containerRef.current) return;

      try {
        // Generate unique ID for mermaid
        const id = `mermaid-${uniqueId.replace(/:/g, "-")}`;
        const { svg: renderedSvg } = await mermaid.render(id, code);
        setSvg(renderedSvg);
        setError(null);
      } catch (err) {
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
      ctx.fillStyle = "#1f2937";
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

  if (error) {
    return (
      <div className="my-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400 mb-2">
          <AlertCircle size={16} />
          <span className="font-medium">Diagram Error</span>
        </div>
        <pre className="text-xs text-red-500 overflow-x-auto">{error}</pre>
        <details className="mt-2">
          <summary className="text-xs text-gray-500 cursor-pointer">
            View source
          </summary>
          <pre className="mt-1 text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded overflow-x-auto">
            {code}
          </pre>
        </details>
      </div>
    );
  }

  const containerClasses = isFullscreen
    ? "fixed inset-0 z-50 bg-gray-900"
    : "my-2 bg-gray-50 dark:bg-gray-800 rounded-lg overflow-hidden";

  return (
    <div
      data-testid="mermaid-container"
      ref={containerRef}
      className={containerClasses}
    >
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2 p-2 bg-gray-100 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
        {/* Zoom controls */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handleZoomOut}
            aria-label="Zoom out"
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300"
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
          </button>
          <span className="text-xs text-gray-500 dark:text-gray-400 w-12 text-center">
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            onClick={handleZoomIn}
            aria-label="Zoom in"
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300"
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
          </button>
          <button
            type="button"
            onClick={handleResetZoom}
            aria-label="Reset zoom"
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300"
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
          </button>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handleCopy}
            aria-label="Copy source"
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300"
          >
            {copied ? (
              <Check size={16} className="text-green-500" />
            ) : (
              <Copy size={16} />
            )}
          </button>
          <button
            type="button"
            onClick={handleDownload}
            aria-label="Download as PNG"
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300"
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
          </button>
          <button
            type="button"
            onClick={handleToggleFullscreen}
            aria-label="Toggle fullscreen"
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300"
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
          </button>
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

/**
 * Chart data structure for AI-generated charts
 * Example JSON:
 * {
 *   "type": "bar",
 *   "title": "Sales by Month",
 *   "data": [
 *     { "name": "Jan", "value": 100 },
 *     { "name": "Feb", "value": 150 }
 *   ]
 * }
 */
interface ChartData {
  type: "line" | "bar" | "pie";
  title?: string;
  data: Array<{ name: string; value: number; [key: string]: string | number }>;
  xKey?: string;
  yKey?: string;
}

/**
 * Interactive chart renderer with controls
 * Parses JSON chart data and renders with Recharts
 * Features: chart type toggle, fullscreen, copy data, data table view
 */
function ChartBlock({ code }: { code: string }) {
  const [error, setError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [chartType, setChartType] = useState<"line" | "bar" | "pie">("bar");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showDataTable, setShowDataTable] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    try {
      const parsed = JSON.parse(code) as ChartData;
      if (!parsed.type || !parsed.data || !Array.isArray(parsed.data)) {
        throw new Error("Invalid chart data: missing type or data array");
      }
      setChartData(parsed);
      setChartType(parsed.type);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to parse chart data",
      );
    }
  }, [code]);

  // Copy chart data as JSON
  const handleCopy = useCallback(async () => {
    if (!chartData) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(chartData, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }, [chartData]);

  // Toggle fullscreen
  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev);
  }, []);

  // Toggle data table
  const handleToggleDataTable = useCallback(() => {
    setShowDataTable((prev) => !prev);
  }, []);

  if (error) {
    return (
      <div className="my-2 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
        <div className="flex items-center gap-2 text-yellow-600 dark:text-yellow-400 mb-2">
          <AlertCircle size={16} />
          <span className="font-medium">Chart Error</span>
        </div>
        <pre className="text-xs text-yellow-600 overflow-x-auto">{error}</pre>
      </div>
    );
  }

  if (!chartData) return null;

  const xKey = chartData.xKey || "name";
  const yKey = chartData.yKey || "value";

  const containerClasses = isFullscreen
    ? "fixed inset-0 z-50 bg-gray-900 p-4"
    : "my-4 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700";

  return (
    <div data-testid="chart-container" className={containerClasses}>
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2 mb-3">
        {/* Title */}
        <div className="flex-1">
          {chartData.title && (
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {chartData.title}
            </h4>
          )}
        </div>

        {/* Chart type toggles */}
        <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-700 rounded-lg p-0.5">
          <button
            type="button"
            onClick={() => setChartType("line")}
            aria-label="Line chart"
            className={`p-1.5 rounded ${
              chartType === "line"
                ? "bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400"
                : "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
            }`}
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
            >
              <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
              <polyline points="16 7 22 7 22 13" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => setChartType("bar")}
            aria-label="Bar chart"
            className={`p-1.5 rounded ${
              chartType === "bar"
                ? "bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400"
                : "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
            }`}
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
            >
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => setChartType("pie")}
            aria-label="Pie chart"
            className={`p-1.5 rounded ${
              chartType === "pie"
                ? "bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400"
                : "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
            }`}
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
            >
              <path d="M21.21 15.89A10 10 0 1 1 8 2.83" />
              <path d="M22 12A10 10 0 0 0 12 2v10z" />
            </svg>
          </button>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handleToggleDataTable}
            aria-label="Toggle data table"
            className={`p-1.5 rounded ${
              showDataTable
                ? "bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400"
                : "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
            }`}
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
            >
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="3" y1="9" x2="21" y2="9" />
              <line x1="3" y1="15" x2="21" y2="15" />
              <line x1="9" y1="3" x2="9" y2="21" />
              <line x1="15" y1="3" x2="15" y2="21" />
            </svg>
          </button>
          <button
            type="button"
            onClick={handleCopy}
            aria-label="Copy data"
            className="p-1.5 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            {copied ? (
              <Check size={14} className="text-green-500" />
            ) : (
              <Copy size={14} />
            )}
          </button>
          <button
            type="button"
            onClick={handleToggleFullscreen}
            aria-label="Toggle fullscreen"
            className="p-1.5 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            {isFullscreen ? (
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
              >
                <polyline points="4 14 10 14 10 20" />
                <polyline points="20 10 14 10 14 4" />
                <line x1="14" y1="10" x2="21" y2="3" />
                <line x1="3" y1="21" x2="10" y2="14" />
              </svg>
            ) : (
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
              >
                <polyline points="15 3 21 3 21 9" />
                <polyline points="9 21 3 21 3 15" />
                <line x1="21" y1="3" x2="14" y2="10" />
                <line x1="3" y1="21" x2="10" y2="14" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className={isFullscreen ? "h-[calc(100vh-200px)]" : "h-64"}>
        <ResponsiveContainer width="100%" height="100%">
          {chartType === "line" ? (
            <LineChart data={chartData.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey={xKey} stroke="#9ca3af" fontSize={12} />
              <YAxis stroke="#9ca3af" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey={yKey}
                stroke={CHART_COLORS[0]}
                strokeWidth={2}
                dot={{ fill: CHART_COLORS[0] }}
              />
            </LineChart>
          ) : chartType === "bar" ? (
            <BarChart data={chartData.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey={xKey} stroke="#9ca3af" fontSize={12} />
              <YAxis stroke="#9ca3af" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                }}
              />
              <Legend />
              <Bar
                dataKey={yKey}
                fill={CHART_COLORS[0]}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          ) : (
            <PieChart>
              <Pie
                data={chartData.data}
                dataKey={yKey}
                nameKey={xKey}
                cx="50%"
                cy="50%"
                outerRadius={isFullscreen ? 200 : 80}
                label={(props) =>
                  `${props.name ?? "Unknown"}: ${((props.percent ?? 0) * 100).toFixed(0)}%`
                }
              >
                {chartData.data.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={CHART_COLORS[index % CHART_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                }}
              />
              <Legend />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Data Table */}
      {showDataTable && (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-sm" role="table">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="px-4 py-2 text-left font-medium text-gray-700 dark:text-gray-300">
                  {xKey}
                </th>
                <th className="px-4 py-2 text-right font-medium text-gray-700 dark:text-gray-300">
                  {yKey}
                </th>
              </tr>
            </thead>
            <tbody>
              {chartData.data.map((row, index) => (
                <tr
                  key={index}
                  className="border-b border-gray-100 dark:border-gray-800"
                >
                  <td className="px-4 py-2 text-gray-600 dark:text-gray-400">
                    {String(row[xKey])}
                  </td>
                  <td className="px-4 py-2 text-right text-gray-600 dark:text-gray-400">
                    {String(row[yKey])}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/**
 * Code block component with syntax highlighting and copy-to-clipboard
 */
function CodeBlock({
  language,
  children,
}: {
  language?: string;
  children: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [children]);

  return (
    <div className="relative group my-2">
      <div className="absolute right-2 top-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={handleCopy}
          className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 hover:text-white transition-colors"
          title="Copy code"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
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

/**
 * Markdown renderer with custom components
 */
function MarkdownContent({ content }: { content: string }) {
  const components = useMemo(
    () => ({
      // Code blocks with syntax highlighting and special renderers
      code: ({
        inline,
        className,
        children,
        ...props
      }: {
        inline?: boolean;
        className?: string;
        children?: React.ReactNode;
      } & React.HTMLAttributes<HTMLElement>) => {
        const match = /language-(\w+)/.exec(className || "");
        const language = match ? match[1] : undefined;
        const codeContent = String(children).replace(/\n$/, "");

        // Handle mermaid diagrams
        if (language === "mermaid" && !inline) {
          return <MermaidDiagram code={codeContent} />;
        }

        // Handle chart blocks
        if (language === "chart" && !inline) {
          return <ChartBlock code={codeContent} />;
        }

        // Handle SVG blocks with interactive controls
        if (language === "svg" && !inline) {
          return <InteractiveSVGArtifact data={codeContent} />;
        }

        // Handle audio blocks (URL or base64)
        if (language === "audio" && !inline) {
          return <AudioArtifact data={codeContent.trim()} />;
        }

        // Handle video blocks (URL or base64)
        if (language === "video" && !inline) {
          return <VideoArtifact data={codeContent.trim()} />;
        }

        // Handle executable code blocks (run:python, run:javascript, etc.)
        if (language?.startsWith("run:") && !inline) {
          const execLanguage = language.replace("run:", "");
          return (
            <ExecutableArtifact
              data={codeContent}
              config={{ language: execLanguage, runtime: "docker" }}
            />
          );
        }

        if (!inline && codeContent.includes("\n")) {
          return <CodeBlock language={language}>{codeContent}</CodeBlock>;
        }

        return (
          <code
            className="bg-gray-200 dark:bg-gray-700 px-1.5 py-0.5 rounded text-sm font-mono text-pink-600 dark:text-pink-400"
            {...props}
          >
            {children}
          </code>
        );
      },
      // Links open in new tab
      a: ({
        href,
        children,
        ...props
      }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 dark:text-blue-400 hover:underline"
          {...props}
        >
          {children}
        </a>
      ),
      // Paragraphs with proper spacing
      p: ({
        children,
        ...props
      }: React.HTMLAttributes<HTMLParagraphElement>) => (
        <p className="mb-2 last:mb-0" {...props}>
          {children}
        </p>
      ),
      // Lists with proper styling
      ul: ({ children, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
        <ul className="list-disc list-inside mb-2 space-y-1" {...props}>
          {children}
        </ul>
      ),
      ol: ({
        children,
        ...props
      }: React.OlHTMLAttributes<HTMLOListElement>) => (
        <ol className="list-decimal list-inside mb-2 space-y-1" {...props}>
          {children}
        </ol>
      ),
      // Headers with proper sizing
      h1: ({
        children,
        ...props
      }: React.HTMLAttributes<HTMLHeadingElement>) => (
        <h1 className="text-xl font-bold mb-2 mt-4 first:mt-0" {...props}>
          {children}
        </h1>
      ),
      h2: ({
        children,
        ...props
      }: React.HTMLAttributes<HTMLHeadingElement>) => (
        <h2 className="text-lg font-bold mb-2 mt-3 first:mt-0" {...props}>
          {children}
        </h2>
      ),
      h3: ({
        children,
        ...props
      }: React.HTMLAttributes<HTMLHeadingElement>) => (
        <h3 className="text-base font-bold mb-1 mt-2 first:mt-0" {...props}>
          {children}
        </h3>
      ),
      // Blockquotes
      blockquote: ({
        children,
        ...props
      }: React.BlockquoteHTMLAttributes<HTMLQuoteElement>) => (
        <blockquote
          className="border-l-4 border-gray-300 dark:border-gray-600 pl-4 italic text-gray-600 dark:text-gray-400 my-2"
          {...props}
        >
          {children}
        </blockquote>
      ),
      // Tables with GFM support
      table: ({
        children,
        ...props
      }: React.TableHTMLAttributes<HTMLTableElement>) => (
        <div className="overflow-x-auto my-2">
          <table
            className="min-w-full border-collapse border border-gray-300 dark:border-gray-600"
            {...props}
          >
            {children}
          </table>
        </div>
      ),
      th: ({
        children,
        ...props
      }: React.ThHTMLAttributes<HTMLTableHeaderCellElement>) => (
        <th
          className="border border-gray-300 dark:border-gray-600 px-3 py-2 bg-gray-100 dark:bg-gray-700 font-semibold text-left"
          {...props}
        >
          {children}
        </th>
      ),
      td: ({
        children,
        ...props
      }: React.TdHTMLAttributes<HTMLTableDataCellElement>) => (
        <td
          className="border border-gray-300 dark:border-gray-600 px-3 py-2"
          {...props}
        >
          {children}
        </td>
      ),
      // Horizontal rule
      hr: (props: React.HTMLAttributes<HTMLHRElement>) => (
        <hr className="my-4 border-gray-300 dark:border-gray-600" {...props} />
      ),
    }),
    [],
  );

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={components}
    >
      {content}
    </ReactMarkdown>
  );
}

export function ChatMessages({
  messages,
  isStreaming = false,
  streamingContent = "",
  isSending = false,
  thinkingTrace,
  onReportHallucination,
}: ChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showThinkingTrace, setShowThinkingTrace] = useState(false);

  // Auto-scroll to bottom when messages or streaming content change
  useEffect(() => {
    // Guard against scrollIntoView not being available (e.g., in jsdom tests)
    if (
      messagesEndRef.current &&
      typeof messagesEndRef.current.scrollIntoView === "function"
    ) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, streamingContent]);

  if (messages.length === 0 && !isStreaming && !isSending) {
    return (
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
          <MessageSquare size={48} className="mb-4 opacity-50" />
          <p>No messages yet. Start a conversation!</p>
        </div>
        <div ref={messagesEndRef} data-testid="messages-end" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[70%] px-4 py-3 rounded-lg ${
              message.role === "user"
                ? "bg-blue-600 text-white"
                : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100"
            }`}
          >
            {/* Rich markdown rendering for all messages */}
            <div
              className={`prose prose-sm dark:prose-invert max-w-none ${
                message.role === "user" ? "prose-invert" : ""
              }`}
            >
              <MarkdownContent content={message.content} />
            </div>
            {/* Source Citations - only for assistant messages with sources */}
            {message.role === "assistant" &&
              message.sources &&
              message.sources.length > 0 && (
                <div className="mt-3 pt-2 border-t border-gray-200 dark:border-gray-600">
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Sources:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {message.sources.map((source, index) => (
                      <a
                        key={index}
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        <ExternalLink size={10} />
                        {source.title}
                      </a>
                    ))}
                  </div>
                </div>
              )}
            {/* AI-specific indicators for assistant messages */}
            {message.role === "assistant" && (
              <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700 flex items-center gap-3 flex-wrap">
                {/* Confidence indicator */}
                {message.confidence !== undefined && (
                  <ConfidenceIndicator score={message.confidence} />
                )}

                {/* Hallucination report button */}
                {onReportHallucination && (
                  <HallucinationIndicator
                    messageId={message.id}
                    onReport={onReportHallucination}
                    isReported={message.isReported}
                  />
                )}
              </div>
            )}

            <p
              className={`text-xs mt-1 ${
                message.role === "user" ? "text-blue-200" : "text-gray-400"
              }`}
            >
              {new Date(message.timestamp).toLocaleTimeString()}
            </p>
          </div>
        </div>
      ))}

      {/* Streaming response with markdown rendering */}
      {isStreaming && (
        <div className="flex justify-start">
          <div className="max-w-[70%] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 rounded-lg text-gray-900 dark:text-gray-100">
            {streamingContent ? (
              <div className="relative prose prose-sm dark:prose-invert max-w-none">
                <MarkdownContent content={streamingContent} />
                <span className="inline-block w-2 h-4 ml-1 bg-blue-500 animate-pulse align-middle" />
              </div>
            ) : (
              <div className="space-y-2">
                {/* Clickable thinking indicator */}
                <button
                  onClick={() => setShowThinkingTrace(!showThinkingTrace)}
                  className="flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                  aria-expanded={showThinkingTrace}
                  aria-label="Toggle thinking trace"
                >
                  <RefreshCw size={16} className="animate-spin" />
                  <span>Thinking...</span>
                  <span className="text-xs text-blue-500 hover:text-blue-600">
                    {showThinkingTrace ? "Hide trace" : "Show trace"}
                  </span>
                </button>

                {/* Thinking trace panel */}
                {showThinkingTrace && thinkingTrace && (
                  <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 text-xs font-mono">
                    {/* Steps visualization */}
                    {thinkingTrace.steps && thinkingTrace.steps.length > 0 && (
                      <div className="mb-2">
                        <p className="text-gray-500 dark:text-gray-400 mb-1 font-sans text-xs font-semibold">
                          Execution Steps:
                        </p>
                        <ul className="space-y-1">
                          {thinkingTrace.steps.map((step, i) => (
                            <li key={i} className="flex items-center gap-2">
                              <span
                                className={`w-2 h-2 rounded-full ${
                                  step.status === "completed"
                                    ? "bg-green-500"
                                    : step.status === "running"
                                      ? "bg-blue-500 animate-pulse"
                                      : "bg-gray-400"
                                }`}
                              />
                              <span className="text-gray-700 dark:text-gray-300">
                                {step.name}
                              </span>
                              {step.duration && (
                                <span className="text-gray-400">
                                  ({step.duration}ms)
                                </span>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Token usage */}
                    {thinkingTrace.tokens && (
                      <div className="mb-2 flex gap-4 text-gray-500 dark:text-gray-400">
                        <span>Input: {thinkingTrace.tokens.input} tokens</span>
                        <span>
                          Output: {thinkingTrace.tokens.output} tokens
                        </span>
                      </div>
                    )}

                    {/* Raw output */}
                    {thinkingTrace.rawOutput && (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 font-sans">
                          Raw Output
                        </summary>
                        <pre className="mt-1 p-2 bg-gray-100 dark:bg-gray-800 rounded overflow-x-auto max-h-48 overflow-y-auto text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
                          {thinkingTrace.rawOutput}
                        </pre>
                      </details>
                    )}

                    {/* Fallback when no trace data */}
                    {!thinkingTrace.steps &&
                      !thinkingTrace.tokens &&
                      !thinkingTrace.rawOutput && (
                        <p className="text-gray-400 italic font-sans">
                          Processing... trace data will appear here.
                        </p>
                      )}
                  </div>
                )}

                {/* Placeholder when trace toggle is on but no data */}
                {showThinkingTrace && !thinkingTrace && (
                  <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 text-xs">
                    <p className="text-gray-400 italic">
                      Trace data not available. Enable verbose mode in settings
                      to see execution details.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Legacy sending indicator (fallback) */}
      {isSending && !isStreaming && (
        <div className="flex justify-start">
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 rounded-lg">
            <button
              onClick={() => setShowThinkingTrace(!showThinkingTrace)}
              className="flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
              aria-expanded={showThinkingTrace}
            >
              <RefreshCw size={16} className="animate-spin" />
              <span>Thinking...</span>
              <span className="text-xs text-blue-500 hover:text-blue-600">
                {showThinkingTrace ? "Hide trace" : "Show trace"}
              </span>
            </button>
            {showThinkingTrace && (
              <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 text-xs text-gray-400 italic">
                Waiting for trace data...
              </div>
            )}
          </div>
        </div>
      )}

      <div ref={messagesEndRef} data-testid="messages-end" />
    </div>
  );
}
