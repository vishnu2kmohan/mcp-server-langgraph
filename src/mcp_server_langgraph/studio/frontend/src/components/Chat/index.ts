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
// Workspace Layout (DevTools-style dockable panels)
// =============================================================================

export { ChatWorkspace, usePanelControl } from "./ChatWorkspace";
export type {
  ChatWorkspaceProps,
  UsePanelControlReturn,
} from "./ChatWorkspace";
