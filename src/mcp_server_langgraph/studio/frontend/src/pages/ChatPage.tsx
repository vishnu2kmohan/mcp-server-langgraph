/**
 * ChatPage
 *
 * Chat interface page with real-time messaging and trace visualization.
 */

import { useState, useRef, useEffect, useMemo } from 'react';
import { useSessionStore } from '../stores/sessionStore';
import { useStreamingChat } from '../hooks/useStreamingChat';
import { SaveAsWorkflowButton } from '../components/Chat/SaveAsWorkflowButton';
import {
  Send,
  Loader2,
  MessageSquare,
  RefreshCw,
  Trash2,
} from 'lucide-react';

export function ChatPage() {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    currentSession,
    sessions,
    isLoadingSession,
    isLoadingSessions,
    isSending,
    error,
    sendMessage,
    addMessage,
    clearMessages,
    clearError,
    fetchSessions,
    createSession,
    loadSession,
  } = useSessionStore();

  // Streaming chat hook for real-time responses (HEART: Happiness)
  const {
    isStreaming,
    streamingContent,
    startStream,
    clearContent,
  } = useStreamingChat();

  const messages = useMemo(() => currentSession?.messages || [], [currentSession?.messages]);

  // Determine if we're in an active sending/streaming state
  const isProcessing = isSending || isStreaming;

  // Auto-scroll to bottom when messages or streaming content change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Auto-create or load session on mount
  useEffect(() => {
    const initSession = async () => {
      // Don't auto-create if already loading or session exists
      if (isLoadingSession || isLoadingSessions || currentSession) {
        return;
      }

      // Fetch sessions if list is empty
      if (sessions.length === 0) {
        await fetchSessions();
        // After fetch, if still no sessions, create one
        // Note: We don't check sessions.length here because fetchSessions updates the store
        return;
      }

      // If sessions exist but none selected, load the most recent
      if (sessions.length > 0) {
        await loadSession(sessions[0].id);
        return;
      }
    };

    initSession();
  }, [currentSession, sessions, isLoadingSession, isLoadingSessions, fetchSessions, createSession, loadSession]);

  // Create session if fetchSessions returned empty list
  useEffect(() => {
    const createIfNeeded = async () => {
      // Only create if not loading, no current session, and sessions list is empty
      if (!isLoadingSession && !isLoadingSessions && !currentSession && sessions.length === 0) {
        await createSession('New Chat');
      }
    };

    createIfNeeded();
  }, [sessions, currentSession, isLoadingSession, isLoadingSessions, createSession]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing || !currentSession) return;

    const content = input.trim();
    setInput('');

    // Add user message immediately (optimistic update)
    const userMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      role: 'user' as const,
      content,
      timestamp: Date.now(),
    };
    addMessage(userMessage);

    // Start streaming response (HEART: Happiness - real-time feedback)
    startStream(currentSession.id, content);
  };

  // When streaming completes, add the response as a message
  useEffect(() => {
    if (!isStreaming && streamingContent && currentSession) {
      // Add the streamed response as an assistant message
      const assistantMessage = {
        id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
        role: 'assistant' as const,
        content: streamingContent,
        timestamp: Date.now(),
      };
      addMessage(assistantMessage);
      clearContent();
    }
  }, [isStreaming, streamingContent, currentSession, addMessage, clearContent]);

  const handleClear = async () => {
    if (confirm('Clear all messages in this session?')) {
      await clearMessages();
    }
  };

  if (isLoadingSession) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!currentSession) {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-gray-500 dark:text-gray-400">
        <MessageSquare size={64} className="mb-4 opacity-50" />
        <h2 className="text-xl font-semibold mb-2">No Active Session</h2>
        <p className="text-sm">Go to Sessions to create or select a session.</p>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {currentSession.name}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {messages.length} messages
            </p>
          </div>
          <div className="flex items-center gap-2">
            <SaveAsWorkflowButton sessionId={currentSession.id} />
            <button
              onClick={handleClear}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
            >
              <Trash2 size={16} />
              Clear
            </button>
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="px-6 py-3 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800 flex items-center justify-between">
          <p className="text-red-700 dark:text-red-400 text-sm">{error}</p>
          <button
            onClick={clearError}
            className="text-red-600 hover:text-red-800 text-sm"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
            <MessageSquare size={48} className="mb-4 opacity-50" />
            <p>No messages yet. Start a conversation!</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] px-4 py-3 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100'
                }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                <p className={`text-xs mt-1 ${message.role === 'user' ? 'text-blue-200' : 'text-gray-400'}`}>
                  {new Date(message.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
        {/* Streaming response with real-time content (HEART: Happiness) */}
        {isStreaming && (
          <div className="flex justify-start">
            <div className="max-w-[70%] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 rounded-lg">
              {streamingContent ? (
                <p className="whitespace-pre-wrap text-gray-900 dark:text-gray-100">
                  {streamingContent}
                  <span className="inline-block w-2 h-4 ml-1 bg-blue-500 animate-pulse" />
                </p>
              ) : (
                <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                  <RefreshCw size={16} className="animate-spin" />
                  <span>Thinking...</span>
                </div>
              )}
            </div>
          </div>
        )}
        {/* Legacy sending indicator (fallback) */}
        {isSending && !isStreaming && (
          <div className="flex justify-start">
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 rounded-lg">
              <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                <RefreshCw size={16} className="animate-spin" />
                <span>Thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="px-6 py-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700"
      >
        <div className="flex gap-4">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={isProcessing}
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isProcessing ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Send size={18} />
            )}
            Send
          </button>
        </div>
      </form>
    </div>
  );
}

export default ChatPage;
