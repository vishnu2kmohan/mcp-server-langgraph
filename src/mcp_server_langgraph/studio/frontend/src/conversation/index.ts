/**
 * Conversation Module - Phase 2
 *
 * Chat experience components for the Studio Canvas.
 */

export {
  MessageBubble,
  type ChatMessage,
  type MessageBubbleProps,
} from "./MessageBubble";
export { MessageList, type MessageListProps } from "./MessageList";
export {
  UnifiedMessageList,
  type UnifiedMessageListProps,
  type FollowUpSuggestion,
} from "./UnifiedMessageList";
export {
  ConnectedChatInputForm,
  type ConnectedChatInputFormProps,
} from "./ConnectedChatInputForm";
// Re-export SlashCommand from the canonical location (components/Chat)
export {
  type SlashCommand,
  type SlashCommandMenuProps,
} from "../components/Chat/SlashCommandMenu";
export {
  FollowUpSuggestions,
  type Suggestion,
  type FollowUpSuggestionsProps,
} from "./FollowUpSuggestions";
export {
  ConversationPanel,
  type ConversationPanelProps,
} from "./ConversationPanel";
export {
  ConnectedConversationPanel,
  type ConnectedConversationPanelProps,
} from "./ConnectedConversationPanel";
