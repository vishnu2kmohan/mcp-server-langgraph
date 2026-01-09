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
  | "executable"
  | "widget";

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
  /** Human-friendly display name (editable in UI) */
  title?: string;
  /** Machine-friendly programmatic identifier (for code/API references) */
  name?: string;
  /** Description explaining the artifact purpose or context */
  description?: string;
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

// =============================================================================
// Widget Artifact Types (Sprint 4 - GenUI Integration)
// =============================================================================

/**
 * Widget chart data - bar chart with labels and values
 * Must match GenerativeWidget.tsx ChartData interface
 */
export interface WidgetChartData {
  labels: string[];
  values: number[];
}

/**
 * Widget table data - columns and rows
 * Must match GenerativeWidget.tsx TableData interface
 */
export interface WidgetTableData {
  columns: string[];
  rows: string[][];
}

/**
 * Widget text data - markdown or plain text content
 * Must match GenerativeWidget.tsx TextData interface
 */
export interface WidgetTextData {
  content: string;
}

/**
 * Widget type discriminator
 */
export type WidgetType = "chart" | "table" | "text";

/**
 * Widget configuration matching GenerativeWidget.tsx WidgetConfig
 */
export interface WidgetConfig {
  id: string;
  title: string;
  data: WidgetChartData | WidgetTableData | WidgetTextData;
}

/**
 * Widget artifact for GenerativeWidget rendering in chat
 * Used for AI-generated dynamic UI widgets
 */
export interface WidgetArtifact extends BaseArtifact {
  type: "widget";
  widgetType: WidgetType;
  config: WidgetConfig;
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
  | ExecutableArtifact
  | WidgetArtifact;

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

// =============================================================================
// Canvas Artifact Types (Phase 0 - Studio Canvas Support)
// =============================================================================

/**
 * Canvas artifact - extends base with session association and versioning
 * Used in StudioShell Canvas Panel for Gemini/ChatGPT-style editing
 */
export interface CanvasArtifact extends BaseArtifact {
  /** Session this artifact belongs to */
  sessionId: string;
  /** Current version number (1-indexed) */
  version: number;
  /** Content of the artifact */
  content: string;
  /** Content type for Canvas rendering */
  contentType: "code" | "markdown" | "json" | "jsx" | "mermaid" | "html";
  /** Creation timestamp (ISO 8601) */
  createdAt: string;
  /** Last update timestamp (ISO 8601) */
  updatedAt: string;
  /** Edit metadata */
  editMetadata?: {
    /** Who made the edit */
    editedBy: "user" | "ai-suggestion" | "ai-generation";
    /** AI confidence score (0-1) if AI-edited */
    aiConfidence?: number;
    /** Language for code artifacts */
    language?: string;
  };
}

/**
 * Artifact version for version history
 */
export interface ArtifactVersion {
  id: string;
  artifactId: string;
  version: number;
  content: string;
  contentType: CanvasArtifact["contentType"];
  createdBy: string;
  createdAt: string;
  parentVersion?: number;
  metadata: {
    editType: "user" | "ai-suggestion" | "ai-generation";
    aiConfidence?: number;
  };
}

// =============================================================================
// API Types for /api/v1/artifacts (Phase 2 - MSW-first development)
// =============================================================================

/**
 * Request to create a new artifact
 */
export interface CreateArtifactRequest {
  type: CanvasArtifact["contentType"];
  content: string;
  sessionId: string;
  title?: string;
  /** Description explaining the artifact purpose or context */
  description?: string;
  language?: string;
}

/**
 * Response from creating an artifact
 */
export interface CreateArtifactResponse {
  id: string;
  version: number;
  createdAt: string;
}

/**
 * Request to list artifacts for a session
 */
export interface ListArtifactsParams {
  session_id: string;
  cursor?: string;
  limit?: number;
}

/**
 * Response from listing artifacts
 */
export interface ListArtifactsResponse {
  items: CanvasArtifact[];
  cursor: string | null;
  hasMore: boolean;
}

/**
 * Request to update an artifact
 */
export interface UpdateArtifactRequest {
  content?: string;
  /** Human-friendly display name */
  title?: string;
  /** Machine-friendly programmatic identifier */
  name?: string;
  /** Description explaining the artifact purpose or context */
  description?: string;
  editedBy?: "user" | "ai-suggestion" | "ai-generation";
  aiConfidence?: number;
}

/**
 * Response from updating an artifact
 */
export interface UpdateArtifactResponse {
  id: string;
  version: number;
  updatedAt: string;
}

/**
 * Request to fork an artifact
 *
 * NOTE: Uses snake_case `new_name` to match backend ArtifactForkRequest schema
 */
export interface ForkArtifactRequest {
  new_name?: string;
}

/**
 * Response from forking an artifact
 */
export interface ForkArtifactResponse {
  id: string;
  parentId: string;
  version: number;
}
