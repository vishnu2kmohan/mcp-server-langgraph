/**
 * ChatDocument Component
 *
 * A streamlined chat document component for use within the MainDock.
 * Unlike the full ChatPage, this component:
 * - Does NOT include SessionPanel (handled by app-level LeftSidebar)
 * - Does NOT include ContextPanel (handled by app-level RightSidebar)
 * - Focuses only on messages display and input
 *
 * Features:
 * - Message display with streaming support
 * - Chat input with voice and file upload
 * - Compact mode for docked tabs
 */

import { useState, useEffect, useMemo, useRef } from "react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  loadSession,
  addMessage,
  selectCurrentSession,
  selectIsLoadingSession,
  selectIsSending,
} from "../../store/slices/sessionSlice";
import { useStreamingChat } from "../../hooks/useStreamingChat";
import { useMCPConnection } from "../../hooks/useMCPConnection";
import { useVoiceInput } from "../../hooks/useVoiceInput";
import { useFileUpload } from "../../hooks/useFileUpload";
import { ChatMessages, type Message, type ThinkingTrace } from "./ChatMessages";
import { ChatInputForm } from "./ChatInputForm";
import { Loader2, MessageSquare } from "lucide-react";
import { useFeatureFlag } from "../../contexts/FeatureFlagContext";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface ChatDocumentProps {
  /** Session ID to display */
  sessionId: string;
  /** Whether to use compact styling for docked mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function ChatDocument({
  sessionId,
  compact = false,
  className,
}: ChatDocumentProps) {
  const [input, setInput] = useState("");
  const dispatch = useAppDispatch();

  // Feature flag for interactive artifacts
  const enableInteractiveArtifacts = useFeatureFlag("interactive_artifacts");

  // Redux selectors
  const currentSession = useAppSelector(selectCurrentSession);
  const isLoadingSession = useAppSelector(selectIsLoadingSession);
  const isSending = useAppSelector(selectIsSending);

  // MCP connection hook
  const { connectionMode: _connectionMode } = useMCPConnection({
    autoConnect: true,
    autoReconnect: true,
    maxReconnectAttempts: 5,
  });

  // Streaming chat hook for real-time responses
  const {
    isStreaming,
    streamingContent,
    startStream,
    stopStream,
    clearContent,
    usage,
    model: _model,
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

  // Messages from current session
  const messages = useMemo(
    () => currentSession?.messages || [],
    [currentSession?.messages],
  );

  // Construct thinking trace from streaming usage data
  const thinkingTrace: ThinkingTrace | undefined = useMemo(() => {
    if (!isStreaming && !usage) {
      return undefined;
    }
    return {
      tokens: usage
        ? {
            input: usage.promptTokens,
            output: usage.completionTokens,
          }
        : undefined,
      rawOutput: streamingContent || undefined,
      steps: isStreaming
        ? [{ name: "Processing", status: "running" }]
        : usage
          ? [{ name: "Completed", status: "success" }]
          : undefined,
    };
  }, [isStreaming, usage, streamingContent]);

  // Determine if we're in an active sending/streaming state
  const isProcessing = isSending || isStreaming;

  // Load session when sessionId changes
  useEffect(() => {
    if (sessionId && (!currentSession || currentSession.id !== sessionId)) {
      dispatch(loadSession(sessionId));
    }
  }, [dispatch, sessionId, currentSession]);

  // Guard against processing streaming completion multiple times
  const hasProcessedStreamRef = useRef(false);

  // Reset the stream processing guard when streaming starts
  useEffect(() => {
    if (isStreaming) {
      hasProcessedStreamRef.current = false;
    }
  }, [isStreaming]);

  // When streaming completes, add the response as a message
  useEffect(() => {
    if (
      !isStreaming &&
      streamingContent &&
      currentSession &&
      !hasProcessedStreamRef.current
    ) {
      hasProcessedStreamRef.current = true;

      const assistantMessage = {
        id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
        role: "assistant" as const,
        content: streamingContent,
        timestamp: Date.now(),
      };
      dispatch(addMessage(assistantMessage));
      clearContent();
    }
  }, [dispatch, isStreaming, streamingContent, currentSession, clearContent]);

  // Sync voice transcript to input field
  useEffect(() => {
    if (transcript) {
      setInput(transcript);
    }
  }, [transcript]);

  const handleSubmit = async () => {
    if (!input.trim() || isProcessing || !currentSession) return;

    const content = input.trim();
    setInput("");
    clearTranscript();
    clearUploadFiles();

    // Add user message immediately (optimistic update)
    const userMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      role: "user" as const,
      content,
      timestamp: Date.now(),
    };
    dispatch(addMessage(userMessage));

    // Start streaming response
    startStream(currentSession.id, content);
  };

  // Loading state
  if (isLoadingSession && !currentSession) {
    return (
      <div
        data-testid="chat-document"
        className={cn(
          "flex items-center justify-center h-full",
          "bg-white dark:bg-gray-900",
          className,
        )}
      >
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  // No session state
  if (!currentSession) {
    return (
      <div
        data-testid="chat-document"
        className={cn(
          "flex flex-col items-center justify-center h-full",
          "bg-white dark:bg-gray-900",
          "text-gray-500 dark:text-gray-400",
          className,
        )}
      >
        <MessageSquare size={64} className="mb-4 opacity-50" />
        <h2 className="text-xl font-semibold mb-2">No Active Session</h2>
        <p className="text-sm">Select or create a session to start chatting.</p>
      </div>
    );
  }

  return (
    <div
      data-testid="chat-document"
      className={cn(
        "flex flex-col h-full",
        "bg-white dark:bg-gray-900",
        compact && "text-sm",
        className,
      )}
    >
      {/* Messages */}
      <ChatMessages
        messages={messages as Message[]}
        isStreaming={isStreaming}
        streamingContent={streamingContent}
        isSending={isSending}
        thinkingTrace={thinkingTrace}
        enableInteractiveArtifacts={enableInteractiveArtifacts}
      />

      {/* Input Form */}
      <ChatInputForm
        input={input}
        onInputChange={setInput}
        onSubmit={handleSubmit}
        isProcessing={isProcessing}
        isStreaming={isStreaming}
        onStopStreaming={stopStream}
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
    </div>
  );
}

export default ChatDocument;
