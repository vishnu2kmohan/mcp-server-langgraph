/**
 * ConnectedConversationPanel
 *
 * Redux-connected wrapper for ConversationPanel that integrates with:
 * - React Router loaders (messages, session)
 * - Redux actions (sendMessage)
 * - Session telemetry (message tracking)
 * - Message revalidation (refresh after sending)
 * - Conversation Intelligence (Sprint 3)
 *
 * Use this in HybridShellLayout instead of the standalone ConversationPanel.
 */
import { useCallback, useMemo, useState } from "react";
import { useNavigate, useRouteLoaderData, useParams } from "react-router";
import { AlertTriangle, Target, Sparkles } from "lucide-react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  sendMessage,
  selectCurrentSession,
  createSession,
  clearMessages,
} from "../store/slices/sessionSlice";
import { useMessageRevalidation } from "../hooks/useMessageRevalidation";
import {
  useIntentDetection,
  useContextOptimization,
  useGoalTracking,
} from "../hooks/useConversationIntelligence";
import { ConversationPanel } from "./ConversationPanel";
import type { SlashCommand } from "./SlashCommandMenu";
import type { ChatLoaderData } from "../router/loaders";
import { devLogger } from "../utils/devLogger";
import { cn } from "../utils/cn";

const logger = devLogger.withPrefix("[ConnectedConversationPanel]");

// =============================================================================
// Types
// =============================================================================

export interface ConnectedConversationPanelProps {
  /** Additional class name */
  className?: string;
  /** Enable AI conversation intelligence (Sprint 3) */
  enableAI?: boolean;
  /** User ID for AI features */
  userId?: string;
  /** Show context optimization warning */
  showContextWarning?: boolean;
  /** Show goal tracking panel */
  showGoals?: boolean;
  /** Current token count (for context optimization) */
  currentTokens?: number;
  /** Maximum tokens (for context optimization) */
  maxTokens?: number;
}

// =============================================================================
// Slash Commands (can be extended via props or config)
// =============================================================================

const DEFAULT_SLASH_COMMANDS: SlashCommand[] = [
  {
    id: "new",
    name: "new",
    description: "Start a new conversation",
    icon: undefined,
  },
  {
    id: "clear",
    name: "clear",
    description: "Clear conversation history",
    icon: undefined,
  },
  {
    id: "help",
    name: "help",
    description: "Show available commands",
    icon: undefined,
  },
];

// =============================================================================
// Component
// =============================================================================

export function ConnectedConversationPanel({
  className,
  enableAI = false,
  userId = "default-user",
  showContextWarning = false,
  showGoals = false,
  currentTokens = 0,
  maxTokens = 128000,
}: ConnectedConversationPanelProps) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { sessionId } = useParams();

  // Track input for intent detection
  const [inputQuery, setInputQuery] = useState("");

  // Hook for revalidating loader data after sending messages
  const { revalidateMessages } = useMessageRevalidation();

  // Get messages from the chat loader (try both session and index routes)
  const sessionLoaderData = useRouteLoaderData("chat-session") as
    | ChatLoaderData
    | undefined;
  const indexLoaderData = useRouteLoaderData("chat-index") as
    | ChatLoaderData
    | undefined;
  const loaderData = sessionLoaderData ?? indexLoaderData;

  const messages = useMemo(
    () => loaderData?.messages ?? [],
    [loaderData?.messages],
  );

  // Get current session for title and streaming state
  const currentSession = useAppSelector(selectCurrentSession);
  const sessionTitle = currentSession?.name;

  // =============================================================================
  // Conversation Intelligence Hooks (Sprint 3)
  // =============================================================================

  // Intent detection - classifies user intent as they type
  const intentDetection = useIntentDetection({
    userId,
    sessionId: sessionId ?? "default-session",
    query: inputQuery,
    enabled: enableAI && inputQuery.length >= 3,
  });

  // Context optimization - suggests trimming when approaching token limit
  const contextOptimization = useContextOptimization({
    userId,
    sessionId: sessionId ?? "default-session",
    currentTokens,
    maxTokens,
    enabled: enableAI && showContextWarning,
  });

  // Goal tracking - tracks session goals across messages
  const goalTracking = useGoalTracking({
    userId,
    sessionId: sessionId ?? "default-session",
    enabled: enableAI && showGoals,
  });

  // Handle sending a message
  const handleSendMessage = useCallback(
    (content: string) => {
      dispatch(sendMessage(content));
      // Trigger revalidation to sync loader data after message is sent
      revalidateMessages();
      // Clear input for next message
      setInputQuery("");
    },
    [dispatch, revalidateMessages],
  );

  // Handle input change for intent detection
  const handleInputChange = useCallback((value: string) => {
    setInputQuery(value);
  }, []);

  // Handle telemetry for messages
  const handleMessageSent = useCallback(
    (data: { messageLength: number; timestamp: number }) => {
      logger.debug("Message sent", data);
    },
    [],
  );

  // Handle telemetry for suggestions
  const handleSuggestionUsed = useCallback(
    (data: { suggestionId: string; suggestionType: string }) => {
      logger.debug("Suggestion used", data);
    },
    [],
  );

  // Handle slash commands
  const handleSlashCommand = useCallback(
    (command: SlashCommand) => {
      switch (command.id) {
        case "new":
          // Create a new session and navigate to it
          dispatch(createSession({ name: "New Chat" }))
            .unwrap()
            .then((session) => {
              navigate(`/studio/v2/chat/${session.id}`);
              logger.debug("Created new session", { sessionId: session.id });
            })
            .catch((error) => {
              logger.error("Failed to create session", error);
            });
          break;
        case "clear":
          // Clear messages in current session
          dispatch(clearMessages())
            .unwrap()
            .then(() => {
              revalidateMessages();
              logger.debug("Cleared messages");
            })
            .catch((error) => {
              logger.error("Failed to clear messages", error);
            });
          break;
        case "help":
          // Navigate to help page
          navigate("/studio/v2/help");
          break;
      }
    },
    [dispatch, navigate, revalidateMessages],
  );

  // Should show context warning when usage is high (>80%)
  const shouldShowContextWarning =
    enableAI &&
    showContextWarning &&
    contextOptimization.usagePercent !== null &&
    contextOptimization.usagePercent > 80;

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Goal Tracker (Sprint 3) */}
      {enableAI && showGoals && goalTracking.primaryGoal && (
        <div
          data-testid="goal-tracker"
          className={cn(
            "flex items-center gap-2 px-4 py-2",
            "bg-blue-50 dark:bg-blue-900/20",
            "border-b border-blue-200 dark:border-blue-800",
            "text-sm text-blue-700 dark:text-blue-300",
          )}
        >
          <Target size={16} className="flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <span className="font-medium">Goal: </span>
            <span className="truncate">{goalTracking.primaryGoal}</span>
            {goalTracking.progressPercent !== null && (
              <span className="ml-2 text-blue-600 dark:text-blue-400">
                ({goalTracking.progressPercent}% complete)
              </span>
            )}
          </div>
        </div>
      )}

      {/* Context Warning (Sprint 3) */}
      {shouldShowContextWarning && (
        <div
          data-testid="context-warning"
          className={cn(
            "flex items-center gap-2 px-4 py-2",
            "bg-amber-50 dark:bg-amber-900/20",
            "border-b border-amber-200 dark:border-amber-800",
            "text-sm text-amber-700 dark:text-amber-300",
          )}
        >
          <AlertTriangle size={16} className="flex-shrink-0" />
          <div className="flex-1">
            <span className="font-medium">Context Usage: </span>
            <span>{contextOptimization.usagePercent?.toFixed(0)}%</span>
            {contextOptimization.recommendedAction && (
              <span className="ml-2 text-amber-600 dark:text-amber-400">
                - {contextOptimization.recommendedAction.replace(/_/g, " ")}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Intent Indicator (Sprint 3) */}
      {enableAI && intentDetection.intent && inputQuery.length >= 3 && (
        <div
          data-testid="intent-indicator"
          className={cn(
            "flex items-center gap-2 px-4 py-1.5",
            "bg-purple-50 dark:bg-purple-900/20",
            "border-b border-purple-200 dark:border-purple-800",
            "text-xs text-purple-700 dark:text-purple-300",
          )}
        >
          <Sparkles size={12} className="flex-shrink-0" />
          <span>
            Detected intent:{" "}
            <span className="font-medium">
              {intentDetection.intent.replace(/_/g, " ")}
            </span>
            {intentDetection.confidence !== null && (
              <span className="ml-1 text-purple-500 dark:text-purple-400">
                ({(intentDetection.confidence * 100).toFixed(0)}%)
              </span>
            )}
          </span>
        </div>
      )}

      <ConversationPanel
        data-testid="connected-conversation-panel"
        messages={messages}
        onSendMessage={handleSendMessage}
        sessionTitle={sessionTitle}
        slashCommands={DEFAULT_SLASH_COMMANDS}
        onSlashCommand={handleSlashCommand}
        onMessageSent={handleMessageSent}
        onSuggestionUsed={handleSuggestionUsed}
        onInputChange={handleInputChange}
        autoFocus
        className="flex-1"
      />
    </div>
  );
}
