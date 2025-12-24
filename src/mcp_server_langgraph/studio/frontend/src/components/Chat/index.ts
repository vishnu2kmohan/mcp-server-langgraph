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
// Workspace Layout - REMOVED
// ChatWorkspace was deprecated (AppShell architecture) and removed.
// StudioShellLayout provides the 3-panel canvas layout for chat.
// =============================================================================

// =============================================================================
// Dockable Document Components (for MainDock integration)
// =============================================================================

export { ChatDocument } from "./ChatDocument";
export type { ChatDocumentProps } from "./ChatDocument";

// =============================================================================
// AI Assistance Components
// =============================================================================

export { AIFollowUpSuggestions } from "./AIFollowUpSuggestions";
export type {
  AIFollowUpSuggestionsProps,
  FollowUpSuggestion,
  SuggestionCategory,
} from "./AIFollowUpSuggestions";

// =============================================================================
// Session Management Components
// =============================================================================

export { ExportButton } from "./ExportButton";
export type { ExportButtonProps } from "./ExportButton";

export { ChatHeader } from "./ChatHeader";
export type { ChatHeaderProps, ConnectionMode } from "./ChatHeader";

// =============================================================================
// Agent Execution Trace Components
// =============================================================================

export { AgentExecutionTracePanel } from "./AgentExecutionTracePanel";
export type { AgentExecutionTracePanelProps } from "./AgentExecutionTracePanel";

export { AgentTraceToggleButton } from "./AgentTraceToggleButton";
export type { AgentTraceToggleButtonProps } from "./AgentTraceToggleButton";
