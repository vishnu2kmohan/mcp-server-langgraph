/**
 * useStreamingChat Hook
 *
 * React hook for handling streaming chat responses using Server-Sent Events (SSE).
 * Manages EventSource connection, message accumulation, and error handling.
 */

import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * State for streaming chat
 */
interface StreamingChatState {
  isStreaming: boolean;
  streamingContent: string;
  error: string | null;
}

/**
 * Return type for useStreamingChat hook
 */
interface UseStreamingChatReturn extends StreamingChatState {
  startStream: (sessionId: string, message: string) => void;
  stopStream: () => void;
  clearContent: () => void;
}

/**
 * Hook for managing streaming chat with SSE
 *
 * @returns Streaming chat state and control functions
 *
 * @example
 * ```tsx
 * const { isStreaming, streamingContent, startStream, stopStream } = useStreamingChat();
 *
 * const handleSend = (message: string) => {
 *   startStream('session-123', message);
 * };
 *
 * return (
 *   <div>
 *     {isStreaming && <p>Loading...</p>}
 *     <p>{streamingContent}</p>
 *   </div>
 * );
 * ```
 */
export function useStreamingChat(): UseStreamingChatReturn {
  const [state, setState] = useState<StreamingChatState>({
    isStreaming: false,
    streamingContent: '',
    error: null,
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  /**
   * Start streaming chat response
   */
  const startStream = useCallback((sessionId: string, message: string) => {
    // Close any existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Reset state
    setState({
      isStreaming: true,
      streamingContent: '',
      error: null,
    });

    // Create EventSource for SSE
    const url = `/api/v1/chat/completions/stream?session_id=${sessionId}&message=${encodeURIComponent(message)}`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    // Handle incoming messages
    eventSource.onmessage = (event: MessageEvent) => {
      // Check for completion signal
      if (event.data === '[DONE]') {
        eventSource.close();
        setState((prev) => ({ ...prev, isStreaming: false }));
        return;
      }

      // Parse and accumulate content
      try {
        const data = JSON.parse(event.data);
        if (data.content) {
          setState((prev) => ({
            ...prev,
            streamingContent: prev.streamingContent + data.content,
          }));
        }
      } catch {
        // Ignore non-JSON messages
      }
    };

    // Handle errors
    eventSource.onerror = () => {
      eventSource.close();
      setState((prev) => ({
        ...prev,
        isStreaming: false,
        error: 'Stream connection failed',
      }));
    };
  }, []);

  /**
   * Stop streaming
   */
  const stopStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setState((prev) => ({ ...prev, isStreaming: false }));
  }, []);

  /**
   * Clear accumulated content
   */
  const clearContent = useCallback(() => {
    setState((prev) => ({
      ...prev,
      streamingContent: '',
      error: null,
    }));
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return {
    ...state,
    startStream,
    stopStream,
    clearContent,
  };
}
