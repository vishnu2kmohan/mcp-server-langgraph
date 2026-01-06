/**
 * SimilarSessionsPanel Component
 *
 * Panel for displaying sessions similar to the currently selected session.
 * Uses AI-powered similarity detection via useSessionSimilarity hook.
 *
 * Features:
 * - Similar sessions list with similarity scores
 * - Common topic badges
 * - Click to navigate to similar session
 * - Loading and error states
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 */

import { useSessionSimilarity } from "../../hooks/useSessionIntelligence";
import { AlertCircle, RefreshCw, Link2, Sparkles } from "lucide-react";

// ==============================================================================
// Types
// ==============================================================================

export interface SimilarSessionsPanelProps {
  /** Current session ID to find similar sessions for */
  sessionId: string;
  /** User ID for the similarity query */
  userId: string;
  /** Optional mapping of session IDs to session names */
  sessionNames?: Record<string, string>;
  /** Maximum number of similar sessions to show */
  limit?: number;
  /** Additional CSS classes */
  className?: string;
  /** Callback when a similar session is selected */
  onSessionSelect?: (sessionId: string) => void;
}

// ==============================================================================
// Component
// ==============================================================================

export function SimilarSessionsPanel({
  sessionId,
  userId,
  sessionNames = {},
  limit = 5,
  className = "",
  onSessionSelect,
}: SimilarSessionsPanelProps) {
  const { similarSessions, isLoading, error, refetch } = useSessionSimilarity({
    userId,
    sessionId,
    limit,
    enabled: !!sessionId && !!userId,
  });

  // ---------------------------------------------------------------------------
  // Render loading state
  // ---------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div
        data-testid="similar-sessions-loading"
        className={`similar-sessions-panel p-4 ${className}`}
      >
        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          <Sparkles size={16} className="text-purple-500" />
          Similar Sessions
        </h3>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2" />
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render error state
  // ---------------------------------------------------------------------------
  if (error) {
    return (
      <div
        data-testid="similar-sessions-error"
        className={`similar-sessions-panel p-4 ${className}`}
        role="alert"
      >
        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          <Sparkles size={16} className="text-purple-500" />
          Similar Sessions
        </h3>
        <div className="text-center py-4">
          <AlertCircle
            className="mx-auto h-8 w-8 text-amber-500 mb-2"
            aria-hidden="true"
          />
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
            Failed to load similar sessions
          </p>
          <button
            onClick={refetch}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <RefreshCw size={14} />
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render empty state
  // ---------------------------------------------------------------------------
  if (similarSessions.length === 0) {
    return (
      <div className={`similar-sessions-panel p-4 ${className}`}>
        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          <Sparkles size={16} className="text-purple-500" />
          Similar Sessions
        </h3>
        <div className="text-center py-4">
          <Link2
            className="mx-auto h-8 w-8 text-gray-400 dark:text-gray-600 mb-2"
            aria-hidden="true"
          />
          <p className="text-sm text-gray-500 dark:text-gray-400">
            No similar sessions found
          </p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render similar sessions
  // ---------------------------------------------------------------------------
  return (
    <div className={`similar-sessions-panel p-4 ${className}`}>
      <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
        <Sparkles size={16} className="text-purple-500" />
        Similar Sessions
      </h3>
      <div className="space-y-2" aria-label="Similar sessions">
        {similarSessions.map((session) => {
          const sessionName =
            sessionNames[session.sessionId] || session.sessionId;
          const scorePercent = Math.round(session.similarityScore * 100);

          return (
            <button
              key={session.sessionId}
              type="button"
              className="w-full text-left group p-2 rounded-md border border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/10 cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500"
              onClick={() => onSessionSelect?.(session.sessionId)}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate flex-1">
                  {sessionName}
                </span>
                <span className="text-xs font-medium text-purple-600 dark:text-purple-400 ml-2">
                  {scorePercent}%
                </span>
              </div>
              {session.commonTopics.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {session.commonTopics.map((topic) => (
                    <span
                      key={topic}
                      className="inline-flex items-center px-1.5 py-0.5 text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default SimilarSessionsPanel;
