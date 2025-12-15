/**
 * Artifacts Components
 *
 * Export all artifact rendering components for multi-modal display.
 * Supports charts, tables, code, JSON, and more.
 */

export { CodeArtifact } from "./CodeArtifact";
export type { CodeArtifactProps } from "./CodeArtifact";

export { JSONArtifact } from "./JSONArtifact";
export type { JSONArtifactProps } from "./JSONArtifact";

export { TableArtifact } from "./TableArtifact";
export type { TableArtifactProps, TableColumn } from "./TableArtifact";

export { ChartArtifact } from "./ChartArtifact";
export type {
  ChartArtifactProps,
  ChartDataPoint,
  ChartType,
} from "./ChartArtifact";

export { LaTeXArtifact } from "./LaTeXArtifact";
export type { LaTeXArtifactProps } from "./LaTeXArtifact";
