/**
 * Artifact Type Definitions
 *
 * Types for multi-modal artifacts including charts, tables, code blocks,
 * diagrams, and JSON visualization.
 */

/**
 * Supported artifact types
 */
export type ArtifactType =
  | "chart"
  | "table"
  | "code"
  | "mermaid"
  | "json"
  | "image"
  | "text"
  | "svg"
  | "audio"
  | "video"
  | "executable";

/**
 * Chart types for ChartArtifact
 */
export type ChartType = "line" | "bar" | "pie" | "area" | "scatter";

/**
 * Base artifact interface
 */
export interface BaseArtifact {
  id: string;
  type: ArtifactType;
  title?: string;
  metadata?: Record<string, unknown>;
  timestamp?: number;
}

/**
 * Chart artifact configuration
 */
export interface ChartConfig {
  chartType: ChartType;
  xAxisKey?: string;
  yAxisKey?: string;
  showLegend?: boolean;
  showTooltip?: boolean;
  showGrid?: boolean;
  colors?: string[];
  width?: number | string;
  height?: number | string;
}

/**
 * Chart artifact data point
 */
export interface ChartDataPoint {
  [key: string]: string | number | boolean | null;
}

/**
 * Chart artifact
 */
export interface ChartArtifact extends BaseArtifact {
  type: "chart";
  data: ChartDataPoint[];
  config: ChartConfig;
}

/**
 * Table column definition
 */
export interface TableColumn {
  id: string;
  header: string;
  accessorKey?: string;
  type?: "string" | "number" | "boolean" | "date";
  sortable?: boolean;
  filterable?: boolean;
  width?: number | string;
}

/**
 * Table artifact configuration
 */
export interface TableConfig {
  columns: TableColumn[];
  pageSize?: number;
  enableSorting?: boolean;
  enableFiltering?: boolean;
  enablePagination?: boolean;
  enableExport?: boolean;
}

/**
 * Table artifact data row
 */
export interface TableDataRow {
  [key: string]: string | number | boolean | null | undefined;
}

/**
 * Table artifact
 */
export interface TableArtifact extends BaseArtifact {
  type: "table";
  data: TableDataRow[];
  config: TableConfig;
}

/**
 * Code artifact configuration
 */
export interface CodeConfig {
  language: string;
  showLineNumbers?: boolean;
  highlightLines?: number[];
  theme?: "light" | "dark";
  maxHeight?: number;
  wrapLines?: boolean;
}

/**
 * Code artifact
 */
export interface CodeArtifact extends BaseArtifact {
  type: "code";
  data: string;
  config: CodeConfig;
}

/**
 * Mermaid artifact configuration
 */
export interface MermaidConfig {
  theme?: "default" | "forest" | "dark" | "neutral";
  enableZoom?: boolean;
  enablePan?: boolean;
  maxWidth?: number | string;
}

/**
 * Mermaid artifact (diagrams)
 */
export interface MermaidArtifact extends BaseArtifact {
  type: "mermaid";
  data: string;
  config?: MermaidConfig;
}

/**
 * JSON artifact configuration
 */
export interface JSONConfig {
  collapsed?: boolean | number;
  enableSearch?: boolean;
  enableCopy?: boolean;
  theme?: "light" | "dark";
  maxHeight?: number;
}

/**
 * JSON artifact
 */
export interface JSONArtifact extends BaseArtifact {
  type: "json";
  data: unknown;
  config?: JSONConfig;
}

/**
 * Image artifact configuration
 */
export interface ImageConfig {
  alt?: string;
  width?: number | string;
  height?: number | string;
  fit?: "contain" | "cover" | "fill" | "none" | "scale-down";
}

/**
 * Image artifact
 */
export interface ImageArtifact extends BaseArtifact {
  type: "image";
  data: string; // URL or base64
  config?: ImageConfig;
}

/**
 * Text artifact (fallback for plain text)
 */
export interface TextArtifact extends BaseArtifact {
  type: "text";
  data: string;
}

/**
 * SVG artifact configuration
 */
export interface SVGConfig {
  width?: number | string;
  height?: number | string;
  preserveAspectRatio?: string;
  enableZoom?: boolean;
  enablePan?: boolean;
}

/**
 * SVG artifact (inline vector graphics)
 */
export interface SVGArtifact extends BaseArtifact {
  type: "svg";
  data: string; // SVG markup or data URL
  config?: SVGConfig;
}

/**
 * Audio artifact configuration
 */
export interface AudioConfig {
  autoplay?: boolean;
  loop?: boolean;
  muted?: boolean;
  controls?: boolean;
  preload?: "none" | "metadata" | "auto";
}

/**
 * Audio artifact
 */
export interface AudioArtifact extends BaseArtifact {
  type: "audio";
  data: string; // URL or base64 data URL
  mimeType?: string; // audio/mpeg, audio/wav, audio/ogg, etc.
  config?: AudioConfig;
}

/**
 * Video artifact configuration
 */
export interface VideoConfig {
  autoplay?: boolean;
  loop?: boolean;
  muted?: boolean;
  controls?: boolean;
  preload?: "none" | "metadata" | "auto";
  width?: number | string;
  height?: number | string;
  poster?: string; // Thumbnail image URL
}

/**
 * Video artifact
 */
export interface VideoArtifact extends BaseArtifact {
  type: "video";
  data: string; // URL or base64 data URL
  mimeType?: string; // video/mp4, video/webm, video/ogg, etc.
  config?: VideoConfig;
}

/**
 * Executable code artifact configuration
 */
export interface ExecutableConfig {
  language: string;
  runtime?: "docker" | "kubernetes" | "webassembly" | "pyodide";
  timeout?: number; // Execution timeout in milliseconds
  showLineNumbers?: boolean;
  theme?: "light" | "dark";
  maxOutputLines?: number;
  enableStdin?: boolean;
}

/**
 * Execution result from sandbox
 */
export interface ExecutionResult {
  stdout: string;
  stderr: string;
  exitCode: number;
  executionTime?: number; // in milliseconds
  error?: string;
}

/**
 * Executable code artifact (sandboxed code execution)
 */
export interface ExecutableArtifact extends BaseArtifact {
  type: "executable";
  data: string; // Source code
  config: ExecutableConfig;
  result?: ExecutionResult;
}

/**
 * Union type of all artifacts
 */
export type Artifact =
  | ChartArtifact
  | TableArtifact
  | CodeArtifact
  | MermaidArtifact
  | JSONArtifact
  | ImageArtifact
  | TextArtifact
  | SVGArtifact
  | AudioArtifact
  | VideoArtifact
  | ExecutableArtifact;

/**
 * Artifact detection result
 */
export interface ArtifactDetectionResult {
  type: ArtifactType;
  confidence: number; // 0-1
  reason?: string;
}

/**
 * File upload result
 */
export interface FileUploadResult {
  file: File;
  url: string;
  type: string;
  size: number;
  error?: string;
}
