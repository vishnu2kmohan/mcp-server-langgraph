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

// =============================================================================
// User Interaction & Feedback Components
// =============================================================================

export { ChatSuggestions } from "./ChatSuggestions";
export type { ChatSuggestionsProps, ChatSuggestion } from "./ChatSuggestions";

export { ResponseRating } from "./ResponseRating";
export type { ResponseRatingProps, RatingValue } from "./ResponseRating";

export { RichTextInput } from "./RichTextInput";
export type { RichTextInputProps, MentionOption } from "./RichTextInput";

export { TokenUsageDisplay } from "./TokenUsageDisplay";
export type {
  TokenUsageDisplayProps,
  ModelProvider,
} from "./TokenUsageDisplay";

// =============================================================================
// Core Chat Components
// =============================================================================

// Legacy export for backward compatibility
export { ChatInputForm } from "./ChatInputForm";
export type { ChatInputFormProps } from "./ChatInputForm";

export { ChatMessages } from "./ChatMessages";
export type {
  ChatMessagesProps,
  Message,
  AgentExecutionTrace,
} from "./ChatMessages";

export { MarkdownContent } from "./MarkdownContent";
export type { MarkdownContentProps } from "./MarkdownContent";

export { MessageActions } from "./MessageActions";
export type { MessageActionsProps } from "./MessageActions";

export { CodeBlock } from "./CodeBlock";
export type { CodeBlockProps } from "./CodeBlock";

// =============================================================================
// LLM Thinking & Visualization Components
// =============================================================================

export { LLMThinkingTrace } from "./LLMThinkingTrace";
export type { LLMThinkingTraceProps } from "./LLMThinkingTrace";

export { LangGraphNodeVisualization } from "./LangGraphNodeVisualization";
export type { LangGraphNodeVisualizationProps } from "./LangGraphNodeVisualization";

export { ReasoningEffortSelector } from "./ReasoningEffortSelector";
export type { ReasoningEffortSelectorProps } from "./ReasoningEffortSelector";

export { PreferencesMenu } from "./PreferencesMenu";
export type { PreferencesMenuProps } from "./PreferencesMenu";

export { ExecutionModeIndicator } from "./ExecutionModeIndicator";
export type { ExecutionModeIndicatorProps } from "./ExecutionModeIndicator";

// =============================================================================
// Command & Template Components
// =============================================================================

export { SlashCommandMenu } from "./SlashCommandMenu";
export type { SlashCommandMenuProps, SlashCommand } from "./SlashCommandMenu";

export { StylePresets } from "./StylePresets";
export type {
  StylePresetsProps,
  StylePreset,
  PresetName,
} from "./StylePresets";

// =============================================================================
// Workflow Integration Components
// =============================================================================

export { SaveAsWorkflowButton } from "./SaveAsWorkflowButton";

// =============================================================================
// Routing Components
// =============================================================================

export { ChatSessionRedirect } from "./ChatSessionRedirect";
