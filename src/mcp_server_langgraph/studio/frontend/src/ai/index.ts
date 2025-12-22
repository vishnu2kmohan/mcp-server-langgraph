/**
 * AI Module Exports
 *
 * Phase 4: AI-Native Features
 * Exports all AI-related components and hooks.
 */

export {
  InlineSuggestions,
  type Suggestion,
  type SuggestionType,
} from "./InlineSuggestions";
export {
  BackgroundAgentPanel,
  type BackgroundAgent,
  type AgentStatus,
  type BackgroundAgentPanelProps,
} from "./BackgroundAgentPanel";
export {
  AICommandPalette,
  type Command,
  type AIInterpretation,
  type AICommandPaletteProps,
} from "./AICommandPalette";
export {
  AIEditOverlay,
  type Selection,
  type DiffLine,
  type EditResult,
  type EditRequest,
  type AIEditOverlayProps,
} from "./AIEditOverlay";
export {
  SuggestionChip,
  type ChipIcon,
  type ChipVariant,
  type ChipSize,
  type SuggestionChipData,
  type SuggestionChipProps,
} from "./SuggestionChip";
export { AgentTaskQueue, type AgentTaskQueueProps } from "./AgentTaskQueue";
