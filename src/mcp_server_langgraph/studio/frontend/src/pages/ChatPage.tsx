/**
 * ChatPage
 *
 * Chat interface page with real-time messaging and trace visualization.
 */

import { useState, useRef, useEffect, useMemo } from 'react';
import { useSessionStore } from '../stores/sessionStore';
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
    isLoadingSession,
    isSending,
    error,
    sendMessage,
    clearMessages,
    clearError,
  } = useSessionStore();

  const messages = useMemo(() => currentSession?.messages || [], [currentSession?.messages]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSending) return;

    const content = input.trim();
    setInput('');
    await sendMessage(content);
  };

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
        {isSending && (
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
            disabled={isSending}
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || isSending}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isSending ? (
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
