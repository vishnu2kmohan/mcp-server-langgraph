/**
 * Chat Components
 *
 * Components for the chat interface integrated from Playground.
 */

export { ChatMessage } from "./ChatMessage";
export type { ChatMessageProps, SourceCitation } from "./ChatMessage";

export { ChatInput } from "./ChatInput";
export type { ChatInputProps } from "./ChatInput";

export { ConfidenceIndicator } from "./ConfidenceIndicator";
export type { ConfidenceIndicatorProps } from "./ConfidenceIndicator";

export { HallucinationIndicator } from "./HallucinationIndicator";
export type {
  HallucinationIndicatorProps,
  HallucinationReport,
  HallucinationCategory,
} from "./HallucinationIndicator";

export { SessionGoalTracker } from "./SessionGoalTracker";
export type {
  SessionGoalTrackerProps,
  GoalSetData,
  GoalResult,
  GoalAchievement,
} from "./SessionGoalTracker";

// =============================================================================
// Interactive Renderers (enhanced media display components)
// =============================================================================

export { InteractiveMermaidDiagram } from "./InteractiveMermaidDiagram";
export type { InteractiveMermaidDiagramProps } from "./InteractiveMermaidDiagram";

export { InteractiveChart } from "./InteractiveChart";
export type { InteractiveChartProps, ChartData } from "./InteractiveChart";

// =============================================================================
// Workspace Layout (DevTools-style dockable panels)
// =============================================================================

export { ChatWorkspace, usePanelControl } from "./ChatWorkspace";
export type {
  ChatWorkspaceProps,
  UsePanelControlReturn,
} from "./ChatWorkspace";

// =============================================================================
// Dockable Document Components (for MainDock integration)
// =============================================================================

export { ChatDocument } from "./ChatDocument";
export type { ChatDocumentProps } from "./ChatDocument";
