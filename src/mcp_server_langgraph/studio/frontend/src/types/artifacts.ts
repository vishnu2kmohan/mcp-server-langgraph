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
  | "text";

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
 * Union type of all artifacts
 */
export type Artifact =
  | ChartArtifact
  | TableArtifact
  | CodeArtifact
  | MermaidArtifact
  | JSONArtifact
  | ImageArtifact
  | TextArtifact;

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
