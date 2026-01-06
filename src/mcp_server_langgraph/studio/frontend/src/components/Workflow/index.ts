/**
 * Workflow Components
 *
 * Decomposed components from Builder App.tsx for the visual workflow builder.
 */

// =============================================================================
// Core Layout Components
// =============================================================================

export { WorkflowHeader } from "./WorkflowHeader";
export type { WorkflowHeaderProps } from "./WorkflowHeader";

export { WorkflowDocument } from "./WorkflowDocument";
export type { WorkflowDocumentProps } from "./WorkflowDocument";

export { WorkflowCanvas } from "./WorkflowCanvas";
export type { WorkflowCanvasProps } from "./WorkflowCanvas";

export { WorkflowEditor } from "./WorkflowEditor";
export type { WorkflowEditorProps } from "./WorkflowEditor";

export { WorkflowMiniView } from "./WorkflowMiniView";
export type { WorkflowMiniViewProps } from "./WorkflowMiniView";

// =============================================================================
// Node & Palette Components
// =============================================================================

export { NodePalette } from "./NodePalette";
export type { NodePaletteProps, NodeType } from "./NodePalette";

export { NodeInspector } from "./NodeInspector";

export { CodePanel } from "./CodePanel";
export type { CodePanelProps } from "./CodePanel";

// =============================================================================
// Execution & Trace Components
// =============================================================================

export { ExecutionTracePanel } from "./ExecutionTracePanel";

export { ExecutionPanel } from "./ExecutionPanel";

export { ExecutionHistoryPanel } from "./ExecutionHistoryPanel";
export type { ExecutionHistoryPanelProps } from "./ExecutionHistoryPanel";

// =============================================================================
// Sharing & Collaboration Components
// =============================================================================

export { ShareWorkflowDialog } from "./ShareWorkflowDialog";
export type { ShareWorkflowDialogProps } from "./ShareWorkflowDialog";

export { SharedWorkflowsList } from "./SharedWorkflowsList";
export type { SharedWorkflowsListProps } from "./SharedWorkflowsList";

// =============================================================================
// Version History & Diff Components
// =============================================================================

export { WorkflowVersionHistory } from "./WorkflowVersionHistory";
export type { WorkflowVersionHistoryProps } from "./WorkflowVersionHistory";

export { WorkflowDiffViewer } from "./WorkflowDiffViewer";
export type { WorkflowDiffViewerProps } from "./WorkflowDiffViewer";

// =============================================================================
// AI Suggestion Components
// =============================================================================

export { SuggestionChips } from "./SuggestionChips";
export type { SuggestionChipsProps } from "./SuggestionChips";
