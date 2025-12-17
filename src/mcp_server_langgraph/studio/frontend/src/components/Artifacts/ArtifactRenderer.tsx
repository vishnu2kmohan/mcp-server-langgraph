/**
 * ArtifactRenderer Component
 *
 * Universal artifact renderer with auto-detection.
 * Automatically detects the type of content and renders
 * the appropriate artifact component.
 *
 * Features:
 * - Auto-detect artifact type from raw data
 * - Render specific component based on type
 * - Fallback to text for unknown types
 */

// Allow exporting helper function alongside component - intentional for reusability
/* eslint-disable react-refresh/only-export-components */

import type {
  Artifact,
  ArtifactType,
  ArtifactDetectionResult,
  ChartArtifact as ChartArtifactType,
  TableArtifact as TableArtifactType,
  CodeArtifact as CodeArtifactType,
  MermaidArtifact as MermaidArtifactType,
  JSONArtifact as JSONArtifactType,
  ImageArtifact as ImageArtifactType,
  TextArtifact as TextArtifactType,
  SVGArtifact as SVGArtifactType,
  ExecutableArtifact as ExecutableArtifactType,
} from "../../types/artifacts";
import { ChartArtifact } from "./ChartArtifact";
import { TableArtifact } from "./TableArtifact";
import { CodeArtifact } from "./CodeArtifact";
import { JSONArtifact } from "./JSONArtifact";
import { MermaidArtifact } from "./MermaidArtifact";
import { InteractiveSVGArtifact } from "./InteractiveSVGArtifact";
import { SandpackExecutor } from "./SandpackExecutor";

export interface ArtifactRendererProps {
  artifact?: Artifact;
  data?: unknown;
  autoDetect?: boolean;
  typeHint?: ArtifactType;
  className?: string;
}

/**
 * Mermaid diagram type patterns
 */
const MERMAID_PATTERNS = [
  /^graph\s+(TD|TB|BT|RL|LR)/m,
  /^flowchart\s+(TD|TB|BT|RL|LR)/m,
  /^sequenceDiagram/m,
  /^classDiagram/m,
  /^stateDiagram/m,
  /^erDiagram/m,
  /^journey/m,
  /^gantt/m,
  /^pie/m,
  /^mindmap/m,
  /^timeline/m,
  /^gitGraph/m,
];

/**
 * Code detection patterns
 */
const CODE_PATTERNS = [
  /^```\w*\n/m, // Markdown code block
  /^(function|const|let|var|class|import|export|async|await)\s+\w+/m, // JS/TS
  /^def\s+\w+\s*\(/m, // Python
  /^(public|private|protected|class|interface)\s+\w+/m, // Java/C#
  /^fn\s+\w+/m, // Rust
  /^func\s+\w+/m, // Go
  /^\s*(if|for|while|switch|try|catch)\s*\(/m, // Control structures
];

/**
 * Image URL patterns
 */
const IMAGE_PATTERNS = [
  /^data:image\/(png|jpg|jpeg|gif|webp|svg\+xml);base64,/i,
  /^https?:\/\/.*\.(png|jpg|jpeg|gif|webp|svg)(\?.*)?$/i,
];

/**
 * Detect artifact type from raw data
 */
export function detectArtifactType(
  data: unknown,
  hint?: ArtifactType,
): ArtifactDetectionResult {
  // If hint is provided, use it
  if (hint) {
    return { type: hint, confidence: 1.0, reason: "Type hint provided" };
  }

  // Handle array data
  if (Array.isArray(data)) {
    if (data.length === 0) {
      return { type: "text", confidence: 0.5, reason: "Empty array" };
    }

    // Check if it's an array of objects (could be table or chart)
    const firstItem = data[0];
    if (typeof firstItem === "object" && firstItem !== null) {
      const keys = Object.keys(firstItem);
      const hasValueKey = keys.some(
        (k) => k === "value" || k === "y" || k === "count",
      );
      const hasLabelKey = keys.some(
        (k) => k === "label" || k === "x" || k === "name",
      );

      // If it looks like chart data
      if (hasValueKey && hasLabelKey) {
        return {
          type: "chart",
          confidence: 0.8,
          reason: "Array with label/value structure",
        };
      }

      // Otherwise treat as table
      return { type: "table", confidence: 0.9, reason: "Array of objects" };
    }
  }

  // Handle object data (JSON)
  if (typeof data === "object" && data !== null && !Array.isArray(data)) {
    return { type: "json", confidence: 0.9, reason: "Object data" };
  }

  // Handle string data
  if (typeof data === "string") {
    const trimmed = data.trim();

    // Check for image
    for (const pattern of IMAGE_PATTERNS) {
      if (pattern.test(trimmed)) {
        return {
          type: "image",
          confidence: 0.95,
          reason: "Image URL or data URL",
        };
      }
    }

    // Check for mermaid
    for (const pattern of MERMAID_PATTERNS) {
      if (pattern.test(trimmed)) {
        return {
          type: "mermaid",
          confidence: 0.95,
          reason: "Mermaid diagram syntax",
        };
      }
    }

    // Check for code
    for (const pattern of CODE_PATTERNS) {
      if (pattern.test(trimmed)) {
        return {
          type: "code",
          confidence: 0.8,
          reason: "Code syntax detected",
        };
      }
    }

    // Check for JSON string
    try {
      const parsed = JSON.parse(trimmed);
      if (typeof parsed === "object") {
        return { type: "json", confidence: 0.9, reason: "Valid JSON string" };
      }
    } catch {
      // Not JSON
    }

    // Default to text
    return { type: "text", confidence: 0.5, reason: "Plain text" };
  }

  // Default fallback
  return { type: "text", confidence: 0.3, reason: "Unknown data type" };
}

/**
 * Create artifact from raw data
 */
function createArtifactFromData(
  data: unknown,
  detectedType: ArtifactType,
): Artifact {
  const id = `auto-${Date.now()}`;

  switch (detectedType) {
    case "json":
      return {
        id,
        type: "json",
        data: typeof data === "string" ? JSON.parse(data) : data,
      } as JSONArtifactType;

    case "mermaid":
      return {
        id,
        type: "mermaid",
        data: data as string,
      } as MermaidArtifactType;

    case "code":
      return {
        id,
        type: "code",
        data: data as string,
        config: { language: "auto" },
      } as CodeArtifactType;

    case "table":
      return {
        id,
        type: "table",
        data: data as Array<Record<string, unknown>>,
        config: {
          columns: Object.keys(
            (data as Array<Record<string, unknown>>)[0] || {},
          ).map((key) => ({
            id: key,
            header: key.charAt(0).toUpperCase() + key.slice(1),
          })),
        },
      } as TableArtifactType;

    case "chart":
      return {
        id,
        type: "chart",
        data: data as Array<Record<string, unknown>>,
        config: { chartType: "bar" },
      } as ChartArtifactType;

    case "image":
      return {
        id,
        type: "image",
        data: data as string,
      } as ImageArtifactType;

    default:
      return {
        id,
        type: "text",
        data: String(data),
      } as TextArtifactType;
  }
}

export function ArtifactRenderer({
  artifact,
  data,
  autoDetect = false,
  typeHint,
  className = "",
}: ArtifactRendererProps) {
  // Determine the artifact to render
  let artifactToRender: Artifact | undefined = artifact;

  if (!artifactToRender && data !== undefined && autoDetect) {
    const detection = detectArtifactType(data, typeHint);
    artifactToRender = createArtifactFromData(data, detection.type);
  }

  if (!artifactToRender) {
    return null;
  }

  // Render based on type
  switch (artifactToRender.type) {
    case "json":
      return (
        <div data-testid="artifact-json" className={className}>
          <JSONArtifact artifact={artifactToRender as JSONArtifactType} />
        </div>
      );

    case "mermaid":
      return (
        <div className={className}>
          <MermaidArtifact
            code={(artifactToRender as MermaidArtifactType).data}
            title={artifactToRender.title}
            theme={(artifactToRender as MermaidArtifactType).config?.theme}
            expandable
          />
        </div>
      );

    case "code":
      return (
        <div data-testid="artifact-code" className={className}>
          <CodeArtifact artifact={artifactToRender as CodeArtifactType} />
        </div>
      );

    case "table": {
      const tableData = artifactToRender as TableArtifactType;
      // Transform TableColumn from artifacts.ts format to TableArtifact component format
      const transformedColumns = tableData.config.columns.map((col) => ({
        key: col.accessorKey || col.id,
        label: col.header,
        sortable: col.sortable,
        type: col.type === "boolean" ? ("string" as const) : col.type,
      }));
      return (
        <div data-testid="artifact-table" className={className}>
          <TableArtifact
            data={tableData.data}
            columns={transformedColumns}
            title={artifactToRender.title || "Table"}
          />
        </div>
      );
    }

    case "chart": {
      const chartData = artifactToRender as ChartArtifactType;
      return (
        <div data-testid="artifact-chart" className={className}>
          <ChartArtifact
            title={artifactToRender.title || "Chart"}
            type={chartData.config.chartType as "bar" | "line" | "pie"}
            data={chartData.data.map((d) => ({
              label: String(d.label || d.name || d.x || ""),
              value: Number(d.value || d.y || d.count || 0),
            }))}
          />
        </div>
      );
    }

    case "image":
      return (
        <div data-testid="artifact-image" className={className}>
          <img
            src={(artifactToRender as ImageArtifactType).data}
            alt={
              (artifactToRender as ImageArtifactType).config?.alt ||
              artifactToRender.title ||
              "Image"
            }
            className="max-w-full h-auto rounded-lg"
          />
        </div>
      );

    case "svg": {
      const svgData = artifactToRender as SVGArtifactType;
      return (
        <div data-testid="artifact-svg" className={className}>
          <InteractiveSVGArtifact
            data={svgData.data}
            title={artifactToRender.title}
            config={{
              enableZoom: svgData.config?.enableZoom,
              enablePan: svgData.config?.enablePan,
            }}
          />
        </div>
      );
    }

    case "executable": {
      const execData = artifactToRender as ExecutableArtifactType;
      // Determine if this is MDX (check metadata or language)
      const isMDX =
        execData.metadata?.isMDX || execData.config.language === "mdx";
      const language = execData.config.language as
        | "tsx"
        | "jsx"
        | "javascript"
        | "typescript"
        | "mdx";

      return (
        <div data-testid="artifact-executable" className={className}>
          <SandpackExecutor
            code={execData.data}
            language={isMDX ? "mdx" : language}
            title={artifactToRender.title}
            showRunButton={true}
            autoRun={false}
            theme="dark"
          />
        </div>
      );
    }

    case "text":
    default:
      return (
        <div
          data-testid="artifact-text"
          className={`p-4 bg-gray-50 dark:bg-gray-800 rounded-lg text-gray-700 dark:text-gray-300 whitespace-pre-wrap ${className}`}
        >
          {(artifactToRender as TextArtifactType).data}
        </div>
      );
  }
}

export default ArtifactRenderer;
