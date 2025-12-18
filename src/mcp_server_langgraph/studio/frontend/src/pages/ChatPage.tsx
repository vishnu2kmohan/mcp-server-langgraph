/**
 * ChatPage - Unified Workspace (DEPRECATED)
 *
 * @deprecated This component is bypassed by the new AppShell architecture.
 * The App.tsx component now renders AppShell with MainDock for studio routes,
 * which uses ChatDocument instead of this full ChatPage.
 *
 * The new architecture provides:
 * - LeftSidebar: Session management (replaces SessionPanel)
 * - MainDock: Chat content via ChatDocument
 * - RightSidebar: Context-sensitive property panels (replaces ContextPanel)
 * - BottomPanel: Activity log, problems, inspector
 *
 * This file is kept for backward compatibility but should be removed
 * once the migration is fully validated.
 *
 * Legacy Layout (not used in studio routes):
 * - Left: SessionPanel (collapsible session list)
 * - Center: Chat area with messages and input
 * - Right: ContextPanel (tools, activity, cost)
 */

import { useState, useRef, useEffect, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { useDeleteSessionMutation } from "../api";
import {
  fetchSessions,
  fetchMoreSessions,
  createSession,
  loadSession,
  clearMessages,
  addMessage,
  clearError,
  setCurrentSession,
  renameSession,
  selectCurrentSession,
  selectSessions,
  selectIsLoadingSession,
  selectIsLoadingSessions,
  selectIsSending,
  selectSessionError,
  selectHasMore,
  selectTotalCount,
  selectIsLoadingMore,
} from "../store/slices/sessionSlice";
import { useStreamingChat } from "../hooks/useStreamingChat";
import { useMCPConnection } from "../hooks/useMCPConnection";
import { useAutoSessionTitle } from "../hooks/useAutoSessionTitle";
import { useVoiceInput } from "../hooks/useVoiceInput";
import { useFileUpload } from "../hooks/useFileUpload";
import { useDebounce } from "../hooks/useDebounce";
import { useBackgroundSync } from "../hooks/useBackgroundSync";
import { SessionPanel, Session } from "../components/Chat/SessionPanel";
import {
  ContextPanel,
  ActivityItem,
  SessionCost,
} from "../components/Chat/ContextPanel";
import { ChatHeader, ConnectionMode } from "../components/Chat/ChatHeader";
import {
  ChatMessages,
  Message,
  ThinkingTrace,
} from "../components/Chat/ChatMessages";
import { ChatInputForm } from "../components/Chat/ChatInputForm";
import {
  SessionGoalTracker,
  type GoalSetData,
  type GoalResult,
} from "../components/Chat";
import {
  Loader2,
  MessageSquare,
  PanelLeftOpen,
  PanelRightOpen,
  CloudOff,
  RefreshCw,
} from "lucide-react";
import { ConfirmDialog, TierUsageBar, UpgradePrompt } from "../components/UI";
import { useTierLimits } from "../hooks/useTierLimits";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";

export function ChatPage() {
  const [input, setInput] = useState("");
  const [isMobileSessionsOpen, setIsMobileSessionsOpen] = useState(false);
  const [isMobileContextOpen, setIsMobileContextOpen] = useState(false);
  const [showClearDialog, setShowClearDialog] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [upgradePromptDismissed, setUpgradePromptDismissed] = useState(false);
  // Session goal tracking for multi-turn conversation (Priority 3.3)
  const [sessionGoal, setSessionGoal] = useState<string | undefined>(undefined);
  const debouncedSearchQuery = useDebounce(searchQuery, 300);
  const navigate = useNavigate();

  // Tier limits for session usage indicator
  const {
    tier,
    maxSessions,
    activeSessions,
    isApproachingLimit,
    isAtLimit,
    nextTier,
  } = useTierLimits();

  // Feature flag for interactive artifacts (mermaid, charts, SVG, etc.)
  // Note: Backend returns "interactive_artifacts" (not "enable_interactive_artifacts")
  const enableInteractiveArtifacts = useFeatureFlag("interactive_artifacts");
  const [searchParams] = useSearchParams();
  const sessionIdFromUrl = searchParams.get("session");
  const dispatch = useAppDispatch();
  const [deleteSession] = useDeleteSessionMutation();

  // Redux selectors
  const currentSession = useAppSelector(selectCurrentSession);
  const sessions = useAppSelector(selectSessions);
  const isLoadingSession = useAppSelector(selectIsLoadingSession);
  const isLoadingSessions = useAppSelector(selectIsLoadingSessions);
  const isSending = useAppSelector(selectIsSending);
  const error = useAppSelector(selectSessionError);
  const hasMore = useAppSelector(selectHasMore);
  const totalCount = useAppSelector(selectTotalCount);
  const isLoadingMore = useAppSelector(selectIsLoadingMore);

  // MCP connection hook - auto-connects on mount with reconnection
  const {
    connectionMode,
    tools,
    error: mcpError,
    connect,
    isReconnecting,
    reconnectAttempts,
  } = useMCPConnection({
    autoConnect: true,
    autoReconnect: true,
    maxReconnectAttempts: 5,
  });

  // Activity tracking
  const [activities, setActivities] = useState<ActivityItem[]>([]);

  // Streaming chat hook for real-time responses
  const {
    isStreaming,
    streamingContent,
    startStream,
    clearContent,
    usage,
    model,
    traceId,
    error: streamingError,
  } = useStreamingChat();

  // Voice input hook for speech-to-text
  const {
    isListening,
    isSupported: isVoiceSupported,
    transcript,
    error: voiceError,
    startListening,
    stopListening,
    clearTranscript,
  } = useVoiceInput({
    continuous: false,
    interimResults: true,
  });

  // File upload hook for attachments
  const {
    files: uploadFiles,
    isUploading,
    isDragging,
    error: fileError,
    selectFiles,
    removeFile,
    clearFiles: clearUploadFiles,
    dragHandlers,
  } = useFileUpload({
    maxSizeMB: 10,
    maxFiles: 5,
  });

  // Background sync hook for offline message queueing
  const { isOnline, isSyncing, pendingCount } = useBackgroundSync();

  // Auto-generate session title from first user message
  const { onUserMessage: autoGenerateTitle } = useAutoSessionTitle();

  // Session cost computed from streaming usage data
  const sessionCost = useMemo<SessionCost>(() => {
    if (!usage) {
      return { tokens: 0, cost: 0, model: model || "unknown" };
    }
    // Simple cost estimation: $0.001 per 1K tokens (approximation)
    const costPerToken = 0.001 / 1000;
    return {
      tokens: usage.totalTokens,
      cost: usage.totalTokens * costPerToken,
      model: model || "unknown",
    };
  }, [usage, model]);

  const messages = useMemo(
    () => currentSession?.messages || [],
    [currentSession?.messages],
  );

  // Construct thinking trace from streaming usage data
  const thinkingTrace: ThinkingTrace | undefined = useMemo(() => {
    // Only show trace when streaming or if we have usage data
    if (!isStreaming && !usage) {
      return undefined;
    }

    // Build trace from available streaming data
    return {
      // Show token usage from streaming response
      tokens: usage
        ? {
            input: usage.promptTokens,
            output: usage.completionTokens,
          }
        : undefined,
      // Show streaming content as raw output for debugging
      rawOutput: streamingContent || undefined,
      // Steps will show the current processing phase
      steps: isStreaming
        ? [{ name: "Processing", status: "running" }]
        : usage
          ? [{ name: "Completed", status: "success" }]
          : undefined,
    };
  }, [isStreaming, usage, streamingContent]);

  // Determine if we're in an active sending/streaming state
  const isProcessing = isSending || isStreaming;

  // Load session from URL param or auto-create on mount
  useEffect(() => {
    const initSession = async () => {
      if (isLoadingSession || isLoadingSessions) {
        return;
      }

      // Priority 1: Load session from URL query param
      if (sessionIdFromUrl) {
        if (currentSession?.id !== sessionIdFromUrl) {
          dispatch(loadSession(sessionIdFromUrl));
        }
        return;
      }

      // Already have a session, nothing to do
      if (currentSession) {
        return;
      }

      // Priority 2: Fetch sessions if none loaded
      if (sessions.length === 0) {
        dispatch(fetchSessions());
        return;
      }

      // Priority 3: Load first session
      if (sessions.length > 0) {
        dispatch(loadSession(sessions[0].id));
        return;
      }
    };

    initSession();
  }, [
    dispatch,
    sessionIdFromUrl,
    currentSession,
    sessions,
    isLoadingSession,
    isLoadingSessions,
  ]);

  // Create session if fetchSessions returned empty list (only when no URL param)
  useEffect(() => {
    const createIfNeeded = async () => {
      // Don't auto-create if a specific session was requested via URL
      if (sessionIdFromUrl) {
        return;
      }

      if (
        !isLoadingSession &&
        !isLoadingSessions &&
        !currentSession &&
        sessions.length === 0
      ) {
        dispatch(createSession({ name: "New Chat" }));
      }
    };

    createIfNeeded();
  }, [
    dispatch,
    sessionIdFromUrl,
    sessions,
    currentSession,
    isLoadingSession,
    isLoadingSessions,
  ]);

  // Track if this is the initial mount to avoid double-fetching
  const isInitialMount = useRef(true);

  // Guard against processing streaming completion multiple times (prevents infinite loop)
  const hasProcessedStreamRef = useRef(false);

  // Refetch sessions when search or status filter changes
  useEffect(() => {
    // Skip on initial mount - the first useEffect handles initial fetch
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    // Build params for fetchSessions
    const params: { search?: string; status?: string } = {};
    if (debouncedSearchQuery.trim()) {
      params.search = debouncedSearchQuery.trim();
    }
    if (statusFilter && statusFilter !== "all") {
      params.status = statusFilter;
    }

    dispatch(fetchSessions(params));
  }, [dispatch, debouncedSearchQuery, statusFilter]);

  const handleSubmit = async () => {
    if (!input.trim() || isProcessing || !currentSession) return;

    const content = input.trim();
    setInput("");
    clearTranscript(); // Clear voice transcript after sending
    clearUploadFiles(); // Clear attached files after sending

    // Add user message immediately (optimistic update)
    const userMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      role: "user" as const,
      content,
      timestamp: Date.now(),
    };
    dispatch(addMessage(userMessage));

    // Add activity
    setActivities((prev) => [
      { timestamp: Date.now(), action: "message sent", details: "" },
      ...prev.slice(0, 9),
    ]);

    // Auto-generate session title from first user message
    autoGenerateTitle(
      currentSession.id,
      currentSession.name,
      content,
      messages.length,
    );

    // Start streaming response
    startStream(currentSession.id, content);
  };

  // Reset the stream processing guard when streaming starts
  useEffect(() => {
    if (isStreaming) {
      hasProcessedStreamRef.current = false;
    }
  }, [isStreaming]);

  // When streaming completes, add the response as a message
  // Uses a ref guard to prevent infinite loop from currentSession reference changes
  useEffect(() => {
    if (
      !isStreaming &&
      streamingContent &&
      currentSession &&
      !hasProcessedStreamRef.current
    ) {
      // Mark as processed FIRST to prevent re-entry
      hasProcessedStreamRef.current = true;

      const assistantMessage = {
        id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
        role: "assistant" as const,
        content: streamingContent,
        timestamp: Date.now(),
      };
      dispatch(addMessage(assistantMessage));
      clearContent();

      // Add activity
      setActivities((prev) => [
        { timestamp: Date.now(), action: "response received", details: "" },
        ...prev.slice(0, 9),
      ]);
    }
  }, [dispatch, isStreaming, streamingContent, currentSession, clearContent]);

  // Sync voice transcript to input field
  useEffect(() => {
    if (transcript) {
      setInput(transcript);
    }
  }, [transcript]);

  const handleClear = () => {
    // Open the styled confirmation dialog
    setShowClearDialog(true);
  };

  const confirmClearMessages = () => {
    dispatch(clearMessages());
    setActivities([]);
    setShowClearDialog(false);
  };

  const handleNewSession = async () => {
    const result = await dispatch(createSession({ name: "New Chat" }));
    // Update URL with new session ID so it persists across navigation
    if (createSession.fulfilled.match(result) && result.payload?.id) {
      navigate(`/studio/chat?session=${result.payload.id}`, { replace: true });
    }
    setActivities([
      { timestamp: Date.now(), action: "session created", details: "" },
    ]);
  };

  const handleSessionSelect = async (sessionId: string) => {
    dispatch(loadSession(sessionId));
    // Update URL with session ID so it persists across navigation
    navigate(`/studio/chat?session=${sessionId}`, { replace: true });
    setActivities([
      { timestamp: Date.now(), action: "session loaded", details: "" },
    ]);
  };

  const handleBulkDelete = async (sessionIds: string[]) => {
    // Delete each selected session
    await Promise.all(sessionIds.map((id) => deleteSession(id)));
    // Refresh sessions list
    dispatch(fetchSessions());
    setActivities((prev) => [
      {
        timestamp: Date.now(),
        action: `${sessionIds.length} sessions deleted`,
        details: "",
      },
      ...prev.slice(0, 9),
    ]);
  };

  const handleSessionDelete = async (sessionId: string) => {
    // Delete a single session
    await deleteSession(sessionId);
    // If the deleted session is the current one, clear current session
    if (currentSession?.id === sessionId) {
      dispatch(setCurrentSession(null));
    }
    // Refresh sessions list
    dispatch(fetchSessions());
    setActivities((prev) => [
      { timestamp: Date.now(), action: "session deleted", details: sessionId },
      ...prev.slice(0, 9),
    ]);
  };

  const handleSessionRename = async (sessionId: string, newName: string) => {
    await dispatch(renameSession({ sessionId, name: newName }));
    setActivities((prev) => [
      {
        timestamp: Date.now(),
        action: "session renamed",
        details: newName,
      },
      ...prev.slice(0, 9),
    ]);
  };

  const handleRefreshTools = () => {
    // Reconnect to refresh tools list
    connect();
    setActivities((prev) => [
      { timestamp: Date.now(), action: "tools refreshed", details: "" },
      ...prev.slice(0, 9),
    ]);
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleStatusChange = (status: string) => {
    setStatusFilter(status);
  };

  const handleLoadMore = () => {
    // Dispatch action to fetch more sessions with current cursor
    dispatch(fetchMoreSessions());
  };

  const handleViewCostDetails = () => {
    navigate("/studio/cost");
  };

  const handleViewAllTraces = () => {
    navigate("/studio/observability");
  };

  const handleViewTrace = (viewTraceId: string) => {
    navigate(`/studio/observability?trace_id=${viewTraceId}`);
  };

  // Session goal tracking handlers (Priority 3.3 - Multi-turn goal tracking)
  const handleGoalSet = (data: GoalSetData) => {
    setSessionGoal(data.goal);
    setActivities((prev) => [
      { timestamp: Date.now(), action: "goal set", details: data.goal },
      ...prev.slice(0, 9),
    ]);
  };

  const handleGoalComplete = (result: GoalResult) => {
    const achievedText =
      result.achieved === true
        ? "achieved"
        : result.achieved === "partial"
          ? "partially achieved"
          : "not achieved";
    setActivities((prev) => [
      {
        timestamp: Date.now(),
        action: `goal ${achievedText}`,
        details: result.goal,
      },
      ...prev.slice(0, 9),
    ]);
    setSessionGoal(undefined);
  };

  const handleGoalClear = () => {
    setSessionGoal(undefined);
    setActivities((prev) => [
      { timestamp: Date.now(), action: "goal cleared", details: "" },
      ...prev.slice(0, 9),
    ]);
  };

  // Convert sessions to SessionPanel format
  // Handle potentially undefined/invalid dates defensively
  const sessionPanelData: Session[] = useMemo(() => {
    let filtered = sessions;

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter((s) => s.name.toLowerCase().includes(query));
    }

    return filtered.map((s) => {
      const now = new Date().toISOString();
      const createdAt = s.createdAt ? new Date(s.createdAt).toISOString() : now;
      const updatedAt = s.updatedAt
        ? new Date(s.updatedAt).toISOString()
        : createdAt;

      return {
        id: s.id,
        name: s.name,
        createdAt,
        updatedAt,
        messageCount: s.messageCount ?? 0,
      };
    });
  }, [sessions, searchQuery]);

  if (isLoadingSession && !currentSession) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="h-screen flex bg-gray-50 dark:bg-gray-900">
      {/* Mobile toggle buttons - visible only on mobile */}
      <div className="fixed top-4 left-4 z-40 flex gap-2 md:hidden">
        <button
          onClick={() => setIsMobileSessionsOpen(!isMobileSessionsOpen)}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700"
          aria-label="Toggle sessions"
        >
          <PanelLeftOpen
            size={20}
            className="text-gray-700 dark:text-gray-300"
          />
        </button>
      </div>
      <div className="fixed top-4 right-4 z-40 flex gap-2 md:hidden">
        <button
          onClick={() => setIsMobileContextOpen(!isMobileContextOpen)}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700"
          aria-label="Toggle context"
        >
          <PanelRightOpen
            size={20}
            className="text-gray-700 dark:text-gray-300"
          />
        </button>
      </div>

      {/* Left Panel - Sessions */}
      <SessionPanel
        sessions={sessionPanelData}
        currentSessionId={currentSession?.id ?? null}
        onSessionSelect={handleSessionSelect}
        onNewSession={handleNewSession}
        isLoading={isLoadingSessions}
        enableBulkSelect={true}
        onBulkDelete={handleBulkDelete}
        onDelete={handleSessionDelete}
        onRename={handleSessionRename}
        enableSearch={true}
        onSearch={handleSearch}
        enableStatusFilter={true}
        statusFilter={statusFilter}
        onStatusChange={handleStatusChange}
        hasMore={hasMore}
        loadingMore={isLoadingMore}
        onLoadMore={handleLoadMore}
        totalCount={totalCount}
      />

      {/* Center - Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header with connection status, session info, and actions */}
        <ChatHeader
          connectionMode={connectionMode as ConnectionMode}
          isReconnecting={isReconnecting}
          reconnectAttempts={reconnectAttempts}
          sessionName={currentSession?.name}
          messageCount={messages.length}
          sessionId={currentSession?.id}
          mcpError={mcpError ?? undefined}
          sessionError={streamingError ?? error ?? undefined}
          onConnect={connect}
          onClear={handleClear}
          onClearError={() => dispatch(clearError())}
        />

        {/* Tier Usage Indicator (Bob's journey - surface tier limits) */}
        {tier !== "dedicated" && (
          <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
            <TierUsageBar
              current={activeSessions}
              max={maxSessions}
              label="Active Sessions"
              tier={tier}
              variant="default"
            />
          </div>
        )}

        {/* Upgrade Prompt (shown when approaching or at limit) */}
        {(isApproachingLimit || isAtLimit) &&
          nextTier &&
          !upgradePromptDismissed && (
            <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-800">
              <UpgradePrompt
                show={true}
                feature="unlimited sessions"
                targetTier={nextTier}
                currentUsage={activeSessions}
                maxUsage={maxSessions}
                urgency={isAtLimit ? "critical" : "warning"}
                onUpgrade={() => navigate("/studio/settings?tab=billing")}
                onDismiss={() => setUpgradePromptDismissed(true)}
              />
            </div>
          )}

        {/* Session Goal Tracker (Priority 3.3 - Multi-turn goal tracking) */}
        {currentSession && (
          <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
            <SessionGoalTracker
              sessionId={currentSession.id}
              currentGoal={sessionGoal}
              onGoalSet={handleGoalSet}
              onGoalComplete={handleGoalComplete}
              onGoalClear={handleGoalClear}
              compact
            />
          </div>
        )}

        {/* Background Sync Status Indicator */}
        {((!isOnline && pendingCount > 0) || isSyncing) && (
          <div className="px-4 py-2 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 flex items-center gap-2">
            {isSyncing ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin text-amber-600 dark:text-amber-400" />
                <span className="text-sm text-amber-700 dark:text-amber-300">
                  Syncing {pendingCount} pending message
                  {pendingCount !== 1 ? "s" : ""}...
                </span>
              </>
            ) : (
              <>
                <CloudOff className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                <span className="text-sm text-amber-700 dark:text-amber-300">
                  {pendingCount} pending message{pendingCount !== 1 ? "s" : ""}{" "}
                  will sync when online
                </span>
              </>
            )}
          </div>
        )}

        {/* Messages */}
        {!currentSession ? (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
            <MessageSquare size={64} className="mb-4 opacity-50" />
            <h2 className="text-xl font-semibold mb-2">No Active Session</h2>
            <p className="text-sm mb-4">
              Create a new session to start chatting.
            </p>
            <button
              onClick={handleNewSession}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              New Session
            </button>
          </div>
        ) : (
          <>
            {/* Message list with streaming support */}
            <ChatMessages
              messages={messages as Message[]}
              isStreaming={isStreaming}
              streamingContent={streamingContent}
              isSending={isSending}
              thinkingTrace={thinkingTrace}
              enableInteractiveArtifacts={enableInteractiveArtifacts}
            />

            {/* Input Form with voice and file support */}
            <ChatInputForm
              input={input}
              onInputChange={setInput}
              onSubmit={handleSubmit}
              isProcessing={isProcessing}
              isListening={isListening}
              isVoiceSupported={isVoiceSupported}
              voiceError={voiceError}
              onStartListening={startListening}
              onStopListening={stopListening}
              uploadFiles={uploadFiles}
              isUploading={isUploading}
              isDragging={isDragging}
              fileError={fileError}
              onSelectFiles={selectFiles}
              onRemoveFile={removeFile}
              dragHandlers={dragHandlers}
            />
          </>
        )}
      </div>

      {/* Right Panel - Context */}
      <ContextPanel
        tools={tools}
        activities={activities}
        sessionCost={sessionCost}
        currentTraceId={traceId}
        onRefreshTools={handleRefreshTools}
        onViewCostDetails={handleViewCostDetails}
        onViewAllTraces={handleViewAllTraces}
        onViewTrace={handleViewTrace}
      />

      {/* Clear Messages Confirmation Dialog */}
      <ConfirmDialog
        open={showClearDialog}
        onClose={() => setShowClearDialog(false)}
        onConfirm={confirmClearMessages}
        title="Clear Messages"
        message="Are you sure you want to clear all messages in this session? This action cannot be undone."
        confirmText="Clear"
        cancelText="Cancel"
        isDestructive={true}
        isLoading={false}
      />
    </div>
  );
}

export default ChatPage;
