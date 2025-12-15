/**
 * ChatMessage Component
 *
 * Displays a single chat message with role-based styling.
 */

import { Loader2, ExternalLink } from "lucide-react";

/**
 * Source citation for AI responses
 */
export interface SourceCitation {
  title: string;
  url: string;
}

export interface ChatMessageProps {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  showTimestamp?: boolean;
  isLoading?: boolean;
  renderMarkdown?: boolean;
  /** Source citations for AI responses (only displayed for assistant messages) */
  sources?: SourceCitation[];
}

export function ChatMessage({
  role,
  content,
  timestamp,
  showTimestamp = true,
  isLoading = false,
  renderMarkdown = false,
  sources,
}: ChatMessageProps) {
  const isUser = role === "user";
  const isAssistant = role === "assistant";

  const roleLabel = isUser ? "You" : isAssistant ? "Assistant" : "System";

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const renderContent = () => {
    if (isLoading) {
      return (
        <div
          data-testid="loading-indicator"
          className="flex items-center gap-2"
        >
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-gray-500">Thinking...</span>
        </div>
      );
    }

    if (renderMarkdown) {
      // Simple markdown rendering for bold text
      const rendered = content
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.*?)\*/g, "<em>$1</em>");
      return (
        <div
          dangerouslySetInnerHTML={{ __html: rendered }}
          className="prose prose-sm max-w-none"
        />
      );
    }

    return <p className="whitespace-pre-wrap">{content}</p>;
  };

  return (
    <div
      data-role={role}
      className={`p-4 rounded-lg mb-2 ${
        isUser
          ? "bg-blue-100 dark:bg-blue-900 ml-8"
          : "bg-gray-100 dark:bg-gray-800 mr-8"
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span
          className={`text-sm font-medium ${
            isUser
              ? "text-blue-700 dark:text-blue-300"
              : "text-gray-700 dark:text-gray-300"
          }`}
        >
          {roleLabel}
        </span>
        {showTimestamp && (
          <span
            data-testid="timestamp"
            className="text-xs text-gray-500 dark:text-gray-400"
          >
            {formatTime(timestamp)}
          </span>
        )}
      </div>
      <div
        className={
          isUser
            ? "text-blue-900 dark:text-blue-100"
            : "text-gray-900 dark:text-gray-100"
        }
      >
        {renderContent()}
      </div>

      {/* AI Source Citations - only for assistant messages with sources */}
      {isAssistant && sources && sources.length > 0 && (
        <div
          data-testid="sources-section"
          className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600"
        >
          <div className="flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
            <ExternalLink
              data-testid="sources-icon"
              size={12}
              className="text-gray-400 dark:text-gray-500"
            />
            <span>Sources:</span>
          </div>
          <ul className="space-y-1">
            {sources.map((source, index) => (
              <li key={index}>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1"
                >
                  {source.title}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
